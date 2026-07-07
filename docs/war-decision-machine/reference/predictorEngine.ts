export type Confidence = "high" | "medium" | "low";
export type BattleMode =
  | "solo_city_attack"
  | "city_rally"
  | "tile_hit"
  | "facility_fight"
  | "defense";

export type Formation =
  | "balanced"
  | "infantry_heavy"
  | "lancer_heavy"
  | "marksman_heavy"
  | "defensive"
  | "burst"
  | "cleanup";

export interface CombatStats {
  infantryAttack?: number;
  infantryDefense?: number;
  infantryHealth?: number;
  infantryLethality?: number;
  lancerAttack?: number;
  lancerDefense?: number;
  lancerHealth?: number;
  lancerLethality?: number;
  marksmanAttack?: number;
  marksmanDefense?: number;
  marksmanHealth?: number;
  marksmanLethality?: number;
}

export interface TroopMix {
  infantry?: number;
  lancer?: number;
  marksman?: number;
  highestTier?: string;
}

export interface Hero {
  name: string;
  type: "infantry" | "lancer" | "marksman";
  generation?: number;
  level?: number;
  stars?: number;
  skillLevels?: number[];
  role?: "leader" | "joiner" | "defender" | "replacement";
}

export interface BattleSide {
  name: string;
  furnaceLevel?: string;
  profilePower?: number;
  sourceType?: "manual" | "ocr" | "city_scout" | "tile_scout" | "battle_report" | "estimated";
  sourceConfidence?: Confidence;
  stats: CombatStats;
  troops: TroopMix;
  heroes?: Hero[];
  unknowns?: string[];
}

export interface BattleInput {
  battleMode: BattleMode;
  attacker: BattleSide;
  defender: BattleSide;
  march: {
    heroes: Hero[];
    troops: TroopMix;
    formation: Formation;
    marchCapacity?: number;
    rallyCapacity?: number;
    targetLandingTime?: string;
  };
  context?: {
    serverAgeDays?: number;
    availableHeroGeneration?: number;
    hasCityBuff?: boolean;
    hasAttackBuff?: boolean;
    hasDefenseBuff?: boolean;
    notes?: string;
  };
}

export interface PredictionResult {
  outcome:
    | "strong_win"
    | "likely_win"
    | "close_fight"
    | "risky"
    | "likely_loss"
    | "avoid";
  winChanceBand: string;
  confidence: Confidence;
  attackScore: number;
  defenseScore: number;
  riskReasons: string[];
  advantages: string[];
  recommendations: string[];
}

const UNKNOWN_RISK_WEIGHT: Record<string, number> = {
  research: 10,
  chief_gear: 10,
  chief_charms: 8,
  hero_gear: 8,
  pets: 5,
  alliance_tech: 6,
  temporary_buffs: 10,
  reinforcements: 14,
  skins: 3,
  city_bonuses: 6
};

export function predictBattle(input: BattleInput): PredictionResult {
  const attackScore = sidePowerScore(input.attacker, input.march.troops, input.march.heroes, input.march.formation, "attack");
  const defenseScore = sidePowerScore(input.defender, input.defender.troops, input.defender.heroes ?? [], "defensive", "defense");
  const hiddenRisk = hiddenStatRisk(input.defender);
  const scoutPenalty = scoutContextPenalty(input);
  const adjustedDefenseScore = defenseScore * (1 + (hiddenRisk + scoutPenalty) / 100);
  const ratio = attackScore / Math.max(adjustedDefenseScore, 1);
  const confidence = confidenceFromRisk(hiddenRisk + scoutPenalty, input.defender.sourceConfidence);

  const riskReasons = buildRiskReasons(input, hiddenRisk, scoutPenalty);
  const advantages = buildAdvantages(input, ratio);
  const recommendations = buildRecommendations(input, ratio, hiddenRisk + scoutPenalty);

  return {
    outcome: outcomeFromRatio(ratio, hiddenRisk + scoutPenalty),
    winChanceBand: winChanceBandFromRatio(ratio, hiddenRisk + scoutPenalty),
    confidence,
    attackScore: Math.round(attackScore),
    defenseScore: Math.round(adjustedDefenseScore),
    riskReasons,
    advantages,
    recommendations
  };
}

