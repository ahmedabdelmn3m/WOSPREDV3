'use strict';

const troops = ['infantry', 'lancer', 'marksman'];
const stats = [
  ['attack_pct', 'Attack %'],
  ['defense_pct', 'Defense %'],
  ['health_pct', 'Health %'],
  ['lethality_pct', 'Lethality %'],
];
const fallbackHeroes = [
  { id: 'natalia', name: 'Natalia', type: 'infantry', specialty: 'infantry', generation: 1 },
  { id: 'jeronimo', name: 'Jeronimo', type: 'infantry', specialty: 'infantry', generation: 1 },
  { id: 'molly', name: 'Molly', type: 'lancer', specialty: 'lancer', generation: 1 },
  { id: 'zinman', name: 'Zinman', type: 'marksman', specialty: 'marksman', generation: 1 },
  { id: 'flint', name: 'Flint', type: 'infantry', specialty: 'infantry', generation: 2 },
  { id: 'philly', name: 'Philly', type: 'lancer', specialty: 'lancer', generation: 2 },
  { id: 'alonso', name: 'Alonso', type: 'marksman', specialty: 'marksman', generation: 2 },
  { id: 'logan', name: 'Logan', type: 'infantry', specialty: 'infantry', generation: 3 },
  { id: 'mia', name: 'Mia', type: 'lancer', specialty: 'lancer', generation: 3 },
  { id: 'greg', name: 'Greg', type: 'marksman', specialty: 'marksman', generation: 3 },
  { id: 'ahmose', name: 'Ahmose', type: 'infantry', specialty: 'infantry', generation: 4 },
  { id: 'reina', name: 'Reina', type: 'lancer', specialty: 'lancer', generation: 4 },
  { id: 'lynn', name: 'Lynn', type: 'marksman', specialty: 'marksman', generation: 4 },
  { id: 'hector', name: 'Hector', type: 'infantry', specialty: 'infantry', generation: 5 },
  { id: 'norah', name: 'Norah', type: 'lancer', specialty: 'lancer', generation: 5 },
  { id: 'gwen', name: 'Gwen', type: 'marksman', specialty: 'marksman', generation: 5 },
];
const state = { heroes: fallbackHeroes, lastPrediction: null, lastFormation: null, lastDecisionText: '' };

const $ = (id) => document.getElementById(id);
const apiBase = () => (window.WOS_API_URL || 'http://localhost:8080').replace(/\/$/, '');
const number = (id) => Number($(id)?.value || 0);
const rawNumber = (id) => $(id)?.value ?? '';
const text = (id) => ($(id)?.value || '').trim();

