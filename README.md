# Customer Churn Prediction

A full-stack machine learning application that predicts customer churn risk, explains predictions with SHAP values, and surfaces insights through an interactive dashboard.

![Dashboard](https://img.shields.io/badge/status-complete-brightgreen) ![Python](https://img.shields.io/badge/Python-3.10+-blue) ![React](https://img.shields.io/badge/React-19-61DAFB) ![XGBoost](https://img.shields.io/badge/ML-XGBoost-orange)

---

## Features

- **Churn risk scoring** — per-customer probability with Critical / High / Medium / Low segments
- **SHAP explainability** — waterfall charts showing the top 5 factors driving each prediction
- **Cohort analysis** — churn rate breakdown by industry, plan tier, contract type, company size, and acquisition channel
- **Model retraining** — trigger a background retrain from the UI and hot-reload the new model without restarting the server
- **Prediction history** — track how a customer's risk score has changed over time

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite, Chart.js, React Router |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| ML | XGBoost, SHAP, scikit-learn, pandas |
| Database | PostgreSQL 15 |
| Infrastructure | Docker Compose |

---

## Architecture

```
┌─────────────────┐       ┌──────────────────────┐       ┌──────────────┐
│  React Frontend │──────▶│   FastAPI Backend     │──────▶│  PostgreSQL  │
│  (port 5173)    │◀──────│   (port 8000)         │◀──────│  (port 5432) │
└─────────────────┘       └──────────────────────┘       └──────────────┘
                                     │
                           ┌─────────▼─────────┐
                           │  XGBoost + SHAP   │
                           │  (artifacts/)     │
                           └───────────────────┘
```

**Feature engineering** aggregates raw events from 4 tables (usage, support, billing, customer) into a 30-feature matrix. The XGBoost classifier is trained on this matrix and loaded as a singleton at startup. SHAP `TreeExplainer` provides per-prediction interpretability.

---

## Getting Started

### Prerequisites
- [Docker](https://www.docker.com/) (for PostgreSQL)
- Python 3.10+
- Node.js 18+

### 1. Start the database
```bash
docker-compose up -d
```

### 2. Set up the backend
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Set these values in `.env`:
```
DATABASE_URL=postgresql://postgres:password@localhost:5432/churn_db
MODEL_VERSION=v1
```

### 3. Seed data and train the model
```bash
python data/generate_data.py    # generates 5000 synthetic customers
python app/models/train.py      # trains XGBoost, saves to backend/artifacts/
```

### 4. Start the backend
```bash
python -m uvicorn main:app --reload
# API at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### 5. Start the frontend
```bash
cd ../frontend
npm install
npm run dev
# UI at http://localhost:5173
```

> Steps 3 is a one-time setup. On subsequent runs, only steps 1, 4, and 5 are needed.

---

## Project Structure

```
churn-prediction/
├── docker-compose.yml
├── backend/
│   ├── main.py                     # FastAPI app entry point
│   ├── requirements.txt
│   ├── data/generate_data.py       # Synthetic data generator
│   ├── artifacts/                  # Trained model files (PKL, JSON)
│   └── app/
│       ├── core/                   # Config & database connection
│       ├── pipeline/               # Feature engineering
│       ├── models/                 # XGBoost training & predictor
│       ├── schemas/                # Pydantic request/response models
│       └── api/routes/             # predictions, customers, analytics, model
└── frontend/
    └── src/
        ├── pages/                  # Dashboard, CustomerDetail, CohortAnalysis
        ├── components/             # Charts and UI components
        └── services/api.js         # Axios API client
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/predictions/{customer_id}` | Run prediction for one customer |
| `POST` | `/predictions/bulk/run` | Batch predict all customers |
| `GET` | `/predictions/{customer_id}/history` | Prediction history |
| `GET` | `/customers` | List customers (filterable, paginated) |
| `GET` | `/customers/{customer_id}` | Customer detail with latest prediction |
| `GET` | `/analytics/dashboard-stats` | KPIs and risk distribution |
| `GET` | `/analytics/churn-trend` | Monthly churn trend |
| `GET` | `/analytics/cohort-analysis` | Churn rate by segment |
| `POST` | `/model/retrain` | Trigger background retraining |
| `GET` | `/model/retrain/status` | Poll retrain job status |
| `POST` | `/model/reload` | Hot-swap model version |

Full interactive docs available at `http://localhost:8000/docs` when the backend is running.

---

## Model Details

- **Algorithm**: XGBoost classifier (300 estimators, max_depth=4, learning_rate=0.05)
- **Features**: 30 engineered features across usage trends, support behavior, billing patterns, and customer demographics
- **Class imbalance**: Handled via `scale_pos_weight=2`
- **Explainability**: SHAP TreeExplainer — top 5 contributing features returned per prediction
- **Risk segments**: Critical (≥75%), High (≥50%), Medium (≥25%), Low (<25%)
