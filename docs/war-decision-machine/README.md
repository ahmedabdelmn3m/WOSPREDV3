# War Decision Machine Update

This update turns the predictor into a scout-driven battle advisor.

The key idea is simple: scouts and screenshots are treated as input evidence, not perfect truth. The machine records what is known, what was extracted by OCR, what was manually confirmed, and what must be estimated.

## Included Files

- `docs/feature-plan.md` - product plan for scout OCR, enemy/self stats, march setup, and outcome prediction.
- `docs/scout-system-concept.md` - how city scouts, tile scouts, battle reports, and hidden stats should be handled.
- `schemas/battle-input.schema.json` - JSON shape for the full battle prediction request.
- `schemas/ocr-capture.schema.json` - JSON shape for OCR extraction from screenshots.
- `src/predictorEngine.ts` - starter TypeScript engine for normalization, risk scoring, and outcome bands.

## Main Flow

1. User uploads screenshots:
   - own stats
   - enemy scout
   - hero setup
   - troop formation
   - optional battle report
2. OCR extracts visible values.
3. User confirms/corrects uncertain OCR fields.
4. Predictor builds both sides:
   - known stats
   - estimated hidden stats
   - confidence level
5. Predictor returns:
   - win chance band
   - risk level
   - expected weak points
   - recommended action
   - hero/formation notes

## Important Design Rule

Never show a single exact prediction without confidence.

The tool should say:

> Based on visible scout data and current assumptions, this is a likely win, but confidence is medium because enemy research/gear/buffs are hidden.

That is much more realistic for war decisions.
