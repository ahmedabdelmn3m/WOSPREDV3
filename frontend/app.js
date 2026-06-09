'use strict';
/* ═══════════════════════════════════════════════════════════════
   WOSPREDV3  app.js  v2.0
   ═══════════════════════════════════════════════════════════════ */

// ── State ─────────────────────────────────────────────────────
const S = {
  mode: 'compare',   // 'compare' | 'reverse' | 'formation'
  atkTab: 'infantry',
  defTab: 'infantry',
};

// ── API ───────────────────────────────────────────────────────
async function api(path, body) {
  const res = await fetch(window.WOS_API_URL + path, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return data;
}

async function apiGet(path) {
  const res = await fetch(window.WOS_API_URL + path);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function checkApi() {
  try {
    await apiGet('/');
    setPill(true);
  } catch {
    setPill(false);
  }
}

function setPill(online) {
  const p = id('api-pill');
  p.textContent = online ? '⬤ Online' : '⬤ Offline';
  p.className = 'api-pill' + (online ? ' online' : '');
}

// ── DOM helpers ───────────────────────────────────────────────
const id   = (s) => document.getElementById(s);
const val  = (s) => parseFloat(id(s)?.value) || 0;
const sval = (s) => (id(s)?.value || '').trim();
const setV = (s, v) => { if (id(s)) id(s).value = v; };

function fmt(n) {
  return Math.round(n || 0).toLocaleString();
}
function pct(p) {
  return Math.round((p || 0) * 100) + '%';
}

// ── Read / write army from form ───────────────────────────────
function readArmy(side) {
  const s = side === 'atk' ? 'atk' : 'def';
  const name = side === 'atk' ? sval('attacker-name') : sval('def-name');
  return {
    name,
    infantry:  { attack_pct: val(`${s}-inf-atk`), defense_pct: val(`${s}-inf-def`), health_pct: val(`${s}-inf-hp`),  lethality_pct: val(`${s}-inf-lth`) },
    lancer:    { attack_pct: val(`${s}-lan-atk`), defense_pct: val(`${s}-lan-def`), health_pct: val(`${s}-lan-hp`),  lethality_pct: val(`${s}-lan-lth`) },
    marksman:  { attack_pct: val(`${s}-mrk-atk`), defense_pct: val(`${s}-mrk-def`), health_pct: val(`${s}-mrk-hp`),  lethality_pct: val(`${s}-mrk-lth`) },
    formation: {
      infantry:  val(`${s}-form-inf`) / 100,
      lancer:    val(`${s}-form-lan`) / 100,
      marksman:  val(`${s}-form-mrk`) / 100,
    },
    troop_count: parseInt(id(`${s === 'atk' ? 'atk' : 'def'}-troops`)?.value || '500000'),
    heroes: readHeroes(side),
  };
}

function readHeroes(side) {
  const heroes = [];
  for (let i = 0; i < 3; i++) {
    const name = id(`${side}-hero-${i}`)?.value;
    if (name) {
      heroes.push({
        name,
        stars:  val(`${side}-star-${i}`) || 5,
        widget: val(`${side}-wid-${i}`)  || 5,
      });
    }
  }
  return heroes;
}

function writeArmy(side, d) {
  const s = side === 'atk' ? 'atk' : 'def';
  const nameId = side === 'atk' ? 'attacker-name' : 'def-name';
  setV(nameId, d.name || side);

  const t = (obj, prefix) => {
    setV(`${s}-${prefix}-atk`, obj.attack_pct    || 0);
    setV(`${s}-${prefix}-def`, obj.defense_pct   || 0);
    setV(`${s}-${prefix}-hp`,  obj.health_pct    || 0);
    setV(`${s}-${prefix}-lth`, obj.lethality_pct || 0);
  };
  t(d.infantry  || {}, 'inf');
  t(d.lancer    || {}, 'lan');
  t(d.marksman  || {}, 'mrk');

  const f = d.formation || {};
  setV(`${s}-form-inf`, Math.round((f.infantry  || 0.5)  * 100));
  setV(`${s}-form-lan`, Math.round((f.lancer    || 0.2)  * 100));
  setV(`${s}-form-mrk`, Math.round((f.marksman  || 0.3)  * 100));

  const troopsId = s === 'atk' ? 'atk-troops' : 'def-troops';
  setV(troopsId, d.troop_count || 500000);
  validateForm(side);
}

// ── Formation validation ──────────────────────────────────────
function validateForm(side) {
  const s = side === 'atk' ? 'atk' : 'def';
  const total = val(`${s}-form-inf`) + val(`${s}-form-lan`) + val(`${s}-form-mrk`);
  const el    = id(`${s}-form-total`);
  if (!el) return true;
  el.textContent = `Total: ${Math.round(total)}%`;
  const ok = Math.abs(total - 100) < 1;
  el.className = 'form-total ' + (ok ? 'valid' : 'invalid');
  return ok;
}

// ── Preset management (localStorage) ─────────────────────────
const PKEY = 'wos_presets_v3';

function getPresets()         { try { return JSON.parse(localStorage.getItem(PKEY) || '{}'); } catch { return {}; } }
function storePresets(p)      { localStorage.setItem(PKEY, JSON.stringify(p)); }
function savePreset(n, data)  { const p = getPresets(); p[n] = data; storePresets(p); refreshDrop(); }
function deletePreset(n)      { const p = getPresets(); delete p[n]; storePresets(p); refreshDrop(); }
function loadPreset(n)        { return getPresets()[n] || null; }

function refreshDrop() {
  const sel  = id('preset-select');
  const keys = Object.keys(getPresets());
  sel.innerHTML = '<option value="">── Saved Presets ──</option>' +
    keys.map(k => `<option value="${k}">${k}</option>`).join('');
}

function handleSave() {
  const n = sval('preset-name');
  if (!n) { showErr('Enter a preset name'); return; }
  savePreset(n, readArmy('atk'));
  toast(`✓ Preset "${n}" saved`);
}

function handleLoad() {
  const n = id('preset-select').value;
  if (!n) { showErr('Select a preset to load'); return; }
  const d = loadPreset(n);
  if (!d) { showErr('Preset not found'); return; }
  writeArmy('atk', d);
  toast(`✓ "${n}" loaded`);
}

function handleDelete() {
  const n = id('preset-select').value;
  if (!n) { showErr('Select a preset to delete'); return; }
  deletePreset(n);
  toast(`✓ "${n}" deleted`);
}

// ── Tab switch ────────────────────────────────────────────────
function switchTab(side, troop) {
  if (side === 'atk') S.atkTab = troop;
  else S.defTab = troop;

  const prefix = side === 'atk' ? 'atk' : 'def';
  document.querySelectorAll(`.${prefix}-tab`).forEach(b => b.classList.remove('active'));
  id(`${prefix}-tab-${troop}`)?.classList.add('active');
  document.querySelectorAll(`.${prefix}-panel`).forEach(p => p.style.display = 'none');
  const panel = id(`${prefix}-panel-${troop}`);
  if (panel) panel.style.display = 'block';
}

// ── Mode switch ───────────────────────────────────────────────
function switchMode(mode) {
  S.mode = mode;
  document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
  id(`mode-${mode}`)?.classList.add('active');
  id('reverse-options').style.display = mode === 'reverse' ? 'flex' : 'none';
  id('action-btn').textContent = { compare:'⚔️ SIMULATE BATTLE', reverse:'🎯 FIND PATH TO VICTORY', formation:'📊 OPTIMISE FORMATION' }[mode];
  clearResults();
  clearErr();
}

// ── Main action ───────────────────────────────────────────────
async function runAction() {
  if (!validateForm('atk'))  { showErr('Your formation must sum to 100 %'); return; }
  if (!validateForm('def'))  { showErr('Enemy formation must sum to 100 %'); return; }

  const atk = readArmy('atk');
  const def = readArmy('def');
  setLoading(true);
  clearErr();
  clearResults();

  try {
    if (S.mode === 'compare') {
      const r = await api('/predict-outcome', { attacker: atk, defender: def, max_rounds: 20 });
      renderCompare(r);

    } else if (S.mode === 'reverse') {
      const target = parseFloat(id('reverse-target').value || '0.75');
      const r = await api('/reverse-optimize', {
        own_army: atk, enemy_army: def,
        target_win_probability: target, max_rounds: 20,
      });
      renderReverse(r);

    } else {
      const r = await api('/formation/optimize', { own_army: atk, enemy_army: def, max_rounds: 20 });
      renderFormation(r);
    }
  } catch (e) {
    showErr(e.message);
  } finally {
    setLoading(false);
  }
}

// ── Render: Compare ───────────────────────────────────────────
function renderCompare(data) {
  const v1      = data;
  const winProb = data.win_probability ?? (v1.winner === 'attacker' ? 0.8 : 0.2);
  const winPct  = Math.round(winProb * 100);
  const isWin   = v1.winner === 'attacker';
  const atk     = v1.attacker;
  const dfn     = v1.defender;

  let html = `
    <div class="result-header ${isWin ? 'win' : 'loss'}">
      ${isWin ? '⚔️ VICTORY' : '💀 DEFEAT'}
    </div>

    <div class="win-prob-block">
      <div class="wp-label">WIN PROBABILITY</div>
      <div class="wp-bar"><div class="wp-fill ${isWin ? 'win' : 'loss'}" style="width:${winPct}%"></div></div>
      <div class="wp-value">${winPct}%</div>
    </div>

    <div class="stat-rows">
      <div class="sr"><span class="sr-label">ROUNDS</span><span class="sr-val">${v1.rounds_played}</span></div>
      <div class="sr"><span class="sr-label">${atk.name} SURVIVORS</span><span class="sr-val ${isWin ? 'v-win' : 'v-loss'}">${fmt(atk.survivors)} / ${fmt(atk.initial_troops)}</span></div>
      <div class="sr"><span class="sr-label">${dfn.name} SURVIVORS</span><span class="sr-val ${isWin ? 'v-loss' : 'v-win'}">${fmt(dfn.survivors)} / ${fmt(dfn.initial_troops)}</span></div>
      <div class="sr"><span class="sr-label">YOUR LOSS RATE</span><span class="sr-val ${atk.loss_rate > 0.5 ? 'v-loss' : 'v-warn'}">${Math.round(atk.loss_rate * 100)}%</span></div>
      <div class="sr"><span class="sr-label">ENEMY LOSS RATE</span><span class="sr-val ${dfn.loss_rate > 0.5 ? 'v-win' : 'v-warn'}">${Math.round(dfn.loss_rate * 100)}%</span></div>
      <div class="sr"><span class="sr-label">ARMY DAMAGE (you)</span><span class="sr-val">${atk.army_damage?.toFixed(5)}</span></div>
      <div class="sr"><span class="sr-label">ARMY DAMAGE (enemy)</span><span class="sr-val">${dfn.army_damage?.toFixed(5)}</span></div>
    </div>`;

  if (data.strength_analysis) html += renderStrength(data.strength_analysis);

  if (data.bottleneck && data.bottleneck.troop_type) {
    const bt = data.bottleneck;
    html += `
    <div class="bottleneck-block">
      <div class="bt-title">⚠ BOTTLENECK</div>
      <div class="bt-text">${bt.recommendation || `Improve ${bt.troop_type} ${bt.stat}`}</div>
    </div>`;
  }

  if (data.summary) html += `<div class="cal-note">${data.summary}</div>`;

  if (v1.history?.length) {
    html += `<details class="round-history">
      <summary>ROUND HISTORY (${v1.rounds_played} rounds) ▾</summary>
      <div class="round-list">
        ${v1.history.map(r => `
          <div class="round-item">
            <strong>Round ${r.round}</strong> —
            Your casualties: <strong>${fmt(r.attacker.casualties)}</strong> |
            Enemy casualties: <strong>${fmt(r.defender.casualties)}</strong> |
            Your troops: ${fmt(r.attacker.remaining)} |
            Enemy troops: ${fmt(r.defender.remaining)}
          </div>`).join('')}
      </div>
    </details>`;
  }

  id('results-panel').innerHTML = html;
}

function renderStrength(sa) {
  const icon = (s) => ({ DOMINANT:'🟢', ADVANTAGE:'🟩', EVEN:'🟡', DISADVANTAGE:'🟠', CRITICAL:'🔴' }[s] || '⚪');
  const cls  = (s) => 's-' + (s || 'even').toLowerCase();
  return `
    <div class="strength-block">
      <div class="strength-title">TROOP MATCHUP</div>
      ${['infantry','lancer','marksman'].map(t => {
        const d = sa[t]; if (!d) return '';
        return `<div class="troop-match">
          <span class="tm-name">${t}</span>
          <span class="tm-status ${cls(d.status)}">${icon(d.status)} ${d.status}</span>
          <span class="tm-pen">Pen ${d.atk_penetration?.toFixed(2)} vs ${d.def_penetration?.toFixed(2)}</span>
        </div>`;
      }).join('')}
    </div>`;
}

// ── Render: Reverse Optimize ──────────────────────────────────
function renderReverse(data) {
  let html = '';

  if (data.already_meets_target) {
    html = `
      <div class="result-header win">✅ TARGET ALREADY MET</div>
      <div class="stat-rows">
        <div class="sr"><span class="sr-label">CURRENT WIN PROBABILITY</span>
          <span class="sr-val v-win">${pct(data.current_win_probability)}</span></div>
      </div>`;
  } else {
    const recs = data.top_recommendations || [];
    html = `
      <div class="result-header loss">🎯 HOW TO WIN</div>
      <div class="stat-rows">
        <div class="sr"><span class="sr-label">CURRENT WIN PROBABILITY</span>
          <span class="sr-val v-loss">${pct(data.current_win_probability)}</span></div>
        <div class="sr"><span class="sr-label">TARGET</span>
          <span class="sr-val">${pct(data.target_win_probability)}</span></div>
      </div>
      <div class="recs-block">
        <div class="recs-title">TOP IMPROVEMENTS (best ROI first)</div>
        ${recs.map((r, i) => `
          <div class="rec-card">
            <span class="rc-rank">#${i+1}</span>
            <span class="rc-troop">${r.troop_type?.toUpperCase()}</span>
            <span class="rc-stat">${r.stat}</span>
            <span class="rc-delta">+${r.needed_increase_pct}%</span>
            <span class="rc-impact i-${(r.impact_label||'low').toLowerCase()}">${r.impact_label}</span>
          </div>`).join('')}
      </div>`;

    if (data.win_paths && Object.keys(data.win_paths).length) {
      html += `<div class="paths-block"><div class="paths-title">WIN PATHS</div>`;
      for (const [key, steps] of Object.entries(data.win_paths)) {
        const label = key.replace('pct', '') + '% WIN';
        if (steps?.already_met) {
          html += `<div class="path-card"><div class="path-label">${label}</div><div class="path-step" style="color:var(--win)">✓ Already met</div></div>`;
        } else if (Array.isArray(steps)) {
          html += `<div class="path-card"><div class="path-label">${label}</div>
            ${steps.map(s => `<div class="path-step">${s.troop_type?.toUpperCase()} ${s.stat} +${s.increase_pct}%</div>`).join('')}
          </div>`;
        }
      }
      html += '</div>';
    }
  }

  id('results-panel').innerHTML = html;
}

// ── Render: Formation Optimize ────────────────────────────────
function renderFormation(data) {
  const best = data.best_formation;
  const all  = data.all_results || [];
  const wins = data.winning_count || 0;

  let html = `
    <div class="result-header ${wins > 0 ? 'win' : 'loss'}">
      📊 FORMATION ANALYSIS — ${wins} / ${all.length} WIN
    </div>`;

  if (best) {
    html += `
      <div class="best-form-card">
        <div class="bf-label">BEST FORMATION</div>
        <div class="form-badges">
          <span class="f-badge f-inf">${best.infantry_pct}% INF</span>
          <span class="f-badge f-lan">${best.lancer_pct}% LAN</span>
          <span class="f-badge f-mrk">${best.marksman_pct}% MRK</span>
        </div>
        <div class="wp-bar"><div class="wp-fill win" style="width:${Math.round((data.best_win_probability||0)*100)}%"></div></div>
        <div style="text-align:center;font-weight:800;color:var(--win);margin-top:4px">
          ${Math.round((data.best_win_probability||0)*100)}%
        </div>
      </div>`;
  }

  html += '<div style="font-size:10px;color:var(--txt-dim);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px">ALL FORMATIONS RANKED</div>';
  html += all.slice(0, 10).map((r, i) => `
    <div class="form-row">
      <span class="fr-rank">#${i+1}</span>
      <span class="fr-form">${r.label}</span>
      <span class="fr-out ${r.winner === 'attacker' ? 'win' : 'loss'}">${r.winner === 'attacker' ? '✓ WIN' : '✗ LOSS'}</span>
      <span class="fr-prob">${Math.round((r.win_probability||0)*100)}%</span>
      <span class="fr-surv">${fmt(r.attacker_survivors)} left</span>
    </div>`).join('');

  id('results-panel').innerHTML = html;
}

// ── UI helpers ────────────────────────────────────────────────
function showErr(msg)  { const e = id('error-bar'); e.textContent = msg; e.style.display = 'block'; }
function clearErr()    { const e = id('error-bar'); e.textContent = '';  e.style.display = 'none'; }
function clearResults(){ id('results-panel').innerHTML = `<div class="placeholder"><div class="ph-icon">⚔️</div><div class="ph-title">Enter stats &amp; run</div><div class="ph-sub">Compare · How to Win · Best Formation</div></div>`; }
function setLoading(b) {
  const btn = id('action-btn');
  btn.disabled = b;
  if (b) btn.textContent = '⏳ CALCULATING…';
  else   switchMode(S.mode);   // restores label
}
function toast(msg) {
  const t = id('toast'); t.textContent = msg; t.style.display = 'block';
  setTimeout(() => t.style.display = 'none', 2500);
}

// ── Settings modal ────────────────────────────────────────────
function openSettings() {
  id('api-url-input').value = window.WOS_API_URL;
  id('settings-modal').style.display = 'flex';
}
function closeSettings() {
  id('settings-modal').style.display = 'none';
}
function saveApiUrl() {
  const url = sval('api-url-input');
  if (!url) return;
  localStorage.setItem('wos_api_url', url);
  window.WOS_API_URL = url;
  closeSettings();
  toast('✓ API URL saved — reconnecting…');
  setTimeout(checkApi, 300);
}

// ── Wire events ───────────────────────────────────────────────
function init() {
  // Mode buttons
  document.querySelectorAll('.mode-btn').forEach(b => {
    b.addEventListener('click', () => switchMode(b.dataset.mode));
  });

  // Action button
  id('action-btn').addEventListener('click', runAction);

  // Presets
  id('btn-save-preset').addEventListener('click', handleSave);
  id('btn-load-preset').addEventListener('click', handleLoad);
  id('btn-delete-preset').addEventListener('click', handleDelete);

  // Tabs — attacker
  ['infantry','lancer','marksman'].forEach(t => {
    id(`atk-tab-${t}`)?.addEventListener('click', () => switchTab('atk', t));
    id(`def-tab-${t}`)?.addEventListener('click', () => switchTab('def', t));
  });

  // Formation validation
  ['atk','def'].forEach(s => {
    ['inf','lan','mrk'].forEach(t => {
      id(`${s}-form-${t}`)?.addEventListener('input', () => validateForm(s === 'atk' ? 'atk' : 'def'));
    });
  });

  // Drag & Drop
  ['atk','def'].forEach(side => {
    const area = id(side + '-upload-area');
    if (area) {
      area.addEventListener('dragover', e => { e.preventDefault(); area.classList.add('dragover'); });
      area.addEventListener('dragleave', () => area.classList.remove('dragover'));
      area.addEventListener('drop', e => handleDrop(e, side));
    }
  });

  // Settings
  id('btn-settings').addEventListener('click', openSettings);
  id('btn-close-settings').addEventListener('click', closeSettings);
  id('btn-save-api-url').addEventListener('click', saveApiUrl);
  id('settings-modal').addEventListener('click', e => { if (e.target === id('settings-modal')) closeSettings(); });

  // Init UI state
  refreshDrop();
  switchMode('compare');
  switchTab('atk', 'infantry');
  switchTab('def', 'infantry');
  validateForm('atk');
  validateForm('def');

  // Check API
  checkApi();
  setInterval(checkApi, 30000);
}

/* ── Scout image upload ───────────────────────────────────── */
function handleFile(input, side) {
  const file = input.files[0];
  if (!file) return;
  showScout(side, URL.createObjectURL(file));
}

function handleDrop(e, side) {
  e.preventDefault();
  id(side + '-upload-area').classList.remove('dragover');
  const file = e.dataTransfer.files[0];
  if (file && file.type.startsWith('image/')) {
    showScout(side, URL.createObjectURL(file));
  }
}

function showScout(side, url) {
  const img  = id(side + '-preview');
  const area = id(side + '-upload-area');
  if (!img || !area) return;
  img.src = url;
  img.style.display = 'block';
  area.querySelector('.upload-icon').textContent = '🔄';
  area.querySelector('.upload-label').innerHTML  =
    'Replace image · <small>Drag &amp; drop or click</small>';
}

document.addEventListener('DOMContentLoaded', init);
