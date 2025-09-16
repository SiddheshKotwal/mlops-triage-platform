# db/engine.py

from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

# Import the metadata object which contains all our table definitions
from .database_setup import metadata

# Load environment variables from the root .env file
# This helps when running scripts from the command line
load_dotenv()

# Get the variables from the environment
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST", "localhost") # Default to localhost for local scripts
DB_PORT = os.getenv("DB_PORT", "5432")

# Connection string
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# The single, shared engine object for the application
engine = create_engine(DATABASE_URL)

# This block will ONLY run when the script is executed directly (e.g., `python -m db.engine`)
if __name__ == "__main__":
    try:
        with engine.connect() as connection:
            print("Successfully connected to the PostgreSQL database!")
            
            # Create the tables in the database
            metadata.create_all(engine)
            
            print("Tables created successfully (if they didn't exist).")

    except Exception as e:
        print(f"Failed to connect or create tables: {e}")