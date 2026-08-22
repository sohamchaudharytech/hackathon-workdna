"""
Simulated authoritative enterprise data sources:
1. Manufacturer ERP Registry (Authorized serials, production timestamps, true SKUs, cryptographic hashes)
2. Certificate Authority (PKI ledger with validity periods, revocation lists, signature algorithms)
3. Carrier / Logistics Network (Known hubs, maximum transit speed thresholds, route geofences)
4. Customs / Port Gateways (Declared manifest logs, weight tolerances, clearance records)
"""

from typing import Dict, Any, Optional
import hashlib

# 1. Authoritative Manufacturer Registry
MANUFACTURER_REGISTRY: Dict[str, Dict[str, Any]] = {
    # Authentic Titanium Turbine Blade SN-9821-X
    "SN-9821-X": {
        "serial_number": "SN-9821-X",
        "sku": "AERO-TURB-TI900",
        "batch_id": "BATCH-2026-A12",
        "manufacturer_id": "MFG-AERO-GLOBAL-01",
        "production_date": "2026-06-15T08:30:00Z",
        "expected_weight_kg": 42.50,
        "weight_tolerance_kg": 0.50,
        "status": "RELEASED",
        "public_key_fingerprint": "SHA256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
        "authorized_destinations": ["WH-NORTH-AMERICA-01", "FACILITY-BERLIN-04", "PORT-SINGAPORE-09"]
    },
    # Authentic Avionics Controller Module SN-5420-Q
    "SN-5420-Q": {
        "serial_number": "SN-5420-Q",
        "sku": "AVION-CTRL-MOD4",
        "batch_id": "BATCH-2026-B88",
        "manufacturer_id": "MFG-AVIO-DYNAMICS",
        "production_date": "2026-07-01T10:00:00Z",
        "expected_weight_kg": 3.20,
        "weight_tolerance_kg": 0.10,
        "status": "RELEASED",
        "public_key_fingerprint": "SHA256:4d83e2098b1dca50a972c72b2203e8529b4e332145e43a6d0c4a45ffc8710329",
        "authorized_destinations": ["WH-EU-CENTRAL-02", "ASSEMBLY-TOKYO-07"]
    },
    # Genuine Hydraulic Actuator SN-1104-Z
    "SN-1104-Z": {
        "serial_number": "SN-1104-Z",
        "sku": "HYD-ACTUATOR-H7",
        "batch_id": "BATCH-2026-C04",
        "manufacturer_id": "MFG-HYDRA-SYSTEMS",
        "production_date": "2026-05-10T14:20:00Z",
        "expected_weight_kg": 18.75,
        "weight_tolerance_kg": 0.30,
        "status": "RELEASED",
        "public_key_fingerprint": "SHA256:9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b",
        "authorized_destinations": ["WH-NORTH-AMERICA-01", "WH-EU-CENTRAL-02"]
    },
    # Stolen/Defective Batch Serial - SN-6632-F
    "SN-6632-F": {
        "serial_number": "SN-6632-F",
        "sku": "RADAR-TRANSCEIVER-X",
        "batch_id": "BATCH-2026-REVOKED-99",
        "manufacturer_id": "MFG-DEFENSE-RADAR",
        "production_date": "2026-04-12T09:00:00Z",
        "expected_weight_kg": 8.40,
        "weight_tolerance_kg": 0.15,
        "status": "RECALLED_DEFECTIVE",
        "public_key_fingerprint": "SHA256:11223344556677889900aabbccddeeff00112233445566778899aabbccddeeff",
        "authorized_destinations": []
    }
}

