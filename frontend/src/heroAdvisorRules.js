(function () {
  const goals = {
    balanced: 'Balanced rally',
    damage: 'More damage',
    survival: 'More survival',
    antiHealth: 'Counter high-health enemy',
    antiDefense: 'Counter high-defense enemy',
    antiLethality: 'Counter high-lethality enemy',
    reduceLosses: 'Reduce wounded/losses',
    aggressive: 'Aggressive rally against weaker enemy',
    safer: 'Safer rally against stronger enemy',
  };

  function analyzeRallySetup(currentFormation, comparisonHeroes, selectedGoal, heroDb) {
    const combinations = generateFormationCombinations(currentFormation, comparisonHeroes);
    const profiles = combinations.map((formation) => {
      const profile = window.WOS_FORMATION_PROFILE.calculateFormationProfile(formation, heroDb);
      const categoryScores = scoreProfile(profile);
      return {
        formation,
        profile,
        categoryScores,
        goalScore: scoreForGoal(categoryScores, selectedGoal),
      };
    }).sort((a, b) => b.goalScore - a.goalScore);

    const selectedBest = profiles[0];
    const bestBalanced = bestBy(profiles, 'balanced');
    const bestDamage = bestBy(profiles, 'damage');
    const bestSurvival = bestBy(profiles, 'survival');
    const bestAntiHealth = bestBy(profiles, 'antiHealth');
    const bestAntiDefense = bestBy(profiles, 'antiDefense');
    const bestAntiLethality = bestBy(profiles, 'antiLethality');
    const current = profiles.find((item) => sameFormation(item.formation, currentFormation)) || profiles[profiles.length - 1];
    const deltaProfile = diffProfiles(current?.profile, selectedBest?.profile);
    const explanation = generateRecommendationExplanation(currentFormation, selectedBest?.formation || [], deltaProfile, selectedGoal, selectedBest?.profile);

    return {
      selectedGoal,
      combinations: profiles,
      selectedBest,
      current,
      categoryWinners: {
        balanced: bestBalanced,
        damage: bestDamage,
        survival: bestSurvival,
        antiHealth: bestAntiHealth,
        antiDefense: bestAntiDefense,
        antiLethality: bestAntiLethality,
      },
      explanation,
    };
  }

  function generateFormationCombinations(currentFormation, comparisonHeroes) {
    const bySlot = { infantry: [], lancer: [], marksman: [] };
    [...currentFormation, ...comparisonHeroes].forEach((selection) => {
      if (!selection?.hero) return;
      const slot = selection.slotType || selection.hero.troopType;
      if (!bySlot[slot]) return;
      const sameType = selection.hero.troopType === slot;
      bySlot[slot].push({ ...selection, crossType: !sameType });
    });
    Object.keys(bySlot).forEach((slot) => {
      const unique = new Map();
      bySlot[slot].filter((item) => !item.crossType).forEach((item) => unique.set(item.hero.id, item));
      if (!unique.size) bySlot[slot].forEach((item) => unique.set(item.hero.id, item));
      bySlot[slot] = Array.from(unique.values());
    });
    const combos = [];
    bySlot.infantry.forEach((infantry) => bySlot.lancer.forEach((lancer) => bySlot.marksman.forEach((marksman) => {
      combos.push([infantry, lancer, marksman]);
    })));
    return combos;
  }

  function scoreProfile(profile) {
    const r = profile.rawStats;
    const e = profile.combatEffects;
    const attack = r.infantryAttack + r.lancerAttack + r.marksmanAttack + r.allTroopsAttack * 3;
    const defense = r.infantryDefense + r.lancerDefense + r.marksmanDefense + r.allTroopsDefense * 3;
    const health = r.infantryHealth + r.lancerHealth + r.marksmanHealth + r.allTroopsHealth * 3;
    const lethality = r.infantryLethality + r.lancerLethality + r.marksmanLethality + r.allTroopsLethality * 3;
    const damage = attack * 0.35 + lethality * 0.45 + e.damageDealtUp * 0.45 + e.enemyDamageTakenUp * 0.55 + e.extraDamageChance * 0.35 + e.extraAttackChance * 0.35 + e.roundBasedEffects * 0.2;
    const survival = health * 0.4 + defense * 0.35 + e.damageTakenDown * 0.75 + e.enemyDamageDealtDown * 0.6 + e.dodgeChance * 0.45 + r.infantryHealth * 0.2 + r.infantryDefense * 0.2;
    const antiHealth = lethality * 0.6 + e.damageDealtUp * 0.4 + e.enemyHealthDown * 0.75 + e.roundBasedEffects * 0.35 + e.extraDamageChance * 0.25;
    const antiDefense = lethality * 0.55 + attack * 0.25 + e.enemyDefenseDown * 0.8 + e.damageDealtUp * 0.35 + e.enemyDamageTakenUp * 0.35;
    const antiLethality = health * 0.45 + defense * 0.35 + e.damageTakenDown * 0.8 + e.enemyDamageDealtDown * 0.7 + r.infantryHealth * 0.2;
    return {
      balanced: round((damage + survival) / 2),
      damage: round(damage),
      survival: round(survival),
      antiHealth: round(antiHealth),
      antiDefense: round(antiDefense),
      antiLethality: round(antiLethality),
      reduceLosses: round(survival * 0.75 + antiLethality * 0.25),
      aggressive: round(damage * 0.8 + antiDefense * 0.2),
      safer: round(survival * 0.65 + damage * 0.2 + antiLethality * 0.15),
    };
  }

  function scoreForGoal(scores, goal) {
    return scores[goal] ?? scores.balanced;
  }

  function bestBy(profiles, key) {
    return profiles.slice().sort((a, b) => (b.categoryScores[key] || 0) - (a.categoryScores[key] || 0))[0];
  }

  function diffProfiles(currentProfile, recommendedProfile) {
    const diff = { rawStats: {}, combatEffects: {} };
    if (!currentProfile || !recommendedProfile) return diff;
    Object.keys(recommendedProfile.rawStats).forEach((key) => {
      diff.rawStats[key] = round((recommendedProfile.rawStats[key] || 0) - (currentProfile.rawStats[key] || 0));
    });
    Object.keys(recommendedProfile.combatEffects).forEach((key) => {
      diff.combatEffects[key] = round((recommendedProfile.combatEffects[key] || 0) - (currentProfile.combatEffects[key] || 0));
    });
    return diff;
  }

  function generateRecommendationExplanation(currentFormation, recommendedFormation, deltaProfile, selectedGoal, profile) {
    const replacements = [];
    ['infantry', 'lancer', 'marksman'].forEach((slot, index) => {
      const current = currentFormation.find((item) => item.slotType === slot) || currentFormation[index];
      const recommended = recommendedFormation.find((item) => item.slotType === slot) || recommendedFormation[index];
      if (!current || !recommended || current.hero.id === recommended.hero.id) return;
      replacements.push({
        from: current.hero.name,
        to: recommended.hero.name,
        slot,
        reason: replacementReason(current, recommended, selectedGoal),
      });
    });
    const missing = profile?.missingData || [];
    return {
      summary: `Recommended formation for ${goals[selectedGoal] || goals.balanced}: ${formationName(recommendedFormation)}.`,
      replacements,
      useWhen: useWhen(selectedGoal),
      doNotUseWhen: [
        'Older current heroes have much higher stars, widget, or active skill levels than the tested replacements.',
        'You are joining a rally instead of leading it; joiner logic is different.',
        'You need Bear Trap, Crazy Joe, or garrison optimization instead of PvP rally leading.',
        'The recommendation depends on a hero with missing skill/widget data you have not verified.',
      ],
      confidence: confidenceFor(recommendedFormation, missing),
      missingData: missing,
      deltaProfile,
    };
  }

  function replacementReason(current, recommended, goal) {
    const investmentGap = investmentScore(recommended) - investmentScore(current);
    if (investmentGap < -25) {
      return `Keep caution: ${recommended.hero.name} has a better profile candidate path, but ${current.hero.name} has much higher current investment. Upgrade ${recommended.hero.name} before replacing.`;
    }
    const parts = [
      `${recommended.hero.name} is a same-type ${recommended.hero.troopType} replacement for ${current.hero.name}.`,
    ];
    if ((recommended.hero.generation || 0) > (current.hero.generation || 0)) parts.push(`It is later generation (${recommended.hero.generation} vs ${current.hero.generation}).`);
    if (goal === 'damage' || goal === 'aggressive') parts.push('The selected goal values Attack, Lethality, Damage Dealt, and extra damage effects.');
    if (goal === 'survival' || goal === 'safer' || goal === 'reduceLosses') parts.push('The selected goal values Health, Defense, Damage Taken reduction, and frontline durability.');
    parts.push('For rally leaders, all 3 selected heroes matter.');
    return parts.join(' ');
  }

  function useWhen(goal) {
    const common = ['You are starting PvP rallies as the rally leader.', 'The tested replacement heroes have similar star/widget/skill investment.'];
    const map = {
      balanced: ['You want a general rally profile without overcommitting to damage or survival.'],
      damage: ['You need more damage pressure, lethality, extra damage, or enemy damage taken pressure.'],
      survival: ['You are facing stronger targets and need more Health, Defense, and damage reduction.'],
      antiHealth: ['The enemy has high Health and you need lethality or sustained damage pressure.'],
      antiDefense: ['The enemy has high Defense and you need lethality, Attack, or enemy-defense pressure.'],
      antiLethality: ['The enemy has high Lethality and you need safer frontline durability.'],
      reduceLosses: ['You want to reduce wounded/losses more than maximize damage.'],
      aggressive: ['The enemy is weaker and you want faster pressure.'],
      safer: ['The enemy is stronger and you want a safer rally profile.'],
    };
    return common.concat(map[goal] || map.balanced);
  }

  function confidenceFor(formation, missing) {
    if (formation.some((item) => item.crossType) || missing.length > 6) return 'Low';
    if (missing.length > 0 || formation.some((item) => item.hero.dataConfidence === 'unverified')) return 'Medium';
    return 'High';
  }

  function investmentScore(selection) {
    const stars = Number(selection.starLevel ?? selection.stars ?? 0) * 20;
    const widget = Number(selection.widgetLevel ?? 0) * 10;
    const skills = Object.values(selection.expeditionSkillLevels || {}).reduce((sum, level) => sum + (level === 'unknown' ? 50 : Number(level) * 20), 0) / 3;
    return stars * 0.45 + widget * 0.35 + skills * 0.2;
  }

  function sameFormation(a, b) {
    return formationName(a) === formationName(b);
  }

  function formationName(formation) {
    return (formation || []).map((item) => item.hero?.name || 'Unknown').join(' / ');
  }

  function round(value) {
    return Math.round(Number(value || 0) * 10) / 10;
  }

  window.WOS_HERO_ADVISOR_RULES = {
    goals,
    analyzeRallySetup,
    generateFormationCombinations,
    scoreProfile,
    generateRecommendationExplanation,
    formationName,
  };
})();
