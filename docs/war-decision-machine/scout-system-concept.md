# Scout System Concept

## Scout Is Evidence, Not Complete Truth

The predictor should not assume a scout shows every combat factor. A scout gives visible details about a target, but many of the most important war stats can remain hidden or only partially inferred.

Hidden or partially hidden factors can include:

- research progress
- chief gear
- chief charms
- hero gear
- hero skill levels
- pets
- alliance technology
- temporary battle buffs
- city defense bonuses
- skins and collection bonuses
- reinforcements arriving after the scout
- march changes after the scout

## Scout Types

### City Scout

Use for:

- city hits
- city rallies
- zeroing decisions
- trap-risk checks
- reinforcement checks

City scout data should be connected to city-defense prediction, but the result must include an uncertainty penalty for hidden stats.

### Gathering Tile Scout

Use for:

- resource tile hits
- exposed march checks

A tile scout should only describe the troops/heroes on that tile. It should not be used to predict the full city defense of the enemy.

### Battle Report

Use for:

- model calibration
- hidden strength estimation
- hero matchup learning
- casualty pattern learning

Battle reports are more valuable than scouts because they reveal actual performance after hidden stats are applied.

## Data Quality Levels

Every field should have a source:

- `ocr` - extracted from screenshot
- `manual` - typed or corrected by user
- `scout` - visible in scout report
- `profile` - taken from player profile
- `battle_report` - taken from previous combat
- `estimated` - inferred by the machine

Every field should also have confidence:

- `high` - visible and confirmed
- `medium` - OCR/readable but not confirmed
- `low` - estimated or incomplete

## Practical Prediction Rule

The tool should be comfortable saying:

> You may win based on visible scout data, but the hidden-stat risk is high. Use a rally or wait for more information.

That honesty makes it useful in real war.
