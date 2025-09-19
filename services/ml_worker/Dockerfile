# services/ml_worker/Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Allow absolute imports from the project root
ENV PYTHONPATH=/app

# 1. Copy the requirements file into the container first.
COPY services/ml_worker/requirements.txt .

# 2. Now, install all dependencies, including libgomp1.
RUN apt-get update && \
    apt-get install -y git curl libgomp1 build-essential && \
    pip install --no-cache-dir -r requirements.txt && \
    python -c "import nltk; nltk.download(['punkt', 'punkt_tab', 'stopwords', 'wordnet', 'averaged_perceptron_tagger', 'averaged_perceptron_tagger_eng'])" && \
    rm -rf /var/lib/apt/lists/*

# 3. Finally, copy the rest of your application source code.
COPY . .

# Run the worker script
CMD ["python", "-u", "services/ml_worker/worker.py"]