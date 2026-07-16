#!/usr/bin/env python3
"""Deterministic seriousness classifier (ICH E2A criteria).

The REGULATORY RULEBOOK as code: given boolean facts about a case,
apply the seriousness criteria and return the classification. No AI,
no judgment, no variance — same facts in, same answer out, forever.
The LLM's job ends at establishing the facts; this script owns the rules.

Stdlib only, BY DESIGN: this script is executed by the agent via the
Bash tool in a bare environment — it must run with no dependencies.

Usage:
  python3 seriousness_scorer.py --death false --life-threatening false \
      --hospitalization true --disability false --congenital-anomaly false \
      --other-medically-important false

Output: JSON to stdout, e.g.
  {"is_serious": true, "criteria_met": ["hospitalization"]}
"""

import argparse
import json

# Vocabulary MUST match clinical_sentinel.models.case.Seriousness enum
# values exactly — the orchestrator validates our output against it.
CRITERIA = [
    "death",
    "life_threatening",
    "hospitalization",
    "disability",
    "congenital_anomaly",
    "other_medically_important",
]


def str2bool(v: str) -> bool:
    """Strict bool parsing: only 'true'/'false' accepted — no clever coercion."""
    if v.lower() == "true":
        return True
    if v.lower() == "false":
        return False
    raise argparse.ArgumentTypeError(f"expected 'true' or 'false', got {v!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    for c in CRITERIA:
        parser.add_argument(f"--{c.replace('_', '-')}", type=str2bool, required=True)
    args = vars(parser.parse_args())

    met = [c for c in CRITERIA if args[c]]
    print(json.dumps({"is_serious": len(met) > 0, "criteria_met": met}))


if __name__ == "__main__":
    main()