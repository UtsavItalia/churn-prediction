from fastapi import APIRouter, BackgroundTasks, HTTPException
from datetime import datetime
import uuid
import os
import sys

_BACKEND_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
_ARTIFACTS = os.path.join(_BACKEND_DIR, "artifacts")

router = APIRouter(prefix="/model", tags=["model"])

# In production this would be Redis or a DB table.
# For now a simple dict is fine — single server, single process.
_jobs: dict = {}


def _run_retraining(job_id: str, new_version: str):
    """
    Runs in a background thread.
    Rebuilds feature matrix, retrains model, saves new artifacts.
    Does NOT hot-swap the running model — that's a separate step.
    This way a failed retrain never breaks the live API.
    """
    _jobs[job_id]["status"] = "running"
    _jobs[job_id]["started_at"] = datetime.now().isoformat()

    try:
        # Add backend to path for imports
        ARTIFACTS = _ARTIFACTS
        os.makedirs(ARTIFACTS, exist_ok=True)
        sys.path.insert(0, _BACKEND_DIR)

        from app.pipeline.feature_engineering import (
            build_feature_matrix,
            FEATURE_COLUMNS,
        )
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import roc_auc_score
        import xgboost as xgb
        import joblib
        import json

        # 1. Rebuild feature matrix from latest DB data
        _jobs[job_id]["stage"] = "building features"
        df = build_feature_matrix()

        X = df[FEATURE_COLUMNS].fillna(0)
        y = df["target"]

        # 2. Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # 3. Retrain with same hyperparameters
        _jobs[job_id]["stage"] = "training"
        model = xgb.XGBClassifier(
            n_estimators=300,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=5,
            scale_pos_weight=2,
            eval_metric="auc",
            random_state=42,
            n_jobs=-1,
        )
        model.fit(X_train, y_train, verbose=False)

        # 4. Evaluate
        _jobs[job_id]["stage"] = "evaluating"
        y_prob = model.predict_proba(X_test)[:, 1]
        roc_auc = roc_auc_score(y_test, y_prob)

        # 5. Save new versioned artifacts
        _jobs[job_id]["stage"] = "saving"
        model_path = os.path.join(ARTIFACTS, f"churn_model_{new_version}.pkl")
        joblib.dump(model, model_path)

        # Feature importance
        import pandas as pd

        fi_df = pd.DataFrame(
            {"feature": FEATURE_COLUMNS, "importance": model.feature_importances_}
        ).sort_values("importance", ascending=False)

        fi_path = os.path.join(ARTIFACTS, f"feature_importance_{new_version}.json")
        with open(fi_path, "w") as f:
            json.dump(fi_df.head(15).to_dict(orient="records"), f, indent=2)

        # Metadata
        meta = {
            "model_version": new_version,
            "trained_at": datetime.now().isoformat(),
            "roc_auc": round(roc_auc, 4),
            "train_size": len(X_train),
            "feature_columns": FEATURE_COLUMNS,
        }
        meta_path = os.path.join(ARTIFACTS, f"model_metadata_{new_version}.json")
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

        # 6. Mark complete
        _jobs[job_id].update(
            {
                "status": "complete",
                "completed_at": datetime.now().isoformat(),
                "stage": "done",
                "metrics": {
                    "roc_auc": round(roc_auc, 4),
                    "train_size": len(X_train),
                    "test_size": len(X_test),
                },
                "new_version": new_version,
                "model_path": model_path,
                "fi_path": fi_path,
            }
        )

    except Exception as e:
        _jobs[job_id].update(
            {
                "status": "failed",
                "error": str(e),
                "stage": "failed",
            }
        )
        raise


# Routes
@router.post("/retrain")
def trigger_retrain(background_tasks: BackgroundTasks):
    """
    Starts model retraining in a background thread.
    Returns immediately with a job ID.
    Poll /model/retrain/status?job_id=... to check progress.
    """
    job_id = str(uuid.uuid4())[:8]
    # Auto-increment version
    existing = [
        f
        for f in os.listdir("artifacts")
        if f.startswith("churn_model_v") and f.endswith(".pkl")
    ]
    versions = [f.replace("churn_model_v", "").replace(".pkl", "") for f in existing]
    try:
        latest = max(float(v) for v in versions)
        new_ver = f"v{latest + 0.1:.1f}"
    except Exception:
        new_ver = "v1.1"

    _jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "stage": "queued",
        "new_version": new_ver,
        "created_at": datetime.now().isoformat(),
    }

    background_tasks.add_task(_run_retraining, job_id, new_ver)

    return {
        "job_id": job_id,
        "status": "queued",
        "new_version": new_ver,
        "message": "Retraining started. Poll /model/retrain/status for updates.",
    }


@router.get("/retrain/status")
def get_retrain_status(job_id: str):
    """Poll this endpoint to check retraining progress."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return _jobs[job_id]


@router.post("/reload")
def reload_model(version: str):
    """
    Hot-swap the in-memory model to a new version.
    Call this AFTER a successful retrain job completes.
    The running API never goes down.
    """
    from app.models.predictor import predictor

    try:
        predictor._loaded = False  # force reload
        predictor.load(model_version=version)
        return {
            "status": "reloaded",
            "model_version": version,
            "reloaded_at": datetime.now().isoformat(),
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/info")
def get_model_info():
    """Current model version and metadata."""
    from app.models.predictor import predictor

    return {
        "model_version": predictor.model_version,
        "metadata": predictor.metadata,
        "n_features": len(predictor.feature_importance),
    }