async function api(path, options = {}) {
  const res = await fetch(`${apiBase()}${path}`, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(Array.isArray(data.detail) ? data.detail.map((d) => d.msg).join(', ') : data.detail || `HTTP ${res.status}`);
  return data;
}

function buildStats(side) {
  $(`${side}-stats`).innerHTML = troops.map((troop) => `
    <section class="troop-card">
      <h3>${label(troop)}</h3>
      <div class="troop-base-grid">
        <label>Tier
          <select id="${side}-${troop}-tier">
            <option value="10">T10 Apex</option>
            <option value="11" selected>T11 Helios</option>
          </select>
        </label>
        <label>FC Level
          <select id="${side}-${troop}-fc">
            ${Array.from({ length: 10 }, (_, i) => `<option value="${i + 1}" ${i === 9 ? 'selected' : ''}>FC${i + 1}</option>`).join('')}
          </select>
        </label>
        <div id="${side}-${troop}-base-note" class="troop-base-note"></div>
      </div>
      <div class="stat-grid">
        ${stats.map(([key, name]) => `
          <label>${name}<input id="${side}-${troop}-${key}" type="number" min="0" max="9999" value="0" /></label>
        `).join('')}
      </div>
    </section>
  `).join('');
}

function buildHeroRows(side) {
  $(`${side}-heroes`).innerHTML = troops.map((troop) => {
    const options = [`<option value="">Select ${label(troop)} hero</option>`]
      .concat(heroesByType(troop).map((h) => `<option value="${h.id}">${h.name} - Gen ${h.generation}</option>`))
      .join('');
    return `
      <div class="hero-row" data-required-type="${troop}">
        <label>${label(troop)} Hero<select id="${side}-hero-${troop}">${options}</select></label>
        <label>Stars<input id="${side}-hero-stars-${troop}" type="number" min="1" max="5" value="5" /></label>
        <label>Widget<input id="${side}-hero-widget-${troop}" type="number" min="1" max="10" value="1" /></label>
      </div>`;
  }).join('');
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
    troop_count: Math.round(number(`${side}-troops`)),
    heroes: readHeroes(side),
  };
  troops.forEach((troop) => stats.forEach(([key]) => {
    army[troop][key] = number(`${side}-${troop}-${key}`);
  }));
  troops.forEach((troop) => {
    const base = selectedTroopBase(side, troop);
    army[troop].troop_type = troop;
    army[troop].tier = Number($(`${side}-${troop}-tier`)?.value || 11);
    army[troop].fc_level = Number($(`${side}-${troop}-fc`)?.value || 10);
    if (base) {
      army[troop].attack_base = base.attack;
      army[troop].defense_base = base.defense;
      army[troop].health_base = base.health;
      army[troop].lethality_base = base.lethality;
    }
  });
  return army;
}

function readHeroes(side) {
  return troops.map((troop) => {
    const id = text(`${side}-hero-${troop}`);
    const def = state.heroes.find((h) => h.id === id);
    return id ? {
      id,
      name: def?.name || id,
      type: heroType(def) || troop,
      stars: Math.round(number(`${side}-hero-stars-${troop}`)),
      widget_level: Math.round(number(`${side}-hero-widget-${troop}`)),
    } : null;
  }).filter(Boolean);
}

function writeArmy(side, army) {
  $(`${side}-name`).value = army.name || '';
  troops.forEach((troop) => stats.forEach(([key]) => {
    $(`${side}-${troop}-${key}`).value = army[troop]?.[key] ?? 0;
  }));
  troops.forEach((troop) => {
    if ($(`${side}-${troop}-tier`)) $(`${side}-${troop}-tier`).value = army[troop]?.tier || 11;
    if ($(`${side}-${troop}-fc`)) $(`${side}-${troop}-fc`).value = army[troop]?.fc_level || 10;
  });
  $(`${side}-form-infantry`).value = Math.round((army.formation?.infantry ?? 0.5) * 100);
  $(`${side}-form-lancer`).value = Math.round((army.formation?.lancer ?? 0.2) * 100);
  $(`${side}-form-marksman`).value = Math.round((army.formation?.marksman ?? 0.3) * 100);
  $(`${side}-troops`).value = army.troop_count || 500000;
  (army.heroes || []).forEach((hero) => {
    const type = hero.type || heroType(state.heroes.find((h) => h.id === hero.id));
    if (!type || !$(`${side}-hero-${type}`)) return;
    $(`${side}-hero-${type}`).value = hero.id || '';
    $(`${side}-hero-stars-${type}`).value = hero.stars || 5;
    $(`${side}-hero-widget-${type}`).value = hero.widget_level || 1;
  });
  updateValidation();
}

function validateStats(side) {
  const errors = [];
  troops.forEach((troop) => stats.forEach(([key, name]) => {
    const value = rawNumber(`${side}-${troop}-${key}`);
    if (value === '') errors.push(`${sideLabel(side)} ${label(troop)} ${name} is required.`);
    if (Number(value) < 0) errors.push(`${sideLabel(side)} ${label(troop)} ${name} cannot be negative.`);
  }));
  return errors;
}

