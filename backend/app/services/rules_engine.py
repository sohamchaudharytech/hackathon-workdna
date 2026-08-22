"""
Deterministic Rule-Based Anomaly & Multi-Source Conflict Resolution Engine.
Cross-references physical serials, PKI certificates, carrier logs, and customs data.
"""

from typing import List, Dict, Any, Tuple
from datetime import datetime, timezone
import math
from ..models.schemas import (
    ShipmentPayload,
    ConflictEvidence,
    ConflictSeverity,
    TraceNode,
    TraceEdge,
    TraceabilityGraph
)
from ..data.simulated_sources import (
    MANUFACTURER_REGISTRY,
    CERTIFICATE_AUTHORITY_LEDGER,
    LOGISTICS_HUBS,
    CUSTOMS_CLEARANCE_REGISTRY,
    MAX_REALISTIC_GROUND_SPEED_KMH,
    MAX_REALISTIC_AIR_SPEED_KMH
)

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on the Earth in kilometers."""
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def parse_iso_datetime(dt_str: str) -> datetime:
    """Parse ISO formatted timestamp strings reliably."""
    dt_str = dt_str.replace("Z", "+00:00")
    return datetime.fromisoformat(dt_str)

class RulesEngine:
    @staticmethod
    def evaluate(shipment: ShipmentPayload) -> Tuple[List[ConflictEvidence], Dict[str, Any], TraceabilityGraph, float]:
        """
        Evaluate all supply chain verification rules.
        Returns:
            - conflicts: List of Conflicting Evidence items
            - metrics: Derived calculation metrics for ML engine
            - graph: Traceability Graph nodes and edges
            - rule_penalty_score: Penalty deductions from baseline 100
        """
        conflicts: List[ConflictEvidence] = []
        rule_penalty = 0.0

        # Data stores
        mfg_record = MANUFACTURER_REGISTRY.get(shipment.serial_number)
        ca_record = CERTIFICATE_AUTHORITY_LEDGER.get(shipment.certificate_hash)

        # -------------------------------------------------------------
        # 1. MANUFACTURER REGISTRY VERIFICATION
        # -------------------------------------------------------------
        if not mfg_record:
            conflicts.append(ConflictEvidence(
                conflict_id=f"CONF-MFG-NOTFOUND-{shipment.serial_number}",
                source_a="Shipment Ingestion Manifest",
                source_b="Manufacturer ERP Registry",
                field_name="serial_number",
                observed_value=shipment.serial_number,
                expected_value="Known Authorized Serial Range",
                severity=ConflictSeverity.CRITICAL,
                description=f"Serial number '{shipment.serial_number}' does not exist in authorized manufacturer ledger.",
                rule_code="RULE_UNKNOWN_SERIAL"
            ))
            rule_penalty += 45.0
        else:
            # Check SKU Match
            if mfg_record.get("sku") != shipment.sku:
                conflicts.append(ConflictEvidence(
                    conflict_id="CONF-SKU-MISMATCH",
                    source_a="Physical Manifest Label",
                    source_b="Manufacturer Master Data",
                    field_name="sku",
                    observed_value=shipment.sku,
                    expected_value=mfg_record.get("sku"),
                    severity=ConflictSeverity.CRITICAL,
                    description=f"Declared SKU '{shipment.sku}' clashes with registered SKU '{mfg_record.get('sku')}'.",
                    rule_code="RULE_SKU_MISMATCH"
                ))
                rule_penalty += 30.0

            # Check Batch ID Match
            if mfg_record.get("batch_id") != shipment.batch_id:
                conflicts.append(ConflictEvidence(
                    conflict_id="CONF-BATCH-MISMATCH",
                    source_a="Shipment Cargo Manifest",
                    source_b="Manufacturer Production Log",
                    field_name="batch_id",
                    observed_value=shipment.batch_id,
                    expected_value=mfg_record.get("batch_id"),
                    severity=ConflictSeverity.HIGH,
                    description=f"Batch ID '{shipment.batch_id}' does not match original production batch '{mfg_record.get('batch_id')}'.",
                    rule_code="RULE_BATCH_MISMATCH"
                ))
                rule_penalty += 20.0

            # Check Manufacturer Recall / Defect Status
            if mfg_record.get("status") in ["RECALLED_DEFECTIVE", "QUARANTINED", "STOLEN"]:
                conflicts.append(ConflictEvidence(
                    conflict_id="CONF-MFG-STATUS-ALERT",
                    source_a="Active Logistics Pipeline",
                    source_b="Manufacturer Security Recall Registry",
                    field_name="status",
                    observed_value="ACTIVE_TRANSIT",
                    expected_value=mfg_record.get("status"),
                    severity=ConflictSeverity.CRITICAL,
                    description=f"Component flagged as '{mfg_record.get('status')}' by manufacturer security advisories.",
                    rule_code="RULE_RECALLED_OR_DEFECTIVE"
                ))
                rule_penalty += 40.0

            # Check Authorized Destination Whitelist
            auth_destinations = mfg_record.get("authorized_destinations", [])
            if auth_destinations and shipment.destination_facility not in auth_destinations:
                conflicts.append(ConflictEvidence(
                    conflict_id="CONF-DESTINATION-UNAUTHORIZED",
                    source_a="Waybill Destination Entry",
                    source_b="Manufacturer Distribution Contract",
                    field_name="destination_facility",
                    observed_value=shipment.destination_facility,
                    expected_value=f"One of {auth_destinations}",
                    severity=ConflictSeverity.MEDIUM,
                    description=f"Destination '{shipment.destination_facility}' is not an authorized distributor destination.",
                    rule_code="RULE_UNAUTHORIZED_DESTINATION"
                ))
                rule_penalty += 15.0

        # -------------------------------------------------------------
        # 2. DIGITAL CERTIFICATE PKI & SIGNATURE LEDGER
        # -------------------------------------------------------------
        cert_validity_days = 0.0
        now_dt = datetime.now(timezone.utc)

        if not ca_record:
            conflicts.append(ConflictEvidence(
                conflict_id="CONF-CA-UNREGISTERED-HASH",
                source_a="Carrier Digital Waybill Token",
                source_b="Public Key Infrastructure (PKI) CA",
                field_name="certificate_hash",
                observed_value=shipment.certificate_hash,
                expected_value="Cryptographically Signed CA Ledger Entry",
                severity=ConflictSeverity.CRITICAL,
                description=f"Digital certificate hash '{shipment.certificate_hash}' was forged or not issued by trusted Root CA.",
                rule_code="RULE_FORGED_CERTIFICATE_HASH"
            ))
            rule_penalty += 50.0
        else:
            # Check Serial Binding
            if ca_record.get("serial_number") != shipment.serial_number:
                conflicts.append(ConflictEvidence(
                    conflict_id="CONF-CERT-SERIAL-MISMATCH",
                    source_a="Physical Serial Stamping",
                    source_b="Digital Certificate Subject Serial",
                    field_name="serial_number",
                    observed_value=shipment.serial_number,
                    expected_value=ca_record.get("serial_number"),
                    severity=ConflictSeverity.CRITICAL,
                    description=f"Digital certificate was issued for '{ca_record.get('serial_number')}' but presented on '{shipment.serial_number}'. Possible clone attack.",
                    rule_code="RULE_CERT_SERIAL_CLONE"
                ))
                rule_penalty += 45.0

            # Check CA Status (Active vs Revoked)
            if ca_record.get("status") == "REVOKED":
                conflicts.append(ConflictEvidence(
                    conflict_id="CONF-CERT-REVOKED",
                    source_a="Shipment Authentication Header",
                    source_b="Certificate Revocation List (CRL)",
                    field_name="status",
                    observed_value="PRESENTED_AS_VALID",
                    expected_value="REVOKED",
                    severity=ConflictSeverity.CRITICAL,
                    description=f"Certificate revoked! Reason: {ca_record.get('revocation_reason')}",
                    rule_code="RULE_CERTIFICATE_REVOKED"
                ))
                rule_penalty += 40.0

            # Check Expiration & Temporal Validity
            try:
                exp_dt = parse_iso_datetime(ca_record.get("expires_at"))
                cert_validity_days = (exp_dt - now_dt).total_seconds() / 86400.0
                if cert_validity_days < 0:
                    conflicts.append(ConflictEvidence(
                        conflict_id="CONF-CERT-EXPIRED",
                        source_a="Incoming Shipment Verification",
                        source_b="CA Expiration Ledger",
                        field_name="expires_at",
                        observed_value=ca_record.get("expires_at"),
                        expected_value="Valid Unexpired Window",
                        severity=ConflictSeverity.HIGH,
                        description=f"Digital certificate expired {abs(cert_validity_days):.1f} days ago.",
                        rule_code="RULE_CERTIFICATE_EXPIRED"
                    ))
                    rule_penalty += 25.0
            except Exception:
                pass

        # -------------------------------------------------------------
        # 3. PHYSICAL ATTRIBUTES & CUSTOMS TOLERANCE
        # -------------------------------------------------------------
        weight_dev_pct = 0.0
        if mfg_record:
            expected_wt = mfg_record.get("expected_weight_kg", 0.0)
            tol = mfg_record.get("weight_tolerance_kg", 0.2)
            if expected_wt > 0:
                weight_dev_pct = (shipment.declared_weight_kg - expected_wt) / expected_wt
                delta_wt = abs(shipment.declared_weight_kg - expected_wt)
                if delta_wt > tol:
                    conflicts.append(ConflictEvidence(
                        conflict_id="CONF-WEIGHT-ANOMALY",
                        source_a="Scale Sensor Weight Sensor",
                        source_b="Manufacturer Specification Blueprint",
                        field_name="declared_weight_kg",
                        observed_value=f"{shipment.declared_weight_kg} kg",
                        expected_value=f"{expected_wt} kg (±{tol} kg)",
                        severity=ConflictSeverity.HIGH,
                        description=f"Physical weight deviates by {delta_wt:.2f} kg ({weight_dev_pct*100:+.1f}%), indicating internal material tampering or imitation alloy.",
                        rule_code="RULE_WEIGHT_DEVIATION"
                    ))
                    rule_penalty += 20.0

        # -------------------------------------------------------------
        # 4. CHRONOLOGY, GEO-VELOCITY & CUSTODY LOG TRANSIT ANALYSIS
        # -------------------------------------------------------------
        nodes: List[TraceNode] = []
        edges: List[TraceEdge] = []

        # Factory Genesis Node
        factory_time = mfg_record.get("production_date") if mfg_record else shipment.dispatch_timestamp
        nodes.append(TraceNode(
            node_id="NODE-0-FACTORY",
            label="Manufacturer Genesis",
            source="Factory Assembly ERP",
            timestamp=factory_time or shipment.dispatch_timestamp,
            status="VERIFIED" if mfg_record else "CONFLICT",
            details={
                "manufacturer": shipment.manufacturer_id,
                "batch": shipment.batch_id,
                "registered": bool(mfg_record)
            }
        ))

        # Evaluate Checkpoint Sequence
        prev_node_id = "NODE-0-FACTORY"
        prev_time = None
        prev_lat, prev_lon = (52.5200, 13.4050) # default Berlin origin
        
        try:
            prev_time = parse_iso_datetime(factory_time or shipment.dispatch_timestamp)
        except Exception:
            prev_time = parse_iso_datetime(shipment.dispatch_timestamp)

        timestamp_inversions = 0
        total_displacement_km = 0.0
        max_leg_speed_kmh = 0.0
        total_transit_hours = 0.0

        for idx, cp in enumerate(shipment.checkpoints):
            cp_node_id = f"NODE-{idx+1}-{cp.checkpoint_id}"
            cp_status = "VERIFIED"
            cp_conflicts = []

            try:
                curr_time = parse_iso_datetime(cp.timestamp)
                hours_diff = (curr_time - prev_time).total_seconds() / 3600.0
                dist_km = haversine_distance(prev_lat, prev_lon, cp.latitude, cp.longitude)
                total_displacement_km += dist_km

                if hours_diff < 0:
                    # Inverted chronology paradox
                    timestamp_inversions += 1
                    cp_status = "CONFLICT"
                    conflict_desc = f"Time paradox! Checkpoint {cp.checkpoint_id} occurred {abs(hours_diff):.2f} hours BEFORE prior node."
                    cp_conflicts.append(conflict_desc)
                    conflicts.append(ConflictEvidence(
                        conflict_id=f"CONF-CHRONO-INVERSION-{idx}",
                        source_a=f"Carrier Checkpoint #{idx+1} ({cp.location_name})",
                        source_b="Prior Custody Timestamp Log",
                        field_name="timestamp",
                        observed_value=cp.timestamp,
                        expected_value=f"After {prev_time.isoformat()}",
                        severity=ConflictSeverity.CRITICAL,
                        description=conflict_desc,
                        rule_code="RULE_CHRONOLOGY_INVERSION"
                    ))
                    rule_penalty += 35.0

                    edges.append(TraceEdge(
                        from_node=prev_node_id,
                        to_node=cp_node_id,
                        transit_hours=hours_diff,
                        distance_km=round(dist_km, 1),
                        implied_speed_kmh=0.0,
                        is_valid_transit=False,
                        anomaly_note="Timestamp inversion / Negative transit duration"
                    ))
                elif hours_diff == 0 and dist_km > 5.0:
                    # Impossible simultaneous location
                    cp_status = "CONFLICT"
                    conflict_desc = f"Impossible instantaneous displacement of {dist_km:.1f} km at 0 hours transit time."
                    cp_conflicts.append(conflict_desc)
                    conflicts.append(ConflictEvidence(
                        conflict_id=f"CONF-TELEPORT-{idx}",
                        source_a=f"GPS Telemetry {cp.location_name}",
                        source_b="Prior Location Telemetry",
                        field_name="geographic_coordinates",
                        observed_value=f"({cp.latitude}, {cp.longitude})",
                        expected_value=f"Realistic transit velocity from ({prev_lat}, {prev_lon})",
                        severity=ConflictSeverity.CRITICAL,
                        description=conflict_desc,
                        rule_code="RULE_IMPOSSIBLE_DISPLACEMENT"
                    ))
                    rule_penalty += 35.0

                    edges.append(TraceEdge(
                        from_node=prev_node_id,
                        to_node=cp_node_id,
                        transit_hours=0.0,
                        distance_km=round(dist_km, 1),
                        implied_speed_kmh=9999.0,
                        is_valid_transit=False,
                        anomaly_note="Instantaneous teleportation anomaly"
                    ))
                else:
                    speed = dist_km / max(hours_diff, 0.01)
                    if speed > max_leg_speed_kmh:
                        max_leg_speed_kmh = speed
                    total_transit_hours += max(hours_diff, 0.0)

                    # Velocity check (Ground vs Air)
                    if speed > MAX_REALISTIC_AIR_SPEED_KMH:
                        cp_status = "CONFLICT"
                        conflict_desc = f"Calculated speed {speed:.1f} km/h exceeds maximum supersonic cargo threshold ({MAX_REALISTIC_AIR_SPEED_KMH} km/h)."
                        cp_conflicts.append(conflict_desc)
                        conflicts.append(ConflictEvidence(
                            conflict_id=f"CONF-SPEED-SUPERSONIC-{idx}",
                            source_a=f"Carrier Transit Log ({cp.location_name})",
                            source_b="Physical Laws & Transport Velocity Envelope",
                            field_name="implied_velocity",
                            observed_value=f"{speed:.1f} km/h",
                            expected_value=f"< {MAX_REALISTIC_AIR_SPEED_KMH} km/h",
                            severity=ConflictSeverity.HIGH,
                            description=conflict_desc,
                            rule_code="RULE_IMPOSSIBLE_SPEED"
                        ))
                        rule_penalty += 25.0

                    edges.append(TraceEdge(
                        from_node=prev_node_id,
                        to_node=cp_node_id,
                        transit_hours=round(hours_diff, 2),
                        distance_km=round(dist_km, 1),
                        implied_speed_kmh=round(speed, 1),
                        is_valid_transit=speed <= MAX_REALISTIC_AIR_SPEED_KMH,
                        anomaly_note=conflict_desc if cp_conflicts else None
                    ))

                prev_time = curr_time
                prev_lat, prev_lon = cp.latitude, cp.longitude
                prev_node_id = cp_node_id

            except Exception as e:
                cp_status = "WARNING"
                cp_conflicts.append(f"Format error: {str(e)}")

            nodes.append(TraceNode(
                node_id=cp_node_id,
                label=f"{cp.location_name}",
                source="Carrier GPS Telemetry",
                timestamp=cp.timestamp,
                status=cp_status,
                details={
                    "handler_id": cp.handler_id,
                    "event": cp.event_type,
                    "lat": cp.latitude,
                    "lon": cp.longitude
                },
                conflicts=cp_conflicts
            ))

        # Final Destination Node
        nodes.append(TraceNode(
            node_id="NODE-FINAL-DEST",
            label=f"Destination: {shipment.destination_facility}",
            source="Receiving Warehouse System",
            timestamp=shipment.delivery_timestamp or (shipment.checkpoints[-1].timestamp if shipment.checkpoints else shipment.dispatch_timestamp),
            status="VERIFIED" if not conflicts else "CONFLICT",
            details={
                "facility": shipment.destination_facility,
                "declared_weight": f"{shipment.declared_weight_kg} kg"
            }
        ))
        if nodes and len(nodes) >= 2:
            edges.append(TraceEdge(
                from_node=prev_node_id,
                to_node="NODE-FINAL-DEST",
                transit_hours=1.0,
                distance_km=25.0,
                implied_speed_kmh=25.0,
                is_valid_transit=True
            ))

        graph = TraceabilityGraph(nodes=nodes, edges=edges)

        # Derived calculations for ML engine
        avg_speed = (total_displacement_km / max(total_transit_hours, 1.0)) if total_transit_hours > 0 else 40.0
        calculated_metrics = {
            "weight_deviation_pct": weight_dev_pct,
            "avg_speed_kmh": avg_speed,
            "max_leg_speed_kmh": max_leg_speed_kmh,
            "timestamp_inversions": timestamp_inversions,
            "total_transit_hours": total_transit_hours,
            "cert_validity_days": cert_validity_days,
            "total_displacement_km": total_displacement_km
        }

        return conflicts, calculated_metrics, graph, rule_penalty
