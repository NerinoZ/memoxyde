#!/usr/bin/env python3
"""
🐙 MeMOXYDe — MemOry eXternal integrity sYstem for Data safEty

Two-layer integrity shield for AI agent memory.
Layer 1: Hash map (file signature tracking)
Layer 2: Content snapshot (exact-content comparison against last known-good state)

When both flag the same file → CRITICAL: probable corruption.

Opt-in Layer 3: Claim verification via AI (memoxyde verify).
Requires ANTHROPIC_API_KEY. Checks if an agent-generated statement is:
  GROUNDED | CONTRADICTED | UNATTESTED
against hash-clean tracked sources.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


# ── Config ──────────────────────────────────────────────────────────────────

APP_NAME = "memoxyde"
DATA_DIR = Path.home() / f".{APP_NAME}"
HASHES_FILE = DATA_DIR / "hashes.json"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
FLAGS_FILE = DATA_DIR / "flags.log"

DEFAULT_PATTERNS = ["*.md"]
MAX_FILE_CHARS = 8000           # Per-file char limit for verify corpus
DEFAULT_VERIFY_MODEL = "claude-sonnet-4-5"


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


def log_flag(
    path: str,
    level: str,
    hash_flag: bool,
    wiki_flag: bool,
    message: str,
    verdict: "str | None" = None,
):
    """Append a flag to the log. Optional verdict field for verify entries."""
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
    if verdict is not None:
        entry["verdict"] = verdict
    with open(FLAGS_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def col(text: str, code: str) -> str:
    """Simple ANSI coloring."""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "cyan": "\033[96m",
        "bold": "\033[1m",
        "reset": "\033[0m",
    }
    return f"{colors.get(code, '')}{text}{colors['reset']}"


# ── Core Commands ───────────────────────────────────────────────────────────

def cmd_track(paths: list):
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

        snap_id = hashlib.sha256(rel.encode()).hexdigest()[:12]
        snap_path = SNAPSHOTS_DIR / f"{snap_id}.snap"
        with open(path) as f:
            content = f.read()
        with open(snap_path, "w") as f:
            f.write(f"# Snapshot of {rel}\n# Created: {ts}\n# hash: {h}\n\n")
            f.write(content)

        print(f"  {col('✓', 'green')} Tracked: {rel}")

    # AI escalation hint
    if flags_raised and not getattr(cmd_check, '_ai_mode', False):
        print(f"  {col('💡 TIP:', 'cyan')} Run {col('memoxyde verify "<claim>"', 'bold')} to escalate flagged files to AI verification.")
        print()

    write_json(HASHES_FILE, hashes)
    print(f"\n  {col(len(paths), 'bold')} file(s) tracked. {col(len(hashes), 'bold')} total.")


def cmd_untrack(paths: list):
    """Remove files from tracking."""
    hashes = read_json(HASHES_FILE)
    removed = 0
    for p in paths:
        rel = str(Path(p).resolve())
        if rel in hashes:
            del hashes[rel]
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


def cmd_check(paths=None):
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

    print(f"\n  {'🐙 MeMOXYDe — Integrity Check':^67}")
    print(f"  {'━'*67}")
    print(f"  {'FILE':<42} {'HASH':^10} {'SNAPSHOT':^10} {'SEVERITY':^10}")
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
        hash_changed = old_hash and current_hash != old_hash
        hash_flag = hash_changed if old_hash else False

        snap_id = hashlib.sha256(rel.encode()).hexdigest()[:12]
        snap_path = SNAPSHOTS_DIR / f"{snap_id}.snap"
        wiki_changed = False
        if snap_path.exists():
            with open(path) as f:
                current_content = f.read()
            with open(snap_path) as f:
                snap_content = f.read()
            snap_body_lines = [
                l for l in snap_content.split("\n")
                if not l.startswith("# Snapshot")
                and not l.startswith("# Created")
                and not l.startswith("# hash")
            ]
            snap_body = "\n".join(snap_body_lines).strip()
            wiki_changed = snap_body != current_content.strip()

        wiki_flag = wiki_changed

        if hash_flag and wiki_flag:
            severity = "🔴CRIT"
            criticals += 1
            flags_raised += 1
            log_flag(rel, "CRITICAL", True, True, "Hash + Snapshot flag: probable corruption")
        elif hash_flag:
            severity = "🟡 WARN"
            flags_raised += 1
            log_flag(rel, "WARNING", True, False, "Hash changed (legitimate edit?) — update hash if intentional")
        elif wiki_flag:
            severity = "🟡 NOTE"
            flags_raised += 1
            log_flag(rel, "NOTE", False, True, "Content changed but hash matches — possible whitespace-only edit")
        else:
            severity = col("✅ OK", "green")

        h_str = col("✅", "green") if not hash_changed else col("🔄", "yellow")
        w_str = col("✅", "green") if not wiki_changed else col("🔄", "yellow")
        if not old_hash:
            h_str = col("📌NEW", "cyan")
            w_str = col("📌NEW", "cyan")
            severity = col("NEW", "cyan")

        if hash_changed and not wiki_changed:
            hashes[rel]["hash"] = current_hash
            hashes[rel]["timestamp"] = datetime.now(timezone.utc).isoformat()
            with open(path) as f:
                new_content = f.read()
            ts = datetime.now(timezone.utc).isoformat()
            with open(snap_path, "w") as f:
                f.write(f"# Snapshot of {rel}\n# Created: {ts}\n# hash: {current_hash}\n\n")
                f.write(new_content)
            h_str = col("✅UPD", "green")

        print(f"  {rel:<42} {h_str:^10} {w_str:^10} {severity:^10}")

    print(f"  {'━'*67}")
    status = col(
        "🔴 CRITICAL" if criticals else ("🟡 FLAGS" if flags_raised else "✅ CLEAN"),
        "red" if criticals else ("yellow" if flags_raised else "green"),
    )
    path_count = len(to_check)
    print(f"  {path_count} files · {col(flags_raised, 'bold')} flag(s) · {col(criticals, 'bold')} critical(s)  Status: {status}")
    print()

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
        ts = e["timestamp"][:19]
        path = e["path"][:40]
        lvl = e["level"]
        verdict_str = f" → {e['verdict']}" if "verdict" in e else ""
        print(f"  {ts} | {lvl:<18} | {e['hash_flag']} {e['wiki_flag']} | {path}{verdict_str}")
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

    cmd_track(test_files)
    cmd_check()

    print(f"  {col('Self-test complete.', 'green')}")


# ── Claim Verification Layer (opt-in, requires ANTHROPIC_API_KEY) ────────────

_VERIFY_SYSTEM_PROMPT = (
    "Sei un verificatore di claim. Ti viene fornito un insieme di documenti "
    "(fonte di verita, hash-verificati) e un'affermazione da controllare.\n"
    'Rispondi SOLO con un oggetto JSON: {"verdict": "GROUNDED"|"CONTRADICTED"|"UNATTESTED", '
    '"evidence": "<citazione breve o nota di assenza>", "confidence": "high"|"medium"|"low"}\n'
    "- GROUNDED: l'affermazione e esplicitamente supportata da almeno un documento.\n"
    "- CONTRADICTED: almeno un documento afferma esplicitamente il contrario.\n"
    "- UNATTESTED: nessun documento conferma ne contraddice l'affermazione.\n"
    "Non inventare fonti. Se il claim non e verificabile con i documenti forniti, usa UNATTESTED."
)


def _call_anthropic_verify(claim: str, sources: dict, model: str) -> dict:
    """
    Call Anthropic Messages API to classify a claim against source documents.
    Uses SDK if available, falls back to stdlib urllib.
    Returns dict with keys: verdict, evidence, confidence.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY not set.\n"
            "  Export it first: export ANTHROPIC_API_KEY=sk-ant-..."
        )

    corpus_parts = []
    for path, content in sources.items():
        corpus_parts.append(f"=== FILE: {path} ===\n{content}\n")
    corpus = "\n".join(corpus_parts)

    user_message = f"DOCUMENTI:\n{corpus}\n\nCLAIM DA VERIFICARE:\n\"{claim}\""

    raw = None

    # Try official SDK first (optional dependency)
    try:
        import anthropic  # type: ignore
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=model,
            max_tokens=256,
            system=_VERIFY_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = msg.content[0].text.strip()
    except ImportError:
        pass  # Fall through to urllib

    # urllib fallback (zero extra deps)
    if raw is None:
        payload = json.dumps(
            {
                "model": model,
                "max_tokens": 256,
                "system": _VERIFY_SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_message}],
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"API HTTP {e.code}: {body[:200]}") from e
        raw = data["content"][0]["text"].strip()

    # Strip markdown code fences if model wraps JSON
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1]).strip() if len(lines) > 2 else raw

    result = json.loads(raw)
    return result


