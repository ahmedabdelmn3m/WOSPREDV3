(function () {
  'use strict';

  const rows = [];
  const skills = [];

  function addRows(troopType, tier, values) {
    const familyName = tier === 10 ? 'Apex' : 'Helios';
    values.forEach(([attack, defense, health, lethality], index) => {
      rows.push({ troopType, tier, familyName, fcLevel: index + 1, attack, defense, health, lethality });
    });
  }

  addRows('infantry', 10, [[11,14,16,10],[12,16,17,11],[13,17,18,12],[13,18,19,13],[14,20,20,13],[14,21,21,13],[15,22,22,14],[15,23,23,15],[16,25,24,15],[18,26,25,16]]);
  addRows('infantry', 11, [[13,16,18,12],[14,17,19,13],[15,18,20,14],[15,19,21,15],[16,22,22,15],[17,23,23,16],[17,24,24,16],[18,25,25,17],[18,27,26,17],[19,28,27,18]]);
  addRows('lancer', 10, [[14,12,11,15],[16,13,12,16],[17,14,13,17],[18,14,13,18],[20,15,14,19],[21,15,14,20],[22,16,15,21],[23,17,15,22],[25,17,16,23],[26,19,17,24]]);
  addRows('lancer', 11, [[16,14,13,17],[18,15,14,18],[19,16,15,19],[20,16,15,20],[22,17,16,21],[23,18,16,22],[24,18,17,23],[25,19,17,24],[27,19,18,25],[28,21,20,26]]);
  addRows('marksman', 10, [[15,11,11,16],[17,12,12,17],[18,13,13,18],[19,14,13,19],[21,14,14,20],[22,15,14,21],[23,15,15,22],[24,16,15,23],[26,17,16,24],[27,19,17,25]]);
  addRows('marksman', 11, [[17,13,13,18],[19,14,14,19],[20,15,15,20],[21,16,15,21],[23,16,16,22],[24,17,16,23],[25,18,17,24],[26,19,18,25],[28,19,18,26],[30,21,20,27]]);

  function skill(troopType, unlock, skillName, effectType, triggerChance, targetType, multiplier, flatValue, description) {
    skills.push({ troopType, ...unlock, skillName, effectType, triggerChance, targetType, multiplier, flatValue, description, enabled: true });
  }

  skill('infantry', { unlockLevel: 1 }, 'Master Brawler', 'damage_up_vs_lancer', 1, 'lancer', .10, null, '+10% attack damage against Lancers.');
  skill('infantry', { unlockLevel: 7 }, 'Bands of Steel', 'defense_up_vs_lancer', 1, 'lancer', .10, null, '+10% defense against Lancers.');
  skill('infantry', { unlockFcLevel: 3 }, 'Crystal Shield I', 'damage_offset', .25, 'self', null, 36, '25% chance to offset 36 damage.');
  skill('infantry', { unlockFcLevel: 5 }, 'Crystal Shield II', 'damage_offset', .375, 'self', null, 36, '37.5% chance to offset 36 damage.');
  skill('infantry', { unlockFcLevel: 8 }, 'Body of Light I', 'defense_up_and_shield_mitigation', 1, 'infantry', .04, null, '+4% Infantry Defense; shield active reduces extra 10% damage.');
  skill('infantry', { unlockFcLevel: 10 }, 'Body of Light II', 'defense_up_and_shield_mitigation', 1, 'infantry', .06, null, '+6% Infantry Defense; shield active reduces extra 15% damage.');
  skill('lancer', { unlockLevel: 1 }, 'Charge', 'damage_up_vs_marksman', 1, 'marksman', .10, null, '+10% attack damage against Marksmen.');
  skill('lancer', { unlockLevel: 7 }, 'Ambusher', 'backline_target_chance', .20, 'marksman', null, null, '20% chance to target Marksmen behind Infantry.');
  skill('lancer', { unlockFcLevel: 3 }, 'Crystal Lance I', 'double_damage_chance', .10, 'current_target', 2, null, '10% chance to deal double damage.');
  skill('lancer', { unlockFcLevel: 5 }, 'Crystal Lance II', 'double_damage_chance', .15, 'current_target', 2, null, '15% chance to deal double damage.');
  skill('lancer', { unlockFcLevel: 8 }, 'Incandescent Field I', 'half_damage_taken_chance', .10, 'self', .5, null, '10% chance to take half damage.');
  skill('lancer', { unlockFcLevel: 10 }, 'Incandescent Field II', 'half_damage_taken_chance', .15, 'self', .5, null, '15% chance to take half damage.');
  skill('marksman', { unlockLevel: 1 }, 'Ranged Strike', 'damage_up_vs_infantry', 1, 'infantry', .10, null, '+10% attack damage against Infantry.');
  skill('marksman', { unlockLevel: 7 }, 'Volley', 'strike_twice_chance', .10, 'current_target', 2, null, '10% chance to strike twice.');
  skill('marksman', { unlockFcLevel: 3 }, 'Crystal Gunpowder I', 'bonus_damage_chance', .20, 'current_target', 1.5, null, '20% chance to deal 50% more damage.');
  skill('marksman', { unlockFcLevel: 5 }, 'Crystal Gunpowder II', 'bonus_damage_chance', .30, 'current_target', 1.5, null, '30% chance to deal 50% more damage.');
  skill('marksman', { unlockFcLevel: 8 }, 'Flame Charge I', 'basic_attack_up_and_proc_bonus', 1, 'marksman', .04, null, '+4% Marksman basic attack; Crystal Gunpowder deals extra 25%.');
  skill('marksman', { unlockFcLevel: 10 }, 'Flame Charge II', 'basic_attack_up_and_proc_bonus', 1, 'marksman', .06, null, '+6% Marksman basic attack; Crystal Gunpowder deals extra 37.5%.');

  function getTroopStats(troopType, tier, fcLevel) {
    return rows.find((row) => row.troopType === troopType && row.tier === Number(tier) && row.fcLevel === Number(fcLevel));
  }

  function unlockedSkills(troopType, fcLevel) {
    return skills.filter((item) => item.enabled && item.troopType === troopType && Number(item.unlockFcLevel || 1) <= Number(fcLevel));
  }

  window.WOS_TROOP_DATA = { rows, skills, getTroopStats, unlockedSkills };
})();