function validateMainMarch(side) {
  const errors = [];
  const heroes = readHeroes(side);
  const ids = heroes.map((h) => h.id);
  const types = heroes.map((h) => h.type);
  const missingTypes = troops.filter((troop) => !types.includes(troop));
  if (heroes.length !== 3) errors.push(`${sideLabel(side)} needs exactly 3 heroes.`);
  missingTypes.forEach((troop) => errors.push(`${sideLabel(side)} needs one ${label(troop)} hero.`));
  if (new Set(ids).size !== ids.length) errors.push(`${sideLabel(side)} cannot use duplicate heroes.`);
  if (new Set(types).size !== types.length) errors.push(`${sideLabel(side)} cannot use duplicate hero types.`);
  heroes.forEach((hero) => {
    if (hero.stars < 1 || hero.stars > 5) errors.push(`${sideLabel(side)} ${hero.name} stars must be 1-5.`);
    if (hero.widget_level <= 0) errors.push(`${sideLabel(side)} ${hero.name} widget level must be greater than 0.`);
  });
  return errors;
}

function validateArmy(side) {
  const errors = [];
  const total = formationTotal(side);
  if (Math.abs(total - 100) > 0.5) errors.push(`${sideLabel(side)} formation must equal 100%.`);
  if (number(`${side}-troops`) <= 0) errors.push(`${sideLabel(side)} troop count must be greater than 0.`);
  return errors.concat(validateMainMarch(side), validateStats(side));
}

function validatePredictionForm() {
  const errors = [];
  if (!text('battle-type')) errors.push('Battle type is required.');
  if (text('simulation-mode') === 'monte_carlo' && (number('monte-carlo-runs') < 50 || number('monte-carlo-runs') > 5000)) {
    errors.push('Monte Carlo runs must be between 50 and 5000.');
  }
  return errors.concat(validateArmy('own'), validateArmy('enemy'));
}

function updateValidation() {
  ['own', 'enemy'].forEach(updateFormation);
  const errors = validatePredictionForm();
  const box = $('validation-messages');
  if (box) {
    box.className = `validation-box ${errors.length ? '' : 'ok'}`;
    box.innerHTML = errors.length ? errors.slice(0, 8).map((err) => `<div>${escapeHtml(err)}</div>`).join('') : '<div>Ready to run prediction.</div>';
  }
  const disabled = errors.length > 0;
  ['run-prediction', 'optimize-formation'].forEach((id) => {
    if ($(id)) $(id).disabled = disabled;
  });
  return errors;
}

function updateFormation(side) {
  const total = formationTotal(side);
  const ok = Math.abs(total - 100) <= 0.5;
  $(`${side}-form-total`).textContent = `Total ${total.toFixed(0)}%`;
  $(`${side}-form-total`).className = `form-total ${ok ? 'ok' : 'bad'}`;
  const totalTroops = Math.max(0, Math.round(number(`${side}-troops`)));
  const inf = Math.round(totalTroops * number(`${side}-form-infantry`) / 100);
  const lan = Math.round(totalTroops * number(`${side}-form-lancer`) / 100);
  const mrk = Math.max(0, totalTroops - inf - lan);
  $(`${side}-breakdown`).textContent = `Troops: ${format(inf)} infantry, ${format(lan)} lancer, ${format(mrk)} marksman`;
  troops.forEach((troop) => updateTroopBaseNote(side, troop));
  return ok;
}

async function uploadScout(side) {
  const file = $(`${side}-upload`).files?.[0];
  if (!file) return notice(`${side}-upload-state`, 'Choose an image first.');
  if (!window.Tesseract) return notice(`${side}-upload-state`, 'OCR did not load. Please refresh and try again.');
  notice(`${side}-upload-state`, 'Reading screenshot with free OCR...');
  try {
    const result = await Tesseract.recognize(file, 'eng', {
      logger: (event) => {
        if (event.status === 'recognizing text') {
          notice(`${side}-upload-state`, `Reading screenshot... ${Math.round((event.progress || 0) * 100)}%`);
        }
      },
    });
    const parsed = parseScoutText(result.data?.text || '');
    const filled = applyParsedStats(side, parsed);
    notice(`${side}-upload-state`, `OCR filled ${filled}/12 stat fields. Please review before predicting.`);
    updateValidation();
  } catch (err) {
    notice(`${side}-upload-state`, `OCR failed: ${err.message}`);
  }
}

