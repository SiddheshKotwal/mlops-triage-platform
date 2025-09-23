# retraining_pipeline/retrain.py

import argparse
import mlflow
import time
import pandas as pd
from dotenv import load_dotenv
from mlflow.tracking import MlflowClient
from mlflow.exceptions import MlflowException
from sqlalchemy import update
import os

# Import our project modules
from data import get_training_data
from preprocess import preprocess_data
from experiment import find_best_model
from db.engine import engine
from db.database_setup import tickets
import config_category as config_cat
import config_priority as config_pri

# --- MODIFIED `run` FUNCTION ---
# It no longer fetches data or updates the database.
# It now accepts a DataFrame as an argument.
def run(model_type: str, processed_df: pd.DataFrame):
    """
    Main function to run the retraining, evaluation, and promotion pipeline for a single model type.
    """
    mlflow_tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow.set_tracking_uri(mlflow_tracking_uri)
    print(f"\n--- MLflow tracking URI set to: {mlflow_tracking_uri} ---")

    client = MlflowClient()

    # --- Configuration and MLflow Setup ---
    if model_type == 'category':
        config = config_cat
        experiment_name = "ticket_category_retraining_v1"
        registry_name = "ticket_category_classifier"
    elif model_type == 'priority':
        config = config_pri
        experiment_name = "ticket_priority_retraining_v1"
        registry_name = "ticket_priority_classifier"
    else:
        # This case should not be hit if called from main()
        raise ValueError("Invalid model_type specified.")

    print(f"--- Starting Retraining Pipeline for: {model_type.upper()} ---")

    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        print(f"Creating new experiment: {experiment_name}")
        mlflow.create_experiment(experiment_name)
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name=f"Retraining Job - {model_type} - {time.strftime('%Y%m%d-%H%M%S')}") as parent_run:
        
        mlflow.log_metric("dataset_size", len(processed_df))

        # --- Step 2: Run Experiment ---
        print("\nStep 2: Running experiment to find the best challenger model...")
        challenger_run_id, challenger_f1_score = find_best_model(
            df=processed_df,
            target_column=model_type,
            vectorizers=config.VECTORIZERS,
            classifiers=config.CLASSIFIERS,
            param_grids=config.PARAM_GRIDS
        )
        
        if not challenger_run_id:
            print(f"\nNo successful challenger models were trained for {model_type}. Skipping promotion.")
            mlflow.set_tag("status", "TRAINING_FAILED")
            return
        
        mlflow.log_metric("challenger_f1_macro", challenger_f1_score)

        # --- Step 3: Champion vs. Challenger Showdown ---
        print(f"\nStep 3: Comparing challenger (F1: {challenger_f1_score:.4f}) with champion model...")
        
        champion_f1_score = -1.0
        try:
            champion_version_obj = client.get_model_version_by_alias(registry_name, "champion")
            champion_run = client.get_run(champion_version_obj.run_id)
            champion_f1_score = champion_run.data.metrics.get("f1_macro", -1.0)
            print(f"Found champion: Version {champion_version_obj.version} with f1_macro: {champion_f1_score:.4f}")
        except MlflowException:
            print("No model with alias 'champion' found. The challenger will be promoted.")
        
        mlflow.log_metric("champion_f1_macro", champion_f1_score)

        # --- Step 4: Model Registration and Promotion ---
        print("\nStep 4: Registering and promoting model...")
        model_uri = f"runs:/{challenger_run_id}/model"
        
        try:
            client.create_registered_model(registry_name)
        except MlflowException:
            pass 
        
        challenger_version_obj = client.create_model_version(
            name=registry_name,
            source=model_uri,
            run_id=challenger_run_id,
            description=f"Challenger model with F1 Macro: {challenger_f1_score:.4f}"
        )
        print(f"Registered challenger as Version {challenger_version_obj.version}.")

        # For the first run or if challenger is better, promote it
        if challenger_f1_score > champion_f1_score:
            print(f"*** PROMOTION: Challenger ({challenger_f1_score:.4f}) is better than Champion ({champion_f1_score:.4f}). ***")
            print(f"Setting alias 'champion' on new Version {challenger_version_obj.version}.")
            mlflow.set_tag("promotion_status", "PROMOTED")
            client.set_registered_model_alias(registry_name, "champion", challenger_version_obj.version)
        else:
            print(f"--- NO PROMOTION: Champion ({champion_f1_score:.4f}) is still better. ---")
            mlflow.set_tag("promotion_status", "CHAMPION_RETAINED")

    print(f"--- Pipeline for {model_type.upper()} Finished ---")

# --- NEW `main` FUNCTION TO ORCHESTRATE THE ENTIRE PROCESS ---
def main():
    """
    Main orchestrator for the retraining pipeline.
    """
    parser = argparse.ArgumentParser(description="Run the model retraining pipeline.")
    parser.add_argument("model_type", choices=['category', 'priority', 'all'], help="The type of model to retrain.")
    args = parser.parse_args()

    # --- STEP 1: DATA PREPARATION (Done ONCE) ---
    print("--- Step 1: Fetching and preprocessing data for all models... ---")
    raw_df, ticket_ids_to_update = get_training_data()
        
    if raw_df.empty:
        print("No new data to train on. Exiting pipeline.")
        return
            
    processed_df = preprocess_data(raw_df)
    print(f"Data ready. Total records for training: {len(processed_df)}")

    # --- STEP 2: MODEL TRAINING ---
    # Run the training process for the selected model type(s)
    if args.model_type in ['category', 'all']:
        run(model_type='category', processed_df=processed_df)
            
    if args.model_type in ['priority', 'all']:
        run(model_type='priority', processed_df=processed_df)

    # --- STEP 3: MARK DATA AS USED (Done ONCE at the end) ---
    if ticket_ids_to_update:
        print(f"\n--- Step 3: Marking {len(ticket_ids_to_update)} tickets as used for retraining... ---")
        try:
            with engine.connect() as connection:
                stmt = (
                    update(tickets)
                    .where(tickets.c.ticket_id.in_(ticket_ids_to_update))
                    .values(used_for_retraining=True)
                )
                connection.execute(stmt)
                connection.commit()
            print("Successfully updated 'used_for_retraining' flags in the database.")
        except Exception as e:
            print(f"ERROR: Failed to update 'used_for_retraining' flags. Error: {e}")

# --- Main execution block ---
if __name__ == "__main__":
    main()