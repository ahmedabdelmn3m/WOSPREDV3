'use strict';

const heroDb = window.WOS_HERO_DATABASE || [];
const rules = window.WOS_HERO_ADVISOR_RULES;
const troopTypes = ['infantry', 'lancer', 'marksman'];
let comparisonCount = 0;

const presets = {
  1: {
    current: { infantry: 'flint', lancer: 'mia', marksman: 'alonso' },
    compare: ['hector', 'reina', 'gwen'],
  },
  2: {
    current: { infantry: 'jeronimo', lancer: 'mia', marksman: 'alonso' },
    compare: ['hector', 'wayne', 'gwen'],
  },
  3: {
    current: { infantry: 'hector', lancer: 'mia', marksman: 'gwen' },
    compare: ['logan', 'reina', 'lynn'],
  },
  4: {
    current: { infantry: 'flint', lancer: 'jessie', marksman: 'bahiti' },
    compare: ['jeronimo', 'mia', 'alonso'],
  },
};

const $ = (id) => document.getElementById(id);

function init() {
  buildCurrentHeroCards();
  addComparisonRow('infantry');
  addComparisonRow('lancer');
  addComparisonRow('marksman');
  bindEvents();
  applyPreset(1);
}

function buildCurrentHeroCards() {
  $('current-heroes').innerHTML = troopTypes.map((type) => `
    <section class="advisor-card" data-current-slot="${type}">
      <h3>${label(type)}</h3>
      <div class="advisor-fields">
        <label>Hero
          <select id="current-${type}-hero">
            ${heroOptions(type)}
          </select>
        </label>
        ${investmentFields(`current-${type}`)}
      </div>
      <div id="current-${type}-note" class="hint"></div>
    </section>
  `).join('');
}

function addComparisonRow(slotType = '') {
  comparisonCount += 1;
  const id = `compare-${comparisonCount}`;
  $('comparison-heroes').insertAdjacentHTML('beforeend', `
    <section class="comparison-row" data-comparison-row="${id}">
      <h3>Comparison Hero</h3>
      <div class="comparison-fields">
        <label>Hero
          <select id="${id}-hero">
            ${heroOptions('all')}
          </select>
        </label>
        <label>Target Slot
          <select id="${id}-slot">
            ${troopTypes.map((type) => `<option value="${type}" ${type === slotType ? 'selected' : ''}>${label(type)}</option>`).join('')}
          </select>
        </label>
        ${investmentFields(id)}
        <button type="button" data-remove-comparison="${id}">Remove</button>
      </div>
      <div id="${id}-note" class="hint"></div>
    </section>
  `);
  bindRowEvents(id);
}

function investmentFields(prefix) {
  return `
    <label>Stars
      <select id="${prefix}-stars">${numberOptions(0, 5, 5)}</select>
    </label>
    <label>Widget
      <select id="${prefix}-widget">
        <option value="0">None / 0</option>
        ${numberOptions(1, 10, 5)}
      </select>
    </label>
    <label>Expedition Skill
      <select id="${prefix}-skill">
        <option value="unknown">Unknown</option>
        ${numberOptions(1, 5, 5)}
      </select>
    </label>
  `;
}

function numberOptions(min, max, selected) {
  return Array.from({ length: max - min + 1 }, (_, index) => {
    const value = min + index;
    return `<option value="${value}" ${value === selected ? 'selected' : ''}>${value}</option>`;
  }).join('');
}

function heroOptions(type) {
  const heroes = type === 'all' ? heroDb : heroDb.filter((hero) => hero.troopType === type);
  return [`<option value="">Select hero</option>`].concat(
    heroes
      .slice()
      .sort((a, b) => (a.troopType || '').localeCompare(b.troopType || '') || (a.generation || 0) - (b.generation || 0) || a.name.localeCompare(b.name))
      .map((hero) => `<option value="${hero.id}">${hero.name} - ${label(hero.troopType)} - Gen ${hero.generation || '?'}</option>`)
  ).join('');
}