function sidePowerScore(
  side: BattleSide,
  troops: TroopMix,
  heroes: Hero[],
  formation: Formation,
  purpose: "attack" | "defense"
): number {
  const troopScore = troopMassScore(troops);
  const statScore = combatStatScore(side.stats, purpose);
  const heroScore = heroLineupScore(heroes);
  const formationScore = formationModifier(formation, troops);
  const sourceModifier = side.sourceConfidence === "high" ? 1 : side.sourceConfidence === "medium" ? 0.96 : 0.9;

  return troopScore * statScore * heroScore * formationScore * sourceModifier;
}

function troopMassScore(troops: TroopMix): number {
  const infantry = troops.infantry ?? 0;
  const lancer = troops.lancer ?? 0;
  const marksman = troops.marksman ?? 0;
  const tierBoost = tierModifier(troops.highestTier);

  return (infantry * 1.08 + lancer * 1.0 + marksman * 1.03) * tierBoost;
}

function combatStatScore(stats: CombatStats, purpose: "attack" | "defense"): number {
  const attack =
    avg([stats.infantryAttack, stats.lancerAttack, stats.marksmanAttack]) +
    avg([stats.infantryLethality, stats.lancerLethality, stats.marksmanLethality]) * 0.85;
  const defense =
    avg([stats.infantryDefense, stats.lancerDefense, stats.marksmanDefense]) +
    avg([stats.infantryHealth, stats.lancerHealth, stats.marksmanHealth]) * 0.9;

  const combined = purpose === "attack" ? attack * 0.6 + defense * 0.4 : defense * 0.6 + attack * 0.4;
  return 1 + Math.max(combined, 0) / 1000;
}

function heroLineupScore(heroes: Hero[]): number {
  if (!heroes.length) return 1;

  const score = heroes.reduce((sum, hero, index) => {
    const generation = hero.generation ?? 1;
    const stars = hero.stars ?? 0;
    const level = hero.level ?? 1;
    const skills = hero.skillLevels?.length ? avg(hero.skillLevels) : 1;
    const leaderWeight = index === 0 || hero.role === "leader" ? 1.35 : 1;

    return sum + (1 + generation * 0.07 + stars * 0.06 + level / 1000 + skills * 0.035) * leaderWeight;
  }, 0);

  return 1 + score / 12;
}

function formationModifier(formation: Formation, troops: TroopMix): number {
  const total = (troops.infantry ?? 0) + (troops.lancer ?? 0) + (troops.marksman ?? 0);
  if (!total) return 0.8;

  const infantryRatio = (troops.infantry ?? 0) / total;
  const lancerRatio = (troops.lancer ?? 0) / total;
  const marksmanRatio = (troops.marksman ?? 0) / total;

  if (formation === "balanced") return 1;
  if (formation === "defensive") return 1 + Math.min(infantryRatio, 0.5) * 0.16;
  if (formation === "burst") return 1 + Math.min(marksmanRatio + lancerRatio, 0.7) * 0.12;
  if (formation === "cleanup") return 0.98 + Math.min(marksmanRatio, 0.5) * 0.1;
  if (formation === "infantry_heavy") return infantryRatio >= 0.45 ? 1.08 : 0.96;
  if (formation === "lancer_heavy") return lancerRatio >= 0.35 ? 1.06 : 0.96;
  if (formation === "marksman_heavy") return marksmanRatio >= 0.35 ? 1.06 : 0.96;

  return 1;
}

function hiddenStatRisk(defender: BattleSide): number {
  const unknowns = defender.unknowns ?? [];
  return unknowns.reduce((sum, key) => sum + (UNKNOWN_RISK_WEIGHT[key] ?? 4), 0);
}

function scoutContextPenalty(input: BattleInput): number {
  if (input.battleMode === "tile_hit" && input.defender.sourceType === "tile_scout") return 0;
  if (input.battleMode !== "tile_hit" && input.defender.sourceType === "tile_scout") return 25;
  if (input.defender.sourceType === "city_scout") return 8;
  if (input.defender.sourceType === "battle_report") return -8;
  return 12;
}

