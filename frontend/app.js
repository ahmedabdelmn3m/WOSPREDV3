'use strict';

const troops = ['infantry', 'lancer', 'marksman'];
const stats = [
  ['attack_pct', 'Attack %'],
  ['defense_pct', 'Defense %'],
  ['health_pct', 'Health %'],
  ['lethality_pct', 'Lethality %'],
];
const fallbackHeroes = [
  { id: 'natalia', name: 'Natalia', specialty: 'infantry', generation: 1 },
  { id: 'jeronimo', name: 'Jeronimo', specialty: 'infantry', generation: 1 },
  { id: 'molly', name: 'Molly', specialty: 'lancer', generation: 1 },
  { id: 'zinman', name: 'Zinman', specialty: 'marksman', generation: 1 },
  { id: 'flint', name: 'Flint', specialty: 'infantry', generation: 2 },
  { id: 'philly', name: 'Philly', specialty: 'lancer', generation: 2 },
  { id: 'alonso', name: 'Alonso', specialty: 'marksman', generation: 2 },
  { id: 'logan', name: 'Logan', specialty: 'infantry', generation: 3 },
  { id: 'mia', name: 'Mia', specialty: 'lancer', generation: 3 },
  { id: 'greg', name: 'Greg', specialty: 'marksman', generation: 3 },
  { id: 'ahmose', name: 'Ahmose', specialty: 'infantry', generation: 4 },
  { id: 'reina', name: 'Reina', specialty: 'lancer', generation: 4 },
  { id: 'lynn', name: 'Lynn', specialty: 'marksman', generation: 4 },
  { id: 'hector', name: 'Hector', specialty: 'infantry', generation: 5 },
  { id: 'norah', name: 'Norah', specialty: 'lancer', generation: 5 },
  { id: 'gwen', name: 'Gwen', specialty: 'marksman', generation: 5 },
];
const state = { heroes: fallbackHeroes, lastPrediction: null, lastFormation: null };

const $ = (id) => document.getElementById(id);
const apiBase = () => (window.WOS_API_URL || 'http://localhost:8080').replace(/\/$/, '');
const number = (id) => Number($(id)?.value || 0);
const text = (id) => ($(id)?.value || '').trim();

