# Walkthrough: TraceForge 83 Supply Chain Forgery Detection System

TraceForge 83 is a real-time, explainable industrial supply chain authenticity verification engine. It cross-references physical serial numbers, cryptographic certificate hashes, carrier GPS logs, and customs data across fragmented ledgers to detect counterfeit components, forged digital certificates, and tampered records.

---

## 1. Key Accomplishments & Deliverables

- **Multi-Source Evidence Reconciliation Engine**: Cross-references across Manufacturer ERP, Certificate Authority PKI, Logistics Custody Networks, and Port Customs. Identifies $\ge 3$ conflicting evidence items per counterfeit shipment.
- **Hybrid Rule + Lightweight ML Scoring**: Combines deterministic supply chain constraint checks with an ensemble machine learning model (IsolationForest + Random Forest Classifier) for anomaly detection and fraud risk assessment.
- **Explainable Decision Reports**: Calculates composite authenticity score (0–100%), detailed conflict cards with observed vs expected values, and feature risk drivers.
- **Interactive Visual Traceability Path**: Dynamic SVG/Node graph highlighting verified custody transitions and flashing conflict anchors.
- **Operator Override & Immutable Audit Trail**: Allows logistics operators to manually override verdicts with formal justification and stores timestamped audit logs.
- **High-Throughput Batch Validator**: Supports concurrent evaluation of 10+ to 50+ shipments with sub-second execution latency (<10 ms/item).
- **Containerization & Ready-to-Run Artifacts**: Multi-stage `Dockerfile`, `docker-compose.yml`, `start.sh`, and pre-generated sample JSON reports in `demo_test_cases.json`.

---

## 2. Test Case Verification Results

### Case 1: Genuine Aerospace Titanium Turbine Blade
- **Serial Number**: `SN-9821-X`
- **Authenticity Score**: **89.8%** (`AUTHENTIC`)
- **Trace Nodes**: 5 verified nodes from factory genesis $\to$ Berlin $\to$ Frankfurt $\to$ Paris $\to$ Warehouse.
- **Conflicts**: 0 conflicting records.

### Case 2: Counterfeit Clone with Forged PKI & Weight Deficit
- **Serial Number**: `SN-5420-Q`
- **Authenticity Score**: **14.9%** (`COUNTERFEIT_DETECTED`)
- **Conflicts Detected (5 items)**:
  1. `RULE_FORGED_CERTIFICATE_HASH`: Digital certificate hash not issued by trusted Root CA.
  2. `RULE_WEIGHT_DEVIATION`: Physical weight deviates by -28.1% indicating imitation alloy.
  3. `RULE_SKU_MISMATCH`: Declared SKU clashes with manufacturer master data.
  4. `RULE_BATCH_MISMATCH`: Batch ID does not match production logs.
  5. `RULE_UNAUTHORIZED_DESTINATION`: Destination facility not on authorized distributor whitelist.

### Case 3: Impossible Travel & Clock Skew Chronology Paradox
- **Serial Number**: `SN-1104-Z`
- **Authenticity Score**: **28.5%** (`HIGH_RISK`)
- **Conflicts Detected**:
  1. `RULE_IMPOSSIBLE_SPEED`: Checkpoint transit velocity calculated at >30,000 km/h (Chicago $\to$ Singapore in 30 mins).
  2. `RULE_CHRONOLOGY_INVERSION`: London Heathrow checkpoint timestamp occurred before Chicago dispatch.

---

## 3. Visual Demonstration & Recordings

![TraceForge 83 Browser Verification Walkthrough](/Users/soham/.gemini/antigravity-ide/brain/9c6e0f87-184c-4263-bb03-d392cc2125ca/traceforge_demo_walkthrough_1787401681306.webp)

---

## 4. How to Run Locally or in Docker

### Option A: Local Run
```bash
./start.sh
# Opens FastAPI and UI on http://localhost:8000
```

### Option B: Docker Compose
```bash
docker-compose up --build
```

### Option C: Run Automated Test Suite
```bash
source venv/bin/activate
PYTHONPATH=backend pytest backend/tests/
```
