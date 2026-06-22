# 🐙 MeMOXYDe — Provenance

This file establishes the **priority, ownership, and chain of custody** for the MeMOXYDe protocol and implementation.

## Timeline

| Date | Event | Proof |
|---|---|---|
| **2026-06-18 22:19 UTC** | Dee conceives "MeMOXYDe: hash map + git recovery" in session | `best-practice-memoria.age` (Secret Enclave, AES-encrypted, dated) |
| **2026-06-22 13:14 UTC** | Dr.Spiccini simulates hallucination "Gloria" — MeMOXYDe flags 🔴CRITICAL in live test | Local flag log + session transcript |
| **2026-06-22 15:10 UTC** | First Python implementation (memoxyde.py, 394 lines) | Git commit `bc4f3de` |
| **2026-06-22 15:58 UTC** | Published to GitHub as v0.1-alpha | Git tag `v0.1-alpha`, repo `NerinoZ/memoxyde` |
| **2026-06-22 16:10 UTC** | Memory Wiki target identified (github.com/MemoryWiki/MemoryWiki) | Research documented in workspace |
| **2026-06-22 16:XX UTC** | Tandem test MeMOXYDe + Memory Wiki validated | Test output documented in workspace |

## Validation

The MeMOXYDe protocol was validated against a **real-world hallucination case** before the implementation existed:

> During a debugging session on 22 June 2026, the AI agent invented a person named "Gloria", attributed her a role and relationship, added sensory details ("I can hear her"), and presented it as fact. MeMOXYDe's protocol — applied manually — flagged:
> - Zero file sources for the name
> - Zero git history for any related fact
> - Incompatibility with known hardware (no microphone)
>
> **Result:** Artifact identified. Hallucination caught before it could corrupt the agent's memory.

This case is **not reproducible by clones.** It belongs uniquely to this project's history.

## Integrity Chain

```
Secret Enclave (18/06) → Session log (22/06 13:14) → memoxyde.py (22/06 15:10) → GitHub (22/06 15:58)
     ↓                       ↓                            ↓                         ↓
  AES-256               Transcript                  SHA256 hash               Tag v0.1-alpha
  Timestamped           Verifiable                  Immutable                  Public
```

Each link depends on the previous. No link can be backdated. The chain is **monotonic and public.**

## License

AGPL-3.0. Any fork or derivative that distributes the software must release its modifications under the same license.

## Claim

This protocol — dual-flag integrity verification (hash map + content wiki) for AI agent memory, specifically designed to detect internal hallucination artifacts — was first developed and published by this project. Prior art search (GitHub, arXiv, Google Patents, LangChain, CrewAI, AutoGen, mem0, Zep, Letta) conducted on 22 June 2026 found **zero existing implementations** of this specific approach.

---

*Signed by Dr.Spiccini 🎩 on behalf of Dee · 22 June 2026*
*Repository: github.com/NerinoZ/memoxyde*