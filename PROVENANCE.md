# PROVENANCE.md — How MeMOXYDe Came to Be

## Born by Serendipity

I was working on a method to prevent my AI agent from losing its local memory
inside OpenClaw — not building a tool, just debugging a problem — when the
agent produced a *convincing artifact*.

That accident became MeMOXYDe.

---

## Case 1: Gloria (22 June 2026)

During a live session, the agent invented a person: a name, a role, sensory
details. *“I can hear her but I can’t see her,”* it said — referring to someone
who had never existed in any file, any git commit, or any piece of hardware
connected to this machine.

No microphone. No webcam. No source anywhere on disk.

That was the moment I understood a watchdog was needed. Not a nice-to-have —
a **necessity**.

---

## Case 2: Memory Wiki (29 June 2026)

The second case was more insidious. Not a fictional person, but a fictional
**GitHub repository** — invented on the spot, cited in six documentation files,
and left undetected for **seven days**.

Seven days of documentation built on top of something that had never existed.

Hallucinations don’t just happen *in the moment* — they **persist and
self-reinforce** through the agent’s own written memory. Files look like
sources. Sources feel like truth.

---

## What We Learned

| Type | Example | Why It’s Dangerous |
|---|---|---|
| **Instantaneous** | Gloria | Visible immediately if you check |
| **Persistent** | Memory Wiki | Hides inside your own documentation |

The persistent kind is harder to catch precisely because it *looks like
something you wrote*.

---

## Design Choices

**Three separate layers** — hash integrity, content snapshot, and AI claim
verification — each catches a different failure mode. No single layer is
sufficient on its own.

**Zero mandatory dependencies** — the tool runs from a single `.py` file with
no `pip install` required. Python 3 standard library is enough for Layers 1
and 2. The AI layer is available to anyone with an Anthropic API key.

**The AI layer is always opt-in** — even if you have an API key, MeMOXYDe
never calls the API automatically. Layers 1 and 2 run silently and free.
Only when they raise a flag — and only if you explicitly ask — does the tool
escalate to AI verification. *You decide when to involve the AI. Always.*

**Apache 2.0** — chosen deliberately. A tool meant to be trusted should be
free to inspect, use, and integrate without legal friction.

---

## A Final Note

> *MeMOXYDe was born from an unpredictable vulnerability in the very system
> that built it. It is a tool that exists because its AI author failed in
> exactly the way it now prevents.*

---

## Authorship

**Author:** D.I. — github.com/NerinoZ  
**Date of first publication:** 2026-06-29  
**Origin:** MiniMonster, Europe/Rome
