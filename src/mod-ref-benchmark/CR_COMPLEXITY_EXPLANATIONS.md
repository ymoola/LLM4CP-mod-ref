# CR Complexity Explanations

This file explains how the stored complexity counts were derived for each CR.

Scope:
- `base_model.decision_variable_count`
- `base_model.constraint_count`
- `cr_impact.affected_decision_variables`
- `cr_impact.affected_constraints`

Counting convention:
- Decision-variable counts are scalar counts after expanding vector/matrix families.
- Constraint counts are scalar counts produced by the loops/comprehensions in the model code.
- `cr_impact` counts only the variables and constraints directly touched by the CR logic.

## Problem 1

### CR1
- Base DV `60`: `sequence` has length `n_cars=10`; `setup` has shape `10 x 5`, so `10 + 50 = 60`.
- Base constraints `88`: demand `6` + option-consistency `10 x 5 = 50` + capacity windows `(10-2) + (10-3) + (10-3) + (10-5) + (10-5) = 32`; total `6 + 50 + 32 = 88`.
- Impact DV `10`: the new adjacency rule uses only `sequence`, so the affected family is the full `sequence` vector of length `10`.
- Impact constraints `9`: one `sequence[s] != sequence[s+1]` per adjacent pair, so `n_cars - 1 = 9`.

### CR2
- Base DV `60`: same base model as CR1, so `sequence 10 + setup 50 = 60`.
- Base constraints `88`: same base model as CR1, so `6 + 50 + 32 = 88`.
- Impact DV `10`: the spacing rule is expressed on `sequence`, so the affected family is the full length-`10` sequence vector.
- Impact constraints `6`: one sliding-window constraint per car type. With `n_types=6` and `n_cars-gap_limit = 10-9 = 1`, the count is `6 x 1 = 6`.

### CR3
- Base DV `96`: `sequence` has length `n_cars=16`; `setup` has shape `16 x 5`, so `16 + 80 = 96`.
- Base constraints `152`: demand `6` + option-consistency `16 x 5 = 80` + capacity windows `(16-2) + (16-2) + (16-3) + (16-3) + (16-4) = 66`; total `6 + 80 + 66 = 152`.
- Impact DV `160`: the softened capacity rule directly uses existing `setup` (`16 x 5 = 80`) and new `viol` (`5 x 16 = 80`); total `160`.
- Impact constraints `66`: the CR keeps the same window structure, so the touched capacity-window family still contributes `66` constraints.

## Problem 2

### CR1
- Base DV `30`: `production` has length `n_templates=3`; `layout` has shape `3 x 9`, so `3 + 27 = 30`.
- Base constraints `12`: slot-fill `3` + demand `9`; total `12`.
- Impact DV `3`: the load-balancing rule uses only `production`, so the affected family is the length-`3` production vector.
- Impact constraints `9`: the rule is added for every ordered template pair, so `n_templates x n_templates = 3 x 3 = 9`.

### CR2
- Base DV `16`: `production` has length `2`; `layout` has shape `2 x 7`, so `2 + 14 = 16`.
- Base constraints `9`: slot-fill `2` + demand `7`; total `9`.
- Impact DV `14`: the diversity rule is expressed on `layout`, so the affected family is the `2 x 7 = 14` layout matrix.
- Impact constraints `2`: one diversity constraint per template, so `n_templates = 2`.

### CR3
- Base DV `16`: same base model as CR2, so `production 2 + layout 14 = 16`.
- Base constraints `9`: same base model as CR2, so `2 + 7 = 9`.
- Impact DV `3`: the new `max_load` scalar is added and the objective is rewritten around it, so the affected families are `production` (`2`) and `max_load` (`1`); total `3`.
- Impact constraints `2`: one `production[i] <= max_load` per template, so `n_templates = 2`.

## Problem 3

### CR1
- Base DV `2503`: the only decision family is `x`, one Boolean per candidate shift.
- Base constraints `53`: one exact-cover constraint per task, so `n_tasks = 53`.
- Impact DV `2503`: the coverage constraints are changed from `== 1` to `== 2`, but they still use the full `x` vector.
- Impact constraints `53`: one modified coverage constraint per task.

### CR2
- Base DV `77`: the only decision family is `x`, one Boolean per candidate shift.
- Base constraints `24`: one exact-cover constraint per task, so `n_tasks = 24`.
- Impact DV `77`: the objective change still uses the full `x` vector.
- Impact constraints `0`: this CR changes only the objective, not the constraints.

### CR3
- Base DV `25`: the only decision family is `x`, one Boolean per candidate shift.
- Base constraints `23`: one exact-cover constraint per task, so `n_tasks = 23`.
- Impact DV `25`: the new duration-budget constraint uses the full `x` vector.
- Impact constraints `1`: one global budget constraint `sum(x[i] * duration[i]) <= H`.

## Problem 4