function confidenceFromRisk(risk: number, sourceConfidence?: Confidence): Confidence {
  if (risk >= 45 || sourceConfidence === "low") return "low";
  if (risk >= 20 || sourceConfidence === "medium") return "medium";
  return "high";
}

function outcomeFromRatio(ratio: number, risk: number): PredictionResult["outcome"] {
  if (risk > 65 && ratio < 1.5) return "avoid";
  if (ratio >= 1.45) return "strong_win";
  if (ratio >= 1.18) return "likely_win";
  if (ratio >= 0.95) return "close_fight";
  if (ratio >= 0.78) return "risky";
  return "likely_loss";
}

function winChanceBandFromRatio(ratio: number, risk: number): string {
  const raw = Math.round((ratio / (ratio + 1)) * 100 - Math.min(risk * 0.25, 18));
  const center = Math.max(5, Math.min(95, raw));
  const spread = risk > 45 ? 18 : risk > 20 ? 12 : 8;
  return `${Math.max(1, center - spread)}-${Math.min(99, center + spread)}%`;
}

function buildRiskReasons(input: BattleInput, hiddenRisk: number, scoutPenalty: number): string[] {
  const reasons: string[] = [];

  if (input.defender.unknowns?.length) {
    reasons.push(`Enemy hidden stats not confirmed: ${input.defender.unknowns.join(", ")}.`);
  }
  if (input.battleMode !== "tile_hit" && input.defender.sourceType === "tile_scout") {
    reasons.push("Tile scout cannot represent full city defense.");
  }
  if (input.defender.sourceType === "city_scout") {
    reasons.push("City scout is useful, but research, gear, buffs, pets, and reinforcement changes may still be hidden.");
  }
  if (hiddenRisk + scoutPenalty >= 45) {
    reasons.push("Prediction confidence is reduced because invisible enemy strength can change the result.");
  }

  return reasons;
}

function buildAdvantages(input: BattleInput, ratio: number): string[] {
  const advantages: string[] = [];
  const marchTroops = input.march.troops;
  const total = (marchTroops.infantry ?? 0) + (marchTroops.lancer ?? 0) + (marchTroops.marksman ?? 0);

  if (ratio > 1.15) advantages.push("Visible attacker strength is above adjusted defender estimate.");
  if (total > 0 && (marchTroops.infantry ?? 0) / total >= 0.45) {
    advantages.push("Infantry-heavy front line improves survival in longer fights.");
  }
  if (input.march.heroes.some((hero) => hero.role === "leader")) {
    advantages.push("Leader hero is explicitly selected, so hero scoring can be more reliable.");
  }

  return advantages;
}

function buildRecommendations(input: BattleInput, ratio: number, risk: number): string[] {
  const recommendations: string[] = [];

  if (ratio < 0.95) recommendations.push("Do not solo with this setup; use rally support or change target.");
  if (ratio >= 0.95 && ratio < 1.18) recommendations.push("Treat as close. Improve hero lineup, add buffs, or sync a rally.");
  if (risk >= 45) recommendations.push("Collect profile screenshots or previous battle reports before committing important troops.");
  if (input.battleMode === "city_rally") recommendations.push("Confirm rally leader heroes and joiner first heroes before launch.");
  if (input.battleMode !== "tile_hit" && input.defender.sourceType === "tile_scout") {
    recommendations.push("Run a city scout before making a city-hit decision.");
  }
  if (input.march.formation === "balanced") recommendations.push("Test infantry-heavy and burst variants; compare outcome bands before attacking.");

  return recommendations;
}

function tierModifier(tier?: string): number {
  if (!tier) return 1;
  const match = tier.match(/\d+/);
  const numericTier = match ? Number(match[0]) : 1;
  return 1 + Math.max(0, numericTier - 1) * 0.045;
}

function avg(values: Array<number | undefined>): number {
  const present = values.filter((value): value is number => typeof value === "number" && Number.isFinite(value));
  if (!present.length) return 0;
  return present.reduce((sum, value) => sum + value, 0) / present.length;
}
