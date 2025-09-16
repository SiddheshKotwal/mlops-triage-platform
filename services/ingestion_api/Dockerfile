# services/ingestion_api/Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Copy only the requirements for THIS service
COPY services/ingestion_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the source code for THIS service into the workdir
COPY services/ingestion_api/ .

# Now this original command will work because app.py is directly in /app
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]