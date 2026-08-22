"""
Lightweight ML Anomaly Engine for Supply Chain Fraud Detection.
Uses an ensemble of IsolationForest and GradientBoostingClassifier trained on synthetic supply chain fraud telemetry.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import time
import math

class MLFraudDetector:
    def __init__(self):
        self.scaler = StandardScaler()
        self.isolation_forest = IsolationForest(
            n_estimators=100,
            contamination=0.15,
            random_state=42
        )
        self.rf_classifier = RandomForestClassifier(
            n_estimators=80,
            max_depth=6,
            random_state=42
        )
        self.is_trained = False
        self.feature_names = [
            "weight_deviation_pct",
            "transit_avg_speed_kmh",
            "max_leg_speed_kmh",
            "timestamp_inversion_count",
            "checkpoint_count",
            "duration_hours",
            "cert_validity_days_remaining",
            "geo_displacement_total_km"
        ]
        self._train_initial_model()

    def _generate_synthetic_training_data(self, n_samples: int = 1500) -> Tuple[np.ndarray, np.ndarray]:
        """Generate realistic supply chain physical and metadata features for genuine and fraud cases."""
        np.random.seed(42)
        n_genuine = int(n_samples * 0.82)
        n_fraud = n_samples - n_genuine

        # 1. Genuine Shipments
        gen_weight_dev = np.random.normal(0.01, 0.02, n_genuine)  # <2% weight delta
        gen_avg_speed = np.random.uniform(20.0, 95.0, n_genuine)   # Truck/Rail speed
        gen_max_speed = gen_avg_speed + np.random.uniform(5.0, 30.0, n_genuine)
        gen_time_inversions = np.zeros(n_genuine)
        gen_checkpoints = np.random.randint(2, 6, n_genuine)
        gen_duration = np.random.uniform(12.0, 120.0, n_genuine)
        gen_cert_days = np.random.uniform(60.0, 700.0, n_genuine)
        gen_displacement = gen_avg_speed * gen_duration * np.random.uniform(0.4, 0.8, n_genuine)

        X_gen = np.column_stack([
            gen_weight_dev, gen_avg_speed, gen_max_speed, gen_time_inversions,
            gen_checkpoints, gen_duration, gen_cert_days, gen_displacement
        ])
        y_gen = np.zeros(n_genuine)

        # 2. Fraudulent / Counterfeit Shipments (mismatched weights, impossible speeds, expired certs, time paradoxes)
        fraud_half1 = n_fraud // 2
        fraud_half2 = n_fraud - fraud_half1
        fraud_weight_dev = np.concatenate([
            np.random.uniform(0.15, 0.85, fraud_half1),
            np.random.uniform(-0.60, -0.15, fraud_half2)
        ])
        fraud_avg_speed = np.concatenate([
            np.random.uniform(800.0, 3500.0, fraud_half1),
            np.random.uniform(0.1, 5.0, fraud_half2)
        ])
        fraud_max_speed = fraud_avg_speed * np.random.uniform(1.2, 3.5, n_fraud)
        fraud_time_inversions = np.random.choice([0, 1, 2, 3], size=n_fraud, p=[0.2, 0.4, 0.3, 0.1])
        fraud_checkpoints = np.random.choice([0, 1, 8, 12], size=n_fraud)
        fraud_duration = np.random.uniform(1.0, 300.0, n_fraud)
        fraud_cert_days = np.concatenate([
            np.random.uniform(-180.0, -1.0, fraud_half1),
            np.random.uniform(10.0, 50.0, fraud_half2)
        ])
        fraud_displacement = np.random.uniform(100.0, 15000.0, n_fraud)

        X_fraud = np.column_stack([
            fraud_weight_dev, fraud_avg_speed, fraud_max_speed, fraud_time_inversions,
            fraud_checkpoints, fraud_duration, fraud_cert_days, fraud_displacement
        ])
        y_fraud = np.ones(n_fraud)

        X = np.vstack([X_gen, X_fraud])
        y = np.concatenate([y_gen, y_fraud])
        return X, y

    def _train_initial_model(self):
        """Train models on initial synthetic baseline."""
        X, y = self._generate_synthetic_training_data(2000)
        X_scaled = self.scaler.fit_transform(X)
        self.isolation_forest.fit(X_scaled)
        self.rf_classifier.fit(X_scaled, y)
        self.is_trained = True

    def extract_features(self, payload_dict: Dict[str, Any], calculated_metrics: Dict[str, Any]) -> np.ndarray:
        """Transform raw shipment validation metrics into normalized ML feature vector."""
        weight_dev = calculated_metrics.get("weight_deviation_pct", 0.0)
        avg_speed = calculated_metrics.get("avg_speed_kmh", 50.0)
        max_speed = calculated_metrics.get("max_leg_speed_kmh", 60.0)
        inversions = float(calculated_metrics.get("timestamp_inversions", 0))
        cp_count = float(len(payload_dict.get("checkpoints", [])))
        duration = calculated_metrics.get("total_transit_hours", 24.0)
        cert_days = calculated_metrics.get("cert_validity_days", 180.0)
        displacement = calculated_metrics.get("total_displacement_km", 500.0)

        feats = np.array([
            weight_dev,
            avg_speed,
            max_speed,
            inversions,
            cp_count,
            duration,
            cert_days,
            displacement
        ]).reshape(1, -1)
        return feats

    def predict_anomaly(self, payload_dict: Dict[str, Any], calculated_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Perform real-time ML anomaly & fraud scoring with feature importances / risk drivers."""
        feats = self.extract_features(payload_dict, calculated_metrics)
        feats_scaled = self.scaler.transform(feats)

        # 1. Isolation Forest Anomaly Score (normalized 0.0 to 1.0)
        # raw decision function: higher is normal, lower is outlier
        raw_if_score = self.isolation_forest.decision_function(feats_scaled)[0]
        # map to 0 (normal) - 1 (highly anomalous)
        anomaly_score = float(np.clip(1.0 - (raw_if_score + 0.5), 0.0, 1.0))
        is_if_anomaly = bool(self.isolation_forest.predict(feats_scaled)[0] == -1)

        # 2. Supervised Fraud Probability (0.0 to 1.0)
        fraud_prob = float(self.rf_classifier.predict_proba(feats_scaled)[0][1])

        # Combined ML confidence & risk assessment
        blended_risk = 0.65 * fraud_prob + 0.35 * anomaly_score

        # Determine top risk feature drivers
        top_risk_features = []
        feature_vals = feats[0]
        for i, name in enumerate(self.feature_names):
            val = feature_vals[i]
            # Inspect anomalous boundaries
            anomaly_reason = None
            if name == "weight_deviation_pct" and abs(val) > 0.05:
                anomaly_reason = f"Declared vs expected weight discrepancy of {val*100:.1f}%"
            elif name == "max_leg_speed_kmh" and val > 150.0:
                anomaly_reason = f"Unrealistic transit velocity ({val:.1f} km/h)"
            elif name == "timestamp_inversion_count" and val > 0:
                anomaly_reason = f"{int(val)} out-of-sequence checkpoint timestamp event(s)"
            elif name == "cert_validity_days_remaining" and val <= 0:
                anomaly_reason = f"Digital Certificate is expired by {abs(val):.0f} days"

            if anomaly_reason:
                top_risk_features.append({
                    "feature": name,
                    "observed_value": round(val, 2),
                    "risk_driver": anomaly_reason
                })

        return {
            "anomaly_score": round(anomaly_score, 4),
            "is_anomaly": is_if_anomaly or (blended_risk > 0.45),
            "fraud_probability": round(fraud_prob, 4),
            "confidence": round(float(np.clip(0.85 + (0.15 * abs(0.5 - blended_risk)), 0.70, 0.99)), 3),
            "blended_ml_risk": round(blended_risk, 4),
            "top_risk_features": top_risk_features
        }

# Global singleton
ml_engine = MLFraudDetector()