function parseScoutText(ocrText) {
  const textBody = normalizeOcrText(ocrText);
  const parsed = {};
  troops.forEach((troop) => {
    parsed[troop] = {};
    stats.forEach(([key]) => {
      parsed[troop][key] = extractScoutValue(textBody, troop, key);
    });
  });
  return parsed;
}

function normalizeOcrText(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/[|]/g, ' ')
    .replace(/defen[sc]e/g, 'defense')
    .replace(/marksmen/g, 'marksman')
    .replace(/\s+/g, ' ');
}

function extractScoutValue(textBody, troop, key) {
  const statWords = {
    attack_pct: '(?:attack|atk)',
    defense_pct: '(?:defense|def|defence)',
    health_pct: '(?:health|hp)',
    lethality_pct: '(?:lethality|lethal)',
  }[key];
  const patterns = [
    new RegExp(`${troop}.{0,50}${statWords}[^0-9]{0,20}([0-9][0-9,.]*)`, 'i'),
    new RegExp(`${statWords}.{0,50}${troop}[^0-9]{0,20}([0-9][0-9,.]*)`, 'i'),
  ];
  for (const pattern of patterns) {
    const match = textBody.match(pattern);
    if (!match) continue;
    const value = Number(match[1].replace(/,/g, ''));
    if (Number.isFinite(value)) return round(value);
  }
  return null;
}

function applyParsedStats(side, parsed) {
  let filled = 0;
  troops.forEach((troop) => stats.forEach(([key]) => {
    const value = parsed[troop]?.[key];
    if (value === null || value === undefined) return;
    $(`${side}-${troop}-${key}`).value = value;
    filled += 1;
  }));
  return filled;
}

function fillTestPredictor() {
  const ownFormation = randomItem([[50, 20, 30], [60, 40, 0], [60, 20, 20], [55, 20, 25]]);
  const enemyFormation = randomItem([[50, 20, 30], [60, 40, 0], [60, 20, 20], [55, 20, 25]]);
  $('battle-type').value = 'solo_attack';
  fillTestSide('own', ownFormation, 1.06);
  fillTestSide('enemy', enemyFormation, 0.98);
  updateValidation();
  renderToast('Test predictor filled realistic sample stats. You can run prediction now.');
}

function fillTestSide(side, formation, strengthMultiplier) {
  $(`${side}-name`).value = side === 'own' ? 'Sample Player' : 'Sample Enemy';
  $(`${side}-troops`).value = randomInt(850000, 1450000);
  troops.forEach((troop, index) => {
    $(`${side}-${troop}-tier`).value = randomItem([10, 11]);
    $(`${side}-${troop}-fc`).value = randomInt(5, 10);
    $(`${side}-form-${troop}`).value = formation[index];
    stats.forEach(([key]) => {
      const base = key === 'health_pct' || key === 'defense_pct' ? randomInt(850, 1650) : randomInt(950, 1850);
      $(`${side}-${troop}-${key}`).value = Math.round(base * strengthMultiplier);
    });
    const hero = randomItem(heroesByType(troop).slice(-3)) || heroesByType(troop)[0];
    if (hero) $(`${side}-hero-${troop}`).value = hero.id;
    $(`${side}-hero-stars-${troop}`).value = 5;
    $(`${side}-hero-widget-${troop}`).value = randomInt(4, 10);
  });
  updateFormation(side);
}

