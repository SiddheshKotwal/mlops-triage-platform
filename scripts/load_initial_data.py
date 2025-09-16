# src/scripts/load_initial_data.py

import kagglehub
import os
import shutil
import pandas as pd
from db.engine import engine

def extract_and_clean_data():
    """
    Performs all the data extraction and cleaning steps from the notebook.
    """
    print("Step 1: Downloading and loading data from KaggleHub...")
    path = kagglehub.dataset_download("tobiasbueck/multilingual-customer-support-tickets")
    df = pd.read_csv(path + "/aa_dataset-tickets-multi-lang-5-2-50-version.csv")

    print("Step 2: Filtering for English tickets...")
    df = df[df['language'] == 'en']

    print("Step 3: Mapping tags to consolidated categories...")
    tag_to_category_mapping = {
        'Security & Compliance': {'security', 'compliance', 'data privacy', 'hipaa', 'vulnerability', 'phishing', 'malware', 'encryption', 'firewall', 'access management', 'data breach', 'unauthorized access', 'security management', 'system integrity', 'data protection', 'regulatory', 'cybersecurity', 'threat', 'intrusion', 'breach', 'confidentiality', 'audit', 'risk management', 'cyberattack', 'cyber threat'},
        'Finance & Billing': {'billing', 'payment', 'refund', 'invoice', 'subscription', 'pricing', 'cost', 'dispute', 'finance', 'investment', 'return', 'transaction', 'payment gateway', 'discount', 'promotion', 'financial', 'expense', 'credit card'},
        'Technical Issues & Bugs': {'bug', 'crash', 'error', 'failure', 'performance', 'slowdown', 'disruption', 'malfunction', 'glitch', 'instability', 'compatibility', 'software conflict', 'app issue', 'system issue', 'technical issue', 'incident', 'update', 'patch', 'version mismatch', 'debugging', 'synchronization error'},
        'Infrastructure & Hardware': {'hardware', 'server', 'network', 'infrastructure', 'cloud', 'aws', 'gcp', 'azure', 'kubernetes', 'docker', 'database', 'platform', 'outage', 'downtime', 'connectivity', 'printer', 'device', 'router', 'storage', 'memory', 'driver', 'saas', 'api', 'load balancing'},
        'User Assistance & How-To': {'support', 'assistance', 'guidance', 'documentation', 'training', 'onboarding', 'configuration', 'installation', 'login', 'password', 'account', 'setup', 'how-to', 'troubleshooting', 'user interface', 'ui', 'usability', 'clarification', 'customer support'},
        'Sales, Product & Marketing Inquiries': {'sales', 'product', 'feature', 'inquiry', 'feedback', 'lead', 'campaign', 'marketing', 'seo', 'brand', 'trial', 'demo', 'pre-sale', 'recommendation'},
    }
    tag_columns = [f'tag_{i}' for i in range(1, 9)]

    def assign_category(row):
        for tag_col in tag_columns:
            tag = row[tag_col]
            if pd.isna(tag): continue
            cleaned_tag = str(tag).lower().strip()
            for category, keywords in tag_to_category_mapping.items():
                if cleaned_tag in keywords:
                    return category
        return 'General Inquiry'

    df['consolidated_category'] = df.apply(assign_category, axis=1)

    print("Step 4: Cleaning the dataset...")
    df = df[~df['consolidated_category'].isin(['General Inquiry'])]
    df.dropna(subset=['subject'], inplace=True)
    
    # Select final raw columns and rename 'body' to 'description'
    final_df = df[['subject', 'body', 'priority', 'consolidated_category']].copy()
    final_df.rename(columns={'body': 'description'}, inplace=True)
    
    final_df.drop_duplicates(inplace=True)
    print(f"Data extraction complete. Found {len(final_df)} clean records.")
    
    return final_df

if __name__ == "__main__":
    # 1. Get the clean, raw data.
    # The returned DataFrame has columns: 'subject', 'description', 'priority', 'consolidated_category'
    clean_df = extract_and_clean_data()

    # 2. Prepare the DataFrame for SQL insertion (CORRECTED LOGIC)
    # Use the correct source column names from clean_df
    df_to_load = clean_df[['subject', 'description', 'consolidated_category', 'priority']].copy()
    
    # Rename 'consolidated_category' to 'category' to match the DB table schema
    df_to_load.rename(columns={'consolidated_category': 'category'}, inplace=True)

    # 3. Load the raw data into the database
    print("\nConnecting to the database and loading raw data...")
    with engine.connect() as connection:
        try:
            df_to_load.to_sql(
                'original_training_data',
                con=connection,
                if_exists='replace',
                index=False
            )
            print(f"Successfully loaded {len(df_to_load)} raw records into the 'original_training_data' table.")
        except Exception as e:
            print(f"An error occurred during database loading: {e}")

    # 4. Clean Up Downloaded Files (Path variable needs to be captured)
    # The 'path' variable was local to the function, let's capture it.
    path_to_clean = "tobiasbueck/multilingual-customer-support-tickets" # Define path for cleanup
    if os.path.exists(path_to_clean):
        print(f"Cleaning up downloaded files at: {path_to_clean}")
        shutil.rmtree(path_to_clean)
        print("Cleanup complete.")