/**
 * TraceForge 83 Client Application Logic
 * Manages Preset Scenarios, Real-Time Validation API Calls, Visual Traceability Graph Rendering,
 * Gauge Animations, Batch Execution, and Manual Overrides with Audit Logging.
 */

let currentReport = null;
let demoPresets = [];

// DOM Elements
const presetListContainer = document.getElementById('presetListContainer');
const shipmentPayloadInput = document.getElementById('shipmentPayloadInput');
const runValidationBtn = document.getElementById('runValidationBtn');
const formatJsonBtn = document.getElementById('formatJsonBtn');
const loadingOverlay = document.getElementById('loadingOverlay');
const reportDashboard = document.getElementById('reportDashboard');
const batchDashboard = document.getElementById('batchDashboard');
const tabSingle = document.getElementById('tabSingle');
const tabBatch = document.getElementById('tabBatch');
const singleSection = document.getElementById('singleSection');
const batchSection = document.getElementById('batchSection');
const runBatchBtn = document.getElementById('runBatchBtn');
const batchSizeSelect = document.getElementById('batchSizeSelect');

// Score Displays
const scoreDisplay = document.getElementById('scoreDisplay');
const gaugeCircle = document.getElementById('gaugeCircle');
const verdictTitle = document.getElementById('verdictTitle');
const riskBadge = document.getElementById('riskBadge');
const overrideBadge = document.getElementById('overrideBadge');
const decisionSummary = document.getElementById('decisionSummary');
const metricSerial = document.getElementById('metricSerial');
const metricRuleScore = document.getElementById('metricRuleScore');
const metricMlRisk = document.getElementById('metricMlRisk');
const metricLatency = document.getElementById('metricLatency');
const traceTimeline = document.getElementById('traceTimeline');
const traceNodeCount = document.getElementById('traceNodeCount');
const conflictList = document.getElementById('conflictList');
const conflictCountBadge = document.getElementById('conflictCountBadge');
const mlDriversList = document.getElementById('mlDriversList');
const mlConfidence = document.getElementById('mlConfidence');

// Modal Elements
const manualOverrideBtn = document.getElementById('manualOverrideBtn');
const exportJsonReportBtn = document.getElementById('exportJsonReportBtn');
const overrideModal = document.getElementById('overrideModal');
const closeOverrideModal = document.getElementById('closeOverrideModal');
const cancelOverrideBtn = document.getElementById('cancelOverrideBtn');
const overrideForm = document.getElementById('overrideForm');
const openAuditBtn = document.getElementById('openAuditBtn');
const auditModal = document.getElementById('auditModal');
const closeAuditModal = document.getElementById('closeAuditModal');
const auditLogsContainer = document.getElementById('auditLogsContainer');

// Initialize Application
async function initApp() {
  setupEventListeners();
  await loadPresets();
}

function setupEventListeners() {
  // Tab Switching
  tabSingle.addEventListener('click', () => {
    tabSingle.classList.add('active');
    tabBatch.classList.remove('active');
    singleSection.style.display = 'block';
    batchSection.style.display = 'none';
    reportDashboard.style.display = 'flex';
    batchDashboard.style.display = 'none';
  });

  tabBatch.addEventListener('click', () => {
    tabBatch.classList.add('active');
    tabSingle.classList.remove('active');
    singleSection.style.display = 'none';
    batchSection.style.display = 'block';
    reportDashboard.style.display = 'none';
    batchDashboard.style.display = 'flex';
  });

  // Action Buttons
  runValidationBtn.addEventListener('click', handleSingleValidation);
  runBatchBtn.addEventListener('click', handleBatchValidation);
  formatJsonBtn.addEventListener('click', formatPayloadInput);
  exportJsonReportBtn.addEventListener('click', exportReportJson);

  // Overrides & Audit
  manualOverrideBtn.addEventListener('click', () => {
    if (!currentReport) {
      alert('Please perform a validation first.');
      return;
    }
    overrideModal.classList.add('show');
  });

  closeOverrideModal.addEventListener('click', () => overrideModal.classList.remove('show'));
  cancelOverrideBtn.addEventListener('click', () => overrideModal.classList.remove('show'));
  overrideForm.addEventListener('submit', handleOverrideSubmit);

  openAuditBtn.addEventListener('click', async () => {
    await fetchAndRenderAuditLogs();
    auditModal.classList.add('show');
  });
  closeAuditModal.addEventListener('click', () => auditModal.classList.remove('show'));
}

async function loadPresets() {
  try {
    const res = await fetch('/api/v1/shipments/presets');
    demoPresets = await res.json();
    renderPresetsList();
    if (demoPresets.length > 0) {
      selectPreset(0);
    }
  } catch (err) {
    console.error('Failed to load demo presets:', err);
  }
}

