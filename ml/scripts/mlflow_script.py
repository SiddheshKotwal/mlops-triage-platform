#!/usr/bin/env python3
# before running this set the env variable for AZURE_STORAGE_CONNECTION_STRING and then use a cmd to start the mlflow server than run this code with given usage cmd

"""
mlflow_script.py

Usage:
    python mlflow_script.py --content-dir "C:/Users/Lenovo/Desktop/mlops-triage-platform/mlops-triage-platform/ml/models" --mlflow-uri http://127.0.0.1:5000 --experiment "customer_ticket_classification_v1" --registry-name "BestOne_Model_Registry" --top-n 5 --transition-stage Staging
"""

import argparse
import ast
import json
import os
import pickle
import re
from pathlib import Path
from typing import Dict, List
import joblib
import mlflow
from mlflow.tracking import MlflowClient

# Sklearn, LightGBM, XGBoost are needed for unpickling
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.preprocessing import LabelEncoder
from scipy import sparse
try:
    from lightgbm import LGBMClassifier
except ImportError:
    LGBMClassifier = None
try:
    from xgboost import XGBClassifier
except ImportError:
    XGBClassifier = None

# ---------------------------
# FIX: Class definitions must match the training script exactly
# ---------------------------
# Using `self.estimator` to match the object saved during training.
class LGBMWrapper(BaseEstimator, ClassifierMixin):
    def __init__(self, **lgb_params):
        self.estimator = LGBMClassifier(**lgb_params) if LGBMClassifier else None
        self.le = None
    # Dummy methods to allow unpickling
    def fit(self, X, y): return self
    def predict(self, X): return X
    def predict_proba(self, X): return X

class XGBWrapper(BaseEstimator, ClassifierMixin):
    def __init__(self, **xgb_params):
        self.estimator = XGBClassifier(**xgb_params) if XGBClassifier else None
        self.le = None
    # Dummy methods to allow unpickling
    def fit(self, X, y): return self
    def predict(self, X): return X
    def predict_proba(self, X): return X


# ---------------------------
# Model detection helpers (no changes here)
# ---------------------------
def prefix_from_name(path: Path) -> str:
    return re.sub(r"__(best|report)$", "", path.stem)

# ---------------------------
# UPDATED: Model detection helpers (reads .json)
# ---------------------------
def discover_models(content_dir: Path):
    """
    Discovers model pairs of (*__best.pkl, *__report.json) and loads
    the structured report data directly from the JSON file.
    """
    pkl_files = list(content_dir.glob("*__best.pkl"))
    report_files = list(content_dir.glob("*__report.json")) # <-- Look for .json

    entries = {}
    for p in pkl_files:
        pref = prefix_from_name(p)
        entries.setdefault(pref, {})['pkl'] = p
    for r in report_files:
        pref = prefix_from_name(r)
        entries.setdefault(pref, {})['report'] = r

    models = []
    for pref, d in entries.items():
        if 'pkl' in d and 'report' in d:
            # --- The main change: load directly from JSON ---
            try:
                with open(d['report'], 'r', encoding='utf-8') as f:
                    parsed_data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Warning: Could not read or parse report {d['report'].name}: {e}")
                continue

            models.append({
                "name": pref,
                "pkl": d['pkl'],
                "report": d['report'],
                "parsed": parsed_data, # The entire JSON content is now the parsed data
                "cv_score": parsed_data.get("Best CV score", -1.0) or -1.0,
                "f1_macro": float(parsed_data.get("Test metrics", {}).get("f1_macro", -1.0))
            })
    return models

# ---------------------------
# FINAL FIX: Updated Logging logic for correct placement
# ---------------------------
def try_log_model_with_flavor(model_obj, artifact_path="model"):
    """
    Saves the model to a temporary local path first, then uses
    log_artifacts to ensure correct placement in the run's artifact directory.
    """
    import tempfile
    import mlflow.sklearn

    # Create a temporary directory to save the model package
    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = os.path.join(tmpdir, "model_package")

        # 1. Save the model to the temporary local path
        try:
            mlflow.sklearn.save_model(
                sk_model=model_obj,
                path=local_path
            )
        except Exception as e:
            print(f"    - ERROR: Failed to save model locally before upload: {e}")
            return False

        # 2. Use log_artifacts to upload the entire directory
        # This command is more reliable for correct placement.
        try:
            mlflow.log_artifacts(local_path, artifact_path=artifact_path)
            print(f"    - Model successfully logged to '{artifact_path}' directory.")
            return True
        except Exception as e:
            print(f"    - ERROR: Failed to log model artifacts: {e}")
            return False

