let currentMission = null;

const $ = (id) => document.getElementById(id);
const pct = (value) => `${Math.round((value || 0) * 100)}%`;
const shortTime = (timestamp) => new Date(timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({detail: response.statusText}));
    throw new Error(payload.detail || response.statusText);
  }
  return response.json();
}

function toast(message) {
  $('toast').textContent = message;
  $('toast').classList.remove('hidden');
  setTimeout(() => $('toast').classList.add('hidden'), 3400);
}

async function boot() {
  const health = await api('/health');
  $('healthText').textContent = `Control plane healthy · ${health.dry_run ? 'dry-run broker' : 'live adapter mode'}`;
  const scenarios = await api('/api/scenarios');
  $('scenarioButtons').innerHTML = scenarios.map(item =>
    `<button title="${item.description}" onclick="launchScenario('${item.id}')">${item.severity} · ${item.title.split(' ').slice(0, 4).join(' ')}</button>`
  ).join('');
}

async function launchScenario(id) {
  toast('Creating mission and running swarm analysis…');
  currentMission = await api(`/api/missions/scenario/${id}`, {method: 'POST'});
  render(currentMission);
}

async function refresh() {
  if (!currentMission) return;
  currentMission = await api(`/api/missions/${currentMission.id}`);
  render(currentMission);
}

async function reanalyze() {
  currentMission = await api(`/api/missions/${currentMission.id}/analyze`, {method: 'POST'});
  toast('Field snapshot and recommendations refreshed');
  render(currentMission);
}

async function approve(recId) {
  currentMission = await api(`/api/missions/${currentMission.id}/recommendations/${recId}/approve`, {
    method: 'POST',
    body: JSON.stringify({actor: 'incident-commander', decision: 'approved', reason: 'Approved in mission control'}),
  });
  toast('Approval recorded in the audit ledger');
  render(currentMission);
}

async function executeRec(recId) {
  try {
    currentMission = await api(`/api/missions/${currentMission.id}/recommendations/${recId}/execute`, {
      method: 'POST', body: JSON.stringify({actor: 'execution-broker'})
    });
    toast('Bounded action brokered; rollback token captured');
    render(currentMission);
  } catch (error) {
    toast(error.message);
  }
}

async function closeMission() {
  currentMission = await api(`/api/missions/${currentMission.id}/close`, {method: 'POST'});
  toast('Mission closed; replay and reusable memory captured');
  render(currentMission);
}

function render(mission) {
  $('emptyState').classList.add('hidden');
  $('missionView').classList.remove('hidden');
  $('missionId').textContent = mission.id;
  $('missionTitle').textContent = mission.title;
  $('severity').textContent = mission.severity;
  $('status').textContent = mission.status;
  $('signalCount').textContent = `${mission.signals.length} signals`;
  $('updatedAt').textContent = `updated ${shortTime(mission.updated_at)}`;
  $('replayLink').href = `/api/missions/${mission.id}/replay`;
  const top = mission.hypotheses[0];
  $('leadConfidence').textContent = top ? pct(top.confidence) : '—';
  $('blastRadius').textContent = top ? pct(top.blast_radius) : '—';
  $('recommendationCount').textContent = mission.recommendations.length;
  $('actionCount').textContent = mission.actions.length;
  $('hypotheses').innerHTML = mission.hypotheses.map((item, index) => `
    <div class="hypothesis">
      <div class="hypothesis-head">
        <div><h4>${index + 1}. ${item.title}</h4><div class="rec-worker">domain: ${item.failure_domain} · blast radius ${pct(item.blast_radius)}</div></div>
        <div class="score">${pct(item.confidence)}</div>
      </div>
      <p>${item.explanation}</p>
      <ul class="evidence">${item.evidence.map(e => `<li>${e.description}</li>`).join('')}</ul>
    </div>`).join('');
  renderGraph(mission);
  renderRecommendations(mission);
  $('internalSummary').textContent = mission.communications.internal_summary;
  $('statusDraft').textContent = mission.communications.status_page_draft;
  $('executiveUpdate').textContent = mission.communications.executive_update;
  $('timeline').innerHTML = [...mission.events].reverse().map(item => `
    <div class="timeline-item">
      <div class="timeline-time">${shortTime(item.timestamp)}</div>
      <div><div class="timeline-message">${item.message}</div><div class="timeline-actor">${item.actor} · ${item.event_type}</div></div>
    </div>`).join('');
  $('closeBtn').disabled = mission.status === 'closed';
}

