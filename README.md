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
| **Hash Map** | Tracks SHA256 file signatures | Detects unauthorized byte-level changes |
| **Content Snapshot** | Exact-content comparison against last known-good state | Distinguishes whitespace-only edits from real content changes |

When **both** flag the same file → **proven corruption.** Not a false alarm. Not a legitimate edit. Recovery mode triggered.

> **Note:** Content Snapshot is a byte-exact diff, not semantic analysis. For semantic claim verification, see [`verify`](#claim-verification-layer-opt-in).

### Decision Matrix

| Hash Flag | Snapshot Flag | Meaning | Action |
|-----------|---------------|---------|--------|
| ✅ Clean | ✅ Clean | All good | — |
| 🔄 Changed | ✅ Clean | Legitimate edit | Auto-update hash |
| ✅ Clean | 🔄 Changed | Whitespace/cosmetic edit | Snapshot resolves |
| 🔄 Changed | 🔄 Changed | ⚠️ **Probable corruption** | **Critical!** Manual review + git recovery |

## Quick Start

```bash
# Install (copy the script anywhere in your PATH)
wget -O /usr/local/bin/memoxyde https://raw.githubusercontent.com/NerinoZ/memoxyde/main/memoxyde.py
chmod +x /usr/local/bin/memoxyde

# Track your agent's memory files
memoxyde track MEMORY.md USER.md SOUL.md

# Check integrity (Layers 1+2 only, zero API calls)
memoxyde check

# Check + offer AI escalation if flags are found
memoxyde check --ai

# Verify a specific claim against tracked files (Layer 3, requires ANTHROPIC_API_KEY)
memoxyde verify "The user's name is Dee and they live in Rome"
```

## Example

```
$ memoxyde check

              🐙 MeMOXYDe — Integrity Check
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  FILE                        HASH   SNAPSHOT  SEVERITY
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  /workspace/MEMORY.md         ✅      ✅     ✅ OK
  /workspace/USER.md           ✅      ✅     ✅ OK
  /workspace/SOUL.md           ✅      ✅     ✅ OK
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  3 files · 0 flag(s) · 0 critical(s)  Status: ✅ CLEAN
```

## Claim Verification Layer (opt-in)

`memoxyde verify` is a semantic layer that checks whether an agent-generated statement is supported, contradicted, or absent in your hash-clean tracked files.

Unlike the Hash and Snapshot layers (which detect *file changes*), `verify` answers a different question: **does this thing my agent just said actually exist in the trusted corpus?**

### The AI layer is always opt-in — even with a key

Having `ANTHROPIC_API_KEY` set does **not** make MeMOXYDe call the API automatically. You are always in control:

```
memoxyde check          →  Layers 1+2 only. Zero API calls. Zero cost.
                            If flags found: prints a tip suggesting verify.

memoxyde check --ai     →  Layers 1+2, then asks:
                            "Flags detected. Escalate to AI layer? [y/N]"
                            Only calls API if you answer y.

memoxyde verify "..."   →  Layer 3 directly on a specific claim.
```

```
$ memoxyde verify "The agent heard Gloria but cannot see her"

  🐙 MeMOXYDe — Claim Verification
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CLAIM: "The agent heard Gloria but cannot see her"
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Sources checked: 3 file(s) (MEMORY.md, USER.md, SOUL.md)
  Model: claude-sonnet-4-5

  Verifying...
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Verdict    : ⚠️  UNATTESTED
  Evidence   : No mention of "Gloria" in any tracked file.
  Confidence : high
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Three possible verdicts:
- **GROUNDED** — explicit source found in tracked files
- **CONTRADICTED** — a tracked file explicitly says the opposite
- **UNATTESTED** — no source either way (the most insidious case — the agent treats it as true with zero backing)

### Requirements

- `ANTHROPIC_API_KEY` environment variable (only for Layer 3)
- Default model: `claude-sonnet-4-5`
- Cheaper option: `--model haiku`
- Only verifies against **hash-clean** files (dirty files are excluded for safety)

## Use Case: Real Hallucination Caught Live

On 22 June 2026, during a debugging session, the AI agent invented a person named "Gloria" — complete with role, backstory, and sensory details. No source on disk. No git history. Hardware-incompatible claim.

See [PROVENANCE.md](PROVENANCE.md) for the full story.

## Key Differentiator

| Tool | Focus | Integrity Check |
|------|-------|----------------|
| mem0, Zep, Letta | Fast memory storage & retrieval | ❌ |
| Aegis Memory | External attack prevention (prompt injection) | 🔶 HMAC only |
| SwarmVault, OMem | Personal knowledge management | ❌ |
| **MeMOXYDe** | **Internal hallucination detection** | **✅ Hash + Snapshot + AI Claim Verify** |

Other tools protect agents from *external* attacks. MeMOXYDe protects agents from *themselves*.

## Stack

- **Python 3** — zero required external dependencies
- **SHA256** — file integrity (Layer 1)
- **Content diff** — exact-content snapshot comparison (Layer 2)
- **Anthropic API** — semantic claim verification, always opt-in (Layer 3)
- **JSON** — state persistence
- No Docker, no vector DB, no cloud for Layers 1–2. Runs anywhere Python does.

## Status

🟢 v0.2-alpha — `verify` and `check --ai` escalation added

## License

Apache 2.0 — Free to use, modify, and distribute, including in commercial products. Attribution required.

---

*Built with 🎩 Dr.Spiccini*
