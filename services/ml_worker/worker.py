import os
import time
import redis
import pandas as pd

# Add the parent directory ('src') to the Python path to allow imports
from preprocess import preprocess_data
from database import get_db_session, get_or_create_model_record, create_ticket_entry, update_ticket_to_completed, update_ticket_for_review
from models import load_champion_models

# --- Configuration ---
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.90))
STREAM_NAME = 'ticket_stream'
GROUP_NAME = 'ml_processing_group'
WORKER_NAME = f'worker_{os.getpid()}'

# --- Redis Connection ---
r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)

print("🚀 Worker starting...")
try:
    r.xgroup_create(STREAM_NAME, GROUP_NAME, id='0', mkstream=True)
    print(f"Consumer group '{GROUP_NAME}' created.")
except redis.exceptions.ResponseError:
    print(f"Consumer group '{GROUP_NAME}' already exists.")

while True:
    db_session = None
    try:
        response = r.xreadgroup(GROUP_NAME, WORKER_NAME, {STREAM_NAME: '>'}, count=1, block=0)
        if not response:
            continue

        message_id = response[0][1][0][0]
        data = response[0][1][0][1]
        ticket_id, subject, description = data['ticket_id'], data['subject'], data['description']
        
        print(f"📨 Received ticket {ticket_id}. Processing...")

        # --- Core Processing Logic ---
        
        # 1. Load models (from cache or MLflow)
        cat_model_info, pri_model_info = load_champion_models()
        if not all([cat_model_info["model"], pri_model_info["model"]]):
            raise Exception("One or more champion models could not be loaded. Skipping ticket.")

        # 2. Start a database session and get/create model records
        db_session = next(get_db_session())
        cat_model_id = get_or_create_model_record(db_session, cat_model_info["name"], cat_model_info["version"])
        pri_model_id = get_or_create_model_record(db_session, pri_model_info["name"], pri_model_info["version"])

        # 3. Create initial ticket entry in DB
        create_ticket_entry(db_session, ticket_id, subject, description, cat_model_id, pri_model_id)

        # 4. Preprocess data for prediction
        input_df = pd.DataFrame([{"subject": subject, "description": description}])
        processed_df = preprocess_data(input_df)
        
        # 5. Make predictions
        category_pred = cat_model_info["model"].predict(processed_df['processed_text'])[0]
        category_prob = max(cat_model_info["model"].predict_proba(processed_df['processed_text'])[0])
        
        priority_pred = pri_model_info["model"].predict(processed_df['processed_text'])[0]
        priority_prob = max(pri_model_info["model"].predict_proba(processed_df['processed_text'])[0])
        
        avg_confidence = (category_prob + priority_prob) / 2
        print(f"   - Predictions: Cat='{category_pred}', Pri='{priority_pred}'. Confidence={avg_confidence:.2f}")

        # 6. Execute HITL Logic and update DB
        if avg_confidence >= CONFIDENCE_THRESHOLD:
            update_ticket_to_completed(db_session, ticket_id, category_pred, priority_pred, category_prob, priority_prob)
            print(f"   - High confidence. Ticket {ticket_id} marked as COMPLETED.")
        else:
            update_ticket_for_review(db_session, ticket_id, category_pred, priority_pred, category_prob, priority_prob)
            print(f"   - Low confidence. Ticket {ticket_id} sent for HUMAN REVIEW.")

        # 7. Acknowledge the message
        r.xack(STREAM_NAME, GROUP_NAME, message_id)
        print(f"✅ Acknowledged message {message_id}")

    except Exception as e:
        print(f"🚨 An error occurred processing message {message_id if 'message_id' in locals() else 'N/A'}: {e}")
        # Do not acknowledge the message, so it can be retried.
        time.sleep(5)
    
    finally:
        if db_session:
            db_session.close()