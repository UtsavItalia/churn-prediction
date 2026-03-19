from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.models.predictor import predictor
from app.api.routes import predictions, customers, analytics, model


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once at startup — load model into memory
    print("Loading churn model...")
    predictor.load(model_version=settings.MODEL_VERSION)
    print("API ready.")
    yield
    # Runs on shutdown
    print("Shutting down.")


app = FastAPI(title="Churn Prediction API", version="1.0.0", lifespan=lifespan)

# Allow React dev server to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default port
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predictions.router)
app.include_router(customers.router)
app.include_router(analytics.router)
app.include_router(model.router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_version": settings.MODEL_VERSION,
        "env": settings.ENV,
    }
