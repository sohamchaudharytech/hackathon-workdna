import pytest
import httpx
import asyncio
from app.services.validator_service import ValidatorService
from app.services.rules_engine import RulesEngine
from app.services.ml_engine import ml_engine
from app.services.audit_service import audit_service
from app.models.schemas import ShipmentPayload, CheckpointRecord, OverrideRequest, OverrideStatus
from app.api.routes import DEMO_PRESETS

@pytest.mark.asyncio
async def test_case_1_authentic_shipment():
    payload_dict = DEMO_PRESETS[0]["payload"]
    shipment = ShipmentPayload(**payload_dict)
    report = await ValidatorService.validate_shipment(shipment)

    assert report.is_authentic is True
    assert report.authenticity_score >= 85.0
    assert report.conflict_count == 0
    assert report.risk_level.value in ["AUTHENTIC", "LOW_RISK"]
    assert report.execution_time_ms < 1500.0  # Non-functional requirement < 1.5s
    assert len(report.traceability_graph.nodes) >= 3

@pytest.mark.asyncio
async def test_case_2_counterfeit_forged_cert_and_weight():
    payload_dict = DEMO_PRESETS[1]["payload"]
    shipment = ShipmentPayload(**payload_dict)
    report = await ValidatorService.validate_shipment(shipment)

    assert report.is_authentic is False
    assert report.authenticity_score <= 35.0
    assert report.conflict_count >= 3  # Non-functional requirement >= 3 conflicting data points
    assert report.risk_level.value in ["COUNTERFEIT_DETECTED", "HIGH_RISK"]
    # Check conflicting sources
    sources = [c.source_b for c in report.conflicting_evidence]
    assert any("PKI" in s or "Certificate" in s for s in sources)

@pytest.mark.asyncio
async def test_case_3_impossible_travel_chronology():
    payload_dict = DEMO_PRESETS[2]["payload"]
    shipment = ShipmentPayload(**payload_dict)
    report = await ValidatorService.validate_shipment(shipment)

    assert report.is_authentic is False
    assert report.conflict_count >= 2
    rule_codes = [c.rule_code for c in report.conflicting_evidence]
    assert "RULE_CHRONOLOGY_INVERSION" in rule_codes or "RULE_IMPOSSIBLE_SPEED" in rule_codes

@pytest.mark.asyncio
async def test_batch_validation_concurrency():
    # Run batch with 12 items (clones of presets)
    shipments = []
    for i in range(4):
        for preset in DEMO_PRESETS:
            p = preset["payload"].copy()
            p["shipment_id"] = f"{p['shipment_id']}-BATCH-{i}"
            shipments.append(ShipmentPayload(**p))

    assert len(shipments) == 12
    tasks = [ValidatorService.validate_shipment(s) for s in shipments]
    reports = await asyncio.gather(*tasks)

    assert len(reports) == 12
    for r in reports:
        assert r.authenticity_score is not None

@pytest.mark.asyncio
async def test_manual_override_audit_trail():
    report = await ValidatorService.validate_shipment(ShipmentPayload(**DEMO_PRESETS[1]["payload"]))
    req = OverrideRequest(
        validation_id=report.validation_id,
        shipment_id=report.shipment_id,
        new_status=OverrideStatus.APPROVED_WITH_EXCEPTION,
        override_reason="Authorized lab chemical analysis confirms metal alloy integrity despite tag mismatch.",
        operator_name="Lead Inspector Dr. Elena Rostova"
    )
    audit_entry = audit_service.record_override(req, report)
    assert audit_entry.new_status == "APPROVED_WITH_EXCEPTION"
    assert audit_entry.operator == "Lead Inspector Dr. Elena Rostova"
    assert len(audit_service.get_all_audit_logs()) >= 1
