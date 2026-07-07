# Integration Notes

## Where This Fits

Add the feature as a new pipeline:

1. `UploadScreens`
2. `RunOcr`
3. `ReviewExtractedFields`
4. `BuildBattleInput`
5. `PredictOutcome`
6. `ShowWarDecision`

## Suggested UI Sections

- Own stats
- Enemy scout
- Enemy uncertainty
- March setup
- Heroes
- Troop formation
- Result

## OCR Review Behavior

Do not trust OCR blindly.

If OCR confidence is below `0.85`, show the value for review. If the field affects battle outcome strongly, show it for review even when OCR confidence is higher.

High-impact fields:

- troop counts
- troop tier
- infantry/lancer/marksman attack
- infantry/lancer/marksman defense
- infantry/lancer/marksman health
- infantry/lancer/marksman lethality
- hero names
- hero stars
- hero skill levels
- scout type
- reinforcement count

## Prediction Display

Recommended result card:

- Outcome: likely win / close fight / risky / avoid
- Win chance band
- Confidence
- Main reason
- Hidden risk
- Recommended action
- Best hero or troop change

Avoid presenting the result as exact truth. Use bands and confidence.

## Backend Shape

The backend endpoint can be:

`POST /api/predict-battle`

Request body:

`BattleInput`

Response body:

`PredictionResult`

## Next Data Tables To Add

- hero database by generation
- hero expedition skill modifiers
- troop tier modifiers
- research modifier ranges by furnace/fire crystal level
- chief gear modifier ranges
- chief charm modifier ranges
- pet modifier ranges
- temporary buff list
- rally joiner hero rules

## Later Learning Layer

When battle reports are available, store:

- input assumptions
- actual result
- killed/wounded/lost
- enemy visible stats
- own visible stats
- hero lineups
- troop ratios
- timestamp

Then adjust hidden-stat estimates using the difference between prediction and actual outcome.
