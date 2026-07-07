# Feature Plan: Scout OCR Battle Predictor

## Goal

Build a realistic war-decision machine for PvP and rallies. The user should be able to upload scouts and stat screenshots, let OCR extract the data, choose heroes/troops/formation, and receive a practical battle outcome.

## User Inputs

### Own Side

- Player name
- Furnace / fire crystal level
- March capacity
- Rally capacity, if rallying
- Troop counts by type and tier
- Infantry / lancer / marksman battle stats
- Hero lineup
- Hero level, stars, skill levels, and generation
- Chief gear and charms, if visible or manually entered
- Hero gear, if visible or manually entered
- Pets, island, alliance tech, temporary buffs, if known

### Enemy Side

- Scout type: city scout, gathering tile scout, facility scout, battle report
- Enemy name
- Enemy furnace / fire crystal level, if visible
- Enemy troop counts from scout
- Enemy reinforcement count, if visible
- Enemy heroes, if visible
- Enemy visible buffs, if visible
- Enemy profile power and hero power, if known
- Any known history from previous fights

### March Setup

- Battle mode: solo attack, city rally, tile hit, defense, facility fight
- Selected heroes
- Troop ratio
- Troop tiers included
- Formation profile:
  - balanced
  - infantry-heavy
  - marksman-heavy
  - lancer-heavy
  - shield-and-burn
  - cleanup
- Rally landing time, if rallying
- Joiner quality, if rallying

## OCR Screens

The first OCR version should support structured extraction from:

- scout report screenshots
- player stats screenshots
- hero lineup screenshots
- march formation screenshots
- battle report screenshots

OCR should return both values and confidence. Any field below the confidence threshold should be marked for manual confirmation.

## Prediction Output

The predictor should return:

- outcome band:
  - strong win
  - likely win
  - close fight
  - risky
  - likely loss
  - avoid
- confidence:
  - high
  - medium
  - low
- risk reasons
- strongest advantage
- biggest weakness
- recommended action:
  - solo
  - rally
  - sync rallies
  - swap heroes
  - change troop ratio
  - avoid
- suggested hero replacements
- suggested troop ratio
- rally timing warning, if relevant

## Realism Rules

- Scout data is visible evidence, not full truth.
- Enemy research, chief gear, hero gear, pets, charms, alliance tech, skins, city buffs, and temporary buffs may be hidden.
- The model must estimate hidden enemy strength from profile power, furnace level, hero generation, visible heroes, and server age.
- A gathering tile scout only predicts a tile hit. It should not be reused as a city-defense prediction.
- City scouts are useful for city hits and rallies, but still do not expose the full hidden stat stack.
- Battle reports are the strongest learning source and should gradually calibrate the estimator.

## First Implementation Milestones

1. Add OCR capture model and manual correction UI.
2. Add battle input model for own side, enemy side, march, and context.
3. Add deterministic first-pass predictor.
4. Add hidden-stat uncertainty and confidence penalties.
5. Add hero/formation recommendation rules.
6. Add battle report calibration later when enough reports exist.