function renderPresetsList() {
  presetListContainer.innerHTML = '';
  demoPresets.forEach((preset, idx) => {
    const card = document.createElement('div');
    card.className = `preset-card ${idx === 0 ? 'active' : ''}`;
    card.id = `preset-${idx}`;

    let badgeClass = 'badge-authentic';
    if (preset.category === 'COUNTERFEIT') badgeClass = 'badge-counterfeit';
    if (preset.category === 'CHRONOLOGY_TAMPER') badgeClass = 'badge-anomaly';

    card.innerHTML = `
      <div class="preset-header">
        <span class="preset-name">${preset.title.split(':')[1] || preset.title}</span>
        <span class="badge ${badgeClass}">${preset.category}</span>
      </div>
      <div class="preset-desc">${preset.description}</div>
    `;

    card.addEventListener('click', () => selectPreset(idx));
    presetListContainer.appendChild(card);
  });
}

function selectPreset(index) {
  document.querySelectorAll('.preset-card').forEach((c, i) => {
    c.classList.toggle('active', i === index);
  });
  const preset = demoPresets[index];
  if (preset) {
    shipmentPayloadInput.value = JSON.stringify(preset.payload, null, 2);
    // Auto-run validation for swift demonstration
    handleSingleValidation();
  }
}

function formatPayloadInput() {
  try {
    const parsed = JSON.parse(shipmentPayloadInput.value);
    shipmentPayloadInput.value = JSON.stringify(parsed, null, 2);
  } catch (e) {
    alert('Invalid JSON syntax: ' + e.message);
  }
}

async function handleSingleValidation() {
  let payload;
  try {
    payload = JSON.parse(shipmentPayloadInput.value);
  } catch (e) {
    alert('Invalid JSON syntax in payload. Please fix before verifying.');
    return;
  }

  loadingOverlay.style.display = 'block';
  reportDashboard.style.opacity = '0.4';

  try {
    const res = await fetch('/api/v1/validate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.detail || 'Validation failed');
    }

    currentReport = await res.json();
    renderValidationReport(currentReport);
  } catch (err) {
    alert('Validation Error: ' + err.message);
  } finally {
    loadingOverlay.style.display = 'none';
    reportDashboard.style.opacity = '1';
  }
}

function renderValidationReport(report) {
  // 1. Gauge Score & Colors
  const score = report.authenticity_score;
  scoreDisplay.textContent = score.toFixed(1);

  // Circumference 2 * PI * 70 = 439.82
  const maxDash = 440;
  const offset = maxDash - (maxDash * (score / 100));
  gaugeCircle.style.strokeDashoffset = offset;

  let strokeColor = 'var(--accent-emerald)';
  let riskClass = 'badge-authentic';

  if (score < 40) {
    strokeColor = 'var(--accent-rose)';
    riskClass = 'badge-counterfeit';
  } else if (score < 75) {
    strokeColor = 'var(--accent-amber)';
    riskClass = 'badge-anomaly';
  }

  gaugeCircle.style.stroke = strokeColor;

  // 2. Verdict & Badges
  verdictTitle.textContent = report.risk_level.replace('_', ' ');
  riskBadge.className = `badge ${riskClass}`;
  riskBadge.textContent = report.risk_level;

  if (report.override_status && report.override_status !== 'AUTO_VERIFIED') {
    overrideBadge.style.display = 'inline-block';
    overrideBadge.textContent = `OVERRIDE: ${report.override_status}`;
  } else {
    overrideBadge.style.display = 'none';
  }

  decisionSummary.textContent = report.decision_summary;

  // 3. Metrics Row
  metricSerial.textContent = report.serial_number;
  metricRuleScore.textContent = `${report.rule_score} / 100`;
  metricMlRisk.textContent = `${(report.ml_assessment.fraud_probability * 100).toFixed(1)}%`;
  metricLatency.textContent = `${report.execution_time_ms} ms`;

  // 4. Render Visual Traceability Path
  renderTraceabilityGraph(report.traceability_graph, report.conflicting_evidence);

  // 5. Render Conflicting Evidence List
  renderConflicts(report.conflicting_evidence);

  // 6. Render ML Drivers
  renderMlDrivers(report.ml_assessment);
}

