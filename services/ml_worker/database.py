import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# --- Database Connection Setup ---
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST", "postgres") # The hostname is the service name in docker-compose
DB_PORT = os.getenv("DB_PORT", "5432")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session():
    """Generator function to provide a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Core Database Functions ---

# --- NEW FUNCTION ---
def get_ticket_by_id(session, ticket_id):
    """Fetches a single, complete ticket record by its ID."""
    stmt = text("SELECT * FROM tickets WHERE ticket_id = :ticket_id")
    result = session.execute(stmt, {"ticket_id": str(ticket_id)}).first()
    return result

def get_or_create_model_record(session, model_name, model_version):
    """
    Checks if a model version is in the 'models' table. If not, it adds it.
    Returns the model_id (primary key).
    """
    # Deactivate any other active models with the same name first
    deactivate_stmt = text("""
        UPDATE models SET is_active = false 
        WHERE model_name = :model_name AND is_active = true;
    """)
    session.execute(deactivate_stmt, {"model_name": model_name})

    # Check for the specific version
    select_stmt = text("SELECT model_id FROM models WHERE model_name = :name AND model_version = :version")
    result = session.execute(select_stmt, {"name": model_name, "version": model_version}).fetchone()

    if result:
        # If it exists, ensure it's active and return its ID
        model_id = result[0]
        activate_stmt = text("UPDATE models SET is_active = true WHERE model_id = :model_id")
        session.execute(activate_stmt, {"model_id": model_id})
        session.commit()
        return model_id
    else:
        # If it doesn't exist, insert it as the new active model
        insert_stmt = text("""
            INSERT INTO models (model_name, model_version, is_active)
            VALUES (:name, :version, true) RETURNING model_id;
        """)
        new_model_id = session.execute(insert_stmt, {"name": model_name, "version": model_version}).scalar_one()
        session.commit()
        return new_model_id

def create_ticket_entry(session, ticket_id, subject, description, cat_model_id, pri_model_id):
    """Inserts a new ticket with status 'PROCESSING'."""
    stmt = text("""
        INSERT INTO tickets (ticket_id, subject, description, status, category_model_id, priority_model_id)
        VALUES (:ticket_id, :subject, :description, 'PROCESSING', :cat_model_id, :pri_model_id)
    """)
    session.execute(stmt, {
        "ticket_id": ticket_id,
        "subject": subject,
        "description": description,
        "cat_model_id": cat_model_id,
        "pri_model_id": pri_model_id
    })
    session.commit()

def update_ticket_to_completed(session, ticket_id, category, priority, cat_confidence, pri_confidence):
    """Updates a ticket to 'COMPLETED' with final predictions."""
    stmt = text("""
        UPDATE tickets SET
            status = 'COMPLETED',
            predicted_category = :cat, final_category = :cat,
            predicted_priority = :pri, final_priority = :pri,
            prediction_confidence_category = :cat_conf,
            prediction_confidence_priority = :pri_conf
        WHERE ticket_id = :ticket_id
    """)
    session.execute(stmt, {
        "ticket_id": ticket_id, "cat": category, "pri": priority,
        "cat_conf": cat_confidence, "pri_conf": pri_confidence
    })
    session.commit()

def update_ticket_for_review(session, ticket_id, category_guess, priority_guess, cat_confidence, pri_confidence):
    """Updates a ticket to 'PENDING_REVIEW' for human-in-the-loop."""
    stmt = text("""
        UPDATE tickets SET
            status = 'PENDING_REVIEW',
            predicted_category = :cat_guess,
            predicted_priority = :pri_guess,
            prediction_confidence_category = :cat_conf,
            prediction_confidence_priority = :pri_conf
        WHERE ticket_id = :ticket_id
    """)
    session.execute(stmt, {
        "ticket_id": ticket_id, "cat_guess": category_guess, "pri_guess": priority_guess,
        "cat_conf": cat_confidence, "pri_conf": pri_confidence
    })
    session.commit()