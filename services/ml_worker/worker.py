# services/ml_worker/worker.py

import os
import time
import redis
import pandas as pd
import json # <-- Import json

from preprocess import preprocess_data
# <-- Import the new get_ticket_by_id function
from database import get_db_session, get_or_create_model_record, create_ticket_entry, update_ticket_to_completed, update_ticket_for_review, get_ticket_by_id
from models import load_champion_models

# --- Configuration ---
# ... (keep existing configuration) ...
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.70))
STREAM_NAME = 'ticket_stream'
GROUP_NAME = 'ml_processing_group'
WORKER_NAME = f'worker_{os.getpid()}'
REDIS_PUB_CHANNEL = "ticket_updates" # <-- NEW: Pub/Sub channel name

# --- Redis Connection ---
r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)

# --- NEW HELPER FUNCTION ---
def publish_ticket_update(ticket_id):
    """Fetches the latest ticket data and publishes it to the Redis channel."""
    db_session = next(get_db_session())
    try:
        # Use the newly created function to get the full ticket record
        ticket_record = get_ticket_by_id(db_session, ticket_id)
        if ticket_record:
            # Convert the SQLAlchemy Row object to a dictionary
            ticket_dict = dict(ticket_record._mapping)
            
            # Serialize fields that are not JSON-native (UUIDs, datetimes)
            for key, value in ticket_dict.items():
                if hasattr(value, 'isoformat'): # Datetime objects
                    ticket_dict[key] = value.isoformat()
                elif hasattr(value, 'hex'): # UUID objects
                    ticket_dict[key] = str(value)

            # Publish the serialized dictionary as a JSON string
            r.publish(REDIS_PUB_CHANNEL, json.dumps(ticket_dict))
            print(f"📢 Published update for ticket {ticket_id} to '{REDIS_PUB_CHANNEL}'")
    except Exception as e:
        print(f"🚨 ERROR publishing ticket update for {ticket_id}: {e}")
    finally:
        db_session.close()

# --- MODIFIED MAIN LOOP ---
print("🚀 Worker starting...")
try:
    r.xgroup_create(STREAM_NAME, GROUP_NAME, id='0', mkstream=True)
    print(f"Consumer group '{GROUP_NAME}' created.")
except redis.exceptions.ResponseError:
    print(f"Consumer group '{GROUP_NAME}' already exists.")

while True:
    db_session = None
    message_id = 'N/A'
    ticket_id = None
    try:
        response = r.xreadgroup(GROUP_NAME, WORKER_NAME, {STREAM_NAME: '>'}, count=1, block=0)
        if not response:
            continue

        message_id = response[0][1][0][0]
        data = response[0][1][0][1]
        ticket_id, subject, description = data['ticket_id'], data['subject'], data['description']
        
        print(f"📨 Received ticket {ticket_id}. Processing...")

        # ... (keep steps 1 and 2: load models, get model records) ...
        cat_model_info, pri_model_info = load_champion_models()
        if not all([cat_model_info["model"], pri_model_info["model"]]):
            raise Exception("One or more champion models could not be loaded. Skipping ticket.")

        db_session = next(get_db_session())
        cat_model_id = get_or_create_model_record(db_session, cat_model_info["name"], cat_model_info["version"])
        pri_model_id = get_or_create_model_record(db_session, pri_model_info["name"], pri_model_info["version"])

        # 3. Create initial ticket entry in DB
        create_ticket_entry(db_session, ticket_id, subject, description, cat_model_id, pri_model_id)
        publish_ticket_update(ticket_id) # <-- BROADCAST EVENT

        # ... (keep steps 4 and 5: preprocess data, make predictions) ...
        input_df = pd.DataFrame([{"subject": subject, "description": description}])
        processed_df = preprocess_data(input_df)
        
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

        publish_ticket_update(ticket_id) # <-- BROADCAST EVENT
        
        # 7. Acknowledge the message
        r.xack(STREAM_NAME, GROUP_NAME, message_id)
        print(f"✅ Acknowledged message {message_id}")

    except Exception as e:
        print(f"🚨 An error occurred processing message {message_id}: {e}")
        time.sleep(5)
    
    finally:
        if db_session:
            db_session.close()