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
from lab9.graders import GRADERS


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
    rows, man = pr.get("rows") or [], pr.get("manifest") or {}
    # 1. metric values must be finite (NaN compares False against every threshold)
    for k, v in (pr.get("metrics") or {}).items():
        if isinstance(v, float) and not math.isfinite(v):
            problems.append(f"metric {k} is {v}")
    # 2. row count and uniqueness: dropped or duplicated rows
    keys = [(r.get("item_id"), r.get("seed")) for r in rows]
    want = (man.get("items") or 0) * len(man.get("seeds") or [])
    if len(rows) != want:
        problems.append(f"{len(rows)} rows, manifest says {man.get('items')} items x "
                        f"{len(man.get('seeds') or [])} seeds = {want}")
    if len(keys) != len(set(keys)):
        problems.append(f"{len(keys) - len(set(keys))} duplicated (item, seed) row(s)")
    # 3. same (item, seed) set, items and seeds as the baseline: no cherry-picking
    base_keys = {(r.get("item_id"), r.get("seed")) for r in base.get("rows") or []}
    if set(keys) != base_keys:
        problems.append(f"(item, seed) set differs from baseline: {len(set(keys) - base_keys)} extra, "
                        f"{len(base_keys - set(keys))} missing")
    bman = base.get("manifest") or {}
    if (man.get("items"), sorted(man.get("seeds") or [])) != (bman.get("items"), sorted(bman.get("seeds") or [])):
        problems.append(f"manifest items/seeds {man.get('items')}/{man.get('seeds')} != baseline "
                        f"{bman.get('items')}/{bman.get('seeds')}")
    # 4. crashed graders: evaluator failures, or a graded metric without a verdict on a row
    if pr.get("evaluator_failures"):
        problems.append(f"{len(pr['evaluator_failures'])} evaluator failure(s): {pr['evaluator_failures'][0]}")
    graded = [m for m in spec.get("metrics", []) if m["id"] in GRADERS]
    for m in graded:
        missing = sum(1 for r in rows if not isinstance(r.get(m["id"]), bool))
        if missing:
            problems.append(f"{missing} row(s) without a {m['id']} verdict (crashed grader scored as missing)")
    # 5. reported metrics must be what the rows say (hand-edited numbers)
    for m in graded:
        v = (pr.get("metrics") or {}).get(m["id"])
        vals = [r[m["id"]] for r in rows if isinstance(r.get(m["id"]), bool)]
        if isinstance(v, (int, float)) and math.isfinite(v) and vals:
            real = sum(vals) if m.get("kind") == "safety" else sum(vals) / len(vals)
            if abs(real - v) > 1e-3:
                problems.append(f"metric {m['id']} reported {v} but rows give {round(real, 4)}")
    # 6. slice tags must match the baseline's for every item
    def tags(rep: dict) -> dict:
        return {r.get("item_id"): sorted(r.get("slices") or []) for r in rep.get("rows") or []}
    bt = tags(base)
    for item, t in sorted(tags(pr).items()):
        if item in bt and bt[item] != t:
            problems.append(f"{item} slice tags {t} != baseline {bt[item]}")
    # 7. ratchet against the spec on main
    if base_spec is not None:
        problems += ratchet(spec, base_spec)
    return problems


def ratchet(spec: dict, base_spec: dict) -> list[str]:
    """Same eval-set version => thresholds may only get stricter. Return every loosening found."""
    if spec.get("eval_set_version") != base_spec.get("eval_set_version"):
        if spec.get("eval_set") == base_spec.get("eval_set"):
            return [f"RATCHET eval_set_version renamed {base_spec.get('eval_set_version')!r} -> "
                    f"{spec.get('eval_set_version')!r} on the same eval set"]
        return []                                   # a new eval set starts a new ratchet
    out: list[str] = []

    def cmp(tag: str, old: dict, new: dict | None) -> None:
        if new is None:
            out.append(f"RATCHET {tag} removed")
            return
        if old.get("blocking") and not new.get("blocking"):
            out.append(f"RATCHET {tag} no longer blocking")
        ot, nt = old.get("threshold", old), new.get("threshold", new)   # slices keep thresholds inline
        for key, looser in (("min", lambda o, n: n < o), ("max", lambda o, n: n > o),
                            ("max_increase", lambda o, n: n > o)):
            if key in ot and (key not in nt or looser(ot[key], nt[key])):
                out.append(f"RATCHET {tag} {key} {ot[key]} -> {nt.get(key, 'removed')}")
        if ot.get("no_significant_drop") and not nt.get("no_significant_drop"):
            out.append(f"RATCHET {tag} no_significant_drop dropped")

    new_m = {m["id"]: m for m in spec.get("metrics", [])}
    for m in base_spec.get("metrics", []):
        cmp(f"metric {m['id']}", m, new_m.get(m["id"]))
    new_s = {(s["name"], s["metric"]): s for s in spec.get("slices") or []}
    for s in base_spec.get("slices") or []:
        cmp(f"slice {s['name']}/{s['metric']}", s, new_s.get((s["name"], s["metric"])))
    if set(base_spec.get("seeds") or []) - set(spec.get("seeds") or []):
        out.append(f"RATCHET seeds {base_spec.get('seeds')} -> {spec.get('seeds')}")
    ob, nb = base_spec.get("bootstrap") or {}, spec.get("bootstrap") or {}
    if nb.get("confidence", 0.95) < ob.get("confidence", 0.95):
        out.append(f"RATCHET bootstrap confidence {ob.get('confidence')} -> {nb.get('confidence')}")
    return out


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for sl in spec.get("slices") or []:
        name, mid = sl["name"], sl["metric"]
        sid = f"slice:{name}/{mid}"
        a, b = per_item(pr, mid, slice_name=name), per_item(base, mid, slice_name=name)
        verdict, note, val = "ok", "", None
        if not a:
            verdict = "missing"                     # an empty slice proves nothing: never a silent pass
        else:
            val = round(sum(a.values()) / len(a), 4)
            if ("min" in sl and val < sl["min"]) or ("max" in sl and val > sl["max"]):
                verdict = "fail"
            keys = sorted(set(a) & set(b))
            if sl.get("no_significant_drop") and keys:
                d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                                   n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
                note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}] n={len(keys)}"
                if hi < 0:
                    verdict = "fail"
        if verdict != "ok" and sl.get("blocking"):
            blocked.append(sid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if sl.get("blocking") else "warn")
        th = {k: sl[k] for k in ("min", "max", "no_significant_drop") if k in sl}
        lines.append(f"  {sid:<34} {val!s:<8} {json.dumps(th):<40} {note:<34} {label}")
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
