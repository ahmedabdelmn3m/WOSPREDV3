(function () {
  const checked = '2026-06-18';
  const sourceRoot = 'https://wos.h5joy-games.com';
  const heroUrl = (gen, id) => `${sourceRoot}/heroes/s${gen}/${id}/`;
  const emptyStats = () => ({
    infantryAttack: null,
    infantryDefense: null,
    infantryHealth: null,
    infantryLethality: null,
    lancerAttack: null,
    lancerDefense: null,
    lancerHealth: null,
    lancerLethality: null,
    marksmanAttack: null,
    marksmanDefense: null,
    marksmanHealth: null,
    marksmanLethality: null,
    allTroopsAttack: null,
    allTroopsDefense: null,
    allTroopsHealth: null,
    allTroopsLethality: null,
  });
  const statsByStar = (troopType, attack, defense, health = null, lethality = null) => {
    const stars = { 0: emptyStats(), 1: emptyStats(), 2: emptyStats(), 3: emptyStats(), 4: emptyStats(), 5: emptyStats() };
    const prefix = troopType === 'marksman' ? 'marksman' : troopType;
    stars[5][`${prefix}Attack`] = attack;
    stars[5][`${prefix}Defense`] = defense;
    stars[5][`${prefix}Health`] = health;
    stars[5][`${prefix}Lethality`] = lethality;
    return stars;
  };
  const blankStars = () => ({ 0: emptyStats(), 1: emptyStats(), 2: emptyStats(), 3: emptyStats(), 4: emptyStats(), 5: emptyStats() });
  const values = (arr) => ({ 1: arr[0], 2: arr[1], 3: arr[2], 4: arr[3], 5: arr[4] });
  const skill = ({
    id, name, unlockStar = 1, appliesWhen = 'rally_leader', targetTroopType = 'all',
    targetScope = 'self_or_targets', effectType = 'conditional', stat = 'conditionalEffects',
    valuesByLevel = null, duration = null, triggerCondition = null, chance = null,
    description, sourceUrl, confidence = 'community',
  }) => ({
    id,
    name,
    unlockStar,
    maxLevel: 5,
    appliesWhen,
    targetTroopType,
    targetScope,
    effectType,
    stat,
    valuesByLevel,
    duration,
    triggerCondition,
    chance,
    description,
    sourceText: description,
    sourceUrl,
    confidence,
  });
  const widget = (name, sourceUrl, effects10 = [], description = null, confidence = 'community') => {
    const effectsByLevel = {};
    for (let i = 0; i <= 10; i += 1) effectsByLevel[i] = i === 10 ? effects10 : [];
    return {
      name,
      unlockType: name ? 'exclusive_gear_widget' : null,
      effectsByLevel,
      description,
      sourceText: description,
      sourceUrl,
      confidence,
    };
  };
  const effect = (stat, value, effectType = 'rawStat', targetTroopType = 'all', targetScope = 'own') => ({
    stat,
    value,
    effectType,
    targetTroopType,
    targetScope,
  });
  const hero = ({
    id, name, aliases = [], troopType, generation, rarity = 'mythic', subClass = 'combat',
    baseStatsByStar = blankStars(), expeditionSkills = [], heroWidget = null,
    dataConfidence = 'community', notes = [],
  }) => {
    const sourceUrl = generation ? heroUrl(generation, id) : `${sourceRoot}/heroes/`;
    return {
      id,
      name,
      aliases,
      troopType,
      generation,
      rarity,
      subClass,
      sourceName: 'h5joy Whiteout Survival Hero Database',
      sourceUrl,
      lastCheckedDate: checked,
      dataConfidence,
      baseStatsByStar,
      expeditionSkills,
      widget: heroWidget || widget(null, sourceUrl, [], 'Widget data not verified.', 'unverified'),
      notes,
      manualOverrides: {
        enabled: false,
        notes: [],
        overriddenFields: {},
      },
      reportCalibration: {
        sampleSize: 0,
        adjustedProfiles: null,
        confidence: 'none',
        notes: [],
      },
    };
  };

  const heroes = [
    hero({
      id: 'jeronimo',
      name: 'Jeronimo',
      troopType: 'infantry',
      generation: 1,
      baseStatsByStar: statsByStar('infantry', 260.2, 260.2, null, 62.5),
      expeditionSkills: [
        skill({ id: 'combo-slash', name: 'Combo Slash', effectType: 'damage', stat: 'damageDealtUp', valuesByLevel: values([160, 176, 192, 208, 224]), description: 'Deals three Attack-scaled slashes.', sourceUrl: heroUrl(1, 'jeronimo') }),
        skill({ id: 'sword-art', name: 'Sword Art', effectType: 'round_damage', stat: 'roundBasedEffects', valuesByLevel: values([15, 17, 19, 21, 23]), description: 'Attacks release sword energy for area damage.', sourceUrl: heroUrl(1, 'jeronimo') }),
        skill({ id: 'lone-wolf', name: 'Lone Wolf', effectType: 'attack_up', stat: 'allTroopsAttack', valuesByLevel: values([16, 24, 32, 40, 48]), triggerCondition: 'Health over 50%', description: 'Gains Attack when Health is over 50%.', sourceUrl: heroUrl(1, 'jeronimo') }),
      ],
      heroWidget: widget('Dawnbreak', heroUrl(1, 'jeronimo'), [
        effect('allTroopsLethality', 62.5),
        effect('allTroopsHealth', 62.5),
        effect('damageTakenDown', 30, 'combatEffect', 'all', 'self'),
        effect('allTroopsAttack', 15, 'rawStat', 'all', 'rally'),
      ], 'Shield of Swords reduces damage taken by 30%. Discernment increases Attack of rallied Troop by 15%.'),
    }),
    hero({ id: 'flint', name: 'Flint', troopType: 'infantry', generation: 2, baseStatsByStar: statsByStar('infantry', 240.19, 240.19, null, 60), expeditionSkills: [
      skill({ id: 'fires-of-vengeance', name: 'Fires of Vengeance', effectType: 'enemy_damage_taken_up', stat: 'enemyDamageTakenUp', valuesByLevel: values([10, 15, 20, 25, 30]), duration: '2 seconds', description: 'Deals repeated damage and amplifies damage taken by target.', sourceUrl: heroUrl(2, 'flint') }),
      skill({ id: 'incinerator', name: 'Incinerator', effectType: 'heal', stat: 'conditionalEffects', valuesByLevel: values([20, 25, 30, 35, 40]), triggerCondition: 'Health below 50%, once per battle', description: 'Regains a portion of max Health.', sourceUrl: heroUrl(2, 'flint') }),
      skill({ id: 'heat-diffusion', name: 'Heat Diffusion', effectType: 'attack_speed', stat: 'normalAttackEffects', valuesByLevel: values([3, 4, 5, 6, 7]), description: 'Boosts Attack Speed.', sourceUrl: heroUrl(2, 'flint') }),
    ], heroWidget: widget('Dragonbane', heroUrl(2, 'flint'), [effect('allTroopsLethality', 60), effect('allTroopsHealth', 60), effect('allTroopsAttack', 15, 'rawStat', 'all', 'defense')], 'Dragonbreath increases Attack of defending Troop by 15%.') }),
    hero({ id: 'logan', name: 'Logan', troopType: 'infantry', generation: 3, baseStatsByStar: blankStars(), notes: ['Detailed skill/widget values need verification.'] }),
    hero({ id: 'ahmose', name: 'Ahmose', troopType: 'infantry', generation: 4, baseStatsByStar: blankStars(), notes: ['Detailed skill/widget values need verification.'] }),
    hero({ id: 'hector', name: 'Hector', troopType: 'infantry', generation: 5, baseStatsByStar: statsByStar('infantry', 444.35, 444.35, 111, 111), expeditionSkills: [
      skill({ id: 'sword-whirlwind', name: 'Sword Whirlwind', effectType: 'attack_speed', stat: 'normalAttackEffects', valuesByLevel: values([80, 90, 100, 110, 120]), duration: '4 seconds', description: 'Increases Attack Speed and grants control immunity.', sourceUrl: heroUrl(5, 'hector') }),
      skill({ id: 'desperado', name: 'Desperado', effectType: 'damage_taken_down', stat: 'damageTakenDown', valuesByLevel: values([20, 30, 40, 50, 60]), triggerCondition: 'Health under 50%', description: 'Reduces damage taken while low Health.', sourceUrl: heroUrl(5, 'hector') }),
      skill({ id: 'adrenaline-surge', name: 'Adrenaline Surge', effectType: 'attack_up', stat: 'infantryAttack', valuesByLevel: values([16, 24, 32, 40, 48]), triggerCondition: 'Health under 50%', description: 'Gains Attack when Health is under 50%.', sourceUrl: heroUrl(5, 'hector') }),
    ], heroWidget: widget('Steel Fangs', heroUrl(5, 'hector'), [effect('allTroopsLethality', 111), effect('allTroopsHealth', 111), effect('allTroopsAttack', 15, 'rawStat', 'all', 'defense')], 'Goliath increases Attack of defending Troop by 15%.') }),

    hero({ id: 'molly', name: 'Molly', troopType: 'lancer', generation: 1, baseStatsByStar: blankStars(), notes: ['Detailed skill/widget values need verification.'] }),
    hero({ id: 'mia', name: 'Mia', troopType: 'lancer', generation: 3, baseStatsByStar: statsByStar('lancer', 290.23, 290.23, 70, 70), expeditionSkills: [
      skill({ id: 'fates-finale', name: "Fate's Finale", effectType: 'damage_or_control', stat: 'conditionalEffects', valuesByLevel: values([270, 297, 324, 351, 378]), description: 'Deals damage and can reduce Attack or stun.', sourceUrl: heroUrl(3, 'mia') }),
      skill({ id: 'bad-omen', name: 'Bad Omen', effectType: 'fluctuating_damage', stat: 'roundBasedEffects', valuesByLevel: values([50, 55, 60, 65, 70]), description: 'Deals fluctuating Attack-scaled damage.', sourceUrl: heroUrl(3, 'mia') }),
      skill({ id: 'guardian-of-destiny', name: 'Guardian of Destiny', effectType: 'heal', stat: 'conditionalEffects', valuesByLevel: values([100, 110, 120, 130, 140]), description: 'Restores Health to the lowest Health hero.', sourceUrl: heroUrl(3, 'mia') }),
    ], heroWidget: widget('Fate Crystal', heroUrl(3, 'mia'), [effect('allTroopsLethality', 70), effect('allTroopsHealth', 70), effect('allTroopsAttack', 15, 'rawStat', 'all', 'rally')], 'Rally of Fate increases Attack of rallied Troop by 15%.') }),
    hero({ id: 'reina', name: 'Reina', troopType: 'lancer', generation: 4, baseStatsByStar: statsByStar('lancer', 370.29, 370.29, 92.5, 92.5), expeditionSkills: [
      skill({ id: 'phantom-assault', name: 'Phantom Assault', effectType: 'damage', stat: 'damageDealtUp', valuesByLevel: values([300, 330, 360, 390, 420]), description: 'Deals Attack-scaled area damage.', sourceUrl: heroUrl(4, 'reina') }),
      skill({ id: 'vanishing-technique', name: 'Vanishing Technique', effectType: 'dodge', stat: 'dodgeChance', valuesByLevel: values([5, 10, 15, 20, 25]), chance: 'listed value', description: 'Chance to dodge normal attack damage.', sourceUrl: heroUrl(4, 'reina') }),
      skill({ id: 'poison-of-demon', name: 'Poison of Demon', effectType: 'damage_control', stat: 'conditionalEffects', valuesByLevel: values([100, 110, 120, 130, 140]), description: 'Deals damage and immobilizes targets.', sourceUrl: heroUrl(4, 'reina') }),
    ], heroWidget: widget('Ninjaken - Raikiri', heroUrl(4, 'reina'), [effect('allTroopsLethality', 92.5), effect('allTroopsHealth', 92.5), effect('allTroopsLethality', 15, 'rawStat', 'all', 'rally')], 'Fiery Invasion increases Lethality of rallied Troop by 15%.') }),
    hero({ id: 'norah', name: 'Norah', aliases: ['Nora'], troopType: 'lancer', generation: 5, baseStatsByStar: statsByStar('lancer', 444.35, 444.35, 111, 111), expeditionSkills: [
      skill({ id: 'barrage', name: 'Barrage', effectType: 'damage', stat: 'damageDealtUp', valuesByLevel: values([60, 66, 72, 78, 84]), description: 'Five-grenade cascade against random target, heroes first.', sourceUrl: heroUrl(5, 'norah') }),
      skill({ id: 'flashbang', name: 'Flashbang', effectType: 'damage_control', stat: 'conditionalEffects', valuesByLevel: values([50, 55, 60, 65, 70]), duration: '1.5 seconds', description: 'Deals damage and stuns the target.', sourceUrl: heroUrl(5, 'norah') }),
      skill({ id: 'valkyrie-cry', name: 'Valkyrie Cry', effectType: 'attack_up', stat: 'allTroopsAttack', valuesByLevel: values([3, 3.5, 4, 4.5, 5]), description: 'Boosts Attack of all troops.', sourceUrl: heroUrl(5, 'norah') }),
    ], heroWidget: widget('Snow Cruiser', heroUrl(5, 'norah'), [effect('allTroopsLethality', 111), effect('allTroopsHealth', 111), effect('allTroopsDefense', 15, 'rawStat', 'all', 'defense')], 'True Grit boosts Defence of defending Troop by 15%.') }),
    hero({ id: 'wayne', name: 'Wayne', troopType: 'lancer', generation: 6, baseStatsByStar: statsByStar('lancer', 540.43, 540.43, 133.5, 133.5), expeditionSkills: [
      skill({ id: 'hurricane-blowback', name: 'Hurricane Blowback', effectType: 'damage', stat: 'damageDealtUp', valuesByLevel: values([100, 110, 120, 130, 140]), description: 'Boomerang deals area damage on throw and return.', sourceUrl: heroUrl(6, 'wayne') }),
      skill({ id: 'phantom-blitz', name: 'Phantom Blitz', effectType: 'extra_attack', stat: 'extraAttackChance', valuesByLevel: values([15, 20, 25, 30, 35]), description: 'Normal attacks can trigger another normal attack.', sourceUrl: heroUrl(6, 'wayne') }),
      skill({ id: 'noon-time', name: 'Noon Time', effectType: 'crit_rate', stat: 'extraDamageChance', valuesByLevel: values([3, 6, 9, 12, 15]), description: 'Grants Crit Rate when dealing damage.', sourceUrl: heroUrl(6, 'wayne') }),
    ], heroWidget: widget('Power Boomerang', heroUrl(6, 'wayne'), [effect('allTroopsLethality', 133.5), effect('allTroopsHealth', 133.5), effect('allTroopsLethality', 15, 'rawStat', 'all', 'defense')], 'Offensive Defense increases Lethality of defending Troop by 15%.', 'community'), notes: ['Prompt requests Wayne in the Lancer MVP list. h5joy labels Wayne as marksmen; keep this ambiguity visible in docs.'] }),

    hero({ id: 'bahiti', name: 'Bahiti', troopType: 'marksman', generation: 1, rarity: 'epic', dataConfidence: 'unverified', notes: ['Detailed page data needs verification.'] }),
    hero({ id: 'alonso', name: 'Alonso', troopType: 'marksman', generation: 2, baseStatsByStar: blankStars(), notes: ['Detailed skill/widget values need verification.'] }),
    hero({ id: 'greg', name: 'Greg', troopType: 'marksman', generation: 3, baseStatsByStar: blankStars(), notes: ['Detailed skill/widget values need verification.'] }),
    hero({ id: 'lynn', name: 'Lynn', troopType: 'marksman', generation: 4, baseStatsByStar: blankStars(), notes: ['Detailed skill/widget values need verification.'] }),
    hero({ id: 'gwen', name: 'Gwen', troopType: 'marksman', generation: 5, baseStatsByStar: statsByStar('marksman', 444.35, 444.35, 111, 111), expeditionSkills: [
      skill({ id: 'salvo', name: 'Salvo', effectType: 'damage_speed_down', stat: 'enemyDamageDealtDown', valuesByLevel: values([180, 198, 216, 234, 252]), duration: '2 seconds', description: 'Deals rear AoE damage and decreases target Attack Speed.', sourceUrl: heroUrl(5, 'gwen') }),
      skill({ id: 'sky-sniper', name: 'Sky Sniper', effectType: 'extra_damage', stat: 'extraDamageChance', valuesByLevel: values([100, 110, 120, 130, 140]), chance: '50% double damage', description: 'Precision strike with chance to deal double damage.', sourceUrl: heroUrl(5, 'gwen') }),
      skill({ id: 'hellfire', name: 'Hellfire', effectType: 'round_damage', stat: 'roundBasedEffects', valuesByLevel: values([35, 38.5, 42, 45.5, 49]), duration: '3 seconds', description: 'Burns enemy targets for damage per second.', sourceUrl: heroUrl(5, 'gwen') }),
    ], heroWidget: widget('Wings of Hope', heroUrl(5, 'gwen'), [effect('allTroopsLethality', 111), effect('allTroopsHealth', 111), effect('allTroopsLethality', 15, 'rawStat', 'all', 'rally')], 'Marauder boosts Lethality of rallied Troop by 15%.') }),
  ];

  window.WOS_HERO_DATABASE = heroes;
})();