function bindEvents() {
  $('add-comparison').addEventListener('click', () => addComparisonRow());
  $('analyze-setup').addEventListener('click', analyze);
  document.querySelectorAll('[data-preset]').forEach((button) => {
    button.addEventListener('click', () => applyPreset(button.dataset.preset));
  });
  troopTypes.forEach((type) => {
    [`current-${type}-hero`, `current-${type}-stars`, `current-${type}-widget`, `current-${type}-skill`].forEach((id) => {
      $(id).addEventListener('change', updateNotes);
    });
  });
}

function bindRowEvents(id) {
  [`${id}-hero`, `${id}-slot`, `${id}-stars`, `${id}-widget`, `${id}-skill`].forEach((fieldId) => {
    $(fieldId).addEventListener('change', updateNotes);
  });
  document.querySelector(`[data-remove-comparison="${id}"]`).addEventListener('click', () => {
    document.querySelector(`[data-comparison-row="${id}"]`).remove();
    updateNotes();
  });
}

function applyPreset(presetId) {
  const preset = presets[presetId];
  if (!preset) return;
  troopTypes.forEach((type) => {
    $(`current-${type}-hero`).value = preset.current[type] || '';
    $(`current-${type}-stars`).value = 5;
    $(`current-${type}-widget`).value = 5;
    $(`current-${type}-skill`).value = '5';
  });
  $('comparison-heroes').innerHTML = '';
  comparisonCount = 0;
  preset.compare.forEach((heroId) => {
    const hero = findHero(heroId);
    addComparisonRow(hero?.troopType || '');
    const id = `compare-${comparisonCount}`;
    $(`${id}-hero`).value = heroId;
    $(`${id}-slot`).value = hero?.troopType || 'infantry';
    $(`${id}-stars`).value = 5;
    $(`${id}-widget`).value = 5;
    $(`${id}-skill`).value = '5';
  });
  updateNotes();
  $('advisor-output').className = 'empty';
  $('advisor-output').textContent = 'Preset loaded. Click Analyze Rally Setup.';
}

function readCurrentSelections() {
  return troopTypes.map((type) => selectionFromPrefix(`current-${type}`, type, 'current')).filter(Boolean);
}

function readComparisonSelections() {
  return Array.from(document.querySelectorAll('[data-comparison-row]')).map((row) => {
    const id = row.dataset.comparisonRow;
    return selectionFromPrefix(id, $(`${id}-slot`).value, 'comparison');
  }).filter(Boolean);
}

function selectionFromPrefix(prefix, slotType, origin) {
  const hero = findHero($(`${prefix}-hero`)?.value);
  if (!hero) return null;
  return {
    hero,
    slotType,
    origin,
    stars: $(`${prefix}-stars`)?.value ?? 0,
    widgetLevel: $(`${prefix}-widget`)?.value ?? 0,
    skillLevel: $(`${prefix}-skill`)?.value ?? 'unknown',
  };
}

function analyze() {
  const current = readCurrentSelections();
  const comparisons = readComparisonSelections();
  if (current.length !== 3) {
    renderError('Select one current Infantry, Lancer, and Marksman hero before analyzing.');
    return;
  }
  const result = rules.analyzeRallySetup(current, comparisons);
  renderResult(result, current, comparisons);
}

function renderResult(result, current, comparisons) {
  const recommendedNames = result.recommended.map((item) => item.hero.name).join(' / ');
  $('advisor-output').className = 'result-card';
  $('advisor-output').innerHTML = `
    <div class="decision-card ${result.recommendedScore >= result.currentScore ? 'win' : 'loss'}">
      <div class="decision-title">
        <strong>Recommended Rally Leader Setup</strong>
        <span>${escapeHtml(recommendedNames || 'n/a')}</span>
      </div>
      <div class="metric-grid">
        <div class="metric"><span>Current Setup</span><strong>${result.currentScore}</strong></div>
        <div class="metric"><span>Recommended Setup</span><strong>${result.recommendedScore}</strong></div>
        <div class="metric"><span>Confidence</span><strong>${result.confidence}</strong></div>
        <div class="metric"><span>Mode</span><strong>PvP Rally Leader</strong></div>
      </div>
      <h3>Replacements</h3>
      ${result.replacements.length ? list(result.replacements.map((item) => `<strong>Replace ${item.from.hero.name} with ${item.to.hero.name}</strong><div class="hint">${item.reason}</div>`)) : list(['No same-type comparison hero clearly beats the current slot.'])}
      <h3>Keep</h3>
      ${result.keep.length ? list(result.keep.map((item) => `<strong>${item.hero.hero?.name || item.hero.name}</strong><div class="hint">${item.reason}</div>`)) : list(['No keep decisions.'])}
      <h3>Scoring Breakdown</h3>
      ${scoreTable(result.recommended)}
      <h3>Warnings</h3>
      ${list(result.warnings.map(escapeHtml))}
      <h3>Source Transparency</h3>
      ${sourceTransparency([...current, ...comparisons])}
    </div>
  `;
}

