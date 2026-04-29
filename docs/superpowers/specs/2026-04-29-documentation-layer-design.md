# Documentation Layer — Design Spec

> **Approved:** 2026-04-29

## Context

Pump Trader v3.0 is an async Python trading bot that grew organically from a Windows 10 dev environment into a complex, multi-subsystem codebase (FastAPI C&C hub, async trading engine, AI/LLM decisions, RL + GA optimizers, PostgreSQL + pgvector). The project is currently running temporarily on macOS 12 (old iMac, CPU-only torch, no CUDA).

The existing `CLAUDE.md` (5.5 KB) mixes quick-start instructions with deep architectural detail. As the codebase grows this doesn't scale — Claude loads everything on every interaction, and the details crowd out the rules. A whole documentation layer is missing: no module READMEs, no API docs, no DB schema docs, no deployment guide, no architecture diagrams.

**Why this change:** Moving to a lean CLAUDE.md index + `docs/` folder means Claude only loads relevant details when doing module-specific work, and human contributors have a clear place to look for each type of information.

**Intended outcome:** Claude Code navigates the codebase confidently, respects known constraints (especially the GlobalState rules and simulate-only development), and understands what is and isn't yet implemented.

**Explicitly out of scope:** No code changes, no refactoring, no new dependencies. Documentation only.

## Approach: Lean index + targeted `docs/` folder

CLAUDE.md becomes a ~2 KB navigation file. A `docs/` folder holds 5 focused documents. Every file uses a consistent `> **TODO:**` annotation convention to flag known gaps.

### Annotation convention

```
> **TODO:** Description of the gap and intended fix direction.
> **NOTE (macOS 12):** Platform-specific callout.
> **WARNING:** Behavior that will surprise a reader without context.
```

## Files

| File | Action | Target size |
|------|--------|-------------|
| `CLAUDE.md` | Modify (restructure to lean index) | ~2 KB |
| `docs/ARCHITECTURE.md` | Create | ~3 KB |
| `docs/DATABASE.md` | Create | ~2 KB |
| `docs/MODULES.md` | Create | ~3 KB |
| `docs/DEVELOPMENT.md` | Create | ~2.5 KB |
| `docs/ROADMAP.md` | Create | ~2 KB |

## Verification

1. `wc -c CLAUDE.md` < 2,500 bytes
2. `ls -lh docs/` shows 5 files, all non-empty
3. Each `docs/` file contains at least one `> **TODO:**` block
4. `python main.py` starts cleanly in simulate mode
