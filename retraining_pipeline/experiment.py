import time
import mlflow
import pandas as pd
import numpy as np
import tempfile
import os
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import classification_report, accuracy_score

def log_model_robustly(model_obj, artifact_path="model"):
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

def find_best_model(
    df: pd.DataFrame,
    target_column: str,
    vectorizers: dict,
    classifiers: dict,
    param_grids: dict
) -> tuple:
    """
    Runs a full grid search experiment, logs each combination, and identifies the best model.
    """
    X = df['processed_text']
    y = df[target_column]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    best_f1_score = -1.0
    best_run_id = None

    for vec_name, vectorizer in vectorizers.items():
        for clf_name, classifier in classifiers.items():
            run_name = f"{vec_name}__{clf_name}"
            with mlflow.start_run(run_name=run_name, nested=True):
                print(f"\n--- Running: {run_name} ---")
                mlflow.set_tags({"vectorizer": vec_name, "classifier": clf_name})

                pipeline = Pipeline([('vect', vectorizer), ('clf', classifier)])
                
                grid_params = {}
                grid_params.update(param_grids.get(vec_name, {}))
                grid_params.update(param_grids.get(clf_name, {}))

                try:
                    search = GridSearchCV(pipeline, grid_params, cv=3, n_jobs=-1, verbose=1, scoring='f1_macro')
                    search.fit(X_train, y_train)

                    best_model = search.best_estimator_
                    y_pred = best_model.predict(X_test)
                    
                    # --- UPDATED METRIC LOGGING ---
                    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
                    acc = accuracy_score(y_test, y_pred)
                    
                    # Log parameters
                    mlflow.log_params(search.best_params_)
                    mlflow.log_metric("best_cv_score", search.best_score_)
                    
                    # Log all key metrics with consistent naming
                    mlflow.log_metric("accuracy", acc)
                    mlflow.log_metric("f1_macro", report['macro avg']['f1-score'])
                    mlflow.log_metric("precision_macro", report['macro avg']['precision'])
                    mlflow.log_metric("recall_macro", report['macro avg']['recall'])
                    mlflow.log_metric("f1_weighted", report['weighted avg']['f1-score'])
                    mlflow.log_metric("precision_weighted", report['weighted avg']['precision'])
                    mlflow.log_metric("recall_weighted", report['weighted avg']['recall'])

                    # Log artifacts
                    mlflow.log_dict(report, "classification_report.json")
                    log_model_robustly(best_model, artifact_path="model")
                    
                    current_f1_score = report['macro avg']['f1-score']
                    print(f"Logged {run_name} with f1_macro: {current_f1_score:.4f}")

                    if current_f1_score > best_f1_score:
                        best_f1_score = current_f1_score
                        best_run_id = mlflow.active_run().info.run_id
                        print(f"*** New best model found: {run_name} (F1: {best_f1_score:.4f}) ***")

                except Exception as e:
                    print(f"!!! Failed to train {run_name}. Error: {e} !!!")
                    continue
    
    return best_run_id, best_f1_score