function renderRecommendations(mission) {
  const approvals = new Set(mission.approvals.filter(a => a.decision === 'approved').map(a => a.recommendation_id));
  $('recommendations').innerHTML = mission.recommendations.map(rec => {
    const needsApproval = rec.policy_decision === 'require_approval';
    const approved = approvals.has(rec.id);
    const done = ['executed', 'simulated'].includes(rec.status);
    return `<article class="recommendation">
      <div class="rec-head">
        <div class="rank">#${rec.rank}</div>
        <div><div class="rec-title">${rec.title}</div><div class="rec-worker">${rec.worker} · ${rec.action_type} · target ${rec.target}</div></div>
        <span class="policy ${rec.policy_decision}">${rec.policy_class} · ${rec.policy_decision.replace('_', ' ')}</span>
      </div>
      <div class="rec-body">
        <div><p>${rec.rationale}</p><p class="rollback"><strong>Rollback:</strong> ${rec.rollback_plan}</p></div>
        <div class="rec-stats">
          <div class="rec-stat"><span>Reward</span><strong>${rec.expected_reward.toFixed(3)}</strong></div>
          <div class="rec-stat"><span>Confidence</span><strong>${pct(rec.confidence)}</strong></div>
          <div class="rec-stat"><span>Impact</span><strong>${pct(rec.expected_impact)}</strong></div>
          <div class="rec-stat"><span>Risk</span><strong>${pct(rec.risk_score)}</strong></div>
        </div>
        <div class="rec-actions">
          ${needsApproval && !approved ? `<button onclick="approve('${rec.id}')">Approve</button>` : ''}
          <button class="secondary" ${done || rec.policy_decision === 'deny' || (needsApproval && !approved) ? 'disabled' : ''} onclick="executeRec('${rec.id}')">${done ? rec.status : 'Execute'}</button>
        </div>
      </div>
    </article>`;
  }).join('');
}

function renderGraph(mission) {
  const svg = $('graph');
  const positions = {
    web:[110,75], cdn:[330,55], mobile_carrier:[565,65], api:[190,190], ai_provider:[545,190], worker:[190,315], queue:[355,310], db:[350,190], cloud_east:[500,310], cloud_west:[625,310]
  };
  const latest = mission.field_snapshots[mission.field_snapshots.length - 1]?.channels || {};
  const edges = mission.edges.map(edge => {
    const a = positions[edge.source], b = positions[edge.target];
    return `<line class="graph-edge" x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}" />`;
  }).join('');
  const nodes = mission.nodes.map(node => {
    const [x,y] = positions[node.id] || [350,195];
    const cell = latest[node.id] || {};
    const failure = cell.failure || 0;
    const suspicion = cell.causal_suspicion || 0;
    const radius = 15 + failure * 17;
    const ring = radius + 5 + suspicion * 7;
    const fill = failure > .55 ? '#ff6f6f' : failure > .25 ? '#f5bb57' : '#2f6c82';
    return `<g>
      <circle cx="${x}" cy="${y}" r="${ring}" fill="none" stroke="#62d8e8" stroke-opacity="${0.12 + suspicion * .75}" stroke-width="${1 + suspicion * 3}" />
      <circle cx="${x}" cy="${y}" r="${radius}" fill="${fill}" fill-opacity="${0.45 + failure * .5}" stroke="#b8e6ec" stroke-opacity=".35" />
      <text x="${x}" y="${y + radius + 17}" class="node-label">${node.label}</text>
      <text x="${x}" y="${y + radius + 29}" class="node-kind">${node.kind.replace('_',' ')}</text>
    </g>`;
  }).join('');
  svg.innerHTML = edges + nodes;
}

$('reanalyzeBtn').addEventListener('click', reanalyze);
$('closeBtn').addEventListener('click', closeMission);
boot().catch(error => toast(error.message));