async function runPrediction() {
  const errors = updateValidation();
  if (errors.length) return renderError(errors.join('<br>'));
  const payload = {
    attacker: readArmy('own'),
    defender: readArmy('enemy'),
    battle_type: text('battle-type'),
    max_rounds: 20,
    simulation_mode: text('simulation-mode') || 'expected_value',
    monte_carlo_runs: Math.round(number('monte-carlo-runs') || 1000),
  };
  renderLoading('Running prediction...');
  try {
    const result = await api('/predict-outcome', jsonOptions(payload));
    const scenarios = await runScenarios(payload, result);
    state.lastPrediction = { payload, result, scenarios };
    renderPrediction(result, payload, scenarios);
  } catch (err) {
    renderError(err.message);
  }
}

async function runScenarios(payload, baseResult) {
  const scenarios = [{ name: 'Current setup', result: baseResult }];
  const copies = [
    ['Infantry HP +10%', (p) => { p.attacker.infantry.health_pct *= 1.1; }],
    ['Infantry DEF +8%', (p) => { p.attacker.infantry.defense_pct *= 1.08; }],
    ['Troops +150k', (p) => { p.attacker.troop_count += 150000; }],
  ];
  await Promise.all(copies.map(async ([name, mutate]) => {
    const next = JSON.parse(JSON.stringify(payload));
    mutate(next);
    next.simulation_mode = 'expected_value';
    try {
      scenarios.push({ name, result: await api('/predict-outcome', jsonOptions(next)) });
    } catch {
      scenarios.push({ name, error: 'Unavailable' });
    }
  }));
  try {
    const best = await api('/formation/optimize', jsonOptions({ own_army: payload.attacker, enemy_army: payload.defender, max_rounds: payload.max_rounds }));
    const bestResult = (best.all_results || [])[0];
    if (bestResult) scenarios.push({ name: `Best formation: ${best.best_label}`, result: bestResult });
  } catch {
    scenarios.push({ name: 'Best formation', error: 'Unavailable' });
  }
  return scenarios;
}

async function optimizeFormation() {
  const errors = updateValidation();
  if (errors.length) return renderError(errors.join('<br>'));
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
    notes: 'Saved from predictor UI. Add actual result after battle.',
  };
  await api('/battle-logs', jsonOptions(body));
  await loadLogs();
  renderToast('Battle log saved.');
}

function renderPrediction(result, payload, scenarios) {
  const meta = result.metadata || {};
  const winPct = Math.round((result.win_probability || 0) * 100);
  const own = result.attacker || {};
  const enemy = result.defender || {};
  const labelText = resultLabel(winPct);
  const decision = decisionText(winPct, payload.battle_type);
  const confidence = confidenceLabel(meta);
  const advantages = statAdvantages(payload.attacker, payload.defender, meta);
  const reasons = topReasons(result, advantages);
  const flips = flipFightText(scenarios, winPct);
  state.lastDecisionText = summaryText(result, payload, scenarios, labelText, decision, confidence, reasons, flips);
  $('prediction-output').innerHTML = `
    <div class="result-card decision-card ${winPct >= 50 ? 'win' : 'loss'}">
      <div class="decision-title">
        <strong>${labelText}</strong>
        <span>${winPct}% win chance</span>
      </div>
      <p><strong>Final Decision:</strong> ${decision}</p>
      <div class="metric-grid">
        <div class="metric"><span>Confidence</span><strong>${confidence}</strong></div>
        <div class="metric"><span>Winner</span><strong>${escapeHtml(result.winner || 'n/a')}</strong></div>
        <div class="metric"><span>Own Survivors</span><strong>${format(own.survivors)} / ${format(own.initial_troops)}</strong></div>
        <div class="metric"><span>Enemy Survivors</span><strong>${format(enemy.survivors)} / ${format(enemy.initial_troops)}</strong></div>
      </div>
      <h3>Why This Result Happened</h3>
      <div class="list">${reasons.map((item) => `<div class="list-item">${item}</div>`).join('')}</div>
      <h3>Stat Breakdown</h3>
      ${renderEffectiveStats(meta.effective_stats)}
      ${renderAdvantageTable(advantages)}
      <h3>Scenario Comparison</h3>
      ${renderScenarioTable(scenarios)}
      <h3>What Flips The Fight</h3>
      <div class="list-item">${flips}</div>
      <div class="warning">${(meta.warnings || []).join('<br>')}</div>
      <button id="copy-summary" type="button">Copy Result Summary</button>
    </div>
  `;
  $('copy-summary').addEventListener('click', copySummary);
}

