"""
API Route Handlers for TraceForge 83.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any
import asyncio
import time

from ..models.schemas import (
    ShipmentPayload,
    ValidationReport,
    BatchValidationRequest,
    BatchValidationResponse,
    OverrideRequest,
    AuditLogEntry
)
from ..services.validator_service import ValidatorService
from ..services.audit_service import audit_service

router = APIRouter(prefix="/api/v1", tags=["Validation Engine"])

# In-memory recent validations cache for fast UI retrieval
RECENT_VALIDATIONS: Dict[str, ValidationReport] = {}

# 3 Preset Scenarios for interactive testing and demonstration
DEMO_PRESETS: List[Dict[str, Any]] = [
    {
        "preset_id": "PRESET-1-AUTHENTIC",
        "title": "Case 1: Fully Authentic Aerospace Turbine Blade",
        "category": "AUTHENTIC",
        "description": "Legitimate Titanium Turbine Blade with valid CA hash, continuous checkpoint sequence, matching physical weights, and cleared customs.",
        "payload": {
            "shipment_id": "SHIP-2026-AERO-01",
            "serial_number": "SN-9821-X",
            "sku": "AERO-TURB-TI900",
            "batch_id": "BATCH-2026-A12",
            "manufacturer_id": "MFG-AERO-GLOBAL-01",
            "certificate_hash": "CERT-HASH-9821-VALID",
            "certificate_issue_date": "2026-06-15T09:00:00Z",
            "certificate_expiry_date": "2027-06-15T09:00:00Z",
            "declared_weight_kg": 42.50,
            "destination_facility": "FACILITY-BERLIN-04",
            "dispatch_timestamp": "2026-06-16T08:00:00Z",
            "delivery_timestamp": "2026-06-18T18:00:00Z",
            "checkpoints": [
                {
                    "checkpoint_id": "CP-BER-01",
                    "location_name": "Berlin Logistics Gateway",
                    "latitude": 52.5200,
                    "longitude": 13.4050,
                    "timestamp": "2026-06-16T12:00:00Z",
                    "handler_id": "OPERATOR-DE-44",
                    "signature": "SIG-RSA-DE-991",
                    "event_type": "DISPATCHED"
                },
                {
                    "checkpoint_id": "CP-FRA-02",
                    "location_name": "Frankfurt Cargo Port",
                    "latitude": 50.0379,
                    "longitude": 8.5622,
                    "timestamp": "2026-06-17T06:30:00Z",
                    "handler_id": "OPERATOR-DE-82",
                    "signature": "SIG-RSA-DE-441",
                    "event_type": "PORT_CUSTOMS"
                },
                {
                    "checkpoint_id": "CP-PAR-03",
                    "location_name": "Paris Charles de Gaulle Logistics",
                    "latitude": 49.0097,
                    "longitude": 2.5479,
                    "timestamp": "2026-06-18T14:00:00Z",
                    "handler_id": "OPERATOR-FR-19",
                    "signature": "SIG-RSA-FR-712",
                    "event_type": "WAREHOUSE_INSPECTION"
                }
            ],
            "metadata": {
                "sensor_temp_avg_c": 21.4,
                "shock_sensor_g_force_max": 1.2
            }
        }
    },
    {
        "preset_id": "PRESET-2-FORGED-CERT-CLONE",
        "title": "Case 2: Counterfeit Clone with Forged PKI & Weight Mismatch",
        "category": "COUNTERFEIT",
        "description": "Counterfeit Avionics module presented with an unverified rogue PKI certificate, altered SKU label, and significant alloy weight deficit (-28%).",
        "payload": {
            "shipment_id": "SHIP-2026-COUNTERFEIT-88",
            "serial_number": "SN-5420-Q",
            "sku": "AVION-FAKE-CLONE-99",
            "batch_id": "BATCH-UNKNOWN-TAMPERED",
            "manufacturer_id": "MFG-AVIO-DYNAMICS",
            "certificate_hash": "CERT-FORGED-ROGUE-HASH-404",
            "certificate_issue_date": "2026-01-01T00:00:00Z",
            "certificate_expiry_date": "2026-05-01T00:00:00Z",
            "declared_weight_kg": 2.30,
            "destination_facility": "UNKNOWN-BLACK-MARKET-WH",
            "dispatch_timestamp": "2026-07-02T10:00:00Z",
            "delivery_timestamp": "2026-07-04T12:00:00Z",
            "checkpoints": [
                {
                    "checkpoint_id": "CP-SHANG-01",
                    "location_name": "Shanghai Pudong Cargo Hub",
                    "latitude": 31.1443,
                    "longitude": 121.8083,
                    "timestamp": "2026-07-02T12:00:00Z",
                    "handler_id": "UNKNOWN_AGENT_X",
                    "signature": "INVALID_SIGNATURE_DATA",
                    "event_type": "DISPATCHED"
                },
                {
                    "checkpoint_id": "CP-FRA-02",
                    "location_name": "Frankfurt Cargo Port",
                    "latitude": 50.0379,
                    "longitude": 8.5622,
                    "timestamp": "2026-07-03T18:00:00Z",
                    "handler_id": "OPERATOR-DE-99",
                    "signature": "SIG-SUSPECT-001",
                    "event_type": "PORT_CUSTOMS"
                }
            ],
            "metadata": {
                "tamper_seal_broken": True,
                "rfid_scanned": False
            }
        }
    },
    {
        "preset_id": "PRESET-3-IMPOSSIBLE-TRAVEL",
        "title": "Case 3: Impossible Travel & Clock Skew Chronology Paradox",
        "category": "CHRONOLOGY_TAMPER",
        "description": "Shipment displays simultaneous teleportation across continents (Chicago -> Singapore in 0.5 hours) and inverted delivery timestamps in custody logs.",
        "payload": {
            "shipment_id": "SHIP-2026-PARADOX-77",
            "serial_number": "SN-1104-Z",
            "sku": "HYD-ACTUATOR-H7",
            "batch_id": "BATCH-2026-C04",
            "manufacturer_id": "MFG-HYDRA-SYSTEMS",
            "certificate_hash": "CERT-HASH-1104-VALID",
            "certificate_issue_date": "2026-05-10T15:00:00Z",
            "certificate_expiry_date": "2027-05-10T15:00:00Z",
            "declared_weight_kg": 18.75,
            "destination_facility": "WH-NORTH-AMERICA-01",
            "dispatch_timestamp": "2026-07-10T10:00:00Z",
            "delivery_timestamp": "2026-07-10T16:00:00Z",
            "checkpoints": [
                {
                    "checkpoint_id": "CP-CHI-01",
                    "location_name": "Chicago O'Hare Intermodal Hub",
                    "latitude": 41.9742,
                    "longitude": -87.9073,
                    "timestamp": "2026-07-10T11:00:00Z",
                    "handler_id": "OPERATOR-US-11",
                    "signature": "SIG-VALID-US-10",
                    "event_type": "DISPATCHED"
                },
                {
                    "checkpoint_id": "CP-SGP-02",
                    "location_name": "Singapore Changi Airfreight Centre",
                    "latitude": 1.3644,
                    "longitude": 103.9915,
                    "timestamp": "2026-07-10T11:30:00Z",  # 30 mins later for 15,000 km! (Teleportation)
                    "handler_id": "OPERATOR-SG-55",
                    "signature": "SIG-VALID-SG-99",
                    "event_type": "PORT_CUSTOMS"
                },
                {
                    "checkpoint_id": "CP-LDN-03",
                    "location_name": "London Heathrow Cargo Center",
                    "latitude": 51.4700,
                    "longitude": -0.4543,
                    "timestamp": "2026-07-10T08:00:00Z",  # INVERTED! Occurred before step 1!
                    "handler_id": "OPERATOR-UK-08",
                    "signature": "SIG-VALID-UK-44",
                    "event_type": "WAREHOUSE_INSPECTION"
                }
            ],
            "metadata": {
                "route_deviation_flag": True
            }
        }
    }
]

@router.post("/validate", response_model=ValidationReport)
async def validate_single_shipment(shipment: ShipmentPayload) -> ValidationReport:
    """Validate a single incoming shipment against multi-source evidence and ML anomaly model."""
    report = await ValidatorService.validate_shipment(shipment)
    RECENT_VALIDATIONS[report.validation_id] = report
    return report

@router.post("/validate/batch", response_model=BatchValidationResponse)
async def validate_batch_shipments(request: BatchValidationRequest) -> BatchValidationResponse:
    """Batch validate multiple shipments concurrently with high throughput."""
    start_time = time.perf_counter()
    tasks = [ValidatorService.validate_shipment(s) for s in request.shipments]
    reports: List[ValidationReport] = await asyncio.gather(*tasks)

    for r in reports:
        RECENT_VALIDATIONS[r.validation_id] = r

    authentic_count = sum(1 for r in reports if r.is_authentic)
    flagged_count = len(reports) - authentic_count
    avg_score = round(sum(r.authenticity_score for r in reports) / max(len(reports), 1), 1)
    total_time_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

    return BatchValidationResponse(
        total_processed=len(reports),
        authentic_count=authentic_count,
        flagged_count=flagged_count,
        average_score=avg_score,
        total_time_ms=total_time_ms,
        reports=reports
    )

@router.get("/shipments/presets")
async def get_demo_presets() -> List[Dict[str, Any]]:
    """Return pre-configured test scenarios (Authentic, Counterfeit Clone, Impossible Velocity)."""
    return DEMO_PRESETS

@router.post("/override", response_model=AuditLogEntry)
async def apply_manual_override(request: OverrideRequest) -> AuditLogEntry:
    """Apply an inspector manual override with mandatory audit trail log."""
    report = RECENT_VALIDATIONS.get(request.validation_id)
    entry = audit_service.record_override(request, report)
    if report:
        report.override_status = request.new_status
        report.override_notes = request.override_reason
        report.override_by = request.operator_name
    return entry

@router.get("/audit-log", response_model=List[AuditLogEntry])
async def get_audit_trail() -> List[AuditLogEntry]:
    """Retrieve full chronological audit trail of operator overrides."""
    return audit_service.get_all_audit_logs()

@router.get("/stats")
async def get_system_stats() -> Dict[str, Any]:
    """Retrieve engine statistics and metrics."""
    reports = list(RECENT_VALIDATIONS.values())
    total = len(reports)
    authentic = sum(1 for r in reports if r.is_authentic)
    counterfeits = total - authentic
    avg_latency = round(sum(r.execution_time_ms for r in reports) / max(total, 1), 1) if total > 0 else 0.0

    return {
        "engine_name": "TraceForge 83 Authenticity Engine",
        "status": "OPERATIONAL",
        "total_validated": total,
        "authentic_count": authentic,
        "flagged_counterfeit_count": counterfeits,
        "average_validation_latency_ms": avg_latency,
        "active_data_sources": 4,
        "ml_model_loaded": True
    }