def cmd_verify(claim: str, model: str = DEFAULT_VERIFY_MODEL):
    """
    Verify a claim against hash-clean tracked files via Anthropic API.
    Requires ANTHROPIC_API_KEY environment variable.
    """
    # Quick pre-flight: API key
    if not os.environ.get("ANTHROPIC_API_KEY", ""):
        print(f"  {col('✗ ANTHROPIC_API_KEY not set.', 'red')}")
        print(f"  {col('  Export it first: export ANTHROPIC_API_KEY=sk-ant-...', 'yellow')}")
        sys.exit(1)

    hashes = read_json(HASHES_FILE)
    if not hashes:
        print(f"  {col('No files tracked.', 'yellow')} Run \'track\' first.")
        sys.exit(1)

    # Collect only hash-clean files
    sources = {}
    skipped = []
    truncated = []

    for rel, data in hashes.items():
        path = Path(rel)
        if not path.exists():
            skipped.append(f"{Path(rel).name} (missing)")
            continue
        current_hash = sha256_of(path)
        if current_hash != data.get("hash", ""):
            skipped.append(f"{Path(rel).name} (hash dirty — excluded for safety)")
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            skipped.append(f"{Path(rel).name} (read error: {e})")
            continue
        if len(content) > MAX_FILE_CHARS:
            content = content[:MAX_FILE_CHARS] + f"\n... [TRUNCATED at {MAX_FILE_CHARS} chars]"
            truncated.append(Path(rel).name)
        sources[rel] = content

    if not sources:
        print(f"  {col('No clean files available for verification.', 'yellow')}")
        print(f"  Run \'memoxyde check\' to update hashes first.")
        sys.exit(1)

    # ── Output Header ──
    print(f"\n  {'🐙 MeMOXYDe — Claim Verification':^67}")
    print(f"  {'━'*67}")
    print(f"  CLAIM: {col(repr(claim), 'bold')}")
    print(f"  {'━'*67}")
    file_names = [Path(p).name for p in sources]
    print(f"  Sources checked : {len(sources)} file(s) ({', '.join(file_names)})")
    if truncated:
        print(f"  {col('⚠  Truncated     :', 'yellow')} {', '.join(truncated)} (>{MAX_FILE_CHARS} chars)")
    for s in skipped:
        print(f"  {col('⚠  Skipped        :', 'yellow')} {s}")
    print(f"  Model           : {col(model, 'cyan')}")
    print()
    print(f"  {col('Verifying...', 'cyan')}", flush=True)

    try:
        result = _call_anthropic_verify(claim, sources, model)
    except ValueError as e:
        print(f"  {col(f'✗ {e}', 'red')}")
        sys.exit(1)
    except Exception as e:
        print(f"  {col(f'✗ API error: {e}', 'red')}")
        sys.exit(1)

    verdict = result.get("verdict", "UNATTESTED").upper().strip()
    evidence = result.get("evidence", "—")
    confidence = result.get("confidence", "low")

    # Sanitise verdict — never let free text leak into level field
    if verdict not in ("GROUNDED", "CONTRADICTED", "UNATTESTED"):
        evidence = f"[Non-standard verdict normalised: {verdict}] {evidence}"
        verdict = "UNATTESTED"

    verdict_display = {
        "GROUNDED": col("✅  GROUNDED", "green"),
        "CONTRADICTED": col("🔴 CONTRADICTED", "red"),
        "UNATTESTED": col("⚠️   UNATTESTED", "yellow"),
    }[verdict]

    print(f"  {'━'*67}")
    print(f"  Verdict    : {verdict_display}")
    print(f"  Evidence   : {evidence}")
    print(f"  Confidence : {confidence}")
    print(f"  {'━'*67}")
    print()

    # Log entry
    log_flag(
        path=f"[verify] {claim[:80]}",
        level=f"VERIFY:{verdict}",
        hash_flag=False,
        wiki_flag=False,
        message=f"model={model} confidence={confidence} evidence={evidence[:120]}",
        verdict=verdict,
    )




