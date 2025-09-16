import pandas as pd
from sqlalchemy.sql import select

# Import the shared database engine and table schemas
from db.engine import engine
from db.database_setup import original_training_data, tickets

def get_training_data() -> tuple[pd.DataFrame, list]:
    """
    Fetches all data required for model retraining from the database.

    Returns:
        tuple: A tuple containing:
            - pd.DataFrame: The combined training data.
            - list: A list of ticket_ids for the new data that needs to be flagged.
    """
    print("Connecting to the database to fetch training data...")
    new_ticket_ids = []
    with engine.connect() as connection:
        # Query 1: Fetch the entire original dataset
        stmt_original = select(
            original_training_data.c.subject,
            original_training_data.c.description,
            original_training_data.c.category,
            original_training_data.c.priority
        )
        try:
            df_original = pd.read_sql(stmt_original, connection)
            print(f"Successfully fetched {len(df_original)} records from the original dataset.")
        except Exception as e:
            print(f"Error fetching original data: {e}")
            df_original = pd.DataFrame()

        # Query 2: Fetch new, human-verified tickets
        stmt_new = select(
            tickets.c.ticket_id,  # <-- ADDED THIS LINE
            tickets.c.subject,
            tickets.c.description,
            tickets.c.final_category.label('category'),
            tickets.c.final_priority.label('priority')
        ).where(
            tickets.c.used_for_retraining == False,
            tickets.c.reviewed_at.isnot(None)
        )
        try:
            df_new_with_ids = pd.read_sql(stmt_new, connection)
            print(f"Successfully fetched {len(df_new_with_ids)} new human-verified records for retraining.")
            if not df_new_with_ids.empty:
                # Store the IDs to be returned, and then drop the column for training
                new_ticket_ids = df_new_with_ids['ticket_id'].tolist()
                df_new = df_new_with_ids.drop(columns=['ticket_id'])
            else:
                df_new = pd.DataFrame()
        except Exception as e:
            print(f"Error fetching new data: {e}")
            df_new = pd.DataFrame()

    # Combine the two DataFrames
    if not df_original.empty or not df_new.empty:
        combined_df = pd.concat([df_original, df_new], ignore_index=True)
        print(f"Total training data size: {len(combined_df)} records.")
        return combined_df, new_ticket_ids
    else:
        print("No training data found.")
        return pd.DataFrame(), []

# This block is updated to handle the new return signature
if __name__ == "__main__":
    print("--- Running data.py as a standalone script for testing ---")
    training_data, ids_to_update = get_training_data()

    if not training_data.empty:
        print("\n--- Test Passed: Data fetched successfully! ---")
        print("Columns in the final DataFrame:", training_data.columns.tolist())
        print("Shape of the final DataFrame:", training_data.shape)
        print(f"\nNumber of new ticket IDs to be updated: {len(ids_to_update)}")
        if ids_to_update:
            print("First 5 IDs:", ids_to_update[:5])
    else:
        print("\n--- Test Result: No data was returned.")

