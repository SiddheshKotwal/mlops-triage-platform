import os
import redis
import uuid
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware # <-- 1. IMPORT THIS
from prometheus_fastapi_instrumentator import Instrumentator

# --- Configuration & Initialization ---

app = FastAPI(title="Ingestion API")
# instrument and expose
Instrumentator().instrument(app).expose(app)

# --- 2. ADD THE CORS MIDDLEWARE ---
origins = [
    "http://localhost",
    "http://localhost:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to the Redis service. 
# The hostname is 'redis', which is the service name in our docker-compose.yml file.
# Docker's internal networking resolves this hostname to the Redis container's IP.
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)
STREAM_NAME = 'ticket_stream'

# --- Data Validation Model ---

class Ticket(BaseModel):
    """
    This is a Pydantic model. FastAPI uses it to automatically validate
    that the incoming request body has a 'subject' and a 'description'.
    If not, it will automatically return a 422 Unprocessable Entity error.
    """
    subject: str
    description: str

# --- API Endpoint ---

@app.post("/tickets")
def create_ticket(ticket: Ticket):
    """
    Receives a ticket, generates a unique ID, and adds it to the Redis Stream
    for asynchronous processing by the ML Worker.
    """
    try:
        # Generate a unique ID for the ticket
        ticket_id = str(uuid.uuid4())
        
        # This is the payload that the ML Worker will receive.
        # We send the subject and description separately as this is what the worker expects.
        ticket_data = {
            "ticket_id": ticket_id,
            "subject": ticket.subject,
            "description": ticket.description
        }

        # Add the new ticket data to our Redis Stream.
        # The '*' tells Redis to auto-generate a unique message ID for this entry.
        r.xadd(STREAM_NAME, ticket_data, '*')
        
        print(f"✅ Added ticket {ticket_id} to the stream.")

        # Immediately return a success response to the client.
        # The client does not have to wait for the ML prediction to finish.
        return {"message": "Ticket received for processing", "ticket_id": ticket_id}

    except Exception as e:
        # If Redis is down or there's another issue, return a server error.
        print(f"🚨 ERROR: Could not add ticket to stream. Error: {e}")
        return {"error": "Failed to enqueue ticket for processing"}, 500


'''
### The Workflow: How a Ticket is Ingested

This workflow is designed to be extremely fast, typically responding in just a few milliseconds.

1.  **Request Sent:** An external client (or our load testing script) sends an `HTTP POST` request to `http://localhost:8001/tickets` with a JSON body like:
    ```json
    {
      "subject": "Cannot connect to the VPN",
      "description": "My VPN client is giving me a 'connection timed out' error."
    }
    
'''