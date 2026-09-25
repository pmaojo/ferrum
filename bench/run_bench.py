#!/usr/bin/env python3
"""Benchmark harness for the `ferrum` CLI.

Measures end-to-end `ferrum compile` latency across DSL complexity tiers,
output size (files / bytes / lines of code), throughput, auxiliary analysis
commands, plugin overhead, `ferrum init`, and compiler determinism.

Usage:
    python3 bench/run_bench.py                 # full run
    python3 bench/run_bench.py --quick         # fewer repetitions
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
from typing import Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import gen_dsl  # noqa: E402

DSL_DIR = os.path.join(HERE, "dsl")
OUT_DIR = os.path.join(HERE, "out")
RES_DIR = os.path.join(HERE, "results")
LOG_DIR = os.path.join(RES_DIR, "logs")
TEMPLATES = os.path.join(ROOT, "templates")

TEXT_EXT = {
    ".rs", ".ts", ".tsx", ".js", ".jsx", ".json", ".yaml", ".yml", ".toml",
    ".md", ".sql", ".css", ".html", ".txt", ".env", ".sh", ".graphql",
}

# Repetitions per tier: the two largest tiers are the slowest, so they get
# fewer samples.
REPS = {"tier1": 5, "tier2": 5, "tier3": 5, "tier4": 3, "tier5": 3}
REPS_QUICK = {"tier1": 2, "tier2": 2, "tier3": 2, "tier4": 1, "tier5": 1}


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def run(cmd: List[str], cwd: str, env: Optional[Dict[str, str]] = None,
        timeout: int = 1800) -> Dict:
    """Run a command, returning timing plus captured streams."""
    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd, cwd=cwd, env=env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, timeout=timeout,
    )
    wall = time.perf_counter() - t0
    return {
        "cmd": cmd,
        "cwd": cwd,
        "wall_s": wall,
        "exit_code": proc.returncode,
        "stdout": proc.stdout.decode("utf-8", "replace"),
        "stderr": proc.stderr.decode("utf-8", "replace"),
    }


def tree_metrics(path: str) -> Dict:
    """Count files, bytes, lines and group by extension / top-level dir."""
    files = 0
    total_bytes = 0
    loc = 0
    by_ext: Dict[str, int] = {}
    by_top: Dict[str, int] = {}
    for dirpath, _dirnames, filenames in os.walk(path):
        for name in filenames:
            full = os.path.join(dirpath, name)
            try:
                size = os.path.getsize(full)
            except OSError:
                continue
            files += 1
            total_bytes += size
            ext = os.path.splitext(name)[1].lower() or "(none)"
            by_ext[ext] = by_ext.get(ext, 0) + 1
            rel = os.path.relpath(full, path)
            top = rel.split(os.sep)[0]
            by_top[top] = by_top.get(top, 0) + 1
            if ext in TEXT_EXT:
                try:
                    with open(full, "rb") as fh:
                        loc += fh.read().count(b"\n")
                except OSError:
                    pass
    return {
        "files": files,
        "bytes": total_bytes,
        "loc": loc,
        "by_ext": dict(sorted(by_ext.items(), key=lambda kv: -kv[1])),
        "by_top": dict(sorted(by_top.items(), key=lambda kv: -kv[1])),
    }


def tree_hashes(path: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for dirpath, _d, filenames in os.walk(path):
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, path)
            with open(full, "rb") as fh:
                out[rel] = hashlib.sha256(fh.read()).hexdigest()
    return out


def stats(samples: List[float]) -> Dict:
    if not samples:
        return {}
    ordered = sorted(samples)
    return {
        "n": len(samples),
        "min": ordered[0],
        "median": statistics.median(ordered),
        "mean": statistics.fmean(ordered),
        "max": ordered[-1],
        "stdev": statistics.stdev(ordered) if len(ordered) > 1 else 0.0,
    }


def fresh(path: str) -> None:
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)


def declared_total(counts: Dict[str, int]) -> int:
    return sum(counts.values())


def log_run(tag: str, r: Dict) -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(os.path.join(LOG_DIR, tag + ".log"), "w") as fh:
        fh.write("$ %s\n(cwd=%s)\nexit=%d wall=%.4fs\n" % (
            " ".join(r["cmd"]), r["cwd"], r["exit_code"], r["wall_s"]))
        fh.write("--- stdout ---\n" + r["stdout"])
        fh.write("--- stderr ---\n" + r["stderr"])


# --------------------------------------------------------------------------
# experiments
# --------------------------------------------------------------------------

def bench_scaling(binary: str, reps: Dict[str, int], label: str,
                  minimal_path: Optional[str]) -> List[Dict]:
    """Compile each tier N times into a fresh directory and time it."""
    results: List[Dict] = []
    for tier, module_count in gen_dsl.TIERS.items():
        if tier not in reps:
            continue
        dsl = os.path.join(DSL_DIR, tier + ".yaml")
        _text, counts = gen_dsl.build_dsl(module_count, tier, "x")
        out = os.path.join(OUT_DIR, "%s_%s" % (label, tier))
        env = dict(os.environ)
        if minimal_path is not None:
            env["PATH"] = minimal_path

        samples: List[float] = []
        last_run: Dict = {}
        for rep in range(reps[tier]):
            fresh(out)
            r = run([binary, "compile", dsl, "-o", out, "-t", TEMPLATES],
                    cwd=ROOT, env=env)
            last_run = r
            if r["exit_code"] != 0:
                print("  !! %s rep %d failed (exit %d)" % (tier, rep, r["exit_code"]))
                print(r["stdout"][-2000:])
                print(r["stderr"][-2000:])
                break
            samples.append(r["wall_s"])
        log_run("%s_%s" % (label, tier), last_run)

        metrics = tree_metrics(out)
        units = declared_total(counts)
        median = statistics.median(samples) if samples else 0.0
        entry = {
            "tier": tier,
            "label": label,
            "modules": module_count,
            "declared_units": units,
            "declared_counts": counts,
            "dsl_bytes": os.path.getsize(dsl),
            "reps": len(samples),
            "wall_samples_s": samples,
            "wall": stats(samples),
            "output": metrics,
            "usecases_per_s": (counts["usecases"] / median) if median else 0.0,
            "units_per_s": (units / median) if median else 0.0,
            "files_per_s": (metrics["files"] / median) if median else 0.0,
            "loc_per_s": (metrics["loc"] / median) if median else 0.0,
            "exit_code": last_run.get("exit_code"),
            "runtime_warnings": last_run.get("stdout", "").count("⚠️"),
        }
        results.append(entry)
        print("  %-6s modules=%-4d units=%-5d median=%7.3fs  files=%-5d loc=%-6d %s"
              % (tier, module_count, units, median, metrics["files"],
                 metrics["loc"], "(no-cargo PATH)" if minimal_path else ""))
    return results


def bench_baseline(binary: str) -> Dict:
    samples = []
    for _ in range(10):
        r = run([binary, "--help"], cwd=ROOT)
        samples.append(r["wall_s"])
    return {"wall": stats(samples), "samples": samples}


def bench_aux(binary: str, atlas: str, legacy: str) -> List[Dict]:
    """Time the read-only analysis subcommands, including known-broken paths."""
    out_dot = os.path.join(OUT_DIR, "atlas.dot")
    legacy_dot = os.path.join(OUT_DIR, "legacy.dot")
    i18n_cwd = os.path.join(OUT_DIR, "i18n_cwd")
    cmds = [
        ("analyze", [binary, "analyze", atlas, "--json"], "ok", ROOT),
        ("analyze-bottleneck", [binary, "analyze", atlas, "--bottleneck", "2", "--json"], "ok", ROOT),
        ("analyze-legacy", [binary, "analyze", legacy, "--json"], "ok", ROOT),
        ("explain", [binary, "explain", atlas], "ok", ROOT),
        ("graph-new-dsl", [binary, "graph", atlas, "-o", out_dot], "unsupported-new-dsl", ROOT),
        ("graph-legacy-dsl", [binary, "graph", legacy, "-o", legacy_dot], "ok", ROOT),
        ("flow", [binary, "flow", atlas], "needs-ai-service", ROOT),
        ("sync", [binary, "sync", atlas], "legacy-only", ROOT),
        ("doctor", [binary, "doctor"], "environment", ROOT),
        ("i18n", [binary, "i18n", atlas], "writes-to-cwd", i18n_cwd),
    ]
    results = []
    for name, cmd, expectation, cwd in cmds:
        samples = []
        last = {}
        for _ in range(5):
            if name == "i18n":
                fresh(i18n_cwd)
            last = run(cmd, cwd=cwd)
            samples.append(last["wall_s"])
        log_run("aux_" + name, last)
        results.append({
            "command": name,
            "expectation": expectation,
            "exit_code": last["exit_code"],
            "wall": stats(samples),
            "stdout_bytes": len(last["stdout"]),
            "stderr_bytes": len(last["stderr"]),
            "stderr_head": last["stderr"].strip().splitlines()[:3],
            "cwd": cwd,
        })
        print("  %-18s median=%7.4fs exit=%d  (%s)"
              % (name, statistics.median(samples), last["exit_code"], expectation))
    return results


PLUGIN_SETS = {
    "none": [],
    "core": ["graphql", "auth", "cron"],
    "all": ["graphql", "auth", "auth-password", "auth-oauth", "stripe", "cron",
            "cms-sanity", "cms-notion", "realtime-sse"],
}


def bench_plugins(binary: str, dsl: str, tier_modules: int) -> List[Dict]:
    """Compile the same DSL with 0 / 3 / 9 plugins enabled."""
    _text, counts = gen_dsl.build_dsl(tier_modules, "tier3", "x")
    results = []
    for name, plugins in PLUGIN_SETS.items():
        out = os.path.join(OUT_DIR, "plugins_" + name)
        samples = []
        last = {}
        for _ in range(3):
            fresh(out)
            ferrum_dir = os.path.join(out, ".ferrum")
            os.makedirs(ferrum_dir, exist_ok=True)
            with open(os.path.join(ferrum_dir, "plugins.txt"), "w") as fh:
                fh.write("\n".join(plugins) + ("\n" if plugins else ""))
            # cwd is the project dir: plugins' compile() writes to paths
            # relative to the working directory, as real users would run it.
            last = run([binary, "compile", dsl, "-o", out, "-t", TEMPLATES], cwd=out)
            if last["exit_code"] != 0:
                break
            samples.append(last["wall_s"])
        log_run("plugins_" + name, last)
        metrics = tree_metrics(out)
        entry = {
            "plugin_set": name,
            "plugins": plugins,
            "n_plugins": len(plugins),
            "wall": stats(samples),
            "exit_code": last.get("exit_code"),
            "output": metrics,
        }
        results.append(entry)
        print("  plugins=%-5s (n=%d) median=%7.3fs files=%d loc=%d exit=%s"
              % (name, len(plugins), statistics.median(samples) if samples else float("nan"),
                 metrics["files"], metrics["loc"], last.get("exit_code")))
    return results


def bench_init(binary: str) -> List[Dict]:
    cases = [
        ("init-plain", [], 0),
        ("init-full", ["--with-db", "--with-auth", "--with-graph", "--with-jobs",
                       "--with-ai"], 0),
        ("init-api-only", ["--api-only", "--with-db"], 0),
        ("init-uploads", ["--with-uploads"], None),
    ]
    results = []
    for name, flags, expected in cases:
        samples = []
        last = {}
        base = os.path.join(OUT_DIR, "init")
        app = os.path.join(base, name + "-app")
        for _ in range(3):
            shutil.rmtree(base, ignore_errors=True)
            os.makedirs(base, exist_ok=True)
            last = run([binary, "init", name + "-app"] + flags, cwd=base)
            samples.append(last["wall_s"])
        log_run(name, last)
        metrics = tree_metrics(app) if os.path.isdir(app) else {}
        results.append({
            "command": name,
            "flags": flags,
            "expected_exit": expected,
            "wall": stats(samples),
            "exit_code": last.get("exit_code"),
            "stderr_head": last.get("stderr", "").strip().splitlines()[:2],
            "output": metrics,
        })
        print("  %-14s median=%7.3fs exit=%s files=%s"
              % (name, statistics.median(samples), last.get("exit_code"),
                 metrics.get("files")))
    return results


def bench_legacy(binary: str) -> Dict:
    dsl = os.path.join(DSL_DIR, "legacy_graph.yaml")
    out = os.path.join(OUT_DIR, "legacy_graph")
    samples = []
    last = {}
    for _ in range(5):
        fresh(out)
        last = run([binary, "compile", dsl, "-o", out, "-t", TEMPLATES], cwd=ROOT)
        samples.append(last["wall_s"])
    log_run("legacy_graph", last)
    metrics = tree_metrics(out)
    files = sorted(os.path.relpath(os.path.join(d, f), out)
                   for d, _s, fs in os.walk(out) for f in fs)
    print("  legacy graph median=%7.3fs files=%d exit=%s"
          % (statistics.median(samples), metrics["files"], last.get("exit_code")))
    return {"wall": stats(samples), "exit_code": last.get("exit_code"),
            "output": metrics, "files": files}


def bench_collisions(binary: str, dsl: str, name: str,
                     expectations: List[Tuple[str, List[str]]]) -> Dict:
    """Compile a DSL and check which declared usecases survive codegen.

    `usecase` nodes are written to `backend/handlers/<module>.rs`, so several
    usecases in one module cannot each get their own handler file.
    """
    out = os.path.join(OUT_DIR, name)
    fresh(out)
    r = run([binary, "compile", dsl, "-o", out, "-t", TEMPLATES], cwd=ROOT)
    log_run(name, r)

    handler_dir = os.path.join(out, "backend", "handlers")
    hook_dir = os.path.join(out, "frontend", "src", "hooks")
    handlers = sorted(os.listdir(handler_dir)) if os.path.isdir(handler_dir) else []
    hooks = sorted(os.listdir(hook_dir)) if os.path.isdir(hook_dir) else []

    per_module = []
    for module, usecases in expectations:
        path = os.path.join(handler_dir, module + ".rs")
        blob = ""
        if os.path.exists(path):
            with open(path) as fh:
                blob = fh.read()
        materialised = [u for u in usecases if (u + "_handler") in blob]
        hooks_found = [u for u in usecases
                       if ("use%s.ts" % u[0].upper() + u[1:]) in hooks]
        per_module.append({
            "module": module,
            "declared": usecases,
            "materialised_in_handler": materialised,
            "lost_from_handler": [u for u in usecases if u not in materialised],
            "component_hooks": hooks_found,
        })

    declared_n = sum(len(u) for _m, u in expectations)
    materialised_n = sum(len(m["materialised_in_handler"]) for m in per_module)
    hook_n = sum(len(m["component_hooks"]) for m in per_module)
    print("  %-12s declared=%d handlers=%d/%d hooks=%d/%d exit=%s"
          % (name, declared_n, materialised_n, declared_n, hook_n, declared_n,
             r["exit_code"]))
    return {
        "fixture": name,
        "modules": [m for m, _u in expectations],
        "declared_usecases": declared_n,
        "materialised_in_handler": materialised_n,
        "component_hooks": hook_n,
        "handler_files": handlers,
        "per_module": per_module,
        "exit_code": r["exit_code"],
    }


def bench_determinism(binary: str, dsl: str) -> Dict:
    """Compile the flagship twice and compare byte-for-byte."""
    a = os.path.join(OUT_DIR, "determinism_a")
    b = os.path.join(OUT_DIR, "determinism_b")
    times = []
    for target in (a, b):
        fresh(target)
        r = run([binary, "compile", dsl, "-o", target, "-t", TEMPLATES], cwd=ROOT)
        times.append(r["wall_s"])
    ha, hb = tree_hashes(a), tree_hashes(b)
    same = ha == hb
    differing = sorted(set(ha) ^ set(hb)) + \
        sorted(k for k in set(ha) & set(hb) if ha[k] != hb[k])
    print("  determinism: identical=%s files=%d differing=%d" % (same, len(ha), len(differing)))
    return {"identical": same, "files": len(ha), "differing": differing[:20],
            "reps_s": times}


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main() -> int:
    global RES_DIR, LOG_DIR
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--binary", default=os.path.join(ROOT, "target", "debug", "ferrum"))
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--skip-slow", action="store_true",
                    help="skip tier5 and the formatter-suppressed sweep")
    ap.add_argument("--out", default=RES_DIR)
    args = ap.parse_args()

    RES_DIR = args.out
    LOG_DIR = os.path.join(RES_DIR, "logs")
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    binary = os.path.abspath(args.binary)
    if not os.path.exists(binary):
        print("binary not found: %s" % binary, file=sys.stderr)
        return 2

    reps = dict(REPS_QUICK if args.quick else REPS)
    if args.skip_slow:
        reps.pop("tier5", None)

    minimal_path = "/usr/bin:/bin:/usr/sbin:/sbin"

    report: Dict = {
        "meta": {
            "binary": binary,
            "binary_bytes": os.path.getsize(binary),
            "binary_mtime": os.path.getmtime(binary),
            "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "platform": sys.platform,
            "python": sys.version.split()[0],
            "reps": reps,
            "cargo_on_default_path": shutil.which("cargo") or None,
            "typeshare_on_path": shutil.which("typeshare"),
            "prettier_on_path": shutil.which("prettier"),
        },
        "startup_baseline": bench_baseline(binary),
    }
    print("[1/8] startup baseline: median=%.4fs" % report["startup_baseline"]["wall"]["median"])

    print("[2/8] scaling: default PATH (external formatters on PATH)")
    report["scaling_default_path"] = bench_scaling(binary, reps, "path_default", None)

    if not args.skip_slow:
        print("[3/8] scaling: minimal PATH (cargo/typeshare/prettier unavailable)")
        report["scaling_minimal_path"] = bench_scaling(binary, reps, "path_minimal", minimal_path)
    else:
        report["scaling_minimal_path"] = []

    print("[4/8] auxiliary analysis commands")
    report["aux_commands"] = bench_aux(binary,
                                       os.path.join(DSL_DIR, "atlas.yaml"),
                                       os.path.join(DSL_DIR, "legacy_graph.yaml"))

    print("[5/8] plugin overhead (tier3 fixture)")
    report["plugins"] = bench_plugins(binary, os.path.join(DSL_DIR, "tier3.yaml"), 20)

    print("[6/8] ferrum init")
    report["init"] = bench_init(binary)

    print("[7/8] legacy raw-graph fixture")
    report["legacy_graph"] = bench_legacy(binary)

    print("[8/8] correctness probes")
    report["collision_probe"] = bench_collisions(
        binary, os.path.join(DSL_DIR, "collide.yaml"), "collide",
        [("order", ["createOrder", "updateOrder", "cancelOrder",
                    "refundOrder", "shipOrder", "archiveOrder"])])
    report["determinism"] = bench_determinism(
        binary, os.path.join(DSL_DIR, "atlas.yaml"))
    report["collision_probe_tier1"] = bench_collisions(
        binary, os.path.join(DSL_DIR, "tier1.yaml"), "collide_tier1",
        [("user", ["createUser", "getUser", "listUsers"]),
         ("tenant", ["createTenant", "getTenant", "listTenants"])])

    report["meta"]["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(os.path.join(RES_DIR, "bench.json"), "w") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)

    print("\nwrote %s" % os.path.join(RES_DIR, "bench.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
