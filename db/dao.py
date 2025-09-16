# src/db/dao.py

from .engine import engine # Assumes you have an engine.py
from .database_setup import tickets, original_training_data # Import table definitions
from sqlalchemy.sql import select, update, insert

# --- Ticket Operations for APIs and Workers ---

def create_ticket(ticket_id, subject, description):
    """Inserts a new ticket into the DB with 'PROCESSING' status."""
    with engine.connect() as conn:
        stmt = insert(tickets).values(
            ticket_id=ticket_id,
            subject=subject,
            description=description,
            status='PROCESSING'
        )
        conn.execute(stmt)
        conn.commit()

def update_ticket_as_pending_review(ticket_id, predicted_cat, predicted_pri, cat_confidence, pri_confidence, cat_model_id, pri_model_id):
    """Updates a ticket's status to PENDING_REVIEW after a low-confidence prediction."""
    with engine.connect() as conn:
        stmt = update(tickets).where(tickets.c.ticket_id == ticket_id).values(
            status='PENDING_REVIEW',
            predicted_category=predicted_cat,
            predicted_priority=predicted_pri,
            prediction_confidence_category=cat_confidence,
            prediction_confidence_priority=pri_confidence,
            category_model_id=cat_model_id,
            priority_model_id=pri_model_id
        )
        conn.execute(stmt)
        conn.commit()

def get_ticket_status(ticket_id):
    """Fetches the status and final labels for a given ticket_id."""
    with engine.connect() as conn:
        stmt = select(
            tickets.c.status,
            tickets.c.final_category,
            tickets.c.final_priority
        ).where(tickets.c.ticket_id == ticket_id)
        result = conn.execute(stmt).first()
        return result

# --- Operations for the Retraining Pipeline ---

def get_data_for_retraining():
    """Fetches the original dataset and all new human-verified tickets."""
    with engine.connect() as conn:
        # Get original data
        stmt_original = select(
            original_training_data.c.subject,
            original_training_data.c.description,
            original_training_data.c.category,
            original_training_data.c.priority
        )
        original_data = conn.execute(stmt_original).fetchall()

        # Get new verified data
        stmt_new = select(
            tickets.c.subject,
            tickets.c.description,
            tickets.c.final_category.label('category'),
            tickets.c.final_priority.label('priority')
        ).where(
            tickets.c.used_for_retraining == False,
            tickets.c.reviewed_at.isnot(None)
        )
        new_data = conn.execute(stmt_new).fetchall()

        return original_data + new_data