function renderAdvantageTable(rows) {
  return `
    <div class="table-wrap"><table class="result-table">
      <thead><tr><th>Category</th><th>Own</th><th>Enemy</th><th>Edge</th></tr></thead>
      <tbody>${rows.map((row) => `<tr><td>${row.label}</td><td>${row.own}</td><td>${row.enemy}</td><td class="${row.edgeClass}">${row.edge}</td></tr>`).join('')}</tbody>
    </table></div>`;
}

function renderEffectiveStats(effectiveStats) {
  if (!effectiveStats) return '';
  const rows = [];
  ['attacker', 'defender'].forEach((side) => troops.forEach((troop) => {
    const item = effectiveStats[side]?.[troop] || {};
    rows.push(`<tr><td>${label(side)}</td><td>${label(troop)}</td><td>${item.attack || 0}</td><td>${item.defense || 0}</td><td>${item.health || 0}</td><td>${item.lethality || 0}</td><td>${format(item.effective_damage)}</td><td>${format(item.effective_defense)}</td></tr>`);
  }));
  return `
    <div class="table-wrap"><table class="result-table">
      <thead><tr><th>Side</th><th>Troop</th><th>Base ATK</th><th>Base DEF</th><th>Base HP</th><th>Base LETH</th><th>Effective Damage</th><th>Effective Defense</th></tr></thead>
      <tbody>${rows.join('')}</tbody>
    </table></div>`;
}

function renderScenarioTable(scenarios = []) {
  return `
    <div class="table-wrap"><table class="result-table">
      <thead><tr><th>Scenario</th><th>Win Chance</th><th>Label</th><th>Winner</th></tr></thead>
      <tbody>${scenarios.map((s) => {
        if (s.error) return `<tr><td>${s.name}</td><td colspan="3">${s.error}</td></tr>`;
        const pct = Math.round((s.result.win_probability || 0) * 100);
        return `<tr><td>${s.name}</td><td>${pct}%</td><td>${resultLabel(pct)}</td><td>${escapeHtml(s.result.winner || 'n/a')}</td></tr>`;
      }).join('')}</tbody>
    </table></div>`;
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
    state.heroes = normalizeHeroes(heroes.heroes || fallbackHeroes);
  } catch (err) {
    console.warn('Prediction service is unavailable:', err.message);
    state.heroes = fallbackHeroes;
  }
  ['own', 'enemy'].forEach(buildHeroRows);
  updateValidation();
}

function bindEvents() {
  document.querySelectorAll('.tab[data-view]').forEach((button) => {
    button.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach((b) => b.classList.remove('active'));
      document.querySelectorAll('.view').forEach((v) => v.classList.remove('active'));
      button.classList.add('active');
      $(button.dataset.view).classList.add('active');
    });
  });
  document.addEventListener('input', updateValidation);
  document.addEventListener('change', updateValidation);
  document.querySelectorAll('[data-formation]').forEach((button) => {
    button.addEventListener('click', () => {
      const [inf, lan, mrk] = button.dataset.values.split(',');
      const side = button.dataset.formation;
      $(`${side}-form-infantry`).value = inf;
      $(`${side}-form-lancer`).value = lan;
      $(`${side}-form-marksman`).value = mrk;
      updateValidation();
    });
  });
  document.querySelectorAll('[data-upload]').forEach((button) => button.addEventListener('click', () => uploadScout(button.dataset.upload)));
  $('run-prediction').addEventListener('click', runPrediction);
  $('test-predictor').addEventListener('click', fillTestPredictor);
  $('optimize-formation').addEventListener('click', optimizeFormation);
  $('save-prediction').addEventListener('click', savePredictionRun);
  $('save-battle-log').addEventListener('click', saveBattleLog);
  $('save-own-preset').addEventListener('click', () => saveLocalPreset('own'));
  $('save-enemy-preset').addEventListener('click', () => saveLocalPreset('enemy'));
}

