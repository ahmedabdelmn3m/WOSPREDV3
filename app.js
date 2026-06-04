// ─────────────────────────────────────────────
//  WOS Battle Predictor – App Logic
// ─────────────────────────────────────────────

// ── On load: fetch model accuracy ────────────
document.addEventListener('DOMContentLoaded', async () => {
  const badge = document.getElementById('accuracy-value');
  try {
    const res = await fetch(`${CONFIG.API_URL}/model-accuracy`);
    if (!res.ok) throw new Error();
    const data = await res.json();
    const pct = data.accuracy !== undefined
      ? `${(data.accuracy * 100).toFixed(1)}%`
      : 'ONLINE';
    badge.textContent = pct;
    badge.className = 'live';
    document.getElementById('status-dot').className = 'status-dot online';
  } catch {
    badge.textContent = 'OFFLINE';
    badge.className = 'error';
    document.getElementById('status-dot').className = 'status-dot offline';
  }
});

// ── Read one side's inputs ────────────────────
function readSide(s) {
  const g = id => parseFloat(document.getElementById(`${s}-${id}`).value) || 0;
  return {
    id: document.getElementById(`${s}-name`).value.trim() || `${s}-player`,
    stats: {
      attack:               g('attack'),
      defense:              g('defense'),
      health:               g('health'),
      lethality:            g('lethality'),
      attack_stats_sum:     g('attack-pct')   / 100,
      defense_stats_sum:    g('defense-pct')  / 100,
      health_stats_sum:     g('health-pct')   / 100,
      lethality_stats_sum:  g('lethality-pct') / 100,
    },
    hp: parseFloat(document.getElementById(`${s}-hp`).value) || 1000
  };
}

// ── Simulate (V1) ────────────────────────────
document.getElementById('simulate-btn').addEventListener('click', () =>
  runBattle('/simulate-battle', 'v1')
);

// ── Predict (V2) ────────────────────────────
document.getElementById('predict-btn').addEventListener('click', () =>
  runBattle('/predict-outcome', 'v2')
);

async function runBattle(endpoint, mode) {
  const btn = document.getElementById(mode === 'v1' ? 'simulate-btn' : 'predict-btn');
  setLoading(btn, true);
  hideResults();

  const payload = {
    attacker: readSide('atk'),
    defender: readSide('def')
  };

  try {
    const res = await fetch(`${CONFIG.API_URL}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    const data = await res.json();
    showResults(data, mode, payload);
  } catch (e) {
    showError(e.message);
  } finally {
    setLoading(btn, false);
  }
}

// ── Display results ───────────────────────────
function showResults(data, mode, payload) {
  const panel     = document.getElementById('results-panel');
  const title     = document.getElementById('result-title');
  const probWrap  = document.getElementById('prob-wrap');
  const probText  = document.getElementById('prob-text');
  const ring      = document.getElementById('prob-ring');
  const details   = document.getElementById('result-details');
  const logEl     = document.getElementById('battle-log');

  panel.classList.remove('hidden', 'attacker', 'defender', 'draw', 'error');

  let winner, prob, v1;
  if (mode === 'v2') {
    winner = data.predicted_winner || 'unknown';
    prob   = data.win_probability  || 0;
    v1     = data.v1_result        || {};
  } else {
    winner = data.winner || 'unknown';
    prob   = winner === 'attacker' ? 0.82 : winner === 'defender' ? 0.18 : 0.5;
    v1     = data;
  }

  panel.classList.add(winner);

  // Title
  const atkName = payload.attacker.id;
  const defName = payload.defender.id;
  const icons   = { attacker: '⚔️', defender: '🛡️', draw: '⚖️' };
  const labels  = {
    attacker: `${icons.attacker} ${atkName.toUpperCase()} WINS`,
    defender: `${icons.defender} ${defName.toUpperCase()} HOLDS`,
    draw: '⚖️ DRAW'
  };
  title.textContent = labels[winner] || '❓ UNKNOWN';

  // Probability ring
  const pct = Math.round(prob * 100);
  const circumference = 2 * Math.PI * 48;
  probText.textContent = `${pct}%`;
  ring.style.strokeDasharray  = `${circumference}`;
  ring.style.strokeDashoffset = `${circumference * (1 - prob)}`;
  probWrap.style.display = 'block';

  // Details table
  const rows = [
    ['Model',         mode === 'v2' ? 'V2 AI Calibrated' : 'V1 Deterministic'],
    ['Rounds Fought', v1.rounds_played ?? v1.history?.length ?? '—'],
    ['Win Probability', `${pct}%`],
    ['V1 Result',     v1.winner ?? winner],
  ];
  details.innerHTML = rows.map(([k, v]) =>
    `<div class="d-row"><span>${k}</span><span class="d-val">${v}</span></div>`
  ).join('');

  // Battle log
  const history = v1.history || [];
  if (history.length) {
    const entries = history.slice(0, 8).map((r, i) => {
      const rnd  = r.result?.round  ?? i + 1;
      const dmg  = r.result?.damage_dealt?.toFixed(4) ?? '—';
      const hp   = r.result?.defender_remaining_hp?.toFixed(1) ?? '—';
      const side = (r.side || '').toUpperCase();
      return `<div class="log-line">[R${rnd}] ${side} › DMG ${dmg} · HP left ${hp}</div>`;
    });
    logEl.innerHTML = entries.join('');
    logEl.style.display = 'block';
  } else {
    logEl.style.display = 'none';
  }

  panel.classList.remove('hidden');
  panel.style.animation = 'none';
  panel.offsetHeight;
  panel.style.animation = '';
}

function showError(msg) {
  const panel = document.getElementById('results-panel');
  panel.classList.remove('hidden', 'attacker', 'defender', 'draw');
  panel.classList.add('error');
  document.getElementById('result-title').textContent  = '⚠ CONNECTION FAILED';
  document.getElementById('prob-wrap').style.display   = 'none';
  document.getElementById('result-details').innerHTML  =
    `<div class="err-msg">Could not reach the API.<br>
     Check <code>config.js</code> has your Railway URL and CORS is enabled.<br>
     <small>${msg}</small></div>`;
  document.getElementById('battle-log').style.display  = 'none';
}

function hideResults() {
  const panel = document.getElementById('results-panel');
  panel.classList.add('hidden');
}

function setLoading(btn, on) {
  btn.disabled = on;
  btn.dataset.loading = on ? '1' : '';
}
