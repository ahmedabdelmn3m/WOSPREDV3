(function () {
  const SCORING_CONFIG = {
    weights: {
      generationScore: 0.25,
      starScore: 0.20,
      widgetScore: 0.20,
      expeditionSkillScore: 0.15,
      rallyLeaderRoleScore: 0.15,
      dataConfidenceScore: 0.05,
    },
    generationScores: {
      1: 30,
      2: 40,
      3: 50,
      4: 60,
      5: 70,
      6: 80,
      7: 90,
    },
    confidenceScores: {
      wiki: 90,
      community: 75,
      manual: 60,
      unverified: 40,
    },
  };

  function normalizeStar(level) {
    return Math.max(0, Math.min(5, Number(level || 0))) * 20;
  }

  function normalizeWidget(level) {
    return Math.max(0, Math.min(10, Number(level || 0))) * 10;
  }

  function normalizeGeneration(generation) {
    const gen = Number(generation || 0);
    if (gen >= 8) return 100;
    return SCORING_CONFIG.generationScores[gen] || 20;
  }

  function normalizeSkill(level) {
    if (level === 'unknown' || level === undefined || level === null || level === '') return 50;
    return Math.max(1, Math.min(5, Number(level || 1))) * 20;
  }

  function confidenceScore(confidence) {
    return SCORING_CONFIG.confidenceScores[confidence] || 40;
  }

  function effectiveRoleRating(hero) {
    const override = hero.manualOverrides?.roleRatings?.rallyLeader;
    const calibrated = hero.reportCalibration?.adjustedRallyLeaderRating;
    if (Number.isFinite(calibrated)) return calibrated;
    if (Number.isFinite(override)) return override;
    if (Number.isFinite(hero.roleRatings?.rallyLeader)) return hero.roleRatings.rallyLeader;

    let inferred = normalizeGeneration(hero.generation) * 0.45;
    inferred += hero.subClass === 'combat' ? 20 : 8;
    const text = [
      hero.widget?.rallyLeaderEffect,
      hero.widget?.description,
      hero.skills?.expeditionSkill1?.description,
      hero.skills?.expeditionSkill2?.description,
      hero.skills?.expeditionSkill3?.description,
    ].join(' ').toLowerCase();
    if (/rallied|rally/.test(text)) inferred += 20;
    if (/damage|attack|defense|health|lethality|taken/.test(text)) inferred += 10;
    return Math.max(0, Math.min(100, Math.round(inferred)));
  }

  function scoreHero(selection) {
    const hero = selection.hero;
    const parts = {
      generationScore: normalizeGeneration(hero.generation),
      starScore: normalizeStar(selection.stars),
      widgetScore: normalizeWidget(selection.widgetLevel),
      expeditionSkillScore: normalizeSkill(selection.skillLevel),
      rallyLeaderRoleScore: effectiveRoleRating(hero),
      dataConfidenceScore: confidenceScore(hero.dataConfidence),
    };
    const total = Object.entries(SCORING_CONFIG.weights).reduce((sum, [key, weight]) => sum + parts[key] * weight, 0);
    return {
      total: Math.round(total * 10) / 10,
      parts,
    };
  }

  function analyzeRallySetup(current, comparisons) {
    const warnings = [
      'This MVP does not include troop count, chief gear, charms, pets, buffs, formation, enemy stats, or full battle simulation.',
      'Wiki/community hero data is the baseline. Future battle report calibration can adjust ratings without deleting source values.',
    ];
    const replacements = [];
    const keep = [];
    const recommended = [];
    const allByType = { infantry: [], lancer: [], marksman: [] };

    [...current, ...comparisons].forEach((selection) => {
      if (!selection?.hero) return;
      const scored = { ...selection, score: scoreHero(selection) };
      const type = selection.slotType || selection.hero.troopType;
      if (allByType[type]) allByType[type].push(scored);
      if (selection.hero.troopType !== type) {
        warnings.push(`${selection.hero.name} is ${selection.hero.troopType}, so using them in a ${type} slot is cross-type and experimental.`);
      }
      if (selection.hero.dataConfidence === 'unverified') {
        warnings.push(`${selection.hero.name} has unverified data and should be checked before making expensive upgrade decisions.`);
      }
      if (hasMissingCoreData(selection.hero)) {
        warnings.push(`${selection.hero.name} has incomplete skill/widget/stat data. Recommendation leans more on generation and investment.`);
      }
    });

    ['infantry', 'lancer', 'marksman'].forEach((type) => {
      const currentHero = current.find((item) => item.slotType === type);
      const currentScored = currentHero ? { ...currentHero, score: scoreHero(currentHero) } : null;
      const sameTypeCandidates = allByType[type].filter((item) => item.hero.troopType === type);
      const best = sameTypeCandidates.sort((a, b) => b.score.total - a.score.total)[0] || currentScored;
      if (!best) return;
      recommended.push(best);
      if (currentScored && best.hero.id !== currentScored.hero.id && best.score.total > currentScored.score.total + 2) {
        replacements.push({
          from: currentScored,
          to: best,
          reason: replacementReason(currentScored, best),
        });
      } else if (currentScored) {
        keep.push({
          hero: currentScored,
          reason: keepReason(currentScored, best),
        });
      }
    });

    const currentScore = average(current.map((item) => scoreHero(item).total));
    const recommendedScore = average(recommended.map((item) => item.score.total));
    const confidence = confidenceLevel(current, comparisons, warnings, replacements);

    return {
      currentScore,
      recommendedScore,
      recommended,
      replacements,
      keep,
      confidence,
      warnings: unique(warnings),
      scoringConfig: SCORING_CONFIG,
    };
  }

  function hasMissingCoreData(hero) {
    return !hero.sourceUrl || hero.dataConfidence === 'unverified' || !hero.skills?.expeditionSkill1?.name || !hero.widget?.name;
  }

  function replacementReason(current, next) {
    const reasons = [];
    if (current.hero.troopType === next.hero.troopType) reasons.push(`${next.hero.name} is a same-type ${next.hero.troopType} replacement.`);
    if ((next.hero.generation || 0) > (current.hero.generation || 0)) reasons.push(`${next.hero.name} is later generation (${next.hero.generation}) than ${current.hero.name} (${current.hero.generation}).`);
    if (next.score.parts.starScore >= current.score.parts.starScore) reasons.push('Star investment is equal or better.');
    if (next.score.parts.widgetScore >= current.score.parts.widgetScore) reasons.push('Widget investment is equal or better.');
    if (next.hero.widget?.rallyLeaderEffect) reasons.push(`Widget note: ${next.hero.widget.rallyLeaderEffect}.`);
    reasons.push('For PvP rally leaders, all 3 selected heroes matter; this is not rally joiner first-skill-only logic.');
    return reasons.join(' ');
  }

  function keepReason(current, best) {
    if (best && best.hero.id !== current.hero.id) {
      return `Keep ${current.hero.name} for now because ${best.hero.name} does not beat the current investment by enough to recommend a swap.`;
    }
    return `Keep ${current.hero.name}; no same-type comparison hero clearly improves this slot.`;
  }

  function confidenceLevel(current, comparisons, warnings, replacements) {
    const pool = [...current, ...comparisons].filter((item) => item?.hero);
    const sameTypeOnly = comparisons.every((item) => item.hero?.troopType === item.slotType);
    const completeInputs = pool.every((item) => item.stars !== '' && item.widgetLevel !== '' && item.skillLevel !== '');
    const trustedData = pool.every((item) => ['wiki', 'community'].includes(item.hero.dataConfidence) && item.hero.sourceUrl);
    const missingWarnings = warnings.some((warning) => /incomplete|unverified|cross-type/i.test(warning));
    if (sameTypeOnly && completeInputs && trustedData && !missingWarnings) return 'High';
    if (sameTypeOnly && trustedData && replacements.length >= 0) return 'Medium';
    return 'Low';
  }

  function average(values) {
    const valid = values.filter((value) => Number.isFinite(value));
    if (!valid.length) return 0;
    return Math.round((valid.reduce((sum, value) => sum + value, 0) / valid.length) * 10) / 10;
  }

  function unique(values) {
    return Array.from(new Set(values));
  }

  window.WOS_HERO_ADVISOR_RULES = {
    SCORING_CONFIG,
    scoreHero,
    analyzeRallySetup,
    normalizeStar,
    normalizeWidget,
    normalizeGeneration,
    normalizeSkill,
  };
})();
