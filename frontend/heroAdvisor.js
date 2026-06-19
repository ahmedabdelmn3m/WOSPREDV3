'use strict';

const heroDb = window.WOS_HERO_DATABASE || [];
const rules = window.WOS_HERO_ADVISOR_RULES;
const troopTypes = ['infantry', 'lancer', 'marksman'];
let comparisonCount = 0;

const presets = {
  1: { current: { infantry: 'flint', lancer: 'mia', marksman: 'alonso' }, compare: ['hector', 'norah', 'gwen'] },
  2: { current: { infantry: 'jeronimo', lancer: 'mia', marksman: 'alonso' }, compare: ['hector', 'norah', 'gwen'] },
  3: { current: { infantry: 'hector', lancer: 'mia', marksman: 'gwen' }, compare: ['logan', 'norah', 'lynn'] },
  4: { current: { infantry: 'flint', lancer: 'molly', marksman: 'bahiti' }, compare: ['jeronimo', 'mia', 'alonso'] },
};

const $ = (id) => document.getElementById(id);

function init() {
  buildGoalSelector();
  buildCurrentHeroCards();
  bindEvents();
  applyPreset(1);
}

function buildGoalSelector() {
  $('rally-goal').innerHTML = Object.entries(rules.goals).map(([value, label]) => `<option value="${value}">${label}</option>`).join('');
}

function buildCurrentHeroCards() {
  $('current-heroes').innerHTML = troopTypes.map((type) => `
    <section class="advisor-card" data-current-slot="${type}">
      <h3>${label(type)}</h3>
      <div class="advisor-fields">
        <label>Hero<select id="current-${type}-hero">${heroOptions(type)}</select></label>
        ${investmentFields(`current-${type}`)}
      </div>
      <div class="action-row mini-actions">
        <button type="button" data-max-skills="current-${type}">Use max active skills</button>
        <button type="button" data-unknown-skills="current-${type}">Unknown skill levels</button>
      </div>
      <div id="current-${type}-note" class="hint"></div>
    </section>
  `).join('');
}

function addComparisonRow(slotType = 'infantry') {
  comparisonCount += 1;
  const id = `compare-${comparisonCount}`;
  $('comparison-heroes').insertAdjacentHTML('beforeend', `
    <section class="comparison-row" data-comparison-row="${id}">
      <h3>${label(slotType)} Comparison</h3>
      <div class="comparison-fields">
        <label>Hero<select id="${id}-hero">${heroOptions(slotType)}</select></label>
        <label>Target Slot<select id="${id}-slot">${troopTypes.map((type) => `<option value="${type}" ${type === slotType ? 'selected' : ''}>${label(type)}</option>`).join('')}</select></label>
        ${investmentFields(id)}
        <button type="button" data-remove-comparison="${id}">Remove</button>
      </div>
      <div class="action-row mini-actions">
        <button type="button" data-max-skills="${id}">Use max active skills</button>
        <button type="button" data-unknown-skills="${id}">Unknown skill levels</button>
      </div>
      <div id="${id}-note" class="hint"></div>
    </section>
  `);
  bindRowEvents(id);
}

