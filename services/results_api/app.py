# services/results_api/app.py

import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, UUID4
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables from the .env file in the project root
load_dotenv()

# --- Configuration & Initialization ---
app = FastAPI(title="Results API")

# Database Connection (uses environment variables set in docker-compose)
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)

# --- Pydantic Models for Response Validation ---
class TicketResult(BaseModel):
    ticket_id: UUID4
    status: str
    predicted_category: str | None = None
    predicted_priority: str | None = None
    final_category: str | None = None
    final_priority: str | None = None

# --- API Endpoint ---
@app.get("/tickets/{ticket_id}", response_model=TicketResult)
def get_ticket_result(ticket_id: UUID4):
    """
    Polls the database for the status and result of a specific ticket.
    """
    try:
        with engine.connect() as connection:
            # Prepare SQL statement to prevent SQL injection
            stmt = text("""
                SELECT status, predicted_category, predicted_priority, final_category, final_priority
                FROM tickets
                WHERE ticket_id = :ticket_id
            """)
            result = connection.execute(stmt, {"ticket_id": str(ticket_id)}).first()

            if not result:
                raise HTTPException(status_code=404, detail="Ticket not found")

            # Map the database row to our Pydantic response model
            status_data = {
                "ticket_id": ticket_id,
                "status": result.status,
                "predicted_category": result.predicted_category,
                "predicted_priority": result.predicted_priority,
                "final_category": result.final_category,
                "final_priority": result.final_priority,
            }
            return TicketResult(**status_data)

    except Exception as e:
        print(f"🚨 An error occurred while fetching ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")