# ---------------------------
# UPDATED: Logging logic (reads from parsed dictionary)
# ---------------------------
def log_single_model_run(client: MlflowClient, experiment_id: str, entry: Dict):
    name = entry['name']
    pkl_path: Path = entry['pkl']
    report_path: Path = entry['report'] # This is now the .json report path
    parsed = entry['parsed']

    with mlflow.start_run(experiment_id=experiment_id, run_name=name) as run:
        run_id = run.info.run_id
        print(f"[+] Starting run for {name} (run_id={run_id})")

        # --- Simplified Logging ---
        # Log parameters and top-level metrics directly from the parsed dictionary
        if parsed.get("Best params"):
            mlflow.log_params(parsed["Best params"])
        if parsed.get("Test metrics"):
            mlflow.log_metrics(parsed["Test metrics"])
        if parsed.get("Best CV score") is not None:
            mlflow.log_metric("best_cv_score", parsed["Best CV score"])

        # Log the structured classification report per-class
        if parsed.get("Classification report"):
            cr_dict = parsed["Classification report"]
            for class_name, metrics in cr_dict.items():
                safe_class_name = re.sub(r'\W+', '_', class_name).strip('_').lower()
                for metric_name, value in metrics.items():
                    # Sanitize metric names like "f1-score"
                    safe_metric_name = metric_name.replace('-', '_')
                    mlflow.log_metric(f"{safe_class_name}_{safe_metric_name}", value)

        # Log confusion matrix and the original report.json as artifacts
        if parsed.get("Confusion matrix"):
            mlflow.log_dict(parsed["Confusion matrix"], "confusion_matrix.json")
        mlflow.log_artifact(str(report_path), artifact_path="report")

        # --- Model Loading and Logging (no changes in this part) ---
        model_obj = None
        try:
            with open(pkl_path, "rb") as f:
                model_obj = joblib.load(f)
        except Exception as e:
            print(f"    - WARNING: failed to load model file '{pkl_path.name}': {e}")

        if model_obj is not None:
            flavor_ok = try_log_model_with_flavor(model_obj, artifact_path="model")
            if not flavor_ok:
                print("    - Falling back to logging raw pickle file.")
                mlflow.log_artifact(str(pkl_path), artifact_path="raw_pickle")
        else:
            flavor_ok = False
            print("    - Model object is None, logging raw pickle as artifact.")
            mlflow.log_artifact(str(pkl_path), artifact_path="raw_pickle")

        mlflow.set_tags({"source_file": pkl_path.name, "report_file": report_path.name})
        return run_id, flavor_ok

# ---------------------------
# Main function (no changes here)
# ---------------------------
def main():
    # (This function remains unchanged)
    p = argparse.ArgumentParser()
    p.add_argument("--content-dir", required=True)
    p.add_argument("--mlflow-uri", required=True)
    p.add_argument("--experiment", required=True)
    p.add_argument("--registry-name", required=True)
    p.add_argument("--top-n", type=int, default=5)
    p.add_argument("--transition-stage", choices=["None", "Staging", "Production"], default="None")
    args = p.parse_args()

    content_dir = Path(args.content_dir)
    mlflow.set_tracking_uri(args.mlflow_uri)
    print("MLflow Tracking URI:", mlflow.get_tracking_uri())

    exp = mlflow.get_experiment_by_name(args.experiment)
    exp_id = exp.experiment_id if exp else mlflow.create_experiment(args.experiment)
    print(f"Using experiment '{args.experiment}' (ID: {exp_id})")

    client = MlflowClient()
    models = discover_models(content_dir)
    if not models:
        raise SystemExit(f"No model+report pairs found in {content_dir}")

    models_sorted = sorted(models, key=lambda x: (x["cv_score"], x["f1_macro"]), reverse=True)
    print("Discovered models (sorted):")
    for m in models_sorted:
        print(f"  {m['name']:<30} cv={m['cv_score']:.4f}  f1_macro={m['f1_macro']:.4f}")

    logged_runs = []
    for e in models_sorted[:args.top_n]:
        run_id, flavor_ok = log_single_model_run(client, exp_id, e)
        logged_runs.append({"entry": e, "run_id": run_id, "flavor_ok": flavor_ok})

    if logged_runs and logged_runs[0]["flavor_ok"]:
        best_run_id = logged_runs[0]["run_id"]
        model_uri = f"runs:/{best_run_id}/model"
        print(f"\nRegistering top model from {model_uri} into '{args.registry_name}'")
        try:
            client.create_registered_model(args.registry_name)
        except: pass
        mv = client.create_model_version(name=args.registry_name, source=model_uri, run_id=best_run_id)
        print(f"  Created model version: {mv.version}")
        if args.transition_stage != "None":
            client.transition_model_version_stage(name=args.registry_name, version=mv.version, stage=args.transition_stage, archive_existing_versions=True)
            print(f"  Transitioned model version {mv.version} -> {args.transition_stage}")
    else:
        print("\nTop model was not logged with a compatible flavor. Skipping registration.")

    print("\nDone.")

if __name__ == "__main__":
    main()