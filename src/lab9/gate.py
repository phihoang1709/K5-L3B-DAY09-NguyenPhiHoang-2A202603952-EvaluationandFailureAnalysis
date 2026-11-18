"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item


def _graded_ids(spec: dict, rows: list[dict]) -> list[str]:
    return [m["id"] for m in spec["metrics"] if m["id"] in (rows[0] if rows else {})]


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems: list[str] = []
    for k, v in pr["metrics"].items():
        if isinstance(v, (int, float)) and not isinstance(v, bool) and not math.isfinite(v):
            problems.append(f"metric {k} is {v}")
    m = pr["manifest"]
    if len(pr["rows"]) != m.get("items", 0) * len(m.get("seeds", [])):
        problems.append(f"row count {len(pr['rows'])} != items {m.get('items')} x seeds {len(m.get('seeds', []))}")
    pr_cells = {(r.get("item_id"), r.get("seed")) for r in pr["rows"]}
    base_cells = {(r.get("item_id"), r.get("seed")) for r in base["rows"]}
    if pr_cells != base_cells:
        problems.append(f"(item, seed) set differs from baseline "
                        f"({len(pr_cells - base_cells)} added, {len(base_cells - pr_cells)} dropped)")
    if pr.get("evaluator_failures"):
        problems.append(f"{len(pr['evaluator_failures'])} evaluator failure(s) in the PR report")
    graded = _graded_ids(spec, pr["rows"])
    for r in pr["rows"]:
        for mid in graded:
            if r.get(mid) is None:
                problems.append(f"{r.get('item_id')}@{r.get('seed')}: {mid} is None (crashed grader?)")
                break
    # ratchet: only meaningful when the eval-set version did not change
    if base_spec is not None and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        base_m = {x["id"]: x for x in base_spec["metrics"]}
        for x in spec["metrics"]:
            bx = base_m.get(x["id"])
            if bx is None:
                problems.append(f"metric {x['id']} disappeared from the spec (ratchet)")
                continue
            th, bth = x.get("threshold", {}), bx.get("threshold", {})
            if th.get("max", -math.inf) > bth.get("max", -math.inf):
                problems.append(f"metric {x['id']}: max raised {bth.get('max')} -> {th.get('max')} (ratchet)")
            if th.get("min", math.inf) < bth.get("min", math.inf):
                problems.append(f"metric {x['id']}: min lowered {bth.get('min')} -> {th.get('min')} (ratchet)")
            if bool(bx.get("blocking")) and not x.get("blocking"):
                problems.append(f"metric {x['id']}: blocking -> non-blocking (ratchet)")
            if bth.get("no_significant_drop") and not th.get("no_significant_drop"):
                problems.append(f"metric {x['id']}: dropped no_significant_drop (ratchet)")
        base_slices = {s["name"]: s for s in base_spec.get("slices", [])}
        for s in spec.get("slices", []):
            bs = base_slices.pop(s["name"], None)
            if bs is None:
                continue
            if s.get("min", math.inf) < bs.get("min", math.inf):
                problems.append(f"slice {s['name']}: min lowered {bs.get('min')} -> {s.get('min')} (ratchet)")
            if bs.get("no_significant_drop") and not s.get("no_significant_drop"):
                problems.append(f"slice {s['name']}: dropped no_significant_drop (ratchet)")
            if bool(bs.get("blocking")) and not s.get("blocking"):
                problems.append(f"slice {s['name']}: blocking -> non-blocking (ratchet)")
        for name in sorted(base_slices):
            problems.append(f"slice {name} disappeared from the spec (ratchet)")
    # slice-tag drift: relabelling an item out of a slice hides its regression
    base_slices_of = {}
    for r in base["rows"]:
        base_slices_of.setdefault(r.get("item_id"), set()).update(r.get("slices") or [])
    for r in pr["rows"]:
        want = base_slices_of.get(r.get("item_id"), set())
        have = set(r.get("slices") or [])
        if have != want:
            problems.append(f"{r.get('item_id')}: slice tags {sorted(have)} != baseline {sorted(want)}")
            break
    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for s in spec.get("slices", []):
        name, mid = s["name"], s["metric"]
        a, b = per_item(pr, mid, slice_name=name), per_item(base, mid, slice_name=name)
        keys = sorted(set(a) & set(b))
        if not keys:
            lines.append(f"  slice:{name:<14} {mid:<20} no items in slice")
            continue
        val = sum(a[k] for k in keys) / len(keys)
        verdict, note = "ok", ""
        if "min" in s and val < s["min"]:
            verdict = "fail"
        if s.get("no_significant_drop"):
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict == "fail" and s.get("blocking"):
            blocked.append(f"slice:{name}/{mid}")
        label = "ok" if verdict == "ok" else ("BLOCK" if s.get("blocking") else "warn")
        lines.append(f"  slice:{name:<14} {mid:<20} {val:<8.3f} {json.dumps({k: s[k] for k in s if k != 'name'}):<40} {note:<28} {label}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
