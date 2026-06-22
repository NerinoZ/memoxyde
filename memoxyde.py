#!/usr/bin/env python3
"""
🐙 MeMOXYDe — MemOry eXternal integrity sYstem for Data safEty

Two-layer integrity shield for AI agent memory.
Layer 1: Hash map (file signature tracking)
Layer 2: Content wiki (content snapshot comparison)

When both flag the same file → CRITICAL: probable corruption.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


# ── Config ──────────────────────────────────────────────────────────────────

APP_NAME = "memoxyde"
DATA_DIR = Path.home() / f".{APP_NAME}"
HASHES_FILE = DATA_DIR / "hashes.json"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
FLAGS_FILE = DATA_DIR / "flags.log"

# Tracked file types by default
DEFAULT_PATTERNS = ["*.md"]


# ── Utils ───────────────────────────────────────────────────────────────────

def sha256_of(path: Path) -> str:
    """Compute SHA256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict:
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    shutil.move(str(tmp), str(path))


def log_flag(path: str, level: str, hash_flag: bool, wiki_flag: bool, message: str):
    """Append a flag to the log."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    entry = {
        "timestamp": ts,
        "path": path,
        "level": level,
        "hash_flag": hash_flag,
        "wiki_flag": wiki_flag,
        "message": message,
    }
    with open(FLAGS_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def col(text: str, code: str) -> str:
    """Simple ANSI coloring."""
    colors = {"red": "\033[91m", "green": "\033[92m", "yellow": "\033[93m", "cyan": "\033[96m", "bold": "\033[1m", "reset": "\033[0m"}
    return f"{colors.get(code, '')}{text}{colors['reset']}"


# ── Core Commands ───────────────────────────────────────────────────────────

def cmd_track(paths: list[str]):
    """Register files for tracking. Computes initial hash + snapshot."""
    hashes = read_json(HASHES_FILE)
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    for p in paths:
        path = Path(p).resolve()
        if not path.exists():
            print(f"  {col('⚠', 'yellow')} Skipped (not found): {path}")
            continue
        if not path.is_file():
            print(f"  {col('⚠', 'yellow')} Skipped (not a file): {path}")
            continue

        rel = str(path)
        h = sha256_of(path)
        ts = datetime.now(timezone.utc).isoformat()

        hashes[rel] = {"hash": h, "timestamp": ts}

        # Initial snapshot
        snap_id = hashlib.sha256(rel.encode()).hexdigest()[:12]
        snap_path = SNAPSHOTS_DIR / f"{snap_id}.snap"
        with open(path) as f:
            content = f.read()
        with open(snap_path, "w") as f:
            f.write(f"# Snapshot of {rel}\n# Created: {ts}\n# hash: {h}\n\n")
            f.write(content)

        print(f"  {col('✓', 'green')} Tracked: {rel}")

    write_json(HASHES_FILE, hashes)
    print(f"\n  {col(len(paths), 'bold')} file(s) tracked. {col(len(hashes), 'bold')} total.")


def cmd_untrack(paths: list[str]):
    """Remove files from tracking."""
    hashes = read_json(HASHES_FILE)
    removed = 0
    for p in paths:
        rel = str(Path(p).resolve())
        if rel in hashes:
            del hashes[rel]
            # Clean snapshot
            snap_id = hashlib.sha256(rel.encode()).hexdigest()[:12]
            snap_path = SNAPSHOTS_DIR / f"{snap_id}.snap"
            if snap_path.exists():
                snap_path.unlink()
            print(f"  {col('✓', 'green')} Untracked: {rel}")
            removed += 1
        else:
            print(f"  {col('⚠', 'yellow')} Not tracked: {p}")
    write_json(HASHES_FILE, hashes)
    if removed:
        print(f"\n  {col(removed, 'bold')} file(s) removed.")


def cmd_check(paths: list[str] | None = None):
    """Check tracked files and produce flag matrix."""
    hashes = read_json(HASHES_FILE)
    if not hashes:
        print(f"  {col('No files tracked.', 'yellow')} Run 'track' first.")
        return

    to_check = set(hashes.keys())
    if paths:
        to_check = {str(Path(p).resolve()) for p in paths} & to_check

    if not to_check:
        print(f"  {col('No matching tracked files.', 'yellow')}")
        return

    # Header
    print(f"\n  {'🐙 MeMOXYDe — Integrity Check':^67}")
    print(f"  {'━'*67}")
    print(f"  {'FILE':<42} {'HASH':^10} {'WIKI':^10} {'SEVERITY':^10}")
    print(f"  {'━'*67}")

    flags_raised = 0
    criticals = 0

    for rel in sorted(to_check):
        path = Path(rel)
        expected = hashes.get(rel, {})
        old_hash = expected.get("hash", "")

        if not path.exists():
            print(f"  {rel:<42} {col('❌MISS', 'red'):^10} {col('❌MISS', 'red'):^10} {col('ERROR', 'red'):^10}")
            log_flag(rel, "ERROR", True, True, "File missing")
            flags_raised += 1
            criticals += 1
            continue

        current_hash = sha256_of(path)

        # Hash flag
        hash_changed = old_hash and current_hash != old_hash
        hash_flag = hash_changed if old_hash else False  # No old hash = first check

        # Wiki flag: compare content with snapshot
        snap_id = hashlib.sha256(rel.encode()).hexdigest()[:12]
        snap_path = SNAPSHOTS_DIR / f"{snap_id}.snap"
        wiki_changed = False
        if snap_path.exists():
            with open(path) as f:
                current_content = f.read()
            with open(snap_path) as f:
                snap_content = f.read()
            # Strip metadata header (lines starting with # Snapshot / # Created / # hash)
            snap_body_lines = [l for l in snap_content.split("\n") if not l.startswith("# Snapshot") and not l.startswith("# Created") and not l.startswith("# hash")]
            snap_body = "\n".join(snap_body_lines).strip()
            wiki_changed = snap_body != current_content.strip()

        wiki_flag = wiki_changed

        # Matrix
        if hash_flag and wiki_flag:
            severity = "🔴CRIT"
            criticals += 1
            flags_raised += 1
            msg = f"Hash + Wiki flag: probable corruption"
            log_flag(rel, "CRITICAL", True, True, msg)
        elif hash_flag:
            severity = "🟡 WARN"
            flags_raised += 1
            msg = "Hash changed (legitimate edit?) — update hash if intentional"
            log_flag(rel, "WARNING", True, False, msg)
        elif wiki_flag:
            severity = "🟡 NOTE"
            flags_raised += 1
            msg = "Content changed but hash matches — possible contradiction"
            log_flag(rel, "NOTE", False, True, msg)
        else:
            severity = col("✅ OK", "green")

        # Color by severity
        h_str = col("✅", "green") if not hash_changed else col("🔄", "yellow")
        w_str = col("✅", "green") if not wiki_changed else col("🔄", "yellow")
        if not old_hash:
            h_str = col("📌NEW", "cyan")
            w_str = col("📌NEW", "cyan")
            severity = col("NEW", "cyan")

        # Update hash if no corruption (legitimate edit)
        if hash_changed and not wiki_changed:
            hashes[rel]["hash"] = current_hash
            hashes[rel]["timestamp"] = datetime.now(timezone.utc).isoformat()
            # Update snapshot
            with open(path) as f:
                new_content = f.read()
            ts = datetime.now(timezone.utc).isoformat()
            with open(snap_path, "w") as f:
                f.write(f"# Snapshot of {rel}\n# Created: {ts}\n# hash: {current_hash}\n\n")
                f.write(new_content)
            h_str = col("✅UPD", "green")

        print(f"  {rel:<42} {h_str:^10} {w_str:^10} {severity:^10}")

    # Footer
    print(f"  {'━'*67}")
    status = col("🔴 CRITICAL" if criticals else ("🟡 FLAGS" if flags_raised else "✅ CLEAN"), "red" if criticals else ("yellow" if flags_raised else "green"))
    path_count = len(to_check)
    print(f"  {path_count} files · {col(flags_raised, 'bold')} flag(s) · {col(criticals, 'bold')} critical(s)  Status: {status}")
    print()

    # Save updated hashes if we auto-updated
    write_json(HASHES_FILE, hashes)


def cmd_status():
    """Show tracked files and last check state."""
    hashes = read_json(HASHES_FILE)
    if not hashes:
        print(f"  {col('No files tracked.', 'yellow')}")
        return

    print(f"\n  {'🐙 MeMOXYDe — Status':^67}")
    print(f"  {'━'*67}")
    print(f"  {'FILE':<50} {'LAST HASH':^14}")
    print(f"  {'━'*67}")
    for rel, data in sorted(hashes.items()):
        h = data.get("hash", "?")[:12]
        print(f"  {rel:<50} {col(h, 'cyan'):>14}")
    print(f"  {'━'*67}")
    print(f"  {col(len(hashes), 'bold')} file(s) tracked.")
    print()


def cmd_log(lines: int = 20):
    """Show recent flags."""
    if not FLAGS_FILE.exists():
        print(f"  {col('No flags logged.', 'yellow')}")
        return

    with open(FLAGS_FILE) as f:
        entries = [json.loads(l) for l in f if l.strip()]

    if not entries:
        print(f"  {col('No flags logged.', 'yellow')}")
        return

    print(f"\n  {'🐙 MeMOXYDe — Last Flags':^67}")
    print(f"  {'━'*67}")
    for e in entries[-lines:]:
        ts = e["timestamp"][:19]  # trim tz
        path = e["path"][:40]
        lvl = e["level"]
        print(f"  {ts} | {lvl:<10} | {e['hash_flag']} {e['wiki_flag']} | {path}")
    print(f"  {'━'*67}")
    print()


def cmd_reset():
    """Wipe all tracking data."""
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
        print(f"  {col('✓', 'green')} Tracking data cleared.")
    else:
        print(f"  {col('Nothing to reset.', 'yellow')}")


# ── Demo / Self-Test ────────────────────────────────────────────────────────

def cmd_self_test():
    """Run a self-test on the current workspace to validate."""
    print(f"\n  {'🐙 MeMOXYDe — Self-Test':^67}")
    print(f"  {'━'*67}")

    # Use MEMORY.md and USER.md as test subjects
    test_files = []
    for f in ["MEMORY.md", "USER.md", "SOUL.md"]:
        p = Path.home() / ".openclaw" / "workspace" / f
        if p.exists():
            test_files.append(str(p))

    if not test_files:
        print(f"  {col('No test files found.', 'yellow')}")
        return

    print(f"  Test files: {len(test_files)}")
    print()

    # Track
    cmd_track(test_files)

    # Check
    cmd_check()

    print(f"  {col('Self-test complete.', 'green')}")


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="🐙 MeMOXYDe — Memory integrity verification for AI agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s track MEMORY.md USER.md      Start tracking files
  %(prog)s check                         Check all tracked files
  %(prog)s check MEMORY.md               Check specific file
  %(prog)s status                        Show tracked files
  %(prog)s log                           Show recent flags
  %(prog)s untrack MEMORY.md             Stop tracking
  %(prog)s self-test                     Run demo on workspace
  %(prog)s reset                         Clear all tracking data
"""
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_track = sub.add_parser("track", help="Register files for tracking")
    p_track.add_argument("paths", nargs="+", help="Files to track")

    p_untrack = sub.add_parser("untrack", help="Remove files from tracking")
    p_untrack.add_argument("paths", nargs="+", help="Files to untrack")

    p_check = sub.add_parser("check", help="Check file integrity (hash + wiki)")
    p_check.add_argument("paths", nargs="*", help="Optional: check only these files")

    sub.add_parser("status", help="Show tracked files")

    p_log = sub.add_parser("log", help="Show flag history")
    p_log.add_argument("-n", type=int, default=20, help="Lines to show (default: 20)")

    sub.add_parser("reset", help="Clear all tracking data")
    sub.add_parser("self-test", help="Run demo on workspace")

    args = parser.parse_args()

    cmds = {
        "track": lambda: cmd_track(args.paths),
        "untrack": lambda: cmd_untrack(args.paths),
        "check": lambda: cmd_check(args.paths if args.paths else None),
        "status": cmd_status,
        "log": lambda: cmd_log(args.n),
        "reset": cmd_reset,
        "self-test": cmd_self_test,
    }

    cmds.get(args.command, lambda: parser.print_help())()


if __name__ == "__main__":
    main()
