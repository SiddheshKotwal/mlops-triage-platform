# services/ml_worker/worker.py

import os
import time
import redis
import pandas as pd
import json
from prometheus_client import start_http_server, Counter, Histogram

from preprocess import preprocess_data
from database import get_db_session, get_or_create_model_record, create_ticket_entry, update_ticket_to_completed, update_ticket_for_review, get_ticket_by_id
from models import load_champion_models

# --- Configuration ---
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.85))
STREAM_NAME = 'ticket_stream'
GROUP_NAME = 'ml_processing_group'
WORKER_NAME = f'worker_{os.getpid()}'
REDIS_PUB_CHANNEL = "ticket_updates"

# --- Prometheus Metrics Definition ---
TICKETS_PROCESSED_TOTAL = Counter(
    'tickets_processed_total',
    'Total number of tickets processed',
    ['final_status']  # Labels: 'completed_auto', 'pending_review'
)
TICKET_PROCESSING_LATENCY = Histogram(
    'ticket_processing_latency_seconds',
    'Time spent processing a ticket'
)
MODEL_CONFIDENCE = Histogram(
    'model_confidence_score',
    'Distribution of model prediction confidence scores',
    ['model_type']  # Labels: 'category', 'priority'
)

# --- Redis Connection ---
r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)

# --- Helper Function ---
def publish_ticket_update(ticket_id):
    """Fetches the latest ticket data and publishes it to the Redis channel."""
    db_session = next(get_db_session())
    try:
        ticket_record = get_ticket_by_id(db_session, ticket_id)
        if ticket_record:
            ticket_dict = dict(ticket_record._mapping)
            
            # Serialize fields that are not JSON-native
            for key, value in ticket_dict.items():
                if hasattr(value, 'isoformat'):  # Datetime objects
                    ticket_dict[key] = value.isoformat()
                elif hasattr(value, 'hex'):  # UUID objects
                    ticket_dict[key] = str(value)

            r.publish(REDIS_PUB_CHANNEL, json.dumps(ticket_dict))
            print(f"📢 Published update for ticket {ticket_id} to '{REDIS_PUB_CHANNEL}'")
    except Exception as e:
        print(f"🚨 ERROR publishing ticket update for {ticket_id}: {e}")
    finally:
        db_session.close()


# --- Main Application Execution ---
if __name__ == "__main__":
    print("🚀 ML Worker starting...")
    
    # Start a server on port 8000 to expose Prometheus metrics
    start_http_server(8000)
    print("📈 Prometheus metrics server started on port 8000.")

    # Create Redis consumer group if it doesn't exist
    try:
        r.xgroup_create(STREAM_NAME, GROUP_NAME, id='0', mkstream=True)
        print(f"Consumer group '{GROUP_NAME}' created.")
    except redis.exceptions.ResponseError:
        print(f"Consumer group '{GROUP_NAME}' already exists.")

    # The main processing loop
    while True:
        db_session = None
        message_id = 'N/A'
        ticket_id = None
        try:
            # Block until a new message is received from the Redis Stream
            response = r.xreadgroup(GROUP_NAME, WORKER_NAME, {STREAM_NAME: '>'}, count=1, block=0)
            if not response:
                continue

            message_id = response[0][1][0][0]
            data = response[0][1][0][1]
            ticket_id, subject, description = data['ticket_id'], data['subject'], data['description']
            
            print(f"📨 Received ticket {ticket_id}. Processing...")

            # Use a context manager to automatically track processing time
            with TICKET_PROCESSING_LATENCY.time():
                # 1. Load Champion Models (from cache or MLflow)
                cat_model_info, pri_model_info = load_champion_models()
                if not all([cat_model_info["model"], pri_model_info["model"]]):
                    raise Exception("One or more champion models could not be loaded.")

                # 2. Get DB Session and Model Records
                db_session = next(get_db_session())
                cat_model_id = get_or_create_model_record(db_session, cat_model_info["name"], cat_model_info["version"])
                pri_model_id = get_or_create_model_record(db_session, pri_model_info["name"], pri_model_info["version"])

                # 3. Create initial ticket entry in DB and publish 'PROCESSING' status
                create_ticket_entry(db_session, ticket_id, subject, description, cat_model_id, pri_model_id)
                publish_ticket_update(ticket_id)

                # 4. Preprocess data and make predictions
                input_df = pd.DataFrame([{"subject": subject, "description": description}])
                processed_df = preprocess_data(input_df)
                
                category_pred = cat_model_info["model"].predict(processed_df['processed_text'])[0]
                category_prob = max(cat_model_info["model"].predict_proba(processed_df['processed_text'])[0])
                
                priority_pred = pri_model_info["model"].predict(processed_df['processed_text'])[0]
                priority_prob = max(pri_model_info["model"].predict_proba(processed_df['processed_text'])[0])
                
                avg_confidence = (category_prob + priority_prob) / 2
                print(f"   - Predictions: Cat='{category_pred}', Pri='{priority_pred}'. Confidence={avg_confidence:.2f}")

                # 5. Observe Prometheus metrics for model performance
                MODEL_CONFIDENCE.labels(model_type='category').observe(category_prob)
                MODEL_CONFIDENCE.labels(model_type='priority').observe(priority_prob)

                # 6. Execute HITL Logic and update DB
                final_status = ''
                if avg_confidence >= CONFIDENCE_THRESHOLD:
                    update_ticket_to_completed(db_session, ticket_id, category_pred, priority_pred, category_prob, priority_prob)
                    print(f"   - High confidence. Ticket {ticket_id} marked as COMPLETED.")
                    final_status = 'completed_auto'
                else:
                    update_ticket_for_review(db_session, ticket_id, category_pred, priority_pred, category_prob, priority_prob)
                    print(f"   - Low confidence. Ticket {ticket_id} sent for HUMAN REVIEW.")
                    final_status = 'pending_review'

                # 7. Increment final status counter and publish final update
                TICKETS_PROCESSED_TOTAL.labels(final_status=final_status).inc()
                publish_ticket_update(ticket_id)

            # 8. Acknowledge the message in the Redis Stream
            r.xack(STREAM_NAME, GROUP_NAME, message_id)
            print(f"✅ Acknowledged message {message_id}")

        except Exception as e:
            print(f"🚨 An error occurred processing message {message_id}: {e}")
            time.sleep(5) # Wait before retrying
        
        finally:
            if db_session:
                db_session.close()