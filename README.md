# LLM4CP-mod-ref
Using LLM's for model modification and refinement in constraint programming

## Agents
- Parser agent (NL alignment): `python3 src/mod-ref-benchmark/parser_agent.py --problem src/mod-ref-benchmark/problems/problem1`  
  Saves structured NL-to-code mapping JSON into the problem's `base/` folder.
- Planner agent (change planning): `python3 src/mod-ref-benchmark/planner_agent.py --problem src/mod-ref-benchmark/problems/problem1 --cr CR1 --parser-json src/mod-ref-benchmark/problems/problem1/base/problem1_parser_<timestamp>.json`  
  Uses CR `desc.json`, parser mapping, base NL, and reference model to emit a structured edit plan saved in the CR folder.
- Modifier agent (apply plan): `python3 src/mod-ref-benchmark/modifier_agent.py --problem src/mod-ref-benchmark/problems/problem1 --cr CR1 --planner-json src/mod-ref-benchmark/problems/problem1/CR1/problem1_CR1_planner_<timestamp>.json`  
  Applies planner steps to rewrite `generated_model.py` inside the CR folder using the reference model plus CR context (no unit-test or validator loop yet).
- Executor agent (sanity run): `python3 src/mod-ref-benchmark/executor_agent.py --problem src/mod-ref-benchmark/problems/problem1 --cr CR1`  
  Runs the chosen model (default `generated_model.py`) in the CR folder and logs stdout JSON or execution errors.
- Validator agent (LLM review): `python3 src/mod-ref-benchmark/validator_agent.py --problem src/mod-ref-benchmark/problems/problem1 --cr CR1`  
  LLM-only review comparing generated model vs. reference model and CR; emits structured feedback (pass/needs_changes) for iterative loops with the modifier.