### CR1
- Base DV `25`: `w` has length `n_stores=10`; `o` has length `n_warehouses=5`; `c` has length `10`; total `10 + 5 + 10 = 25`.
- Base constraints `25`: capacity `5` + open-warehouse assignment `10` + supply-cost definitions `10`; total `25`.
- Impact DV `15`: the profit objective directly uses `o` (`5`) and `c` (`10`); total `15`.
- Impact constraints `0`: this CR changes only the objective.

### CR2
- Base DV `25`: same base model as CR1, so `10 + 5 + 10 = 25`.
- Base constraints `25`: same base model as CR1, so `5 + 10 + 10 = 25`.
- Impact DV `10`: the feasible-region rule is written on `w`, so the affected family is the length-`10` assignment vector.
- Impact constraints `10`: one disallowance constraint per store.

### CR3
- Base DV `25`: same base model as CR1, so `10 + 5 + 10 = 25`.
- Base constraints `25`: same base model as CR1, so `5 + 10 + 10 = 25`.
- Impact DV `15`: the CR adds `u` of length `5` and rewrites capacity via `w`, so the affected families are `w` (`10`) and `u` (`5`).
- Impact constraints `5`: one rewritten capacity constraint per warehouse.

## Problem 5

### CR1
- Base DV `9`: the only decision family is `digits`, a length-`9` vector.
- Base constraints `2`: `AllDifferent(digits)` plus the main arithmetic equality.
- Impact DV `9`: the CR still uses only the `digits` vector.
- Impact constraints `6`: the single arithmetic equality is replaced by six permuted equalities.

### CR2
- Base DV `9`: the only decision family is `digits`, a length-`9` vector.
- Base constraints `2`: `AllDifferent(digits)` plus the main arithmetic equality.
- Impact DV `9`: the denominator ordering constraints still use the same `digits` vector.
- Impact constraints `2`: `BC < EF` and `EF < HI`.

## Problem 6

### CR1
- Base DV `142`: `state` has shape `(n+1) x T = 6 x 16 = 96`; `move` has shape `(T-1) x 2 = 15 x 2 = 30`; `done` has length `16`; total `96 + 30 + 16 = 142`.
- Base constraints `283`: table-fixed `16` + initial-state `5` + goal-state `5` + done-definition `16` + monotonicity `1` + per-transition rules over `15` steps:
  - noop destination `15`
  - freeze state after done `15`
  - freeze move after done `15`
  - moved block changes destination `15`
  - only moved block changes `5 x 15 = 75`
  - moved block free `5 x 15 = 75`
  - destination free `15`
  - pile limit `15`
  - total `16 + 5 + 5 + 16 + 1 + 15 + 15 + 15 + 15 + 75 + 75 + 15 + 15 = 283`
- Impact DV `112`: the new table-limit rule reads `state` (`96`) and `done` (`16`), so the affected families sum to `112`.
- Impact constraints `15`: one extra implication per transition step `t=1..15`.

## Problem 7

### CR1
- Base DV `45`: only `g`, with shape `n_rounds x n_players = 5 x 9 = 45`.
- Base constraints `375`: group-size constraints `5 x 3 = 15` plus pairwise no-repeat constraints `n_pairs x C(n_rounds, 2) = 36 x 10 = 360`; total `375`.
- Impact DV `333`: the CR introduces helper families around the existing schedule:
  - `g`: `45`
  - `meet`: `5 x 36 = 180`
  - `pair_count`: `36`
  - `repeats`: `36`
  - `has_meeting`: `36`
  - total `45 + 180 + 36 + 36 + 36 = 333`
- Impact constraints `648`: the mixed count includes the removed no-repeat family and the new tracking objective machinery:
  - removed no-repeat constraints `36 x 10 = 360`
  - `meet[r,k] == ...`: `36 x 5 = 180`
  - `pair_count[k] == ...`: `36`
  - `has_meeting[k] == ...`: `36`
  - `repeats[k] == ...`: `36`
  - total `360 + 180 + 36 + 36 + 36 = 648`

### CR2
- Base DV `280`: only `g`, with shape `10 x 28 = 280`.
- Base constraints `17030`: group-size constraints `10 x 2 = 20` plus no-repeat pair constraints `378 x 45 = 17010`; total `17030`.
- Impact DV `280`: the new lower-bound rule uses only `g`, so the affected family is the full `g` matrix.
- Impact constraints `378`: one `sum(g[r, p1] == g[r, p2]) >= 2` per golfer pair.

### CR3
- Base DV `96`: only `g`, with shape `4 x 24 = 96`.
- Base constraints `1672`: group-size constraints `4 x 4 = 16` plus no-repeat pair constraints `276 x 6 = 1656`; total `1672`.
- Impact DV `1476`: the CR adds conceptual helper families around the existing schedule:
  - `g`: `96`
  - `meet`: `276 x 4 = 1104`
  - `met_pair`: `276`
  - total `96 + 1104 + 276 = 1476`
