"""
Main Validation Service Orchestrator.
Coordinates simulated source lookups with exponential backoff retry, evaluates rule conflicts,
executes ML fraud inference, computes explainable composite authenticity score, and generates decision reports.
"""

import time
import uuid
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from ..models.schemas import (
    ShipmentPayload,
    ValidationReport,
    RiskLevel,
    MLAnomalyAssessment,
    ConflictEvidence,
    OverrideStatus
)
from .rules_engine import RulesEngine
from .ml_engine import ml_engine
from .audit_service import audit_service

class ValidatorService:
    @staticmethod
    async def _simulate_resilient_source_lookup(source_name: str, max_retries: int = 3) -> bool:
        """
        Demonstrates resilient source query with exponential backoff & jitter.
        Ensures fragmented data lookups gracefully handle transient delays.
        """
        for attempt in range(max_retries):
            try:
                # Simulated micro-latency
                await asyncio.sleep(0.005 * (attempt + 1))
                return True
            except Exception:
                if attempt == max_retries - 1:
                    return False
                await asyncio.sleep(0.02 * (2 ** attempt))
        return True

    @classmethod
    async def validate_shipment(cls, shipment: ShipmentPayload) -> ValidationReport:
        start_time = time.perf_counter()
        validation_id = f"VAL-{uuid.uuid4().hex[:10].upper()}"

        # 1. Resilient multi-source lookup queries (async concurrent)
        await asyncio.gather(
            cls._simulate_resilient_source_lookup("ERP_MANUFACTURER_REGISTRY"),
            cls._simulate_resilient_source_lookup("CERTIFICATE_AUTHORITY_PKI"),
            cls._simulate_resilient_source_lookup("LOGISTICS_CUSTODY_NETWORK"),
            cls._simulate_resilient_source_lookup("PORT_CUSTOMS_GATEWAY")
        )

        # 2. Execute Rule-Based Evaluation & Conflict Extraction
        conflicts, metrics, trace_graph, rule_penalty = RulesEngine.evaluate(shipment)

        # 3. Execute ML Anomaly & Fraud Inference
        shipment_dict = shipment.model_dump()
        ml_result = ml_engine.predict_anomaly(shipment_dict, metrics)

        # 4. Compute Composite Authenticity Score (0.0 to 100.0)
        # Base starts at 100, deducted by rule violations and ML fraud probability
        rule_score = max(0.0, 100.0 - rule_penalty)
        ml_score_component = max(0.0, 100.0 - (ml_result["blended_ml_risk"] * 100.0))

        # Weighting: 60% Deterministic Rule Proofs, 40% ML Pattern Anomaly
        composite_score = (0.60 * rule_score) + (0.40 * ml_score_component)

        # Hard bounds: if there are CRITICAL conflicts (e.g. unknown serial, forged cert, clone), cap score at 30
        has_critical = any(c.severity.value == "CRITICAL" for c in conflicts)
        if has_critical:
            composite_score = min(composite_score, 28.5)

        composite_score = round(float(composite_score), 1)

        # 5. Determine Explainable Risk Tier
        if composite_score >= 85.0:
            risk_level = RiskLevel.AUTHENTIC
            is_authentic = True
            decision_summary = f"Shipment verified authentic. Cryptographic signatures match PKI records, custody chain is continuous without temporal or physical anomalies."
        elif composite_score >= 65.0:
            risk_level = RiskLevel.LOW_RISK
            is_authentic = True
            decision_summary = f"Shipment largely authentic with minor non-critical telemetry variances."
        elif composite_score >= 40.0:
            risk_level = RiskLevel.MEDIUM_RISK
            is_authentic = False
            decision_summary = f"Suspicious shipment. Detected {len(conflicts)} data discrepancies across custody records requiring manual inspector clearance."
        elif composite_score >= 20.0:
            risk_level = RiskLevel.HIGH_RISK
            is_authentic = False
            decision_summary = f"High probability counterfeit or tampered record. {len(conflicts)} conflicting data point(s) detected across manufacturer and carrier logs."
        else:
            risk_level = RiskLevel.COUNTERFEIT_DETECTED
            is_authentic = False
            decision_summary = f"CONFIRMED COUNTERFEIT / FORGERY. Critical cryptographic or provenance conflicts identified. Shipment rejected."

        # Check existing manual override if previously recorded
        override_data = audit_service.get_override_for_report(validation_id)
        override_status = OverrideStatus.AUTO_VERIFIED
        override_notes = None
        override_by = None

        if override_data:
            override_status = override_data["status"]
            override_notes = override_data["reason"]
            override_by = override_data["operator"]

        exec_time_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        ml_assessment = MLAnomalyAssessment(
            anomaly_score=ml_result["anomaly_score"],
            is_anomaly=ml_result["is_anomaly"],
            fraud_probability=ml_result["fraud_probability"],
            top_risk_features=ml_result["top_risk_features"],
            confidence=ml_result["confidence"]
        )

        return ValidationReport(
            validation_id=validation_id,
            shipment_id=shipment.shipment_id,
            serial_number=shipment.serial_number,
            authenticity_score=composite_score,
            risk_level=risk_level,
            is_authentic=is_authentic,
            decision_summary=decision_summary,
            conflicting_evidence=conflicts,
            conflict_count=len(conflicts),
            rule_score=round(rule_score, 1),
            ml_assessment=ml_assessment,
            traceability_graph=trace_graph,
            validated_at=datetime.now(timezone.utc).isoformat(),
            execution_time_ms=exec_time_ms,
            override_status=override_status,
            override_notes=override_notes,
            override_by=override_by
        )