function investmentFields(prefix) {
  return `
    <label>Stars<select id="${prefix}-stars">${numberOptions(0, 5, 5)}</select></label>
    <label>Widget<select id="${prefix}-widget"><option value="0">None / 0</option>${numberOptions(1, 10, 5)}</select></label>
    <label>Skill 1<select id="${prefix}-skill1"><option value="unknown">Unknown</option>${numberOptions(1, 5, 5)}</select></label>
    <label>Skill 2<select id="${prefix}-skill2"><option value="unknown">Unknown</option>${numberOptions(1, 5, 5)}</select></label>
    <label>Skill 3<select id="${prefix}-skill3"><option value="unknown">Unknown</option>${numberOptions(1, 5, 5)}</select></label>
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
  return ['<option value="">Select hero</option>'].concat(
    heroes.map((hero) => `<option value="${hero.id}">${hero.name} - Gen ${hero.generation || '?'}${hero.aliases?.length ? ` (${hero.aliases.join('/')})` : ''}</option>`)
  ).join('');
}

function bindEvents() {
  document.querySelectorAll('[data-add-comparison]').forEach((button) => {
    button.addEventListener('click', () => addComparisonRow(button.dataset.addComparison));
  });
  $('analyze-setup').addEventListener('click', analyze);
  $('rally-goal').addEventListener('change', analyzeIfReady);
  document.querySelectorAll('[data-preset]').forEach((button) => button.addEventListener('click', () => applyPreset(button.dataset.preset)));
  document.addEventListener('click', (event) => {
    const max = event.target.closest('[data-max-skills]');
    const unknown = event.target.closest('[data-unknown-skills]');
    if (max) setSkillLevels(max.dataset.maxSkills, '5');
    if (unknown) setSkillLevels(unknown.dataset.unknownSkills, 'unknown');
  });
  document.addEventListener('change', updateNotes);
}

function bindRowEvents(id) {
  $(`${id}-slot`).addEventListener('change', () => {
    const slot = $(`${id}-slot`).value;
    const current = $(`${id}-hero`).value;
    $(`${id}-hero`).innerHTML = heroOptions(slot);
    if (findHero(current)?.troopType === slot) $(`${id}-hero`).value = current;
  });
  document.querySelector(`[data-remove-comparison="${id}"]`).addEventListener('click', () => {
    document.querySelector(`[data-comparison-row="${id}"]`).remove();
    updateNotes();
  });
}

function applyPreset(presetId) {
  const preset = presets[presetId];
  if (!preset) return;
  $('rally-goal').value = presetId === '3' ? 'survival' : 'balanced';
  troopTypes.forEach((type) => {
    const prefix = `current-${type}`;
    $(`${prefix}-hero`).value = preset.current[type] || '';
    setInvestment(prefix, 5, 5, '5');
  });
  $('comparison-heroes').innerHTML = '';
  comparisonCount = 0;
  preset.compare.forEach((heroId) => {
    const hero = findHero(heroId);
    addComparisonRow(hero?.troopType || 'infantry');
    const prefix = `compare-${comparisonCount}`;
    $(`${prefix}-hero`).value = heroId;
    $(`${prefix}-slot`).value = hero?.troopType || 'infantry';
    setInvestment(prefix, 5, 5, '5');
  });
  updateNotes();
  $('advisor-output').className = 'empty';
  $('advisor-output').textContent = 'Preset loaded. Click Analyze Rally Setup.';
}

function setInvestment(prefix, stars, widget, skill) {
  $(`${prefix}-stars`).value = stars;
  $(`${prefix}-widget`).value = widget;
  setSkillLevels(prefix, skill);
}

function setSkillLevels(prefix, value) {
  [1, 2, 3].forEach((index) => {
    if ($(`${prefix}-skill${index}`)) $(`${prefix}-skill${index}`).value = value;
  });
  updateNotes();
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
    heroId: hero.id,
    slotType,
    origin,
    starLevel: Number($(`${prefix}-stars`)?.value || 0),
    widgetLevel: Number($(`${prefix}-widget`)?.value || 0),
    expeditionSkillLevels: {
      skill1: $(`${prefix}-skill1`)?.value || 'unknown',
      skill2: $(`${prefix}-skill2`)?.value || 'unknown',
      skill3: $(`${prefix}-skill3`)?.value || 'unknown',
    },
  };
}

function analyzeIfReady() {
  if (readCurrentSelections().length === 3) analyze();
}

function analyze() {
  const current = readCurrentSelections();
  if (current.length !== 3) return renderError('Select one current Infantry, Lancer, and Marksman hero before analyzing.');
  const comparisons = readComparisonSelections();
  const result = rules.analyzeRallySetup(current, comparisons, $('rally-goal').value, heroDb);
  renderResult(result, current, comparisons);
}

function renderResult(result, current, comparisons) {
  const best = result.selectedBest;
  const explanation = result.explanation;
  $('advisor-output').className = 'result-card';
  $('advisor-output').innerHTML = `
    <div class="decision-card win">
      <div class="decision-title">
        <strong>Recommended formation for selected goal</strong>
        <span>${escapeHtml(rules.formationName(best.formation))}</span>
      </div>
      <div class="metric-grid">
        <div class="metric"><span>Goal Score</span><strong>${format(best.goalScore)}</strong></div>
        <div class="metric"><span>Balanced</span><strong>${format(best.categoryScores.balanced)}</strong></div>
        <div class="metric"><span>Damage</span><strong>${format(best.categoryScores.damage)}</strong></div>
        <div class="metric"><span>Survival</span><strong>${format(best.categoryScores.survival)}</strong></div>
      </div>
      <h3>Category Winners</h3>
      ${categoryWinners(result.categoryWinners)}
      <h3>Replacement Explanation</h3>
      ${explanation.replacements.length ? list(explanation.replacements.map((item) => `<strong>${item.from} -> ${item.to}</strong><div class="hint">${escapeHtml(item.reason)}</div>`)) : list(['No replacement beats the current same-type formation for this goal.'])}
      <h3>Use When</h3>
      ${list(explanation.useWhen.map(escapeHtml))}
      <h3>Do Not Use When</h3>
      ${list(explanation.doNotUseWhen.map(escapeHtml))}
      <h3>Formation Profile Comparison</h3>
      ${formationTable(result.combinations)}
      <h3>Profile Details</h3>
      ${profileTable(best.profile)}
      <h3>Missing Data Warnings</h3>
      ${list((explanation.missingData.length ? explanation.missingData : ['No missing data warnings for selected recommended profile.']).map(escapeHtml))}
      <h3>Source Transparency</h3>
      ${sourceTransparency([...current, ...comparisons])}
      <div class="warning">This is a formation profile comparison, not a full battle simulator. It does not yet include chief gear, charms, pets, research, buffs, troop formation, enemy stats, or battle report calibration.</div>
    </div>
  `;
}

function categoryWinners(winners) {
  return `<div class="metric-grid">${Object.entries(winners).map(([key, item]) => `
    <div class="metric"><span>${escapeHtml(goalLabel(key))}</span><strong>${escapeHtml(rules.formationName(item.formation))}</strong></div>
  `).join('')}</div>`;
}

function formationTable(items) {
  return `<div class="table-wrap"><table class="result-table">
    <thead><tr><th>Formation</th><th>Goal</th><th>Balanced</th><th>Damage</th><th>Survival</th><th>Anti Health</th><th>Anti Defense</th><th>Anti Lethality</th><th>Missing</th></tr></thead>
    <tbody>${items.slice(0, 12).map((item) => `<tr>
      <td>${escapeHtml(rules.formationName(item.formation))}</td>
      <td>${format(item.goalScore)}</td>
      <td>${format(item.categoryScores.balanced)}</td>
      <td>${format(item.categoryScores.damage)}</td>
      <td>${format(item.categoryScores.survival)}</td>
      <td>${format(item.categoryScores.antiHealth)}</td>
      <td>${format(item.categoryScores.antiDefense)}</td>
      <td>${format(item.categoryScores.antiLethality)}</td>
      <td>${item.profile.missingData.length}</td>
    </tr>`).join('')}</tbody>
  </table></div>`;
}

function profileTable(profile) {
  const importantRaw = ['allTroopsAttack', 'allTroopsDefense', 'allTroopsHealth', 'allTroopsLethality', 'infantryDefense', 'infantryHealth', 'lancerAttack', 'marksmanAttack'];
  const importantEffects = ['damageDealtUp', 'damageTakenDown', 'enemyDamageDealtDown', 'enemyDamageTakenUp', 'extraDamageChance', 'extraAttackChance', 'dodgeChance', 'roundBasedEffects'];
  return `<div class="table-wrap"><table class="result-table">
    <thead><tr><th>Profile Field</th><th>Value</th></tr></thead>
    <tbody>${importantRaw.map((key) => `<tr><td>${key}</td><td>${format(profile.rawStats[key])}</td></tr>`).join('')}
    ${importantEffects.map((key) => `<tr><td>${key}</td><td>${format(profile.combatEffects[key])}</td></tr>`).join('')}</tbody>
  </table></div>`;
}

function sourceTransparency(selections) {
  const uniqueHeroes = Array.from(new Map(selections.map((item) => [item.hero.id, item.hero])).values());
  return `<div class="source-list">${uniqueHeroes.map((hero) => `
    <div class="source-item">
      <strong>${escapeHtml(hero.name)} - ${label(hero.troopType)} - Gen ${hero.generation || '?'}${hero.aliases?.length ? ` - aliases: ${hero.aliases.join(', ')}` : ''}</strong>
      <span>Source status: ${escapeHtml(hero.dataConfidence)} | Last checked: ${escapeHtml(hero.lastCheckedDate || 'n/a')}</span>
      <a href="${escapeHtml(hero.sourceUrl || '#')}" target="_blank" rel="noreferrer">${escapeHtml(hero.sourceName || 'Source')}</a>
      <span class="hint">${escapeHtml((hero.notes || []).join(' ') || 'No notes.')}</span>
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
  const missing = [];
  if (selection.hero.dataConfidence === 'unverified') missing.push('unverified source');
  if (selection.hero.troopType !== selection.slotType) missing.push(`cross-type: ${selection.hero.troopType} hero in ${selection.slotType} slot`);
  if (!hasAnyStats(selection.hero)) missing.push('base stats missing');
  return `${selection.hero.name}: ${selection.hero.dataConfidence} data${missing.length ? `; ${missing.join('; ')}` : ''}.`;
}

function hasAnyStats(hero) {
  return Object.values(hero.baseStatsByStar?.[5] || {}).some((value) => value !== null && value !== undefined);
}

function list(items) {
  return `<div class="list">${items.map((item) => `<div class="list-item">${item}</div>`).join('')}</div>`;
}

function renderError(message) {
  $('advisor-output').className = 'warning';
  $('advisor-output').textContent = message;
}

function findHero(idOrAlias) {
  const value = String(idOrAlias || '').toLowerCase();
  return heroDb.find((hero) => hero.id === value || hero.aliases?.map((alias) => alias.toLowerCase()).includes(value));
}

function goalLabel(key) {
  return rules.goals[key] || key;
}

function label(value) {
  return String(value || '').charAt(0).toUpperCase() + String(value || '').slice(1);
}

function format(value) {
  return Math.round(Number(value || 0) * 10) / 10;
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[ch]));
}

document.addEventListener('DOMContentLoaded', init);
