(function () {
  const rawStatKeys = [
    'infantryAttack', 'infantryDefense', 'infantryHealth', 'infantryLethality',
    'lancerAttack', 'lancerDefense', 'lancerHealth', 'lancerLethality',
    'marksmanAttack', 'marksmanDefense', 'marksmanHealth', 'marksmanLethality',
    'allTroopsAttack', 'allTroopsDefense', 'allTroopsHealth', 'allTroopsLethality',
  ];
  const effectKeys = [
    'damageDealtUp', 'damageTakenDown', 'enemyDamageDealtDown', 'enemyDamageTakenUp',
    'enemyHealthDown', 'enemyDefenseDown', 'extraDamageChance', 'extraAttackChance',
    'dodgeChance', 'counterattackEffects', 'normalAttackEffects', 'roundBasedEffects',
    'conditionalEffects',
  ];

  function emptyProfile() {
    const rawStats = Object.fromEntries(rawStatKeys.map((key) => [key, 0]));
    const combatEffects = Object.fromEntries(effectKeys.map((key) => [key, 0]));
    return {
      rawStats,
      combatEffects,
      specialEffects: [],
      missingData: [],
      sourceConfidence: {
        wikiFields: 0,
        communityFields: 0,
        manualFields: 0,
        missingFields: 0,
      },
    };
  }

  function calculateFormationProfile(selections, heroDb) {
    const profile = emptyProfile();
    selections.forEach((selection) => applyHero(profile, selection, heroDb));
    return profile;
  }

  function applyHero(profile, selection, heroDb) {
    const hero = selection.hero || heroDb.find((item) => item.id === selection.heroId || item.aliases?.includes(selection.heroId));
    if (!hero) {
      profile.missingData.push(`Unknown hero ${selection.heroId || 'not selected'}.`);
      profile.sourceConfidence.missingFields += 1;
      return;
    }
    countSource(profile, hero.dataConfidence);
    const star = clamp(Number(selection.starLevel ?? selection.stars ?? 0), 0, 5);
    const starStats = hero.baseStatsByStar?.[star] || null;
    const maxStats = hero.baseStatsByStar?.[5] || null;
    if (starStats && hasAnyValue(starStats)) {
      addRawStats(profile, starStats, 1);
    } else if (maxStats && hasAnyValue(maxStats)) {
      addRawStats(profile, maxStats, star / 5);
      profile.missingData.push(`${hero.name}: exact star-${star} stats missing, scaled from available 5-star source values.`);
      profile.sourceConfidence.missingFields += 1;
    } else {
      profile.missingData.push(`${hero.name}: base stats by star are missing.`);
      profile.sourceConfidence.missingFields += 1;
    }

    (hero.expeditionSkills || []).forEach((skill, index) => {
      const level = skillLevel(selection, index + 1);
      if (star < (skill.unlockStar || 1)) {
        profile.missingData.push(`${hero.name}: ${skill.name} is locked at selected star level.`);
        return;
      }
      if (level === 'unknown') {
        profile.missingData.push(`${hero.name}: ${skill.name} level is unknown.`);
        profile.sourceConfidence.missingFields += 1;
        return;
      }
      const value = skill.valuesByLevel?.[Number(level)];
      if (value === null || value === undefined) {
        profile.missingData.push(`${hero.name}: ${skill.name} value for level ${level} is missing.`);
        profile.sourceConfidence.missingFields += 1;
        return;
      }
      applySkill(profile, hero, skill, value);
    });

    const widgetLevel = clamp(Number(selection.widgetLevel ?? 0), 0, 10);
    const widgetEffects = hero.widget?.effectsByLevel?.[widgetLevel] || [];
    if (widgetLevel > 0 && widgetEffects.length === 0) {
      const fallback = hero.widget?.effectsByLevel?.[10] || [];
      if (fallback.length) {
        fallback.forEach((item) => applyWidgetEffect(profile, hero, item, widgetLevel / 10));
        profile.missingData.push(`${hero.name}: exact widget level ${widgetLevel} effects missing, scaled from level 10 source values.`);
        profile.sourceConfidence.missingFields += 1;
      } else {
        profile.missingData.push(`${hero.name}: widget effect values are missing.`);
        profile.sourceConfidence.missingFields += 1;
      }
    } else {
      widgetEffects.forEach((item) => applyWidgetEffect(profile, hero, item, 1));
    }
  }

  function applySkill(profile, hero, skill, value) {
    if (rawStatKeys.includes(skill.stat)) {
      profile.rawStats[skill.stat] += Number(value) || 0;
      return;
    }
    if (effectKeys.includes(skill.stat)) {
      profile.combatEffects[skill.stat] += Number(value) || 0;
      profile.specialEffects.push(`${hero.name} - ${skill.name}: ${skill.description}`);
      return;
    }
    profile.combatEffects.conditionalEffects += Number(value) || 0;
    profile.specialEffects.push(`${hero.name} - ${skill.name}: ${skill.description}`);
  }

  function applyWidgetEffect(profile, hero, item, scale) {
    const value = (Number(item.value) || 0) * scale;
    if (rawStatKeys.includes(item.stat)) {
      profile.rawStats[item.stat] += value;
    } else if (effectKeys.includes(item.stat)) {
      profile.combatEffects[item.stat] += value;
    } else {
      profile.combatEffects.conditionalEffects += value;
    }
    profile.specialEffects.push(`${hero.name} widget: ${item.stat} ${round(value)}`);
  }

  function addRawStats(profile, stats, scale) {
    rawStatKeys.forEach((key) => {
      if (stats[key] === null || stats[key] === undefined) return;
      profile.rawStats[key] += Number(stats[key]) * scale;
    });
  }

  function hasAnyValue(stats) {
    return rawStatKeys.some((key) => stats[key] !== null && stats[key] !== undefined);
  }

  function skillLevel(selection, index) {
    const levels = selection.expeditionSkillLevels || {};
    return levels[`skill${index}`] ?? levels[index] ?? 'unknown';
  }

  function countSource(profile, confidence) {
    if (confidence === 'wiki') profile.sourceConfidence.wikiFields += 1;
    else if (confidence === 'community') profile.sourceConfidence.communityFields += 1;
    else if (confidence === 'manual') profile.sourceConfidence.manualFields += 1;
    else profile.sourceConfidence.missingFields += 1;
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, Number.isFinite(value) ? value : min));
  }

  function round(value) {
    return Math.round(Number(value || 0) * 10) / 10;
  }

  window.WOS_FORMATION_PROFILE = {
    rawStatKeys,
    effectKeys,
    calculateFormationProfile,
  };
})();
