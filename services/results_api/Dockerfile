# services/results_api/Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Add the project root to PYTHONPATH to allow absolute imports (like from the 'db' module)
ENV PYTHONPATH=/app

# Copy service-specific requirements first to leverage Docker layer caching
COPY services/results_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source code from the project root into the container
COPY . .

# Command to run the API server
CMD ["uvicorn", "services.results_api.app:app", "--host", "0.0.0.0", "--port", "8000"]