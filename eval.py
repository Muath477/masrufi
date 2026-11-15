# -*- coding: utf-8 -*-
"""Score models on the held-out test set.

    python eval.py qwen3:1.7b masrufi
    python eval.py masrufi --n 40
"""
import argparse
import json
import os
import time

from llm import chat, parse

HERE = os.path.dirname(os.path.abspath(__file__))


def same(pred, gold):
    """A message counts as right when every expense matches on amount, category and day."""
    p, g = pred.get("expenses", []), gold["expenses"]
    if len(p) != len(g):
        return False
    for a, b in zip(p, g):
        if not isinstance(a, dict):
            return False
        try:
            if abs(float(a.get("amount")) - b["amount"]) > 0.01:
                return False
        except (TypeError, ValueError):
            return False
        if a.get("category") != b["category"] or a.get("when", "اليوم") != b["when"]:
            return False
    return True


def score(model, rows):
    valid = right = 0
    misses = []
    started = time.time()
    for r in rows:
        data = parse(chat(model, r["text"]))
        if data is not None:
            valid += 1
            if same(data, r["label"]):
                right += 1
                continue
        misses.append(r["text"])
    n = len(rows)
    return {"model": model, "n": n, "json_ok": valid / n, "correct": right / n,
            "sec_per_msg": (time.time() - started) / n, "misses": misses[:5]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("models", nargs="+")
    ap.add_argument("--n", type=int, default=60)
    args = ap.parse_args()
    with open(os.path.join(HERE, "data", "test.jsonl"), encoding="utf-8") as f:
        rows = [json.loads(line) for line in f][: args.n]
    for model in args.models:
        s = score(model, rows)
        print(f"\n{model}\n  JSON صالح: {s['json_ok']:.0%}   إجابات صحيحة: {s['correct']:.0%}   "
              f"{s['sec_per_msg']:.1f} ث/رسالة")
        for m in s["misses"]:
            print("   ✗", m)


if __name__ == "__main__":
    main()
