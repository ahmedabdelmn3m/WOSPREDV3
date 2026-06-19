# Hero Advisor Data Sources

Last checked: 2026-06-18

Primary MVP source:
- h5joy Whiteout Survival Hero Database: https://wos.h5joy-games.com/heroes/
- Confidence label used in app: `community`
- Reason: h5joy exposes public hero generation pages and individual hero pages with troop type, subclass, exploration stats, expedition stats, skills, and exclusive gear/widget sections. It is community-driven, so the data is not marked as official.

Implementation policy:
- Missing values remain `null`.
- Source values are stored in `frontend/src/data/heroDatabase.js`.
- Future manual corrections go under `manualOverrides`.
- Future battle-report calibration goes under `reportCalibration`.
- Source values should not be deleted when overrides/calibration are added.

## MVP Heroes

| Hero | Source URL | Populated | Missing / Notes | Confidence |
| --- | --- | --- | --- | --- |
| Jeronimo | https://wos.h5joy-games.com/heroes/s1/jeronimo/ | Gen 1, infantry, combat, 5-star/max visible expedition stats, skill text/values, widget notes | Exact base stats by stars 0-4 | community |
| Flint | https://wos.h5joy-games.com/heroes/s2/flint/ | Gen 2, infantry, combat, visible expedition stats, skills, widget notes | Exact base stats by stars 0-4 | community |
| Logan | https://wos.h5joy-games.com/heroes/s3/logan/ | Gen 3 infantry identity | Detailed skill/widget values still need extraction | community |
| Ahmose | https://wos.h5joy-games.com/heroes/s4/ahmose/ | Gen 4 infantry identity | Detailed skill/widget values still need extraction | community |
| Hector | https://wos.h5joy-games.com/heroes/s5/hector/ | Gen 5, infantry, combat, visible expedition stats, skills, widget notes | Exact base stats by stars 0-4 | community |
| Molly | https://wos.h5joy-games.com/heroes/s1/molly/ | Gen 1 lancer identity | Detailed skill/widget values still need extraction | community |
| Mia | https://wos.h5joy-games.com/heroes/s3/mia/ | Gen 3, lancer, combat, visible expedition stats, skills, widget notes | Exact base stats by stars 0-4 | community |
| Reina | https://wos.h5joy-games.com/heroes/s4/reina/ | Gen 4, lancer, combat, visible expedition stats, skills, widget notes | Exact base stats by stars 0-4 | community |
| Norah / Nora | https://wos.h5joy-games.com/heroes/s5/norah/ | Gen 5, lancer, combat, visible expedition stats, skills, widget notes, `Nora` alias | Exact base stats by stars 0-4 | community |
| Wayne | https://wos.h5joy-games.com/heroes/s6/wayne/ | Gen 6, visible stats, skills, widget notes | Source labels Wayne as marksmen, while prompt requests Wayne in Lancer MVP list. App keeps this ambiguity documented. | community |
| Bahiti | https://wos.h5joy-games.com/heroes/ | Marksman MVP slot placeholder | Detailed page data needs verification | unverified |
| Alonso | https://wos.h5joy-games.com/heroes/s2/alonso/ | Gen 2 marksman identity | Detailed skill/widget values still need extraction | community |
| Greg | https://wos.h5joy-games.com/heroes/s3/greg/ | Gen 3 marksman identity | Detailed skill/widget values still need extraction | community |
| Lynn | https://wos.h5joy-games.com/heroes/s4/lynn/ | Gen 4 marksman identity | Detailed skill/widget values still need extraction | community |
| Gwen | https://wos.h5joy-games.com/heroes/s5/gwen/ | Gen 5, marksman, combat, visible expedition stats, skills, widget notes | Exact base stats by stars 0-4 | community |

## Norah / Nora Spelling

The source page uses `Norah`. The app stores `aliases: ["Nora"]`, so user-facing matching can support both spellings.

## Jessie Exclusion

Jessie is excluded from Rally Leader MVP because she is mainly useful in Rally Joiner mode, not as a primary rally-leading lancer candidate. She can be added later to the Rally Joiner Advisor mode.

## Formation Profile Notes

The app calculates separate profile fields:
- raw troop stats: attack, defense, health, lethality by troop type and all-troops fields
- combat effects: damage dealt up, damage taken down, enemy damage changes, extra damage/attack chance, dodge, normal attack effects, round-based effects, conditional effects

The app compares formations by goal-specific profile indicators. These are comparative indicators, not battle results.

## Future Calibration

Battle report calibration should update:
- `reportCalibration.sampleSize`
- `reportCalibration.adjustedProfiles`
- `reportCalibration.confidence`
- `reportCalibration.notes`

Manual admin corrections should update:
- `manualOverrides.enabled`
- `manualOverrides.notes`
- `manualOverrides.overriddenFields`

Future logic should keep the baseline source data and layer calibrated assumptions on top.
