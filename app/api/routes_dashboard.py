from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from app.core.auth import verify_dashboard

router = APIRouter()

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>nnUNet Dashboard</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='5' fill='%231e293b'/><line x1='6' y1='5' x2='6' y2='24' stroke='%23475569' stroke-width='1'/><line x1='6' y1='24' x2='28' y2='24' stroke='%23475569' stroke-width='1'/><polyline points='6,8 11,12 16,15 21,18 26,20' fill='none' stroke='%2360a5fa' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'/><polyline points='6,23 11,20 16,17 21,14 26,12' fill='none' stroke='%2334d399' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'/></svg>">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/jsoneditor/10.1.0/jsoneditor.min.css">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }
  header { background: #1e293b; border-bottom: 1px solid #334155; padding: 14px 24px; display: flex; align-items: center; gap: 12px; }
  header h1 { font-size: 1.2rem; font-weight: 700; color: #f1f5f9; }
  header .subtitle { font-size: 0.8rem; color: #64748b; }
  .tabs { display: flex; gap: 2px; background: #1e293b; border-bottom: 1px solid #334155; padding: 0 24px; }
  .tab { padding: 12px 20px; cursor: pointer; font-size: 0.875rem; font-weight: 500; color: #94a3b8; border-bottom: 2px solid transparent; transition: all 0.15s; user-select: none; }
  .tab:hover { color: #e2e8f0; }
  .tab.active { color: #60a5fa; border-bottom-color: #60a5fa; }
  .tab-count { background: #334155; color: #94a3b8; border-radius: 10px; padding: 1px 7px; font-size: 0.75rem; margin-left: 6px; }
  .tab.active .tab-count { background: #1d4ed8; color: #bfdbfe; }
  .panel { display: none; padding: 24px; }
  .panel.active { display: block; }
  .card { background: #1e293b; border: 1px solid #334155; border-radius: 8px; overflow: hidden; }
  .card-header { padding: 14px 18px; border-bottom: 1px solid #334155; display: flex; justify-content: space-between; align-items: center; }
  .card-title { font-size: 0.95rem; font-weight: 600; color: #f1f5f9; }
  table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  th { background: #0f172a; color: #64748b; font-weight: 600; padding: 10px 14px; text-align: left; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; }
  td { padding: 10px 14px; border-top: 1px solid #1e293b; color: #cbd5e1; vertical-align: top; }
  tr:hover td { background: #1e2d3d; }
  .badge { display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 9999px; font-size: 0.72rem; font-weight: 600; }
  .badge-green { background: #064e3b; color: #34d399; }
  .badge-blue { background: #1e3a5f; color: #60a5fa; }
  .badge-yellow { background: #451a03; color: #fbbf24; }
  .badge-red { background: #450a0a; color: #f87171; }
  .badge-gray { background: #1e293b; color: #64748b; border: 1px solid #334155; }
  .badge-purple { background: #2e1065; color: #c084fc; }
  .btn { display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; border-radius: 6px; font-size: 0.8rem; font-weight: 500; cursor: pointer; border: none; transition: all 0.15s; }
  .btn-primary { background: #2563eb; color: white; }
  .btn-primary:hover { background: #1d4ed8; }
  .btn-success { background: #059669; color: white; }
  .btn-success:hover { background: #047857; }
  .btn-danger { background: #dc2626; color: white; }
  .btn-danger:hover { background: #b91c1c; }
  .btn-secondary { background: #334155; color: #e2e8f0; }
  .btn-secondary:hover { background: #475569; }
  .btn-sm { padding: 4px 10px; font-size: 0.75rem; }
  .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: none; align-items: center; justify-content: center; z-index: 1000; }
  .modal-overlay.open { display: flex; }
  .modal { background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 24px; width: 480px; max-width: 95vw; }
  .modal h2 { font-size: 1.1rem; font-weight: 600; margin-bottom: 18px; color: #f1f5f9; }
  .form-group { margin-bottom: 16px; }
  label { display: block; font-size: 0.8rem; font-weight: 500; color: #94a3b8; margin-bottom: 6px; }
  select, input, textarea { width: 100%; padding: 8px 12px; background: #0f172a; border: 1px solid #334155; border-radius: 6px; color: #e2e8f0; font-size: 0.875rem; outline: none; }
  select:focus, input:focus, textarea:focus { border-color: #3b82f6; }
  .modal-footer { display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px; }
  .progress-bar-wrap { background: #0f172a; border-radius: 4px; height: 8px; overflow: hidden; }
  .progress-bar { height: 100%; background: #2563eb; border-radius: 4px; transition: width 0.3s; }
  .expand-row td { padding: 0; }
  .expand-content { padding: 16px; background: #0f172a; border-top: 1px solid #334155; }
  .expand-content h4 { color: #94a3b8; font-size: 0.8rem; font-weight: 600; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.05em; }
  .log-box { background: #020617; border: 1px solid #1e293b; border-radius: 6px; padding: 12px; font-family: 'Courier New', monospace; font-size: 0.75rem; color: #94a3b8; max-height: 300px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; }
  .status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 6px; }
  .dot-green { background: #34d399; }
  .dot-gray { background: #475569; }
  .dot-yellow { background: #fbbf24; }
  .empty-state { text-align: center; padding: 40px 20px; color: #475569; font-size: 0.875rem; }
  .refresh-info { font-size: 0.75rem; color: #475569; }
  .top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
  .sub-table { font-size: 0.78rem; }
  .sub-table th { font-size: 0.72rem; padding: 6px 10px; }
  .sub-table td { padding: 6px 10px; }
  .modal-wide { width: 780px; max-height: 88vh; display: flex; flex-direction: column; }
  .modal-wide h2 { flex-shrink: 0; }
  .file-tabs { display: flex; gap: 2px; margin-bottom: 14px; flex-shrink: 0; }
  .file-tab { padding: 6px 14px; border-radius: 6px 6px 0 0; font-size: 0.8rem; font-weight: 500; cursor: pointer; color: #94a3b8; background: #0f172a; border: 1px solid #334155; border-bottom: none; }
  .file-tab:hover { color: #e2e8f0; }
  .file-tab.active { color: #60a5fa; background: #1e293b; border-color: #3b82f6; }
  .file-tab.missing { color: #475569; cursor: default; }
  .file-viewer { flex: 1; overflow-y: auto; background: #0f172a; border: 1px solid #334155; border-radius: 0 6px 6px 6px; padding: 8px; }
  .json-summary { margin-bottom: 10px; display: flex; flex-wrap: wrap; gap: 8px; padding: 4px 2px; }
  .json-kv { background: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 6px 12px; font-size: 0.78rem; }
  .json-kv .k { color: #64748b; margin-right: 4px; }
  .json-kv .v { color: #e2e8f0; font-weight: 500; }
  .json-pre { font-family: 'Courier New', monospace; font-size: 0.75rem; color: #94a3b8; white-space: pre-wrap; word-break: break-all; line-height: 1.6; padding: 8px; }
  /* JSONEditor dark mode overrides */
  .file-viewer .jsoneditor { border: none !important; }
  .file-viewer .jsoneditor-menu { background: #0f172a !important; border-bottom: 1px solid #1e293b !important; }
  .file-viewer .jsoneditor-menu button { color: #64748b !important; background: transparent !important; border: none !important; }
  .file-viewer .jsoneditor-menu button:hover, .file-viewer .jsoneditor-menu button:focus { background: #1e293b !important; color: #94a3b8 !important; }
  .file-viewer div.jsoneditor-tree, .file-viewer .jsoneditor-outer { background: #0f172a !important; }
  .file-viewer table.jsoneditor-tree tr td { background: #0f172a !important; }
  .file-viewer .jsoneditor .jsoneditor-field { color: #60a5fa !important; }
  .file-viewer .jsoneditor .jsoneditor-value.jsoneditor-string { color: #86efac !important; }
  .file-viewer .jsoneditor .jsoneditor-value.jsoneditor-number { color: #fbbf24 !important; }
  .file-viewer .jsoneditor .jsoneditor-value.jsoneditor-boolean { color: #f87171 !important; }
  .file-viewer .jsoneditor .jsoneditor-value.jsoneditor-null { color: #94a3b8 !important; }
  .file-viewer .jsoneditor .jsoneditor-value.jsoneditor-object,
  .file-viewer .jsoneditor .jsoneditor-value.jsoneditor-array { color: #94a3b8 !important; }
  .file-viewer .jsoneditor .jsoneditor-separator { color: #475569 !important; }
  .file-viewer .jsoneditor .jsoneditor-button { filter: invert(1) opacity(0.6) !important; border: none !important; }
  .file-viewer .jsoneditor .jsoneditor-button:hover { filter: invert(1) opacity(1) !important; }
  .file-viewer tr.jsoneditor-highlight td, .file-viewer tr.jsoneditor-selected td { background: #1e293b !important; }
  .file-viewer .jsoneditor-readonly { color: #e2e8f0 !important; }
  .file-viewer .jsoneditor-empty { color: #475569 !important; }
  .file-viewer .jsoneditor-schema-error { display: none; }
  .file-viewer .jsoneditor-statusbar { background: #0f172a !important; color: #475569 !important; border-top: 1px solid #1e293b !important; }
</style>
</head>
<body>

<header>
  <svg width="36" height="36" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg" style="flex-shrink:0">
    <rect width="32" height="32" rx="5" fill="#0f172a"/>
    <line x1="6" y1="5" x2="6" y2="24" stroke="#475569" stroke-width="1"/>
    <line x1="6" y1="24" x2="28" y2="24" stroke="#475569" stroke-width="1"/>
    <polyline points="6,8 11,12 16,15 21,18 26,20" fill="none" stroke="#60a5fa" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
    <polyline points="6,23 11,20 16,17 21,14 26,12" fill="none" stroke="#34d399" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>
  <div>
    <h1>nnUNet Dashboard</h1>
    <div class="subtitle">Training management & model approval</div>
  </div>
  <div style="margin-left:auto; display:flex; align-items:center; gap:14px;">
    <span class="refresh-info" id="lastRefresh">Polling every 10s</span>
  </div>
</header>

<div class="tabs">
  <div class="tab active" onclick="switchTab('datasets')">Datasets <span class="tab-count" id="cnt-datasets">0</span></div>
  <div class="tab" onclick="switchTab('jobs')">Training Jobs <span class="tab-count" id="cnt-jobs">0</span></div>
  <div class="tab" onclick="switchTab('models')">Models <span class="tab-count" id="cnt-models">0</span></div>
  <div class="tab" onclick="switchTab('workers')">Workers <span class="tab-count" id="cnt-workers">0</span></div>
</div>

<!-- DATASETS TAB -->
<div class="panel active" id="panel-datasets">
  <div class="top-bar">
    <span class="card-title">Datasets</span>
  </div>
  <div class="card">
    <table id="tbl-datasets">
      <thead><tr>
        <th>Name</th><th>Submitted By</th><th>Submitted At</th><th>Plan</th><th>Jobs</th><th>Actions</th>
      </tr></thead>
      <tbody id="body-datasets"><tr><td colspan="6" class="empty-state">Loading...</td></tr></tbody>
    </table>
  </div>
</div>

<!-- JOBS TAB -->
<div class="panel" id="panel-jobs">
  <div class="top-bar">
    <span class="card-title">Training Jobs</span>
  </div>
  <div class="card">
    <table id="tbl-jobs">
      <thead><tr>
        <th>Dataset</th><th>Worker</th><th>Config</th><th>Status</th><th>Created</th><th>Actions</th>
      </tr></thead>
      <tbody id="body-jobs"><tr><td colspan="6" class="empty-state">Loading...</td></tr></tbody>
    </table>
  </div>
</div>

<!-- MODELS TAB -->
<div class="panel" id="panel-models">
  <div class="top-bar">
    <span class="card-title">Models</span>
  </div>
  <div class="card">
    <table id="tbl-models">
      <thead><tr>
        <th>Dataset</th><th>Config</th><th>Status</th><th>Created</th><th>Description</th><th>Actions</th>
      </tr></thead>
      <tbody id="body-models"><tr><td colspan="6" class="empty-state">Loading...</td></tr></tbody>
    </table>
  </div>
</div>

<!-- WORKERS TAB -->
<div class="panel" id="panel-workers">
  <div class="top-bar">
    <span class="card-title">Workers</span>
  </div>
  <div class="card">
    <table id="tbl-workers">
      <thead><tr>
        <th>Name</th><th>Hostname</th><th>GPU</th><th>CPU Cores</th><th>RAM (GB)</th><th>Status</th><th>Last Heartbeat</th>
      </tr></thead>
      <tbody id="body-workers"><tr><td colspan="7" class="empty-state">Loading...</td></tr></tbody>
    </table>
  </div>
</div>

<!-- CREATE JOB MODAL -->
<div class="modal-overlay" id="modal-create-job">
  <div class="modal">
    <h2>Create Training Job</h2>
    <div class="form-group">
      <label>Dataset</label>
      <input type="text" id="cj-dataset-name" disabled style="color:#64748b;">
      <input type="hidden" id="cj-dataset-id">
    </div>
    <div class="form-group">
      <label>Worker</label>
      <select id="cj-worker"></select>
    </div>
    <div class="form-group">
      <label>Configuration</label>
      <select id="cj-config">
        <option value="3d_fullres">3d_fullres</option>
        <option value="3d_lowres">3d_lowres</option>
        <option value="2d">2d</option>
      </select>
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="closeModal('modal-create-job')">Cancel</button>
      <button class="btn btn-primary" onclick="submitCreateJob()">Create Job</button>
    </div>
  </div>
</div>

<!-- EDIT DESCRIPTION MODAL -->
<div class="modal-overlay" id="modal-edit-desc">
  <div class="modal">
    <h2>Edit Model Description</h2>
    <div class="form-group">
      <label>Description</label>
      <textarea id="edit-desc-text" rows="4"></textarea>
      <input type="hidden" id="edit-desc-model-id">
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="closeModal('modal-edit-desc')">Cancel</button>
      <button class="btn btn-primary" onclick="submitEditDesc()">Save</button>
    </div>
  </div>
</div>

<!-- DATASET FILES MODAL -->
<div class="modal-overlay" id="modal-dataset-files">
  <div class="modal modal-wide">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;flex-shrink:0">
      <h2 id="files-modal-title">Dataset Files</h2>
      <div style="display:flex;gap:8px">
        <button id="btn-copy-json" class="btn btn-secondary btn-sm" onclick="copyFileJson()">Copy JSON</button>
        <button class="btn btn-secondary btn-sm" onclick="closeModal('modal-dataset-files')">✕ Close</button>
      </div>
    </div>
    <div class="file-tabs" id="file-tabs">
      <div class="file-tab active" data-file="dataset.json" onclick="loadFileTab('dataset.json')">dataset.json</div>
      <div class="file-tab" data-file="dataset_fingerprint.json" onclick="loadFileTab('dataset_fingerprint.json')">dataset_fingerprint.json</div>
      <div class="file-tab" data-file="nnUNetPlans.json" onclick="loadFileTab('nnUNetPlans.json')">nnUNetPlans.json</div>
    </div>
    <div class="file-viewer" id="file-viewer-content">
      <div style="color:#64748b;font-size:0.82rem">Loading…</div>
    </div>
  </div>
</div>

<script>
const API_KEY = '__DASHBOARD_API_KEY__';

// State
let state = { datasets: [], jobs: [], models: [], workers: [] };
let expandedJobs = new Set();
let jobDetails = {};
let expandedWorkers = new Set();
let workerLogPages = {};

// Tab switching
function switchTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  const tabs = ['datasets','jobs','models','workers'];
  document.querySelectorAll('.tab')[tabs.indexOf(name)].classList.add('active');
  document.getElementById('panel-' + name).classList.add('active');
}

// Fetch helpers
async function apiFetch(path, opts = {}) {
  const { headers: extraHeaders, ...restOpts } = opts;
  const res = await fetch('/api' + path, {
    headers: { 'X-Api-Key': API_KEY, ...extraHeaders },
    ...restOpts
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function apiPost(path, body, opts = {}) {
  return apiFetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), ...opts });
}

async function apiPut(path, body) {
  return apiFetch(path, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
}

// Formatting helpers
function fmtDate(s) {
  if (!s) return '—';
  try { return new Date(s).toLocaleString(); } catch { return s; }
}

function relTime(s) {
  if (!s) return '—';
  const diff = Math.floor((Date.now() - new Date(s).getTime()) / 1000);
  if (diff < 60) return diff + 's ago';
  if (diff < 3600) return Math.floor(diff/60) + 'm ago';
  return Math.floor(diff/3600) + 'h ago';
}

function statusBadge(st) {
  const map = {
    online: 'badge-green', offline: 'badge-gray', busy: 'badge-yellow',
    pending: 'badge-gray', assigned: 'badge-blue', preprocessing: 'badge-blue',
    training: 'badge-purple', validating: 'badge-yellow', uploading: 'badge-yellow',
    done: 'badge-green', failed: 'badge-red', cancelled: 'badge-gray',
    pending_approval: 'badge-yellow', approved: 'badge-green', rejected: 'badge-red'
  };
  return `<span class="badge ${map[st] || 'badge-gray'}">${st || '?'}</span>`;
}

// Data loading
async function loadAll() {
  try {
    const [datasets, jobs, models, workers] = await Promise.all([
      apiFetch('/datasets/'),
      apiFetch('/jobs/'),
      apiFetch('/models/'),
      apiFetch('/workers/')
    ]);
    state = { datasets, jobs, models, workers };
    renderDatasets();
    renderJobs();
    renderModels();
    renderWorkers();
    document.getElementById('lastRefresh').textContent = 'Last updated: ' + new Date().toLocaleTimeString();
  } catch (e) {
    console.error('Failed to load data:', e);
  }
}

// Count helpers
function countJobsForDataset(datasetId) {
  return state.jobs.filter(j => j.dataset_id === datasetId).length;
}

function getDatasetName(datasetId) {
  const d = state.datasets.find(d => d.id === datasetId);
  return d ? d.name : datasetId.substring(0,8) + '…';
}

function getWorkerName(workerId) {
  const w = state.workers.find(w => w.id === workerId);
  return w ? w.name : (workerId ? workerId.substring(0,8) + '…' : '—');
}

function getJobConfig(jobId) {
  const j = state.jobs.find(j => j.id === jobId);
  return j ? j.configuration : '—';
}

// Render datasets
function renderDatasets() {
  document.getElementById('cnt-datasets').textContent = state.datasets.length;
  const tbody = document.getElementById('body-datasets');
  if (!state.datasets.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No datasets yet</td></tr>';
    return;
  }
  tbody.innerHTML = state.datasets.map(d => `
    <tr>
      <td><strong>${esc(d.name)}</strong><br><small style="color:#64748b">${d.id.substring(0,8)}</small></td>
      <td>${esc(d.submitted_by || '—')}</td>
      <td>${fmtDate(d.submitted_at)}</td>
      <td>${d.has_plan ? '<span class="badge badge-green">has plan</span>' : '<span class="badge badge-gray">no plan</span>'}</td>
      <td>${countJobsForDataset(d.id)}</td>
      <td style="white-space:nowrap">
        <button class="btn btn-secondary btn-sm" onclick="openDatasetFiles('${d.id}')">Files</button>
        <button class="btn btn-primary btn-sm" onclick="openCreateJob('${d.id}','${esc(d.name)}')">+ Create Job</button>
      </td>
    </tr>
  `).join('');
}

// Render jobs
function renderJobs() {
  document.getElementById('cnt-jobs').textContent = state.jobs.length;
  const tbody = document.getElementById('body-jobs');
  if (!state.jobs.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No training jobs yet</td></tr>';
    return;
  }
  let rows = '';
  state.jobs.forEach(j => {
    const expanded = expandedJobs.has(j.id);
    const terminalStatuses = ['done','failed','cancelled'];
    const activeJob = !terminalStatuses.includes(j.status);
    let statusCell = statusBadge(j.status);
    if (j.status === 'training' && j.latest_fold != null)
      statusCell += `<br><small style="color:#94a3b8;font-size:0.72rem">fold ${j.latest_fold}/4 · ep ${j.latest_epoch}</small>`;
    rows += `
      <tr style="cursor:pointer" onclick="toggleJobExpand('${j.id}')">
        <td><strong>${esc(getDatasetName(j.dataset_id))}</strong></td>
        <td>${esc(getWorkerName(j.worker_id))}</td>
        <td><code style="font-size:0.78rem">${esc(j.configuration || '—')}</code></td>
        <td>${statusCell}</td>
        <td>${fmtDate(j.created_at)}</td>
        <td style="white-space:nowrap">
          ${activeJob ? `<button class="btn btn-secondary btn-sm" onclick="event.stopPropagation();cancelJob('${j.id}')">Cancel</button>` : ''}
          <button class="btn btn-danger btn-sm" onclick="event.stopPropagation();deleteJob('${j.id}')">Delete</button>
          <span style="color:#475569;font-size:0.75rem;margin-left:4px">${expanded ? '▲' : '▼'}</span>
        </td>
      </tr>`;
    if (expanded) {
      rows += `<tr class="expand-row"><td colspan="6"><div class="expand-content" id="expand-${j.id}">
        <div style="color:#64748b;font-size:0.8rem">Loading details…</div>
      </div></td></tr>`;
    }
  });
  tbody.innerHTML = rows;
  // Load details for expanded jobs
  expandedJobs.forEach(jid => loadJobDetail(jid));
}

async function toggleJobExpand(jid) {
  if (expandedJobs.has(jid)) {
    expandedJobs.delete(jid);
  } else {
    expandedJobs.add(jid);
  }
  renderJobs();
}

async function cancelJob(jid) {
  if (!confirm('Cancel this job?')) return;
  try {
    await apiPut('/jobs/' + jid + '/status', { status: 'cancelled' });
    await loadAll();
  } catch (e) { alert('Failed to cancel job: ' + e.message); }
}

async function deleteJob(jid) {
  if (!confirm('Delete this job and all its progress data? This cannot be undone.')) return;
  try {
    await apiFetch('/jobs/' + jid, { method: 'DELETE' });
    expandedJobs.delete(jid);
    await loadAll();
  } catch (e) { alert('Failed to delete job: ' + e.message); }
}

async function loadJobDetail(jid) {
  try {
    const detail = await apiFetch('/jobs/' + jid);
    jobDetails[jid] = detail;
    renderJobDetail(jid, detail);
  } catch (e) {
    const el = document.getElementById('expand-' + jid);
    if (el) el.innerHTML = '<div style="color:#f87171">Failed to load details</div>';
  }
}

function renderJobDetail(jid, detail) {
  const el = document.getElementById('expand-' + jid);
  if (!el) return;

  let html = '';

  // Error message
  if (detail.error_message) {
    html += `<div style="background:#450a0a;border:1px solid #7f1d1d;border-radius:6px;padding:10px 14px;margin-bottom:14px;color:#fca5a5;font-size:0.82rem">
      <strong>Error:</strong> ${esc(detail.error_message)}
    </div>`;
  }

  // Preprocessing progress
  if (detail.preprocessing_progress) {
    const pp = detail.preprocessing_progress;
    const pct = pp.total_images ? Math.round((pp.done_images / pp.total_images) * 100) : 0;
    html += `<h4>Preprocessing Progress</h4>
    <div style="margin-bottom:14px">
      <div style="display:flex;justify-content:space-between;font-size:0.8rem;margin-bottom:4px">
        <span>${pp.done_images || 0} / ${pp.total_images || '?'} images</span>
        <span>${pct}%${pp.mean_time_per_image_s ? ' · ' + pp.mean_time_per_image_s.toFixed(2) + 's/img' : ''}</span>
      </div>
      <div class="progress-bar-wrap"><div class="progress-bar" style="width:${pct}%"></div></div>
    </div>`;
  }

  // Training progress per fold
  if (detail.training_progress && detail.training_progress.length > 0) {
    // Group by fold
    const folds = {};
    detail.training_progress.forEach(tp => {
      if (!folds[tp.fold]) folds[tp.fold] = [];
      folds[tp.fold].push(tp);
    });
    Object.keys(folds).sort().forEach(fold => {
      const rows = folds[fold];
      const last = rows[rows.length - 1];
      html += `<h4 style="margin-top:14px">Fold ${fold} Training (${rows.length} epochs)</h4>
      <table class="sub-table" style="margin-bottom:10px">
        <thead><tr><th>Epoch</th><th>LR</th><th>Train Loss</th><th>Val Loss</th><th>Pseudo Dice</th><th>Time/ep</th></tr></thead>
        <tbody>`;
      // Show last 10 epochs
      rows.slice(-10).forEach(r => {
        let dice = '—';
        try { dice = JSON.parse(r.pseudo_dice || 'null'); if (Array.isArray(dice)) dice = dice.map(v => { const n = typeof v === 'number' ? v : parseFloat(String(v).match(/[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?/)?.[0]); return isNaN(n) ? String(v) : n.toFixed(3); }).join(', '); } catch {}
        html += `<tr>
          <td>${r.epoch}</td>
          <td>${r.learning_rate != null ? r.learning_rate.toExponential(2) : '—'}</td>
          <td>${r.train_loss != null ? r.train_loss.toFixed(4) : '—'}</td>
          <td>${r.val_loss != null ? r.val_loss.toFixed(4) : '—'}</td>
          <td style="font-size:0.72rem;max-width:200px;overflow:hidden;text-overflow:ellipsis">${esc(String(dice))}</td>
          <td>${r.epoch_time_s != null ? r.epoch_time_s.toFixed(1) + 's' : '—'}</td>
        </tr>`;
      });
      html += `</tbody></table>`;

      // Log viewer
      html += `<div style="margin-top:10px;margin-bottom:4px">
        <button id="log-btn-${jid}-${fold}" class="btn btn-secondary btn-sm" onclick="toggleLog('${jid}',${fold})">▼ Show Log</button>
        <div id="log-${jid}-${fold}" style="display:none;margin-top:8px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
            <span id="log-info-${jid}-${fold}" style="font-size:0.72rem;color:#64748b"></span>
            <button class="btn btn-secondary btn-sm" onclick="refreshLog('${jid}',${fold})">↻ Refresh</button>
          </div>
          <pre class="log-box" id="log-pre-${jid}-${fold}" style="max-height:400px"></pre>
        </div>
      </div>`;
    });
  }

  // Validation results
  if (detail.validation_results && detail.validation_results.length > 0) {
    html += `<h4 style="margin-top:14px">Validation Results</h4>`;
    detail.validation_results.forEach(vr => {
      let summary = '';
      try {
        const obj = JSON.parse(vr.summary_json);
        summary = JSON.stringify(obj, null, 2).substring(0, 500);
      } catch { summary = vr.summary_json ? vr.summary_json.substring(0, 300) : ''; }
      html += `<div style="margin-bottom:8px"><strong style="font-size:0.8rem;color:#94a3b8">Fold ${vr.fold}</strong>
        <div class="log-box" style="max-height:150px">${esc(summary)}</div></div>`;
    });
  }

  if (!html) html = '<div style="color:#64748b;font-size:0.82rem">No detailed progress reported yet.</div>';

  el.innerHTML = html;
}

async function toggleLog(jid, fold) {
  const panel = document.getElementById(`log-${jid}-${fold}`);
  const btn = document.getElementById(`log-btn-${jid}-${fold}`);
  if (!panel) return;
  if (panel.style.display !== 'none') {
    panel.style.display = 'none';
    if (btn) btn.textContent = '▼ Show Log';
    return;
  }
  panel.style.display = 'block';
  if (btn) btn.textContent = '▲ Hide Log';
  const pre = document.getElementById(`log-pre-${jid}-${fold}`);
  if (pre && !pre.textContent) await refreshLog(jid, fold);
}

async function refreshLog(jid, fold) {
  const pre = document.getElementById(`log-pre-${jid}-${fold}`);
  const info = document.getElementById(`log-info-${jid}-${fold}`);
  if (!pre) return;
  pre.textContent = 'Loading…';
  try {
    const res = await fetch(`/api/jobs/${jid}/log/${fold}`, { headers: { 'X-Api-Key': API_KEY } });
    if (res.ok) {
      const text = await res.text();
      const MAX = 12000;
      if (text.length > MAX) {
        pre.textContent = `[… showing last ${MAX} of ${text.length} chars …]\n\n` + text.slice(-MAX);
        if (info) info.textContent = `${text.length.toLocaleString()} chars total`;
      } else {
        pre.textContent = text;
        if (info) info.textContent = `${text.length.toLocaleString()} chars`;
      }
      pre.scrollTop = pre.scrollHeight;
    } else {
      pre.textContent = 'Log not available';
      if (info) info.textContent = '';
    }
  } catch (e) {
    pre.textContent = 'Failed to load log';
    if (info) info.textContent = '';
  }
}


// Render models
function renderModels() {
  document.getElementById('cnt-models').textContent = state.models.length;
  const tbody = document.getElementById('body-models');
  if (!state.models.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No models yet</td></tr>';
    return;
  }
  tbody.innerHTML = state.models.map(m => {
    const job = state.jobs.find(j => j.id === m.job_id);
    const config = job ? job.configuration : '—';
    const datasetName = getDatasetName(m.dataset_id);
    const actions = [];
    if (m.status === 'pending_approval') {
      actions.push(`<button class="btn btn-success btn-sm" onclick="approveModel('${m.id}')">Approve</button>`);
      actions.push(`<button class="btn btn-danger btn-sm" onclick="rejectModel('${m.id}')">Reject</button>`);
    }
    if (m.status === 'approved') {
      actions.push(`<a class="btn btn-secondary btn-sm" href="/api/models/${m.id}/download">Download</a>`);
    }
    actions.push(`<button class="btn btn-secondary btn-sm" onclick="openEditDesc('${m.id}','${esc(m.description||'')}')">Edit</button>`);
    return `
      <tr>
        <td><strong>${esc(datasetName)}</strong></td>
        <td><code style="font-size:0.78rem">${esc(config)}</code></td>
        <td>${statusBadge(m.status)}</td>
        <td>${fmtDate(m.created_at)}</td>
        <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(m.description || '—')}</td>
        <td style="white-space:nowrap">${actions.join(' ')}</td>
      </tr>`;
  }).join('');
}

async function approveModel(mid) {
  try {
    await apiPost('/models/' + mid + '/approve', { approved_by: 'admin' });
    await loadAll();
  } catch (e) { alert('Failed: ' + e.message); }
}

async function rejectModel(mid) {
  if (!confirm('Reject this model?')) return;
  try {
    await apiPost('/models/' + mid + '/reject', {});
    await loadAll();
  } catch (e) { alert('Failed: ' + e.message); }
}

function openEditDesc(mid, desc) {
  document.getElementById('edit-desc-model-id').value = mid;
  document.getElementById('edit-desc-text').value = desc;
  openModal('modal-edit-desc');
}

async function submitEditDesc() {
  const mid = document.getElementById('edit-desc-model-id').value;
  const desc = document.getElementById('edit-desc-text').value;
  try {
    await apiPut('/models/' + mid, { description: desc });
    closeModal('modal-edit-desc');
    await loadAll();
  } catch (e) { alert('Failed: ' + e.message); }
}

// Render workers
function renderWorkers() {
  document.getElementById('cnt-workers').textContent = state.workers.length;
  const tbody = document.getElementById('body-workers');
  if (!state.workers.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No workers registered yet</td></tr>';
    return;
  }
  let rows = '';
  state.workers.forEach(w => {
    const expanded = expandedWorkers.has(w.id);
    const dot = w.status === 'online' ? 'dot-green' : w.status === 'busy' ? 'dot-yellow' : 'dot-gray';
    rows += `
      <tr style="cursor:pointer" onclick="toggleWorkerExpand('${w.id}')">
        <td><strong>${esc(w.name)}</strong></td>
        <td>${esc(w.hostname || '—')}</td>
        <td>${esc(w.gpu_name || '—')}${w.gpu_memory_gb ? ` (${w.gpu_memory_gb} GB)` : ''}</td>
        <td>${w.cpu_cores || '—'}</td>
        <td>${w.system_memory_gb != null ? w.system_memory_gb + ' GB' : '—'}</td>
        <td><span class="status-dot ${dot}"></span>${statusBadge(w.status)}</td>
        <td style="white-space:nowrap">${relTime(w.last_heartbeat)}
          <span style="color:#475569;font-size:0.75rem;margin-left:8px">${expanded ? '▲' : '▼'}</span>
        </td>
      </tr>`;
    if (expanded) {
      rows += `<tr class="expand-row"><td colspan="7">
        <div class="expand-content" id="worker-expand-${w.id}">
          <div style="color:#64748b;font-size:0.8rem">Loading logs…</div>
        </div></td></tr>`;
    }
  });
  tbody.innerHTML = rows;
  expandedWorkers.forEach(wid => loadWorkerLogs(wid, workerLogPages[wid] || 1));
}

function toggleWorkerExpand(wid) {
  if (expandedWorkers.has(wid)) {
    expandedWorkers.delete(wid);
  } else {
    expandedWorkers.add(wid);
  }
  renderWorkers();
}

async function loadWorkerLogs(wid, page) {
  workerLogPages[wid] = page || 1;
  try {
    const data = await apiFetch(`/logs/?worker_id=${wid}&page=${workerLogPages[wid]}&per_page=20`);
    renderWorkerLogs(wid, data);
  } catch (e) {
    const el = document.getElementById('worker-expand-' + wid);
    if (el) el.innerHTML = '<div style="color:#f87171;font-size:0.82rem">Failed to load logs</div>';
  }
}

function renderWorkerLogs(wid, data) {
  const el = document.getElementById('worker-expand-' + wid);
  if (!el) return;
  const levelBadge = lvl => {
    const cls = lvl === 'ERROR' || lvl === 'CRITICAL' ? 'badge-red'
              : lvl === 'WARNING' ? 'badge-yellow' : 'badge-blue';
    return `<span class="badge ${cls}">${esc(lvl)}</span>`;
  };
  let html = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
    <span style="font-size:0.82rem;color:#64748b">${data.total} entr${data.total===1?'y':'ies'} · page ${data.page} / ${data.pages}</span>
    <button class="btn btn-danger btn-sm" onclick="event.stopPropagation();clearWorkerLogs('${wid}')">Clear</button>
  </div>`;
  if (!data.items.length) {
    html += '<div style="color:#64748b;font-size:0.82rem;padding:6px 0">No log entries yet</div>';
  } else {
    html += `<table class="sub-table">
      <thead><tr><th style="white-space:nowrap">Time</th><th>Level</th><th>Message</th></tr></thead>
      <tbody>`;
    html += data.items.map(log => `
      <tr>
        <td style="white-space:nowrap;font-size:0.78rem;color:#94a3b8">${fmtDate(log.created_at)}</td>
        <td>${levelBadge(log.level)}</td>
        <td style="font-size:0.82rem;word-break:break-word">${esc(log.message)}</td>
      </tr>`).join('');
    html += '</tbody></table>';
  }
  if (data.pages > 1) {
    html += '<div style="display:flex;gap:6px;justify-content:center;padding:10px 0;flex-wrap:wrap">';
    if (data.page > 1)
      html += `<button class="btn btn-secondary btn-sm" onclick="event.stopPropagation();loadWorkerLogs('${wid}',${data.page-1})">← Prev</button>`;
    const start = Math.max(1, data.page - 2), end = Math.min(data.pages, data.page + 2);
    for (let p = start; p <= end; p++)
      html += `<button class="btn ${p===data.page?'btn-primary':'btn-secondary'} btn-sm" onclick="event.stopPropagation();loadWorkerLogs('${wid}',${p})">${p}</button>`;
    if (data.page < data.pages)
      html += `<button class="btn btn-secondary btn-sm" onclick="event.stopPropagation();loadWorkerLogs('${wid}',${data.page+1})">Next →</button>`;
    html += '</div>';
  }
  el.innerHTML = html;
}

async function clearWorkerLogs(wid) {
  if (!confirm('Clear all logs for this worker?')) return;
  try {
    await apiFetch(`/logs/?worker_id=${wid}`, { method: 'DELETE' });
    await loadWorkerLogs(wid, 1);
  } catch (e) { alert('Failed: ' + e.message); }
}

// Dataset file viewer
let fileCache = {};
let currentFilesDatasetId = null;
let currentFileTab = 'dataset.json';
let currentJsonEditor = null;
let jsonEditorLoaded = false;

function loadJsonEditor() {
  if (jsonEditorLoaded) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = 'https://cdnjs.cloudflare.com/ajax/libs/jsoneditor/10.1.0/jsoneditor.min.js';
    s.onload = () => { jsonEditorLoaded = true; resolve(); };
    s.onerror = reject;
    document.head.appendChild(s);
  });
}

async function openDatasetFiles(datasetId) {
  currentFilesDatasetId = datasetId;
  const d = state.datasets.find(d => d.id === datasetId);
  document.getElementById('files-modal-title').textContent = d ? d.name : datasetId;
  document.querySelectorAll('.file-tab').forEach(t => {
    t.classList.remove('active', 'missing');
    if (t.dataset.file === 'dataset.json') t.classList.add('active');
  });
  openModal('modal-dataset-files');
  await loadFileTab('dataset.json');
}

async function copyFileJson() {
  const cached = fileCache[currentFilesDatasetId]?.[currentFileTab];
  if (!cached) return;
  const content = cached.content;
  const jsonStr = typeof content === 'object' ? JSON.stringify(content, null, 2) : String(content);
  try {
    await navigator.clipboard.writeText(jsonStr);
    const btn = document.getElementById('btn-copy-json');
    const orig = btn.textContent;
    btn.textContent = '✓ Copied!';
    btn.style.background = '#059669';
    btn.style.color = '#fff';
    setTimeout(() => { btn.textContent = orig; btn.style.background = ''; btn.style.color = ''; }, 2000);
  } catch(e) {
    alert('Copy failed: ' + e.message);
  }
}

async function loadFileTab(name) {
  currentFileTab = name;
  const did = currentFilesDatasetId;
  if (!did) return;
  document.querySelectorAll('.file-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.file === name);
  });
  // Destroy existing JSONEditor before replacing the DOM
  if (currentJsonEditor) {
    try { currentJsonEditor.destroy(); } catch(e) {}
    currentJsonEditor = null;
  }
  const viewer = document.getElementById('file-viewer-content');
  if (fileCache[did] && name in fileCache[did]) {
    renderFileContent(name, fileCache[did][name]);
    return;
  }
  viewer.innerHTML = '<div style="color:#64748b;font-size:0.82rem">Loading…</div>';
  try {
    const data = await apiFetch('/datasets/' + did + '/file?name=' + encodeURIComponent(name));
    if (!fileCache[did]) fileCache[did] = {};
    fileCache[did][name] = data;
    renderFileContent(name, data);
  } catch (e) {
    if (!fileCache[did]) fileCache[did] = {};
    fileCache[did][name] = null;
    renderFileContent(name, null);
    document.querySelectorAll('.file-tab').forEach(t => {
      if (t.dataset.file === name) t.classList.add('missing');
    });
  }
}

function renderFileContent(name, data) {
  const viewer = document.getElementById('file-viewer-content');
  if (!data) {
    viewer.innerHTML = '<div style="color:#475569;font-size:0.82rem;padding:20px 0">File not found in dataset ZIP.</div>';
    return;
  }
  const content = data.content;
  // Build optional summary bar for dataset.json
  let summaryHtml = '';
  if (name === 'dataset.json' && typeof content === 'object' && content !== null) {
    const kvItems = [];
    if (content.name) kvItems.push(['Name', content.name]);
    if (content.description) kvItems.push(['Description', content.description]);
    if (content.numTraining != null) kvItems.push(['Training', content.numTraining + ' images']);
    if (content.numTest != null) kvItems.push(['Test', content.numTest + ' images']);
    const mods = content.modality || content.channel_names;
    if (mods && typeof mods === 'object') kvItems.push(['Modality', Object.values(mods).join(', ')]);
    if (content.labels && typeof content.labels === 'object') kvItems.push(['Labels', Object.keys(content.labels).length]);
    if (kvItems.length > 0) {
      summaryHtml = '<div class="json-summary">' + kvItems.map(([k, v]) =>
        `<div class="json-kv"><span class="k">${esc(k)}:</span><span class="v">${esc(String(v))}</span></div>`
      ).join('') + '</div>';
    }
  }
  viewer.innerHTML = summaryHtml + '<div id="json-editor-mount"></div>';
  const mount = document.getElementById('json-editor-mount');
  if (typeof content === 'object' && content !== null) {
    loadJsonEditor().then(() => {
      if (!mount || !document.body.contains(mount)) return;
      const editor = new JSONEditor(mount, { mode: 'view', navigationBar: false, mainMenuBar: false });
      editor.set(content);
      currentJsonEditor = editor;
    }).catch(() => {
      if (mount) mount.innerHTML = `<pre class="json-pre">${esc(JSON.stringify(content, null, 2))}</pre>`;
    });
  } else {
    mount.innerHTML = `<pre class="json-pre">${esc(String(content))}</pre>`;
  }
}

// Create job modal
function openCreateJob(datasetId, datasetName) {
  document.getElementById('cj-dataset-id').value = datasetId;
  document.getElementById('cj-dataset-name').value = datasetName;
  // Populate workers
  const sel = document.getElementById('cj-worker');
  sel.innerHTML = '';
  const online = state.workers.filter(w => w.status !== 'offline');
  const all = online.length > 0 ? online : state.workers;
  if (all.length === 0) {
    sel.innerHTML = '<option value="">No workers available</option>';
  } else {
    all.forEach(w => {
      const opt = document.createElement('option');
      opt.value = w.id;
      opt.textContent = w.name + (w.status === 'offline' ? ' (offline)' : '');
      sel.appendChild(opt);
    });
  }
  openModal('modal-create-job');
}

async function submitCreateJob() {
  const dataset_id = document.getElementById('cj-dataset-id').value;
  const worker_id = document.getElementById('cj-worker').value;
  const configuration = document.getElementById('cj-config').value;
  if (!worker_id) { alert('Select a worker'); return; }
  try {
    await apiPost('/jobs/', { dataset_id, worker_id, configuration });
    closeModal('modal-create-job');
    await loadAll();
    switchTab('jobs');
  } catch (e) { alert('Failed to create job: ' + e.message); }
}

// Modal helpers
function openModal(id) { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

// Escape HTML
function esc(s) {
  if (s == null) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// Close modal on overlay click
document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', e => { if (e.target === overlay) overlay.classList.remove('open'); });
});

// Initial load + polling
loadAll();
setInterval(loadAll, 10000);
</script>
</body>
</html>"""


@router.get("/")
def root():
    return RedirectResponse(url="/dashboard")


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(_user: str = Depends(verify_dashboard)):
    from app.core.config import settings
    html = DASHBOARD_HTML.replace("__DASHBOARD_API_KEY__", settings.API_KEY)
    return HTMLResponse(content=html)