def cmd_check_ai(paths=None):
    """
    Run check (Layer 1+2) then optionally escalate to AI verify (Layer 3).
    Never calls AI without explicit user confirmation.
    """
    cmd_check._ai_mode = True  # suppress tip, we handle escalation ourselves
    cmd_check(paths)
    cmd_check._ai_mode = False

    hashes = read_json(HASHES_FILE)
    # Check if any flags exist in recent log
    flagged = False
    if FLAGS_FILE.exists():
        with open(FLAGS_FILE) as f:
            lines = [l for l in f if l.strip()]
        if lines:
            try:
                last = [json.loads(l) for l in lines[-5:]]
                flagged = any(
                    e.get("level") in ("CRITICAL", "WARNING", "NOTE", "ERROR")
                    and not e.get("level", "").startswith("VERIFY")
                    for e in last
                )
            except Exception:
                pass

    if not flagged:
        print(f"  {col('✅ No flags — AI escalation not needed.', 'green')}")
        print()
        return

    if not os.environ.get("ANTHROPIC_API_KEY", ""):
        print(f"  {col('⚠ ANTHROPIC_API_KEY not set — cannot escalate to AI layer.', 'yellow')}")
        print()
        return

    print(f"  {col('─'*67, 'yellow')}")
    print(f"  {col('⚠ Flags detected.', 'yellow')} Escalate to AI verification layer? [y/N] ", end="", flush=True)
    try:
        answer = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if answer != "y":
        print(f"  Skipped. You can run {col('memoxyde verify "<claim>"', 'bold')} manually later.")
        print()
        return

    print(f"  Enter the claim to verify: ", end="", flush=True)
    try:
        claim = input().strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if not claim:
        print(f"  {col('Empty claim — skipped.', 'yellow')}")
        return

    print()
    cmd_verify(claim)

# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="🐙 MeMOXYDe — Memory integrity verification for AI agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s track MEMORY.md USER.md      Start tracking files
  %(prog)s check                         Check all tracked files
  %(prog)s check --ai                    Check + offer AI escalation if flags found
  %(prog)s check MEMORY.md               Check specific file
  %(prog)s status                        Show tracked files
  %(prog)s log                           Show recent flags
  %(prog)s untrack MEMORY.md             Stop tracking
  %(prog)s self-test                     Run demo on workspace
  %(prog)s reset                         Clear all tracking data
  %(prog)s verify "claim text"           Verify a claim against tracked files (AI)
  %(prog)s verify "claim" --model haiku  Use Haiku (faster, cheaper)
""",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_track = sub.add_parser("track", help="Register files for tracking")
    p_track.add_argument("paths", nargs="+", help="Files to track")

    p_untrack = sub.add_parser("untrack", help="Remove files from tracking")
    p_untrack.add_argument("paths", nargs="+", help="Files to untrack")

    p_check = sub.add_parser("check", help="Check file integrity (hash + snapshot)")
    p_check.add_argument("paths", nargs="*", help="Optional: check only these files")
    p_check.add_argument(
        "--ai",
        action="store_true",
        help="After check, offer AI escalation (Layer 3) if flags are found (requires ANTHROPIC_API_KEY)",
    )

    sub.add_parser("status", help="Show tracked files")

    p_log = sub.add_parser("log", help="Show flag history")
    p_log.add_argument("-n", type=int, default=20, help="Lines to show (default: 20)")

    sub.add_parser("reset", help="Clear all tracking data")
    sub.add_parser("self-test", help="Run demo on workspace")

    p_verify = sub.add_parser(
        "verify",
        help="Verify a claim against hash-clean tracked files (requires ANTHROPIC_API_KEY)",
    )
    p_verify.add_argument("claim", help="The statement/claim to verify")
    p_verify.add_argument(
        "--model",
        default=DEFAULT_VERIFY_MODEL,
        metavar="MODEL",
        help=(
            f"Anthropic model to use (default: {DEFAULT_VERIFY_MODEL}). "
            "Aliases: 'haiku' → claude-haiku-4-5, "
            "'sonnet' → claude-sonnet-4-5"
        ),
    )

    args = parser.parse_args()

    # Resolve model aliases for verify
    model_aliases = {
        "haiku": "claude-haiku-4-5",
        "sonnet": "claude-sonnet-4-5",
        "opus": "claude-opus-4-5",
    }

    cmds = {
        "track": lambda: cmd_track(args.paths),
        "untrack": lambda: cmd_untrack(args.paths),
        "check": lambda: (
            cmd_check_ai(args.paths if args.paths else None)
            if getattr(args, "ai", False)
            else cmd_check(args.paths if args.paths else None)
        ),
        "status": cmd_status,
        "log": lambda: cmd_log(args.n),
        "reset": cmd_reset,
        "self-test": cmd_self_test,
        "verify": lambda: cmd_verify(
            args.claim,
            model_aliases.get(args.model, args.model),
        ),
    }

    cmds.get(args.command, lambda: parser.print_help())()


if __name__ == "__main__":
    main()
