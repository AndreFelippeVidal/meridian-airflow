# Engineering standards

The rules that make every repo in this portfolio look like one engineer's deliberate work.
Recruiters skim across repos — consistency is the signal.

## README (fixed section order, never reorder)
1. Title + one-line value prop (written for an 8-second skim)
2. Badges (CI, Python, license) + live demo / write-up links + demo GIF
3. **Why this exists** — the problem and what a senior cares about (scale, cost, correctness, observability)
4. **Architecture** — a Mermaid diagram + link to ADRs
5. **Stack** — table of tool → why
6. **Quickstart** — `make setup / test / run`
7. **What I learned** — the honest tradeoffs. This is the differentiator. Never leave it as a placeholder.
8. Roadmap / status

## Diagrams
- Mermaid in the README (renders on GitHub, zero tooling).
- One "hero" diagram per project; Excalidraw is fine for that if you want something richer. Commit the source.

## ADRs (Architecture Decision Records)
- One short file per non-obvious decision in `docs/adr/`, MADR-style: Context → Decision → Consequences.
- Use the `/adr` command. Status starts Proposed, becomes Accepted on merge.
- ADRs are where you *show your architectural reasoning* — they matter more than the code to a hiring manager.

## Code quality (non-negotiable, enforced by CI)
- `uv` for env/deps, `ruff` for lint+format, `mypy --strict` for types, `pytest` for tests.
- pre-commit must pass locally; CI must be green before a commit is "done".
- gitleaks scans for secrets. A committed credential is an automatic credibility hit — never do it.

## The domain
- One fictional company, **Meridian** (online marketplace), shared across every project.
- All synthetic data flows from a single `meridian.synthetic` module so ids/skus/events align platform-wide.

## Definition of done
CI green · README complete incl. diagram · ADR(s) for key choices · a demo (GIF or live link)
· a vault note capturing learnings · a LinkedIn draft. Only then is it shippable.
