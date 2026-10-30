import os
import sys
import joblib
from typing import Dict, Any, Tuple, Optional

# Ensure ml directory is on sys.path for preprocess imports
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ML_DIR = os.path.join(BASE_DIR, "ml")
if ML_DIR not in sys.path:
    sys.path.insert(0, ML_DIR)

from preprocess import combine_fields, clean_text


class ModelManager:
    """Manages loading and inference for the JobShield ML fraud model."""

    def __init__(self, model_path: Optional[str] = None):
        if model_path is None:
            self.model_path = os.path.join(BASE_DIR, "ml", "model.pkl")
        else:
            self.model_path = model_path

        self.model_artifact = None
        self.pipeline = None
        self.version = "unknown"
        self.algorithm = "unknown"
        self.is_loaded = False
        self.load_error = None

        self.load_model()

    def load_model(self) -> bool:
        """Loads the persisted joblib model artifact."""
        if not os.path.exists(self.model_path):
            self.is_loaded = False
            self.load_error = f"Model artifact not found at {self.model_path}"
            print(f"[ModelManager] WARNING: {self.load_error}")
            return False

        try:
            self.model_artifact = joblib.load(self.model_path)
            if isinstance(self.model_artifact, dict) and "pipeline" in self.model_artifact:
                self.pipeline = self.model_artifact["pipeline"]
                self.version = self.model_artifact.get("model_version", "1.0.0")
                self.algorithm = self.model_artifact.get("algorithm", "TF-IDF + LogisticRegression")
            else:
                self.pipeline = self.model_artifact
                self.version = "1.0.0"
                self.algorithm = "TF-IDF + LogisticRegression"

            self.is_loaded = True
            self.load_error = None
            print(f"[ModelManager] Loaded ML model version {self.version} ({self.algorithm})")
            return True
        except Exception as e:
            self.is_loaded = False
            self.load_error = str(e)
            print(f"[ModelManager] ERROR loading model: {e}")
            return False

    def predict_fraud_risk(self, job: Dict[str, Any]) -> Tuple[float, bool]:
        """
        Returns (ml_fraud_score_0_to_100, is_success).
        If inference fails, returns (0.0, False).
        """
        if not self.is_loaded or self.pipeline is None:
            return 0.0, False

        try:
            title = job.get("title") or ""
            company = job.get("company") or ""
            description = job.get("description") or ""
            requirements = job.get("requirements") or ""
            benefits = job.get("salary") or job.get("benefits") or ""

            combined_text = combine_fields(
                title=title,
                company=company,
                description=description,
                requirements=requirements,
                benefits=benefits
            )

            proba = self.pipeline.predict_proba([combined_text])[0, 1]
            ml_score = float(proba * 100.0)
            return ml_score, True
        except Exception as e:
            print(f"[ModelManager] Prediction error: {e}")
            return 0.0, False

    def get_info(self) -> Dict[str, Any]:
        metrics = {}
        if isinstance(self.model_artifact, dict):
            metrics = self.model_artifact.get("metrics", {})
        return {
            "loaded": self.is_loaded,
            "version": self.version,
            "algorithm": self.algorithm,
            "error": self.load_error,
            "metrics": metrics
        }


# Singleton instance
model_manager = ModelManager()
