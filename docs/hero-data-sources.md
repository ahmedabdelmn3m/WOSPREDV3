# Hero Advisor Data Sources

Last checked: 2026-06-18

Primary MVP source:
- h5joy Whiteout Survival Hero Database: https://wos.h5joy-games.com/heroes/
- Confidence label used in app: `community`
- Reason: public, structured hero pages expose generation, troop type, subclass, exploration stats, expedition stats, skill text, and exclusive gear sections. The site states it is community-driven and fan-made, so this is not marked as official/wiki-verified.

Source policy:
- Store original source fields in `frontend/src/data/heroDatabase.js`.
- Store manual corrections separately in `manualOverrides`.
- Store future battle report changes separately in `reportCalibration`.
- Do not delete source values when calibration or admin corrections are added.

## Source Summary

| Hero | Source URL | Extracted | Missing | Confidence |
| --- | --- | --- | --- | --- |
| Sergey | https://wos.h5joy-games.com/heroes/ | Name, provisional troop type | Exact page, stats, skills, widget | unverified |
| Natalia | https://wos.h5joy-games.com/heroes/s1/natalia/ | Generation/type from Gen 1 list | Exact skills/widget not extracted | community |
| Jeronimo | https://wos.h5joy-games.com/heroes/s1/jeronimo/ | Generation, infantry type, combat subclass, exploration stats, expedition attack/defense, skills, widget name/effects | Full backend-calibrated role rating | community |
| Flint | https://wos.h5joy-games.com/heroes/s2/flint/ | Generation/type from Gen 2 list | Exact skills/widget not extracted | community |
| Logan | https://wos.h5joy-games.com/heroes/s3/logan/ | Generation/type from Gen 3 list | Exact skills/widget not extracted | community |
| Ahmose | https://wos.h5joy-games.com/heroes/s4/ahmose/ | Generation/type from Gen 4 list | Exact skills/widget not extracted | community |
| Hector | https://wos.h5joy-games.com/heroes/s5/hector/ | Generation, infantry type, combat subclass, exploration stats, expedition attack/defense, skill names/text/values, widget name/effects | Battle-report calibration | community |
| Jessie | https://wos.h5joy-games.com/heroes/ | Name, provisional lancer use | Exact page/type/stats/skills/widget | unverified |
| Jasser | https://wos.h5joy-games.com/heroes/ | Name, provisional lancer use | Exact page/type/stats/skills/widget | unverified |
| Molly | https://wos.h5joy-games.com/heroes/s1/molly/ | Generation/type from Gen 1 list | Exact skills/widget not extracted | community |
| Mia | https://wos.h5joy-games.com/heroes/s3/mia/ | Generation/type from Gen 3 list | Exact skills/widget not extracted | community |
| Reina | https://wos.h5joy-games.com/heroes/s4/reina/ | Generation, lancer type, combat subclass, exploration stats, expedition attack/defense, skill names/text/values, widget name/effects | Battle-report calibration | community |
| Wayne | https://wos.h5joy-games.com/heroes/s6/wayne/ | Generation, marksman type, combat subclass, exploration stats, expedition attack/defense, skill names/text/values, widget name/effects | Prompt listed Wayne as a lancer comparison, but source identifies marksman | community |
| Zinman | https://wos.h5joy-games.com/heroes/s1/zinman/ | Generation/type from Gen 1 list | Exact skills/widget not extracted | community |
| Bahiti | https://wos.h5joy-games.com/heroes/ | Name, provisional marksman use | Exact page, stats, skills, widget | unverified |
| Gina | https://wos.h5joy-games.com/heroes/ | Name, provisional marksman use | Exact page, stats, skills, widget | unverified |
| Alonso | https://wos.h5joy-games.com/heroes/s2/alonso/ | Generation/type from Gen 2 list | Exact skills/widget not extracted | community |
| Greg | https://wos.h5joy-games.com/heroes/s3/greg/ | Generation/type from Gen 3 list | Exact skills/widget not extracted | community |
| Lynn | https://wos.h5joy-games.com/heroes/s4/lynn/ | Generation/type from Gen 4 list | Exact skills/widget not extracted | community |
| Gwen | https://wos.h5joy-games.com/heroes/s5/gwen/ | Generation/type from Gen 5 list | Exact skills/widget not extracted | community |

## Notes

- h5joy's hero list documents generation groupings from Gen 1 through Gen 16 and links individual hero pages.
- Individual checked pages for Jeronimo, Hector, Reina, and Wayne expose the detailed fields currently populated in the MVP database.
- Fields not extracted are intentionally `null` or documented in `calibrationNotes`; no hidden percentages were invented.
- Wayne is stored as Marksman because the checked source page labels Wayne as marksmen.
- Zinman is stored as Marksman, not Lancer, pending any source that proves otherwise.

## Future Calibration Plan

Battle report calibration should not overwrite source data. It should update:

- `reportCalibration.sampleSize`
- `reportCalibration.adjustedRallyLeaderRating`
- `reportCalibration.confidence`
- `reportCalibration.notes`

Manual admin corrections should update:

- `manualOverrides.roleRatings`
- `manualOverrides.notes`

The advisor rule engine should prefer battle-report calibration first, manual overrides second, then the original source-based role ratings.