function statAdvantages(own, enemy, meta = {}) {
  const rows = [];
  troops.forEach((troop) => stats.forEach(([key, name]) => {
    const a = Number(own[troop][key] || 0);
    const d = Number(enemy[troop][key] || 0);
    rows.push(advRow(`${label(troop)} ${name}`, a, d, '%'));
  }));
  rows.push(advRow('Total Troops', own.troop_count, enemy.troop_count, ''));
  troops.forEach((troop) => rows.push(advRow(`${label(troop)} Formation`, Math.round(own.formation[troop] * 100), Math.round(enemy.formation[troop] * 100), '%')));
  rows.push({
    label: 'Hero Skill Impact',
    own: 'Recorded only',
    enemy: 'Recorded only',
    edge: meta.confidence_level === 'low' ? 'Pending verified skill mapping' : 'Not applied',
    edgeClass: 'tag-warn',
  });
  return rows;
}

function advRow(labelText, ownValue, enemyValue, suffix) {
  const diff = ownValue - enemyValue;
  return {
    label: labelText,
    own: `${format(round(ownValue))}${suffix}`,
    enemy: `${format(round(enemyValue))}${suffix}`,
    edge: diff > 0 ? `Own +${round(diff)}${suffix}` : diff < 0 ? `Enemy +${round(Math.abs(diff))}${suffix}` : 'Even',
    edgeClass: diff > 0 ? 'tag-good' : diff < 0 ? 'tag-bad' : 'tag-warn',
    rawDiff: diff,
  };
}

function topReasons(result, rows) {
  const sorted = rows.filter((r) => Number.isFinite(r.rawDiff)).sort((a, b) => Math.abs(b.rawDiff) - Math.abs(a.rawDiff)).slice(0, 5);
  const reasons = sorted.map((row) => `${row.label}: ${row.edge}.`);
  if (result.summary) reasons.unshift(escapeHtml(result.summary));
  return reasons.slice(0, 5);
}

function flipFightText(scenarios, basePct) {
  const winning = (scenarios || []).filter((s) => !s.error && Math.round((s.result.win_probability || 0) * 100) >= 50 && Math.round((s.result.win_probability || 0) * 100) > basePct);
  if (winning.length) {
    const best = winning.sort((a, b) => (b.result.win_probability || 0) - (a.result.win_probability || 0))[0];
    return `${best.name} moves the fight to ${Math.round((best.result.win_probability || 0) * 100)}%.`;
  }
  const best = (scenarios || []).filter((s) => !s.error).sort((a, b) => (b.result.win_probability || 0) - (a.result.win_probability || 0))[0];
  return best ? `Closest improvement is ${best.name} at ${Math.round((best.result.win_probability || 0) * 100)}%; stronger verified stats or a rally are needed.` : 'No scenario comparison was available.';
}

function summaryText(result, payload, scenarios, labelText, decision, confidence, reasons, flips) {
  const scenarioLines = (scenarios || []).map((s) => s.error ? `${s.name}: ${s.error}` : `${s.name}: ${Math.round((s.result.win_probability || 0) * 100)}%`).join('\n');
  return [
    `${labelText} - ${Math.round((result.win_probability || 0) * 100)}% win chance`,
    `Battle type: ${payload.battle_type}`,
    `Decision: ${decision}`,
    `Confidence: ${confidence}`,
    `Reasons: ${reasons.map((r) => r.replace(/<[^>]+>/g, '')).join(' ')}`,
    `What flips it: ${flips}`,
    `Scenarios:\n${scenarioLines}`,
  ].join('\n');
}