function renderTraceabilityGraph(graph, conflicts) {
  traceTimeline.innerHTML = '';
  traceNodeCount.textContent = `${graph.nodes.length} Nodes • ${graph.edges.length} Vectors`;

  graph.nodes.forEach((node, idx) => {
    const nodeEl = document.createElement('div');
    const isConflict = node.status === 'CONFLICT';
    nodeEl.className = `trace-node ${isConflict ? 'conflict' : 'verified'}`;

    let icon = 'ph-check-circle';
    if (idx === 0) icon = 'ph-factory';
    else if (idx === graph.nodes.length - 1) icon = 'ph-warehouse';
    else if (isConflict) icon = 'ph-warning-octagon';
    else icon = 'ph-truck';

    nodeEl.innerHTML = `
      <div class="node-icon-circle" title="${node.source}">
        <i class="ph-bold ${icon}"></i>
      </div>
      <div class="node-label">${node.label}</div>
      <div class="node-sub">${new Date(node.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
    `;

    traceTimeline.appendChild(nodeEl);
  });
}

function renderConflicts(conflicts) {
  conflictCountBadge.textContent = `${conflicts.length} Conflict${conflicts.length === 1 ? '' : 's'}`;
  conflictCountBadge.className = conflicts.length > 0 ? 'badge badge-counterfeit' : 'badge badge-authentic';

  if (conflicts.length === 0) {
    conflictList.innerHTML = `
      <div style="text-align: center; padding: 2rem; color: var(--text-muted); font-size: 0.85rem;">
        <i class="ph-bold ph-shield-check" style="font-size: 2rem; color: var(--accent-emerald); display: block; margin-bottom: 0.5rem;"></i>
        Zero conflicting records found across ERP, Certificate Authority, Carrier GPS & Customs databases.
      </div>
    `;
    return;
  }

  conflictList.innerHTML = '';
  conflicts.forEach(c => {
    const item = document.createElement('div');
    item.className = 'conflict-item';
    item.innerHTML = `
      <div class="conflict-item-header">
        <div class="conflict-title-wrap">
          <i class="ph-bold ph-warning" style="color: var(--accent-rose);"></i>
          <strong style="font-size: 0.88rem; color: var(--text-highlight);">${c.rule_code}</strong>
        </div>
        <span class="badge badge-counterfeit">${c.severity}</span>
      </div>
      <p style="font-size: 0.82rem; color: var(--text-main); margin-bottom: 0.5rem;">
        ${c.description}
      </p>
      <div class="conflict-sources-box">
        <div class="source-col">
          <strong>Source A: ${c.source_a}</strong>
          <span style="color: var(--accent-rose); font-family: monospace;">${JSON.stringify(c.observed_value)}</span>
        </div>
        <div class="source-col">
          <strong>Source B: ${c.source_b}</strong>
          <span style="color: var(--accent-emerald); font-family: monospace;">${JSON.stringify(c.expected_value)}</span>
        </div>
      </div>
    `;
    conflictList.appendChild(item);
  });
}

function renderMlDrivers(ml) {
  mlConfidence.textContent = `Model Confidence: ${(ml.confidence * 100).toFixed(1)}%`;
  mlDriversList.innerHTML = '';

  if (!ml.top_risk_features || ml.top_risk_features.length === 0) {
    mlDriversList.innerHTML = `
      <div class="metric-card" style="grid-column: 1/-1;">
        <div class="metric-key">Anomaly Status</div>
        <div class="metric-val" style="color: var(--accent-emerald); font-size: 0.9rem;">
          Normal Baseline • No statistical fraud indicators detected (Anomaly Score: ${(ml.anomaly_score * 100).toFixed(1)}%)
        </div>
      </div>
    `;
    return;
  }

  ml.top_risk_features.forEach(feat => {
    const card = document.createElement('div');
    card.className = 'metric-card';
    card.style.borderLeft = '3px solid var(--accent-amber)';
    card.innerHTML = `
      <div class="metric-key">${feat.feature.replace(/_/g, ' ')}</div>
      <div style="font-size: 0.82rem; color: var(--accent-rose); font-weight: 600; margin-bottom: 0.2rem;">
        ${feat.risk_driver}
      </div>
      <div style="font-size: 0.72rem; color: var(--text-dim);">
        Observed Metric Value: <strong>${feat.observed_value}</strong>
      </div>
    `;
    mlDriversList.appendChild(card);
  });
}

async function handleOverrideSubmit(e) {
  e.preventDefault();
  if (!currentReport) return;

  const payload = {
    validation_id: currentReport.validation_id,
    shipment_id: currentReport.shipment_id,
    new_status: document.getElementById('overrideStatusSelect').value,
    operator_name: document.getElementById('overrideOperatorInput').value,
    override_reason: document.getElementById('overrideReasonInput').value
  };

  try {
    const res = await fetch('/api/v1/override', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) throw new Error('Override failed to submit');

    const result = await res.json();
    overrideModal.classList.remove('show');
    currentReport.override_status = payload.new_status;
    currentReport.override_notes = payload.override_reason;
    currentReport.override_by = payload.operator_name;

    overrideBadge.style.display = 'inline-block';
    overrideBadge.textContent = `OVERRIDE: ${payload.new_status}`;
    alert(`Manual override recorded successfully by ${result.operator}. Log ID: ${result.audit_id}`);
  } catch (err) {
    alert('Override Error: ' + err.message);
  }
}

