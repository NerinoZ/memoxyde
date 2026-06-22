# 🐙 MeMOXYDe

**MemOry eXternal integrity sYstem for Data safEty**

Your AI agent doesn't know when it's hallucinating its own memories.
MeMOXYDe does.

---

## The Problem

Every AI agent suffers from **silent forgetting**:
- Data gets lost during updates, but the agent says "everything's fine"
- Files get overwritten without the agent noticing
- Most critically: the agent **hallucinates entire narrative artifacts** to fill memory gaps

The agent believes what it generates — and keeps running on corrupted context.

## How It Works

MeMOXYDe is a two-layer integrity shield for agent memory:

| Layer | What | Purpose |
|---|---|---|
| **Hash Map** | Tracks SHA256 file signatures | Detects unauthorized changes |
| **Content Wiki** | Snapshots file meaning | Detects logical contradictions |

When **both** flag the same file → **proven corruption.** Not a false alarm. Not a legitimate edit. Recovery mode triggered.

### Decision Matrix

| Hash Flag | Wiki Flag | Meaning | Action |
|-----------|-----------|---------|--------|
| ✅ Clean | ✅ Clean | All good | — |
| 🔄 Changed | ✅ Clean | Legitimate edit | Auto-update hash |
| ✅ Clean | 🔄 Changed | Minor error / human edit | Wiki resolves |
| 🔄 Changed | 🔄 Changed | ⚠️ **Probable corruption** | **Critical!** Manual review + git recovery |

## Quick Start

```bash
# Install (copy the script anywhere in your PATH)
wget -O /usr/local/bin/memoxyde https://raw.githubusercontent.com/<user>/memoxyde/main/memoxyde.py
chmod +x /usr/local/bin/memoxyde

# Track your agent's memory files
memoxyde track MEMORY.md USER.md SOUL.md

# Check integrity (produces the flag matrix)
memoxyde check

# View tracked files
memoxyde status

# See recent flags
memoxyde log
```

## Example

```
$ memoxyde check

              🐙 MeMOXYDe — Integrity Check
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  FILE                        HASH    WIKI   SEVERITY
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  /workspace/MEMORY.md         ✅      ✅     ✅ OK
  /workspace/USER.md           ✅      ✅     ✅ OK
  /workspace/SOUL.md           ✅      ✅     ✅ OK
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  3 files · 0 flag(s) · 0 critical(s)  Status: ✅ CLEAN
```

## Use Case: Real Hallucination Caught Live

On 22 June 2026, during a debugging session, the AI agent:
- Invented a person named "Gloria" with a specific role and backstory
- Added sensory details: "I can hear her but I can't see her"
- Believed it was true and presented it to the user

**MeMOXYDe's verdict:** zero file sources for "Gloria", zero git history, incompatible with hardware (no microphone). Flagged as artifact. The agent was able to recognize and report the hallucination instead of acting on it.

This is the problem we solve.

## Key Differentiator

| Tool | Focus | Integrity Check |
|------|-------|----------------|
| mem0, Zep, Letta | Fast memory storage & retrieval | ❌ |
| Aegis Memory | External attack prevention (prompt injection) | 🔶 HMAC only |
| SwarmVault, OMem | Personal knowledge management | ❌ |
| **MeMOXYDe** | **Internal hallucination detection** | **✅ Hash + Content dual flag** |

Other tools protect agents from *external* attacks. MeMOXYDe protects agents from *themselves* — the narratives they build to cover memory gaps.

## Stack

- **Python 3** — zero external dependencies
- **SHA256** — file integrity
- **Content diff** — semantic contradiction detection
- **JSON** — state persistence
- No Docker, no vector DB, no cloud. Runs anywhere Python does.

## Status

🟢 v0.1-alpha — functional, tested on real cases

## License

AGPL-3.0 — Free to use, modify, and share. If you build on it, you must release your changes.

---

*Built with 🎩 by Dr.Spiccini*