function copySummary() {
  navigator.clipboard.writeText(state.lastDecisionText || '').then(() => renderToast('Result summary copied.'));
}

function resultLabel(winPct) {
  if (winPct <= 20) return 'Heavy Loss';
  if (winPct <= 40) return 'Likely Loss';
  if (winPct < 50) return 'Close Loss';
  if (winPct < 60) return 'Close Win';
  if (winPct < 80) return 'Likely Win';
  return 'Heavy Win';
}

function decisionText(winPct, battleType) {
  if (battleType === 'reinforce') return winPct >= 50 ? 'Reinforce is reasonable, but verify hospital/risk limits.' : 'Do not reinforce this as-is.';
  if (winPct >= 80) return 'Safe attack by current model.';
  if (winPct >= 60) return 'Attack is favored but still risky.';
  if (winPct >= 50) return 'Adjust formation before committing.';
  if (winPct >= 41) return 'Use rally or improve stats before attacking.';
  return 'Do not solo attack.';
}

function confidenceLabel(meta) {
  if (meta.confidence_level === 'low') return 'Low - hero skills recorded but not applied';
  if (meta.confidence_level === 'high') return 'High';
  return 'Medium';
}

function heroesByType(type) {
  return normalizeHeroes(state.heroes).filter((hero) => heroType(hero) === type);
}

function heroType(hero = {}) {
  return hero.type || hero.specialty || '';
}

function normalizeHeroes(heroes) {
  return heroes.map((hero) => ({ ...hero, type: hero.type || hero.specialty }));
}

function selectedTroopBase(side, troop) {
  const data = window.WOS_TROOP_DATA;
  if (!data) return null;
  return data.getTroopStats(troop, Number($(`${side}-${troop}-tier`)?.value || 11), Number($(`${side}-${troop}-fc`)?.value || 10));
}

function updateTroopBaseNote(side, troop) {
  const target = $(`${side}-${troop}-base-note`);
  if (!target) return;
  const base = selectedTroopBase(side, troop);
  const skills = window.WOS_TROOP_DATA?.unlockedSkills(troop, Number($(`${side}-${troop}-fc`)?.value || 10)) || [];
  target.textContent = base
    ? `${base.familyName} FC${base.fcLevel}: ATK ${base.attack}, DEF ${base.defense}, HP ${base.health}, LETH ${base.lethality}. Skills: ${skills.map((s) => s.skillName).join(', ') || 'base skills'}`
    : 'Troop base stats unavailable.';
}

function formationTotal(side) {
  return number(`${side}-form-infantry`) + number(`${side}-form-lancer`) + number(`${side}-form-marksman`);
}

function jsonOptions(body) {
  return { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
}
function renderLoading(message) { $('prediction-output').innerHTML = `<div class="empty">${message}</div>`; }
function renderError(message) { $('prediction-output').innerHTML = `<div class="warning">${message}</div>`; }
function renderToast(message) { $('prediction-output').insertAdjacentHTML('afterbegin', `<div class="warning">${message}</div>`); }
function notice(id, message) { $(id).textContent = message; }
function format(value) { return Number(value || 0).toLocaleString(); }
function round(value) { return Math.round(Number(value || 0) * 10) / 10; }
function randomInt(min, max) { return Math.floor(Math.random() * (max - min + 1)) + min; }
function randomItem(items) { return items[Math.floor(Math.random() * items.length)]; }
function label(value) { return value.charAt(0).toUpperCase() + value.slice(1); }
function sideLabel(side) { return side === 'own' ? 'Own march' : 'Enemy march'; }
function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[ch]));
}

function init() {
  ['own', 'enemy'].forEach(buildStats);
  ['own', 'enemy'].forEach(buildHeroRows);
  ['own', 'enemy'].forEach(updateFormation);
  bindEvents();
  loadPresets();
  loadLogs();
  checkApi();
  updateValidation();
}

document.addEventListener('DOMContentLoaded', init);