async function fetchAndRenderAuditLogs() {
  try {
    const res = await fetch('/api/v1/audit-log');
    const logs = await res.json();

    auditLogsContainer.innerHTML = '';
    if (logs.length === 0) {
      auditLogsContainer.innerHTML = `<div style="text-align: center; color: var(--text-dim); padding: 2rem;">No manual override audit records logged yet.</div>`;
      return;
    }

    logs.forEach(log => {
      const item = document.createElement('div');
      item.className = 'audit-item';
      item.innerHTML = `
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
          <strong style="color: var(--accent-cyan); font-family: monospace;">${log.audit_id}</strong>
          <span style="color: var(--text-dim);">${new Date(log.timestamp).toLocaleString()}</span>
        </div>
        <div style="font-size: 0.8rem; color: var(--text-main); margin-bottom: 0.25rem;">
          <strong>${log.operator}</strong> set status to <span class="badge badge-anomaly">${log.new_status}</span>
        </div>
        <div style="color: var(--text-muted); font-size: 0.75rem;">
          Reason: <em>"${log.reason}"</em>
        </div>
      `;
      auditLogsContainer.appendChild(item);
    });
  } catch (err) {
    console.error('Failed to fetch audit log:', err);
  }
}

async function handleBatchValidation() {
  const count = parseInt(batchSizeSelect.value, 10);
  const shipments = [];

  for (let i = 0; i < count; i++) {
    const preset = demoPresets[i % demoPresets.length];
    const clone = JSON.parse(JSON.stringify(preset.payload));
    clone.shipment_id = `BATCH-${String(i+1).padStart(3, '0')}-${clone.shipment_id}`;
    shipments.push(clone);
  }

  runBatchBtn.disabled = true;
  runBatchBtn.innerHTML = `<i class="ph-bold ph-spinner"></i> Processing ${count} Shipments...`;

  try {
    const res = await fetch('/api/v1/validate/batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ shipments })
    });

    if (!res.ok) throw new Error('Batch validation failed');

    const data = await res.json();
    renderBatchResults(data);
  } catch (err) {
    alert('Batch Error: ' + err.message);
  } finally {
    runBatchBtn.disabled = false;
    runBatchBtn.innerHTML = `<i class="ph-bold ph-stack"></i> Execute Batch Validation`;
  }
}

function renderBatchResults(data) {
  document.getElementById('batchTotalCount').textContent = data.total_processed;
  document.getElementById('batchAuthenticCount').textContent = data.authentic_count;
  document.getElementById('batchFlaggedCount').textContent = data.flagged_count;
  document.getElementById('batchAvgLatency').textContent = `${(data.total_time_ms / data.total_processed).toFixed(1)} ms/item`;
  document.getElementById('batchThroughputBadge').textContent = `Total Time: ${data.total_time_ms} ms`;

  const tbody = document.getElementById('batchTableBody');
  tbody.innerHTML = '';

  data.reports.forEach(r => {
    const tr = document.createElement('tr');
    let riskBadgeClass = 'badge-authentic';
    if (r.authenticity_score < 40) riskBadgeClass = 'badge-counterfeit';
    else if (r.authenticity_score < 75) riskBadgeClass = 'badge-anomaly';

    tr.innerHTML = `
      <td style="font-family: monospace; color: var(--accent-cyan);">${r.shipment_id}</td>
      <td style="font-family: monospace;">${r.serial_number}</td>
      <td><strong>${r.authenticity_score}</strong>%</td>
      <td><span class="badge ${riskBadgeClass}">${r.risk_level}</span></td>
      <td>${r.conflict_count} conflict(s)</td>
      <td><span style="color: ${r.is_authentic ? 'var(--accent-emerald)' : 'var(--accent-rose)'}; font-weight: 600;">${r.is_authentic ? 'AUTHENTIC' : 'FLAGGED'}</span></td>
      <td>
        <button class="btn btn-secondary" style="padding: 0.25rem 0.5rem; font-size: 0.72rem;" onclick='inspectBatchItem(${JSON.stringify(r)})'>
          Inspect
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

window.inspectBatchItem = function(report) {
  currentReport = report;
  tabSingle.click();
  renderValidationReport(report);
};

function exportReportJson() {
  if (!currentReport) {
    alert('No report available to export.');
    return;
  }
  const blob = new Blob([JSON.stringify(currentReport, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `TraceForge83_Report_${currentReport.shipment_id}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

// Start application
initApp();
