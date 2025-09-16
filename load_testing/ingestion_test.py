import os
import random
import psycopg2
from locust import HttpUser, task, between
from dotenv import load_dotenv

# --- 1. Load Configuration and Data ---

# Load environment variables from the .env file in the project root
load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
# For Locust, the host is 'localhost' because the script runs on your machine,
# not inside a Docker container from the compose file.
DB_HOST = "localhost" 
DB_PORT = os.getenv("DB_PORT")

# Global list to hold our test data
TICKET_DATA = []

def setup_test_data():
    """
    Connects to the database and fetches ticket data to be used for the test.
    This function runs once when Locust starts.
    """
    global TICKET_DATA
    print(" locust: Setting up test data...")
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()
        # Fetch the subject and description from your original data table
        # Limiting to 5000 rows for quick startup, you can adjust this
        cursor.execute("SELECT subject, description FROM original_training_data LIMIT 5000;")
        rows = cursor.fetchall()
        
        # Store data in a format ready for JSON submission
        TICKET_DATA = [{"subject": row[0], "description": row[1]} for row in rows]
        
        cursor.close()
        conn.close()
        print(f" locust: Successfully loaded {len(TICKET_DATA)} tickets from the database.")
    except Exception as e:
        print(f" locust: FATAL - Failed to connect to database and load data: {e}")
        # Exit if we can't load data, as the test can't run
        exit(1)

# Run the setup function once at the start of the test
setup_test_data()

# --- 2. Define the User Behavior ---

class TicketSubmitUser(HttpUser):
    """
    This class defines the behavior of a single simulated user.
    Locust will create many instances of this class to generate load.
    """
    # This makes each simulated user wait 1 to 3 seconds between submitting tickets
    wait_time = between(1, 3)

    @task # This decorator marks the following method as a task for the user to perform
    def submit_ticket(self):
        if not TICKET_DATA:
            print(" locust: No ticket data available to send.")
            return

        # Pick a random ticket from our globally loaded data
        ticket = random.choice(TICKET_DATA)
        
        # The endpoint we want to test
        endpoint = "tickets"
        
        # Send a POST request to the API endpoint
        # The 'self.client' is Locust's powerful, built-in HTTP client
        self.client.post(endpoint, json=ticket)
'''

### Step 3: How to Run the Test and Analyze the Results

This is a multi-step process where you'll have your application and the test tool running simultaneously.

**1. Start Your Application:**
Make sure your entire backend stack is running via Docker Compose. From the project root:
```bash
docker-compose up -d --build
```

**2. Launch Locust:**
In a **new terminal** (with your venv active), navigate to your project root and run the following command to start the Locust test server:
```bash
locust -f load_testing/ingestion_test.py
```
You will see output indicating that Locust is running and its web UI is available.

**3. Start the Test in the Locust Web UI:**
* Open your browser and go to **`http://localhost:8089`**.
* You will see the Locust start page. Configure your test:
    * **Number of users:** Start with `10`. This simulates 10 concurrent users.
    * **Spawn rate:** Enter `2`. This means Locust will start 2 new users per second until it reaches 10.
    * **Host:** Enter the URL of your Ingestion API: `http://localhost:8001`
* Click **"Start swarming"**.



**4. Analyze the Results (The Payoff):**
Now you have two crucial dashboards to watch to see your system working under pressure.

* **The Locust Dashboard (`localhost:8089`):** Go to the **"Charts"** tab. You'll see real-time graphs for:
    * **Total Requests per Second (RPS):** The throughput of your Ingestion API.
    * **Response Time (ms):** How quickly your API is responding. A low, stable number is good.
    * In the **"Failures"** tab, you can see if any requests are failing.

* **Your Worker's Logs:** In your terminal, watch the live logs from your services to see the end-to-end flow.
    ```bash
    # Watch the ML worker to see tickets being processed
    docker-compose logs -f ml-worker

    # Watch the Ingestion API to see incoming requests
    docker-compose logs -f ingestion-api
    
'''