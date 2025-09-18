# services/results_api/app.py

import os
import json
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, UUID4
from sqlalchemy import create_engine, text, func
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import redis # <-- Import the standard sync redis client
import redis.asyncio as redis_async # Use async redis client for the background task
from starlette_prometheus import metrics, PrometheusMiddleware # <-- 1. Import

# --- Configuration & Initialization ---
load_dotenv()
app = FastAPI(title="Results API & Real-Time Hub")
app.add_middleware(PrometheusMiddleware, app_name="results_api")
app.add_route("/metrics", metrics)      # <-- 3. Add the /metrics endpoint

# --- CORS Middleware ---
origins = ["http://localhost", "http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Database Connection ---
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

# Create a synchronous Redis client for our regular API endpoints
redis_client = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=6379, decode_responses=True)

# --- WebSocket Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# --- Redis Subscriber Background Task ---
async def redis_subscriber():
    """Listens to Redis Pub/Sub and broadcasts messages to connected clients."""
    r = await redis.from_url(f"redis://{os.getenv('REDIS_HOST', 'redis')}", encoding="utf-8", decode_responses=True)
    async with r.pubsub() as pubsub:
        await pubsub.subscribe("ticket_updates")
        print("Subscribed to 'ticket_updates' channel.")
        while True:
            try:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message:
                    await manager.broadcast(message['data'])
            except asyncio.CancelledError:
                print("Subscriber task cancelled.")
                break
            except Exception as e:
                print(f"🚨 Redis subscriber error: {e}")
                await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    # Start the Redis subscriber as a background task
    asyncio.create_task(redis_subscriber())

# --- NEW HELPER FUNCTION TO PUBLISH UPDATES ---
def publish_ticket_update(ticket_id):
    """Fetches full ticket data and publishes it to the Redis channel."""
    try:
        with engine.connect() as connection:
            stmt = text("SELECT * FROM tickets WHERE ticket_id = :ticket_id")
            ticket_record = connection.execute(stmt, {"ticket_id": str(ticket_id)}).first()

            if ticket_record:
                ticket_dict = dict(ticket_record._mapping)
                for key, value in ticket_dict.items():
                    if hasattr(value, 'isoformat'):
                        ticket_dict[key] = value.isoformat()
                    elif hasattr(value, 'hex'):
                        ticket_dict[key] = str(value)
                
                redis_client.publish("ticket_updates", json.dumps(ticket_dict))
                print(f"📢 Published manual review update for ticket {ticket_id}")
    except Exception as e:
        print(f"🚨 ERROR publishing review update for {ticket_id}: {e}")

# --- Pydantic Models ---
class TicketResult(BaseModel):
    ticket_id: UUID4
    status: str
    subject: str | None = None
    description: str | None = None
    predicted_category: str | None = None
    predicted_priority: str | None = None
    final_category: str | None = None
    final_priority: str | None = None
    created_at: datetime | None = None
    prediction_confidence_category: float | None = None
    prediction_confidence_priority: float | None = None

class ReviewLabel(BaseModel):
    final_category: str
    final_priority: str

# --- API Endpoints ---

@app.get("/tickets/recent", response_model=list[TicketResult])
def get_recent_tickets():
    """Fetches the 100 most recently created tickets."""
    with engine.connect() as connection:
        stmt = text("SELECT * FROM tickets ORDER BY created_at DESC LIMIT 100")
        results = connection.execute(stmt).fetchall()
        return [TicketResult(**row._asdict()) for row in results]

@app.get("/stats")
def get_stats():
    """Calculates and returns live statistics about the system."""
    with engine.connect() as connection:
        total_tickets = connection.execute(text("SELECT COUNT(*) FROM tickets")).scalar_one()
        
        status_counts_res = connection.execute(
            text("SELECT status, COUNT(*) as count FROM tickets GROUP BY status")
        ).fetchall()
        status_counts = {row.status: row.count for row in status_counts_res}

        one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
        throughput = connection.execute(
            text("SELECT COUNT(*) FROM tickets WHERE created_at >= :time"),
            {"time": one_minute_ago}
        ).scalar_one()

        category_counts_res = connection.execute(
            text("SELECT final_category, COUNT(*) as count FROM tickets WHERE final_category IS NOT NULL GROUP BY final_category")
        ).fetchall()
        category_counts = {row.final_category: row.count for row in category_counts_res}

        return {
            "total_tickets": total_tickets,
            "status_breakdown": {
                "processing": status_counts.get("PROCESSING", 0),
                "completed": status_counts.get("COMPLETED", 0),
                "pending_review": status_counts.get("PENDING_REVIEW", 0)
            },
            "throughput_last_minute": throughput,
            "category_breakdown": category_counts
        }

# --- Keep existing endpoints for review queue and ticket details ---
@app.get("/tickets/{ticket_id}", response_model=TicketResult)
def get_ticket_result(ticket_id: UUID4):
    with engine.connect() as connection:
        stmt = text("SELECT * FROM tickets WHERE ticket_id = :ticket_id")
        result = connection.execute(stmt, {"ticket_id": str(ticket_id)}).first()
        if not result:
            raise HTTPException(status_code=404, detail="Ticket not found")
        return TicketResult(**result._asdict())

@app.get("/review-queue", response_model=list[TicketResult])
def get_review_queue():
    with engine.connect() as connection:
        stmt = text("SELECT * FROM tickets WHERE status = 'PENDING_REVIEW' ORDER BY created_at ASC")
        results = connection.execute(stmt).fetchall()
        return [TicketResult(**row._asdict()) for row in results]

# --- MODIFIED /review/{ticket_id} ENDPOINT ---
@app.post("/review/{ticket_id}")
def submit_review(ticket_id: UUID4, labels: ReviewLabel):
    with engine.connect() as connection:
        stmt = text("""
            UPDATE tickets
            SET status = 'COMPLETED', final_category = :final_category, final_priority = :final_priority, reviewed_at = :reviewed_at
            WHERE ticket_id = :ticket_id AND status = 'PENDING_REVIEW'
            RETURNING ticket_id;
        """)
        result = connection.execute(stmt, {
            "ticket_id": str(ticket_id), "final_category": labels.final_category,
            "final_priority": labels.final_priority, "reviewed_at": datetime.utcnow()
        }).first()
        connection.commit()

        if not result:
            raise HTTPException(status_code=404, detail="Ticket not found or already reviewed")
        
        print(f"✅ Review for ticket {ticket_id} submitted successfully to DB.") # <-- ADDED LOG
        
        # NOW, PUBLISH THE UPDATE FOR A REAL-TIME RESPONSE
        publish_ticket_update(ticket_id)

        return {"message": "Review submitted successfully", "ticket_id": ticket_id}

# --- NEW: WebSocket Endpoint ---
@app.websocket("/ws/ticket-updates")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    print(f"New client connected. Total clients: {len(manager.active_connections)}")
    try:
        while True:
            # We keep the connection alive by waiting for a message, but don't need to do anything with it.
            # The broadcast will happen from the Redis subscriber task.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"Client disconnected. Total clients: {len(manager.active_connections)}")