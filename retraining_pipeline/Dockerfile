# retraining_pipeline/Dockerfile

FROM python:3.13-slim

WORKDIR /app

# Set the PYTHONPATH to include the root directory
ENV PYTHONPATH=/app

# 1. Copy the requirements file into the container first.
COPY retraining_pipeline/requirements.txt .

# 2. Now, install all dependencies, including libgomp1.
RUN apt-get update && \
    apt-get install -y git curl libgomp1 && \
    pip install --no-cache-dir -r requirements.txt && \
    python -c "import nltk; nltk.download(['punkt', 'punkt_tab', 'stopwords', 'wordnet', 'averaged_perceptron_tagger', 'averaged_perceptron_tagger_eng'])" && \
    rm -rf /var/lib/apt/lists/*

# 3. Finally, copy the rest of your application source code.
COPY . .

# Define the entry point for the container.
ENTRYPOINT ["python", "retraining_pipeline/retrain.py"]

# Default command if none is provided to `docker run`
CMD ["all"]