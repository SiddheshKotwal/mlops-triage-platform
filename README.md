# Self-Improving AI Triage System with Human-in-the-Loop (HITL)

[![CI](https://github.com/SiddheshKotwal/mlops-triage-platform/workflows/CI/badge.svg)](https://github.com/SiddheshKotwal/mlops-triage-platform/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An enterprise-grade, local-first MLOps project that demonstrates a complete, self-improving system for triaging customer support tickets. The system uses machine learning to classify tickets by category and priority, leverages a human-in-the-loop workflow to verify low-confidence predictions, and uses this feedback to automatically retrain and deploy improved models with zero downtime.

## 🎯 Project Vision & Goal

The primary goal is to build an intelligent, automated system that intelligently triages customer support tickets. The core innovation is its ability to function as a **self-improving learning system**. It is designed to:

- **Intelligently identify** its own low-confidence predictions
- **Route** these ambiguous tickets to a human for efficient review and correction
- **Use** this newly verified data to retrain, validate, and deploy improved versions of its machine learning models over time, creating a complete MLOps feedback loop

## ✨ Core Features

### 🤖 AI-Powered Classification
- **Automated Multi-Label Classification**: Automatically assigns both a category and a priority to every new ticket
- **Confidence-Based HITL Routing**: Low-confidence predictions are automatically flagged and sent to a dedicated queue for manual human review

### 🎨 User Interface
- **React-based UI**: A complete user interface with:
  - A dashboard for submitting tickets and tracking their status
  - An expert review panel to efficiently correct and verify flagged tickets

### 🔄 MLOps Pipeline
- **Local MLOps Retraining Pipeline**: A manually-triggered, containerized pipeline that uses human-verified data to train, evaluate, and register new "challenger" models
- **Champion vs. Challenger Deployment**: A new model is only promoted if it demonstrably outperforms the current "champion" model, preventing performance regressions
- **Zero-Downtime Model Deployment**: The live ml-worker service automatically detects newly promoted champion models and loads them without requiring a service restart

### 📊 Monitoring & Observability
- **Real-Time Observability Dashboard**: A Grafana dashboard powered by Prometheus provides deep insights into the system's performance, including API latency (p99), throughput (RPS), and custom MLOps metrics
- **Continuous Integration**: A GitHub Actions workflow automatically runs a full suite of pytest unit tests on every code push to ensure code quality

## 🏗️ Architecture Overview

This project is built on a **containerized, event-driven microservices architecture**. All services run in isolated Docker containers and are managed locally via Docker Compose.

```mermaid
graph TB
    UI[React Frontend] --> API[FastAPI Backend]
    API --> DB[(PostgreSQL)]
    API --> Redis[Redis Streams]
    Redis --> Worker[ML Worker]
    Worker --> MLflow[MLflow Server]
    MLflow --> Storage[Azure Blob Storage]
    Prometheus --> Grafana[Grafana Dashboard]
```

### Key Components

- **Frontend**: A React Single-Page Application (SPA) built with Vite and styled with Tailwind CSS
- **Backend Services**: Lightweight, high-performance APIs built with Python and FastAPI
- **Asynchronous Communication**: Services are decoupled using Redis Streams, which acts as a robust message broker, allowing the system to handle high-volume ingestion without impacting performance
- **Database**: PostgreSQL serves as the single source of truth for all application data (tickets) and as the Backend Store for MLflow experiment metadata
- **MLOps Backend**: MLflow is used for experiment tracking and model registration. While the MLflow server and its database run locally, the model artifacts (the most valuable assets) are stored securely and persistently in Azure Blob Storage

## 🛠️ Technology Stack

| Category | Technology |
|----------|------------|
| **Backend** | Python, FastAPI, Docker, Docker Compose |
| **Frontend** | React, Vite, Tailwind CSS, Recharts |
| **Database & Broker** | PostgreSQL, Redis |
| **MLOps** | Scikit-learn, spaCy, Pandas, MLflow |
| **Observability** | Prometheus, Grafana |
| **CI/CD** | GitHub Actions, Pytest |
| **Cloud** | Azure Blob Storage (for MLflow artifacts) |

## 📊 Dataset

This system is trained on the **Multilingual Customer Support Tickets** dataset from Kaggle:
- **Source**: [Multilingual Customer Support Tickets Dataset](https://www.kaggle.com/datasets/tobiasbueck/multilingual-customer-support-tickets/data)
- **Description**: A comprehensive dataset containing customer support tickets with various categories and priority levels
- **Usage**: Used for initial model training and validation of the triage system

## 🚀 Quick Start

### Prerequisites

Before you begin, ensure you have the following installed:

- [Git](https://git-scm.com/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (must be running)
- [Python 3.11+](https://www.python.org/downloads/)
- [Node.js and npm](https://nodejs.org/)

### Installation

#### 1. Clone the Repository

```bash
git clone https://github.com/SiddheshKotwal/mlops-triage-platform.git
cd mlops-triage-platform
```

#### 2. Configure Environment Secrets

> ⚠️ **Critical Step**: This is the most important setup step.

The project uses a `.env` file to manage all secrets and configurations.

```bash
# On Windows (Command Prompt)
copy .env.example .env

# On macOS/Linux
cp .env.example .env
```

Open the new `.env` file and configure the following required variables:

```bash
# Azure Storage Configuration
RESOURCE_GROUP=your_resource_group
LOCATION=your_azure_location
STORAGE_ACCOUNT_NAME=your_storage_account
AZURE_STORAGE_CONNECTION_STRING=your_connection_string

# Database Configuration  
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=your_db_name
DB_HOST=postgres
DB_PORT=5432

# Redis Configuration
REDIS_HOST=redis

# ML Configuration
CONFIDENCE_THRESHOLD=0.70
MLFLOW_TRACKING_URI=http://mlflow-server:5000
MLFLOW_ARTIFACT_ROOT=your_azure_blob_artifact_root

# MLflow Server Configuration (auto-configured)
MLFLOW_SERVER_CMD="mlflow server --host 0.0.0.0 --port 5000 --backend-store-uri postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME} --default-artifact-root ${AZURE_STORAGE_CONNECTION_STRING}"
```

> 💡 **Note**: All database and Redis configurations can remain as defaults for local development. You primarily need to configure the Azure Storage settings.

#### 3. Backend Initialization (First Time Only)

These commands prepare the database and train the initial models:

**Start Core Services:**
```bash
docker-compose up -d postgres redis mlflow-server
```

**Create Database Tables:**
```bash
docker-compose run --rm --entrypoint "python -m" retraining-pipeline db.engine
```

**Load Initial Dataset:**
```bash
docker-compose run --rm --entrypoint "python -m" retraining-pipeline scripts.load_initial_data
```

**Train Initial "Champion" Models:**
```bash
docker-compose run --build --rm retraining-pipeline all
```

#### 4. Launch the Full Application

**Start All Backend Services:**
```bash
docker-compose up -d postgres redis mlflow-server ingestion-api ml-worker results-api prometheus grafana
```

**Start the Frontend:**
```bash
cd frontend
npm install
npm start
```

### 🌐 Access Your Services

Your full MLOps application is now running locally!

| Service | URL | Description |
|---------|-----|-------------|
| **React Application** | http://localhost:3000 | Main user interface |
| **MLflow UI** | http://localhost:5000 | Experiment tracking and model registry |
| **Grafana Dashboard** | http://localhost:3001 | Monitoring dashboard (login: admin/admin) |
| **Prometheus UI** | http://localhost:9090 | Metrics collection interface |

## 🔄 Usage

### Using the Application

1. **Submit Tickets**: Use the React UI to submit new support tickets
2. **View Dashboard**: Monitor ticket status and system performance
3. **Review Queue**: Use the "Review Queue" to correct low-confidence AI predictions

### Manual Model Retraining

When you have accumulated enough human-verified data, trigger the self-improvement loop:

```bash
docker-compose run --build --rm retraining-pipeline all
```

This script will automatically:
- Fetch all new verified data
- Retrain the models
- Evaluate performance
- Promote a new "champion" model if it performs better
- The live ml-worker will automatically pick up the new model within minutes

### Running Tests

To run the automated test suite:

```bash
pytest
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
