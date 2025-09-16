import os
import time
import mlflow
from mlflow.tracking import MlflowClient

# --- Configuration ---
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
CATEGORY_MODEL_NAME = "ticket_category_classifier"
PRIORITY_MODEL_NAME = "ticket_priority_classifier"
CACHE_EXPIRATION_SECONDS = 3600  # 10 minutes

# --- In-memory cache for models ---
model_cache = {
    "category": {"model": None, "version": None, "timestamp": 0},
    "priority": {"model": None, "version": None, "timestamp": 0}
}

client = MlflowClient(tracking_uri=os.getenv("MLFLOW_TRACKING_URI"))

def load_champion_models():
    """
    Loads the latest 'champion' aliased models from the MLflow Model Registry.
    Uses a time-based cache to avoid reloading on every request.
    Returns the loaded model objects and their version details.
    """
    now = time.time()
    
    # --- Load Category Model ---
    if now - model_cache["category"]["timestamp"] > CACHE_EXPIRATION_SECONDS:
        print("Category model cache expired. Fetching latest champion from MLflow...")
        try:
            latest_champion = client.get_model_version_by_alias(CATEGORY_MODEL_NAME, "champion")
            model_uri = latest_champion.source
            loaded_model = mlflow.sklearn.load_model(model_uri)
            
            model_cache["category"]["model"] = loaded_model
            model_cache["category"]["version"] = latest_champion.version
            model_cache["category"]["timestamp"] = now
            print(f"Loaded new category model version: {latest_champion.version}")
        except Exception as e:
            print(f"🚨 ERROR: Could not load category model from MLflow: {e}")
            # Keep using the old cached model if available
    
    # --- Load Priority Model ---
    if now - model_cache["priority"]["timestamp"] > CACHE_EXPIRATION_SECONDS:
        print("Priority model cache expired. Fetching latest champion from MLflow...")
        try:
            latest_champion = client.get_model_version_by_alias(PRIORITY_MODEL_NAME, "champion")
            model_uri = latest_champion.source
            loaded_model = mlflow.sklearn.load_model(model_uri)

            model_cache["priority"]["model"] = loaded_model
            model_cache["priority"]["version"] = latest_champion.version
            model_cache["priority"]["timestamp"] = now
            print(f"Loaded new priority model version: {latest_champion.version}")
        except Exception as e:
            print(f"🚨 ERROR: Could not load priority model from MLflow: {e}")

    # Return the currently cached models and their versions
    category_model_info = {"model": model_cache["category"]["model"], "version": model_cache["category"]["version"], "name": CATEGORY_MODEL_NAME}
    priority_model_info = {"model": model_cache["priority"]["model"], "version": model_cache["priority"]["version"], "name": PRIORITY_MODEL_NAME}

    return category_model_info, priority_model_info