function scoreTable(items) {
  return `
    <div class="table-wrap"><table class="result-table">
      <thead><tr><th>Hero</th><th>Slot</th><th>Total</th><th>Generation</th><th>Stars</th><th>Widget</th><th>Skill</th><th>Role</th><th>Data</th></tr></thead>
      <tbody>${items.map((item) => {
        const score = item.score || rules.scoreHero(item);
        return `<tr>
          <td>${escapeHtml(item.hero.name)}</td>
          <td>${label(item.slotType)}</td>
          <td><span class="score-pill">${score.total}</span></td>
          <td>${score.parts.generationScore}</td>
          <td>${score.parts.starScore}</td>
          <td>${score.parts.widgetScore}</td>
          <td>${score.parts.expeditionSkillScore}</td>
          <td>${score.parts.rallyLeaderRoleScore}</td>
          <td>${score.parts.dataConfidenceScore}</td>
        </tr>`;
      }).join('')}</tbody>
    </table></div>
  `;
}

function sourceTransparency(selections) {
  const uniqueHeroes = Array.from(new Map(selections.map((item) => [item.hero.id, item.hero])).values());
  return `<div class="source-list">${uniqueHeroes.map((hero) => `
    <div class="source-item">
      <strong>${escapeHtml(hero.name)} - ${label(hero.troopType)} - Gen ${hero.generation || '?'}</strong>
      <span>Data source: ${escapeHtml(hero.dataConfidence)} | Last checked: ${escapeHtml(hero.lastCheckedDate || 'n/a')}</span>
      <a href="${escapeHtml(hero.sourceUrl || '#')}" target="_blank" rel="noreferrer">${escapeHtml(hero.sourceName || 'Source')}</a>
      <span class="hint">${escapeHtml((hero.calibrationNotes || []).join(' ') || 'No calibration reports yet.')}</span>
    </div>
  `).join('')}</div>`;
}

function updateNotes() {
  troopTypes.forEach((type) => {
    const selection = selectionFromPrefix(`current-${type}`, type, 'current');
    $(`current-${type}-note`).textContent = selection ? noteFor(selection) : '';
  });
  document.querySelectorAll('[data-comparison-row]').forEach((row) => {
    const id = row.dataset.comparisonRow;
    const selection = selectionFromPrefix(id, $(`${id}-slot`).value, 'comparison');
    $(`${id}-note`).textContent = selection ? noteFor(selection) : '';
  });
}

function noteFor(selection) {
  const score = rules.scoreHero(selection).total;
  const crossType = selection.hero.troopType !== selection.slotType ? ` Cross-type warning: ${selection.hero.name} is ${selection.hero.troopType}.` : '';
  return `Score ${score}. Source confidence: ${selection.hero.dataConfidence}.${crossType}`;
}

function list(items) {
  return `<div class="list">${items.map((item) => `<div class="list-item">${item}</div>`).join('')}</div>`;
}

function renderError(message) {
  $('advisor-output').className = 'warning';
  $('advisor-output').textContent = message;
}

function findHero(id) {
  return heroDb.find((hero) => hero.id === id);
}

function label(value) {
  return String(value || '').charAt(0).toUpperCase() + String(value || '').slice(1);
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[ch]));
}

document.addEventListener('DOMContentLoaded', init);
