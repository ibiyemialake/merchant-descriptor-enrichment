"""Evaluate extractors field by field against a hand-labelled gold set.

Usage:
    python src/evaluate.py            # rules baseline only
    python src/evaluate.py --llm      # also run the LLM extractor (needs an API key)
    python src/evaluate.py --data data/holdout.csv   # score on the held-out set
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_rules  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ["merchant", "processor", "city", "province", "category"]


def norm(value) -> str:
    value = "" if pd.isna(value) else str(value)
    return " ".join(value.lower().replace("-", " ").replace("'", "").split())


def run(name, extractor, gold):
    preds = pd.DataFrame([extractor(r) for r in gold["raw"]])
    scores, errors = {"method": name}, []
    all_right = pd.Series(True, index=gold.index)
    for f in FIELDS:
        correct = gold[f].map(norm) == preds[f].map(norm)
        scores[f] = round(correct.mean(), 3)
        all_right &= correct
        for i in gold.index[~correct]:
            errors.append({"method": name, "field": f, "raw": gold.at[i, "raw"],
                           "expected": gold.at[i, f], "got": preds.at[i, f]})
    scores["all fields correct"] = round(all_right.mean(), 3)
    return scores, errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--data", default="data/descriptors.csv",
                        help="labelled CSV to score, e.g. data/holdout.csv")
    args = parser.parse_args()

    gold = pd.read_csv(ROOT / args.data, keep_default_na=False)
    methods = [("Rules", extract_rules.extract)]
    if args.llm:
        import extract_llm
        methods.append(("LLM", extract_llm.extract))

    scores, errors = [], []
    for name, fn in methods:
        s, e = run(name, fn, gold)
        scores.append(s)
        errors += e

    table = pd.DataFrame(scores)
    print("Field accuracy on", len(gold), "descriptors\n")
    print(table.to_string(index=False))
    pd.DataFrame(errors).to_csv(ROOT / "errors.csv", index=False)
    print(f"\n{len(errors)} field errors written to errors.csv for error analysis")


if __name__ == "__main__":
    main()