- Impact constraints `3060`: the mixed count includes the removed no-repeat family plus the new tracking and fairness constraints:
  - removed no-repeat constraints `276 x 6 = 1656`
  - `meet[r] == ...`: `276 x 4 = 1104`
  - `met_pair[k] == ...`: `276`
  - fairness lower bounds: `24`
  - total `1656 + 1104 + 276 + 24 = 3060`

## Problem 8

### CR1
- Base DV `5`: only `s`, the start-time vector of length `n_jobs=5`.
- Base constraints `6`: precedence constraints `5` plus one `Cumulative(...)` call for the single resource.
- Impact DV `11`: the CR adds `tardiness` of length `5` and `total_tardiness` as a scalar, alongside the existing `s`; total `5 + 5 + 1 = 11`.
- Impact constraints `6`: one tardiness lower-bound per job `5` plus one total-tardiness aggregation equality `1`.

### CR2
- Base DV `11`: only `s`, length `n_jobs=11`.
- Base constraints `17`: precedence constraints `15` plus two `Cumulative(...)` calls for the two active resources.
- Impact DV `11`: the max-delay rule is still written only on `s`, so the affected family is the full start-time vector.
- Impact constraints `15`: one max-delay bound per listed precedence arc, and the instance lists `15` arcs.

### CR3
- Base DV `8`: only `s`, length `n_jobs=8`.
- Base constraints `12`: precedence constraints `10` plus two `Cumulative(...)` calls for the two active resources.
- Impact DV `8`: the maintenance-window disjunctions are written on `s`, so the affected family is the full start-time vector.
- Impact constraints `12`: two maintenance windows, each affecting six jobs, so `6 + 6 = 12`.

## Problem 9

### CR1
- Base DV `20`: only `x` and `y`, each a length-`10` vector, so `10 + 10 = 20`.
- Base constraints `65`: deck-boundary constraints `2 x 10 = 20` plus pairwise separation constraints `C(10,2) = 45`; total `65`.
- Impact DV `50`: the CR adds `rot`, `eff_w`, and `eff_l` and still uses `x` and `y`; total `10 + 10 + 10 + 10 + 10 = 50`.
- Impact constraints `85`: effective-dimension equations `10 + 10`, rewritten boundary constraints `20`, and rewritten pairwise separation constraints `45`; total `85`.

### CR2
- Base DV `10`: only `x` and `y`, each a length-`5` vector, so `5 + 5 = 10`.
- Base constraints `20`: deck-boundary constraints `2 x 5 = 10` plus pairwise separation constraints `C(5,2) = 10`; total `20`.
- Impact DV `10`: the restricted-region rules are written on the existing `x` and `y` vectors.
- Impact constraints `10`: one region-avoidance disjunction per container-region pair, so `5 x 2 = 10`.

### CR3
- Base DV `12`: only `x` and `y`, each a length-`6` vector, so `6 + 6 = 12`.
- Base constraints `27`: deck-boundary constraints `2 x 6 = 12` plus pairwise separation constraints `C(6,2) = 15`; total `27`.
- Impact DV `19`: the CR adds `load` of length `6` and `total_value` as a scalar, alongside `x` and `y`; total `6 + 6 + 6 + 1 = 19`.
- Impact constraints `28`: conditional boundary constraints `12`, conditional pairwise separation constraints `15`, and one value-aggregation equality `1`; total `28`.

## Problem 10

### CR1
- Base DV `18`: `p` has length `n_patients=12`; `w` has length `n_nurses=6`; total `12 + 6 = 18`.
- Base constraints `72`: patient-count lower bounds `6`, patient-count upper bounds `6`, cross-zone one-zone-per-nurse inequalities `48`, workload equalities `6`, and workload upper bounds `6`; total `72`.
- Impact DV `20`: the CR adds `total_workload` and `variance_numerator` scalars, while still using `p` and `w`; total `12 + 6 + 1 + 1 = 20`.
- Impact constraints `8`: workload-definition equalities are modified `6`, plus `total_workload == sum(w)` `1` and `variance_numerator == ...` `1`; total `8`.

### CR2
- Base DV `12`: `p` has length `8`; `w` has length `4`; total `8 + 4 = 12`.
- Base constraints `37`: patient-count lower bounds `4`, upper bounds `4`, cross-zone one-zone-per-nurse inequalities `21`, workload equalities `4`, and workload upper bounds `4`; total `37`.
- Impact DV `14`: the CR adds `total_workload` and `total_travel_cost` scalars, while still using `p` and `w`; total `8 + 4 + 1 + 1 = 14`.
- Impact constraints `23`: removed one-zone-per-nurse constraints `21`, plus `total_workload == sum(w)` `1` and `total_travel_cost == ...` `1`; total `23`.

## Assumptions and ambiguities

- `Cumulative(...)` is counted as one scalar constraint per call.
- For `mixed` CRs, `affected_constraints` includes removed and added/modified families when that better matches the reformulation scope.
- `affected_decision_variables` counts families directly touched by the CR logic, not every downstream variable that may be influenced indirectly by solving.
- Some helper arrays created inside loops are counted conceptually by family name in the report where that is the clearest way to explain the metadata.
