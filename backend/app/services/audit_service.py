"""
Audit Trail and Manual Override Management Service.
Allows logistics operators to review conflicting data and apply verified overrides with full audit logs.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import uuid
from ..models.schemas import OverrideRequest, OverrideStatus, AuditLogEntry, ValidationReport

class AuditService:
    def __init__(self):
        self._audit_logs: List[AuditLogEntry] = []
        self._report_overrides: Dict[str, Dict[str, Any]] = {}

    def record_override(self, request: OverrideRequest, current_report: Optional[ValidationReport] = None) -> AuditLogEntry:
        prev_status = current_report.override_status.value if current_report else "AUTO_VERIFIED"
        entry = AuditLogEntry(
            audit_id=f"AUDIT-{uuid.uuid4().hex[:8].upper()}",
            validation_id=request.validation_id,
            shipment_id=request.shipment_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=f"STATUS_OVERRIDDEN_TO_{request.new_status.value}",
            previous_status=prev_status,
            new_status=request.new_status.value,
            operator=request.operator_name,
            reason=request.override_reason
        )
        self._audit_logs.insert(0, entry)
        self._report_overrides[request.validation_id] = {
            "status": request.new_status,
            "operator": request.operator_name,
            "reason": request.override_reason,
            "updated_at": entry.timestamp
        }
        return entry

    def get_override_for_report(self, validation_id: str) -> Optional[Dict[str, Any]]:
        return self._report_overrides.get(validation_id)

    def get_all_audit_logs(self) -> List[AuditLogEntry]:
        return self._audit_logs

audit_service = AuditService()
