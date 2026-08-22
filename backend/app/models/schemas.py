from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class RiskLevel(str, Enum):
    AUTHENTIC = "AUTHENTIC"
    LOW_RISK = "LOW_RISK"
    MEDIUM_RISK = "MEDIUM_RISK"
    HIGH_RISK = "HIGH_RISK"
    COUNTERFEIT_DETECTED = "COUNTERFEIT_DETECTED"

class ConflictSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class OverrideStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED_WITH_EXCEPTION = "APPROVED_WITH_EXCEPTION"
    REJECTED_COUNTERFEIT = "REJECTED_COUNTERFEIT"
    AUTO_VERIFIED = "AUTO_VERIFIED"

class CheckpointRecord(BaseModel):
    checkpoint_id: str
    location_name: str
    latitude: float
    longitude: float
    timestamp: str  # ISO Format
    handler_id: str
    signature: str
    event_type: str = "IN_TRANSIT"  # MANUFACTURED, DISPATCHED, PORT_CUSTOMS, WAREHOUSE_INSPECTION, DELIVERED

class ShipmentPayload(BaseModel):
    shipment_id: str
    serial_number: str
    sku: str
    batch_id: str
    manufacturer_id: str
    certificate_hash: str
    certificate_issue_date: str
    certificate_expiry_date: str
    declared_weight_kg: float
    destination_facility: str
    dispatch_timestamp: str
    delivery_timestamp: Optional[str] = None
    checkpoints: List[CheckpointRecord] = []
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ConflictEvidence(BaseModel):
    conflict_id: str
    source_a: str
    source_b: str
    field_name: str
    observed_value: Any
    expected_value: Any
    severity: ConflictSeverity
    description: str
    rule_code: str

class MLAnomalyAssessment(BaseModel):
    anomaly_score: float  # 0.0 to 1.0 (higher is more anomalous)
    is_anomaly: bool
    fraud_probability: float
    top_risk_features: List[Dict[str, Any]]
    confidence: float

class TraceNode(BaseModel):
    node_id: str
    label: str
    source: str
    timestamp: str
    status: str  # VERIFIED, CONFLICT, WARNING, PENDING
    details: Dict[str, Any] = Field(default_factory=dict)
    conflicts: List[str] = []

class TraceEdge(BaseModel):
    from_node: str
    to_node: str
    transit_hours: Optional[float] = None
    distance_km: Optional[float] = None
    implied_speed_kmh: Optional[float] = None
    is_valid_transit: bool = True
    anomaly_note: Optional[str] = None

class TraceabilityGraph(BaseModel):
    nodes: List[TraceNode]
    edges: List[TraceEdge]

class ValidationReport(BaseModel):
    validation_id: str
    shipment_id: str
    serial_number: str
    authenticity_score: float  # 0 to 100
    risk_level: RiskLevel
    is_authentic: bool
    decision_summary: str
    conflicting_evidence: List[ConflictEvidence]
    conflict_count: int
    rule_score: float
    ml_assessment: MLAnomalyAssessment
    traceability_graph: TraceabilityGraph
    validated_at: str
    execution_time_ms: float
    override_status: OverrideStatus = OverrideStatus.AUTO_VERIFIED
    override_notes: Optional[str] = None
    override_by: Optional[str] = None

class BatchValidationRequest(BaseModel):
    shipments: List[ShipmentPayload]

class BatchValidationResponse(BaseModel):
    total_processed: int
    authentic_count: int
    flagged_count: int
    average_score: float
    total_time_ms: float
    reports: List[ValidationReport]

class OverrideRequest(BaseModel):
    validation_id: str
    shipment_id: str
    new_status: OverrideStatus
    override_reason: str
    operator_name: str

class AuditLogEntry(BaseModel):
    audit_id: str
    validation_id: str
    shipment_id: str
    timestamp: str
    action: str
    previous_status: str
    new_status: str
    operator: str
    reason: str
