# CI Prototype Run Report (2026-03-25)

This report is generated from a local dry-run of the new CI runner:

```bash
python scripts/run_example.py <example> --version stable --output artifacts/local-ci-results/<example>_stable.json
```

- Total examples discovered: **32**
- Passed: **8**
- Failed: **24**
- Skipped: **0**

## ✅ Successes
- `examples/conways_game_of_life_fast`
- `gis/agents_and_networks`
- `gis/geo_schelling`
- `gis/geo_schelling_points`
- `gis/geo_sir`
- `gis/population`
- `gis/rainfall`
- `gis/urban_growth`

## ❌ Failures
- `examples/aco_tsp` — Traceback (most recent call last):
- `examples/bank_reserves` — Traceback (most recent call last):
- `examples/boltzmann_wealth_model_network` — Traceback (most recent call last):
- `examples/caching_and_replay` — Traceback (most recent call last):
- `examples/charts` — Traceback (most recent call last):
- `examples/color_patches` — Traceback (most recent call last):
- `examples/deffuant_weisbuch` — Traceback (most recent call last):
- `examples/dining_philosophers` — Traceback (most recent call last):
- `examples/el_farol/el_farol` — attempted relative import with no known parent package
- `examples/emperor_dilemma` — Traceback (most recent call last):
- `examples/forest_fire` — Traceback (most recent call last):
- `examples/hex_ant` — Traceback (most recent call last):
- `examples/hex_snowflake` — Traceback (most recent call last):
- `examples/hotelling_law` — Traceback (most recent call last):
- `examples/humanitarian_aid_distribution` — Traceback (most recent call last):
- `examples/mmc_queue` — No module named 'mesa.experimental.scenarios'
- `examples/rumor_mill` — Traceback (most recent call last):
- `examples/shape_example` — Traceback (most recent call last):
- `examples/termites` — Traceback (most recent call last):
- `examples/virus_antibody` — Traceback (most recent call last):
- `examples/warehouse` — Traceback (most recent call last):
- `rl/boltzmann_money` — No Model class found. Add run.py for reliable execution.
- `rl/epstein_civil_violence` — attempted relative import with no known parent package
- `rl/wolf_sheep` — Traceback (most recent call last):