async function api(path, options = {}) {
  const res = await fetch(`${apiBase()}${path}`, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return data;
}

function buildStats(side) {
  $(`${side}-stats`).innerHTML = troops.map((troop) => `
    <section class="troop-card">
      <h3>${label(troop)}</h3>
      <div class="stat-grid">
        ${stats.map(([key, name]) => `
          <label>${name}<input id="${side}-${troop}-${key}" type="number" min="0" max="9999" value="0" /></label>
        `).join('')}
      </div>
    </section>
  `).join('');
}

function buildHeroRows(side) {
  const options = ['<option value="">Unknown / not applied</option>']
    .concat(state.heroes.map((h) => `<option value="${h.id}">${h.name} - ${label(h.specialty)} Gen ${h.generation}</option>`))
    .join('');
  $(`${side}-heroes`).innerHTML = [0, 1, 2].map((i) => `
    <div class="hero-row">
      <select id="${side}-hero-${i}">${options}</select>
      <label>Stars<input id="${side}-hero-stars-${i}" type="number" min="1" max="5" value="5" /></label>
      <label>Widget<input id="${side}-hero-widget-${i}" type="number" min="0" max="10" value="0" /></label>
    </div>
  `).join('');
}

function readArmy(side) {
  const army = {
    name: text(`${side}-name`) || (side === 'own' ? 'My March' : 'Enemy March'),
    infantry: {},
    lancer: {},
    marksman: {},
    formation: {
      infantry: number(`${side}-form-infantry`) / 100,
      lancer: number(`${side}-form-lancer`) / 100,
      marksman: number(`${side}-form-marksman`) / 100,
    },
    troop_count: Math.max(1, Math.round(number(`${side}-troops`))),
    heroes: readHeroes(side),
  };
  troops.forEach((troop) => stats.forEach(([key]) => {
    army[troop][key] = number(`${side}-${troop}-${key}`);
  }));
  return army;
}

function readHeroes(side) {
  return [0, 1, 2].map((i) => {
    const id = text(`${side}-hero-${i}`);
    const def = state.heroes.find((h) => h.id === id);
    return id ? {
      id,
      name: def?.name || id,
      stars: Math.max(1, Math.min(5, Math.round(number(`${side}-hero-stars-${i}`)))),
      widget_level: Math.max(0, Math.round(number(`${side}-hero-widget-${i}`))),
    } : null;
  }).filter(Boolean);
}

function writeArmy(side, army) {
  $(`${side}-name`).value = army.name || '';
  troops.forEach((troop) => stats.forEach(([key]) => {
    $(`${side}-${troop}-${key}`).value = army[troop]?.[key] ?? 0;
  }));
  $(`${side}-form-infantry`).value = Math.round((army.formation?.infantry ?? 0.5) * 100);
  $(`${side}-form-lancer`).value = Math.round((army.formation?.lancer ?? 0.2) * 100);
  $(`${side}-form-marksman`).value = Math.round((army.formation?.marksman ?? 0.3) * 100);
  $(`${side}-troops`).value = army.troop_count || 500000;
  updateFormation(side);
}

function validateAll() {
  return ['own', 'enemy'].every(updateFormation);
}

function updateFormation(side) {
  const total = number(`${side}-form-infantry`) + number(`${side}-form-lancer`) + number(`${side}-form-marksman`);
  const ok = Math.abs(total - 100) <= 0.5;
  $(`${side}-form-total`).textContent = `Total ${total.toFixed(0)}%`;
  $(`${side}-form-total`).className = `form-total ${ok ? 'ok' : 'bad'}`;
  const totalTroops = Math.max(1, Math.round(number(`${side}-troops`)));
  const inf = Math.round(totalTroops * number(`${side}-form-infantry`) / 100);
  const lan = Math.round(totalTroops * number(`${side}-form-lancer`) / 100);
  const mrk = Math.max(0, totalTroops - inf - lan);
  $(`${side}-breakdown`).textContent = `Troops: ${format(inf)} infantry, ${format(lan)} lancer, ${format(mrk)} marksman`;
  return ok;
}

async function uploadScout(side) {
  const file = $(`${side}-upload`).files?.[0];
  if (!file) return notice(`${side}-upload-state`, 'Choose an image first.');
  const form = new FormData();
  form.append('file', file);
  notice(`${side}-upload-state`, 'Uploading scout image...');
  try {
    const result = await api('/scout-upload', { method: 'POST', body: form });
    notice(`${side}-upload-state`, `${result.ocr_status}: ${result.message}`);
  } catch (err) {
    notice(`${side}-upload-state`, err.message);
  }
}

async function runPrediction() {
  if (!validateAll()) return renderError('Both formations must equal 100%.');
  const payload = { attacker: readArmy('own'), defender: readArmy('enemy'), max_rounds: 20 };
  renderLoading('Running prediction...');
  try {
    const result = await api('/predict-outcome', jsonOptions(payload));
    state.lastPrediction = { payload, result };
    renderPrediction(result);
  } catch (err) {
    renderError(err.message);
  }
}

async function optimizeFormation() {
  if (!validateAll()) return renderError('Both formations must equal 100%.');
  const payload = { own_army: readArmy('own'), enemy_army: readArmy('enemy'), max_rounds: 20 };
  renderLoading('Checking formation presets...');
  try {
    const result = await api('/formation/optimize', jsonOptions(payload));
    state.lastFormation = result;
    renderFormation(result);
  } catch (err) {
    renderError(err.message);
  }
}

async function savePredictionRun() {
  if (!state.lastPrediction) return renderError('Run a prediction first.');
  const body = {
    attacker: state.lastPrediction.payload.attacker,
    defender: state.lastPrediction.payload.defender,
    result: state.lastPrediction.result,
  };
  await api('/prediction-runs', jsonOptions(body));
  renderToast('Prediction run saved.');
}

async function saveBattleLog() {
  const own = readArmy('own');
  const enemy = readArmy('enemy');
  const body = {
    own_stats: { infantry: own.infantry, lancer: own.lancer, marksman: own.marksman },
    enemy_stats: { infantry: enemy.infantry, lancer: enemy.lancer, marksman: enemy.marksman },
    own_formation: own.formation,
    enemy_formation: enemy.formation,
    own_heroes: own.heroes,
    enemy_heroes: enemy.heroes,
    prediction_result: state.lastPrediction?.result || null,
    actual_result: null,
    notes: 'Saved from MVP UI. Add actual result after battle.',
  };
  await api('/battle-logs', jsonOptions(body));
  await loadLogs();
  renderToast('Battle log saved.');
}

function renderPrediction(result) {
  const meta = result.metadata || {};
  const win = Math.round((result.win_probability || 0) * 100);
  const own = result.attacker || {};
  const enemy = result.defender || {};
  $('prediction-output').innerHTML = `
    <div class="result-card">
      <div class="metric-grid">
        <div class="metric"><span>Win Probability</span><strong>${win}%</strong></div>
        <div class="metric"><span>Winner</span><strong>${result.winner}</strong></div>
        <div class="metric"><span>Confidence</span><strong>${meta.confidence_level || 'medium'}</strong></div>
        <div class="metric"><span>Rounds</span><strong>${result.rounds_played}</strong></div>
      </div>
      <div class="metric-grid">
        <div class="metric"><span>Own Survivors</span><strong>${format(own.survivors)} / ${format(own.initial_troops)}</strong></div>
        <div class="metric"><span>Enemy Survivors</span><strong>${format(enemy.survivors)} / ${format(enemy.initial_troops)}</strong></div>
        <div class="metric"><span>Strongest Advantage</span><strong>${meta.strongest_advantage?.troop_type || 'n/a'}</strong></div>
        <div class="metric"><span>Weakest Weakness</span><strong>${meta.weakest_weakness?.troop_type || 'n/a'}</strong></div>
      </div>
      ${renderBreakdown(meta.troop_type_breakdown)}
      ${renderStrength(result.strength_analysis)}
      <div class="warning">${(meta.warnings || []).join('<br>')}</div>
      <p>${result.summary || ''}</p>
    </div>
  `;
}

function renderFormation(result) {
  const rows = (result.all_results || []).slice(0, 8).map((r) => `
    <div class="list-item">
      <strong>${r.label}</strong> - ${Math.round((r.win_probability || 0) * 100)}% - ${r.winner}
      <div class="hint">${format(r.attacker_survivors)} own troops survive</div>
    </div>
  `).join('');
  $('prediction-output').innerHTML = `
    <div class="result-card">
      <div class="metric"><span>Recommended Formation</span><strong>${result.best_label || 'n/a'}</strong></div>
      <div class="list">${rows}</div>
      <div class="warning">Formation recommendations use the same pending-verification constants as the prediction engine.</div>
    </div>
  `;
}

function renderStrength(analysis = {}) {
  return `<div class="list">${troops.map((troop) => {
    const item = analysis[troop] || {};
    return `<div class="list-item"><strong>${label(troop)}</strong>: ${item.status || 'n/a'} <span class="hint">Net advantage ${item.net_advantage ?? 'n/a'}</span></div>`;
  }).join('')}</div>`;
}

function renderBreakdown(breakdown) {
  if (!breakdown) return '';
  return `
    <div class="list-item">
      <strong>Troop Type Breakdown</strong>
      <div class="hint">Own: ${breakdownLine(breakdown.attacker)}</div>
      <div class="hint">Enemy: ${breakdownLine(breakdown.defender)}</div>
    </div>`;
}

function saveLocalPreset(side) {
  const key = side === 'own' ? 'wos-own-presets' : 'wos-enemy-presets';
  const army = readArmy(side);
  const list = JSON.parse(localStorage.getItem(key) || '[]');
  list.unshift({ id: crypto.randomUUID(), created_at: new Date().toISOString(), side, army });
  localStorage.setItem(key, JSON.stringify(list.slice(0, 20)));
  loadPresets();
  renderToast('Preset saved.');
}

function loadPresets() {
  const own = JSON.parse(localStorage.getItem('wos-own-presets') || '[]');
  const enemy = JSON.parse(localStorage.getItem('wos-enemy-presets') || '[]');
  const all = own.concat(enemy);
  $('preset-list').className = `list ${all.length ? '' : 'empty'}`;
  $('preset-list').innerHTML = all.length ? all.map((p) => `
    <div class="list-item">
      <strong>${p.army.name}</strong> <span class="hint">${p.side} - ${new Date(p.created_at).toLocaleString()}</span>
      <button data-load-preset="${p.id}" data-side="${p.side}">Load</button>
    </div>
  `).join('') : 'No presets saved yet.';
  document.querySelectorAll('[data-load-preset]').forEach((button) => {
    button.addEventListener('click', () => {
      const preset = all.find((item) => item.id === button.dataset.loadPreset);
      if (preset) writeArmy(preset.side, preset.army);
    });
  });
}

async function loadLogs() {
  try {
    const data = await api('/battle-logs');
    const logs = data.battle_logs || [];
    $('log-list').className = `list ${logs.length ? '' : 'empty'}`;
    $('log-list').innerHTML = logs.length ? logs.map((log) => `
      <div class="list-item">
        <strong>${log.actual_result || 'Pending actual result'}</strong>
        <div class="hint">${log.created_at}</div>
        <div class="hint">${log.notes || ''}</div>
      </div>
    `).join('') : 'No battle logs saved yet.';
  } catch {
    $('log-list').textContent = 'Battle logs are unavailable until the backend is online.';
  }
}

async function checkApi() {
  try {
    await api('/health');
    const heroes = await api('/hero-definitions');
    state.heroes = heroes.heroes || [];
  } catch (err) {
    console.warn('Prediction service is unavailable:', err.message);
    state.heroes = fallbackHeroes;
  }
  ['own', 'enemy'].forEach(buildHeroRows);
}

function bindEvents() {
  document.querySelectorAll('.tab').forEach((button) => {
    button.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach((b) => b.classList.remove('active'));
      document.querySelectorAll('.view').forEach((v) => v.classList.remove('active'));
      button.classList.add('active');
      $(button.dataset.view).classList.add('active');
    });
  });
  ['own', 'enemy'].forEach((side) => {
    troops.forEach((troop) => $(`${side}-form-${troop}`).addEventListener('input', () => updateFormation(side)));
    $(`${side}-troops`).addEventListener('input', () => updateFormation(side));
  });
  document.querySelectorAll('[data-formation]').forEach((button) => {
    button.addEventListener('click', () => {
      const [inf, lan, mrk] = button.dataset.values.split(',');
      const side = button.dataset.formation;
      $(`${side}-form-infantry`).value = inf;
      $(`${side}-form-lancer`).value = lan;
      $(`${side}-form-marksman`).value = mrk;
      updateFormation(side);
    });
  });
  document.querySelectorAll('[data-upload]').forEach((button) => button.addEventListener('click', () => uploadScout(button.dataset.upload)));
  $('run-prediction').addEventListener('click', runPrediction);
  $('optimize-formation').addEventListener('click', optimizeFormation);
  $('save-prediction').addEventListener('click', savePredictionRun);
  $('save-battle-log').addEventListener('click', saveBattleLog);
  $('save-own-preset').addEventListener('click', () => saveLocalPreset('own'));
  $('save-enemy-preset').addEventListener('click', () => saveLocalPreset('enemy'));
}

function jsonOptions(body) {
  return { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
}
function renderLoading(message) { $('prediction-output').innerHTML = `<div class="empty">${message}</div>`; }
function renderError(message) { $('prediction-output').innerHTML = `<div class="warning">${message}</div>`; }
function renderToast(message) { $('prediction-output').insertAdjacentHTML('afterbegin', `<div class="warning">${message}</div>`); }
function notice(id, message) { $(id).textContent = message; }
function format(value) { return Number(value || 0).toLocaleString(); }
function label(value) { return value.charAt(0).toUpperCase() + value.slice(1); }
function breakdownLine(data = {}) { return troops.map((troop) => `${label(troop)} ${format(data[troop])}`).join(', '); }

function init() {
  ['own', 'enemy'].forEach(buildStats);
  ['own', 'enemy'].forEach(buildHeroRows);
  ['own', 'enemy'].forEach(updateFormation);
  bindEvents();
  loadPresets();
  loadLogs();
  checkApi();
}

document.addEventListener('DOMContentLoaded', init);