# 2. Authoritative Digital Certificate Authority PKI Ledger
CERTIFICATE_AUTHORITY_LEDGER: Dict[str, Dict[str, Any]] = {
    # Authentic Certificate for SN-9821-X
    "CERT-HASH-9821-VALID": {
        "cert_id": "CERT-2026-AERO-9821",
        "serial_number": "SN-9821-X",
        "issuer": "Global Aerospace PKI Root CA",
        "issued_at": "2026-06-15T09:00:00Z",
        "expires_at": "2027-06-15T09:00:00Z",
        "status": "ACTIVE",
        "revocation_reason": None,
        "algorithm": "ECDSA_P384_SHA384",
        "allowed_sku": "AERO-TURB-TI900"
    },
    # Authentic Certificate for SN-5420-Q
    "CERT-HASH-5420-VALID": {
        "cert_id": "CERT-2026-AVIO-5420",
        "serial_number": "SN-5420-Q",
        "issuer": "Avionics Safety Trust Network",
        "issued_at": "2026-07-01T11:00:00Z",
        "expires_at": "2028-07-01T11:00:00Z",
        "status": "ACTIVE",
        "revocation_reason": None,
        "algorithm": "RSA_4096_SHA256",
        "allowed_sku": "AVION-CTRL-MOD4"
    },
    # Authentic Certificate for SN-1104-Z
    "CERT-HASH-1104-VALID": {
        "cert_id": "CERT-2026-HYD-1104",
        "serial_number": "SN-1104-Z",
        "issuer": "Industrial Hydraulics Trust Authority",
        "issued_at": "2026-05-10T15:00:00Z",
        "expires_at": "2027-05-10T15:00:00Z",
        "status": "ACTIVE",
        "revocation_reason": None,
        "algorithm": "ECDSA_P256_SHA256",
        "allowed_sku": "HYD-ACTUATOR-H7"
    },
    # Revoked Certificate
    "CERT-HASH-REVOKED-99": {
        "cert_id": "CERT-2026-REVOKED-99",
        "serial_number": "SN-6632-F",
        "issuer": "Defense Standards Security CA",
        "issued_at": "2026-04-12T10:00:00Z",
        "expires_at": "2027-04-12T10:00:00Z",
        "status": "REVOKED",
        "revocation_reason": "SECURITY_COMPROMISE_SUSPECTED_COUNTERFEIT_CLONE",
        "algorithm": "ECDSA_P384_SHA384",
        "allowed_sku": "RADAR-TRANSCEIVER-X"
    }
}

# 3. Known Logistics Hub Coordinates & Physical Velocity Limits
LOGISTICS_HUBS: Dict[str, Dict[str, Any]] = {
    "HUB-BERLIN": {"name": "Berlin Logistics Gateway", "lat": 52.5200, "lon": 13.4050, "country": "DE"},
    "HUB-FRANKFURT": {"name": "Frankfurt Cargo Port", "lat": 50.0379, "lon": 8.5622, "country": "DE"},
    "HUB-PARIS": {"name": "Paris Charles de Gaulle Logistics", "lat": 49.0097, "lon": 2.5479, "country": "FR"},
    "HUB-LONDON": {"name": "London Heathrow Cargo Center", "lat": 51.4700, "lon": -0.4543, "country": "UK"},
    "HUB-CHICAGO": {"name": "Chicago O'Hare Intermodal Hub", "lat": 41.9742, "lon": -87.9073, "country": "US"},
    "HUB-NEWYORK": {"name": "JFK Air Cargo Complex", "lat": 40.6413, "lon": -73.7781, "country": "US"},
    "HUB-SINGAPORE": {"name": "Singapore Changi Airfreight Centre", "lat": 1.3644, "lon": 103.9915, "country": "SG"},
    "HUB-SHANGHAI": {"name": "Shanghai Pudong Cargo Hub", "lat": 31.1443, "lon": 121.8083, "country": "CN"},
    "HUB-TOKYO": {"name": "Tokyo Narita Logistics Facility", "lat": 35.7720, "lon": 140.3929, "country": "JP"}
}

# Max realistic velocity in km/h (Commercial air freight maximum realistic door-to-door speed ~900km/h)
MAX_REALISTIC_GROUND_SPEED_KMH = 130.0
MAX_REALISTIC_AIR_SPEED_KMH = 950.0

# 4. Customs / Port Clearance Database
CUSTOMS_CLEARANCE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "CUSTOMS-DE-8821": {
        "serial_number": "SN-9821-X",
        "port_code": "DE-BER",
        "manifest_weight_kg": 42.50,
        "declared_hs_code": "8411.91.00",
        "clearance_status": "CLEARED",
        "clearance_timestamp": "2026-06-18T14:30:00Z"
    },
    "CUSTOMS-US-5420": {
        "serial_number": "SN-5420-Q",
        "port_code": "US-ORD",
        "manifest_weight_kg": 3.20,
        "declared_hs_code": "8803.30.00",
        "clearance_status": "CLEARED",
        "clearance_timestamp": "2026-07-05T18:00:00Z"
    }
}
