# DevMemory

DevMemory is a bidirectional RAG knowledge system for coding agents. It automatically searches for proven solutions before you code and saves new ones after you ship — with real code, not abstract descriptions.

## How it works

Before your agent writes a single line of code, DevMemory queries a Pinecone vector database for existing solutions to the problem at hand. If it finds a match (score > 0.6), it shows you the proven code, explains why it worked, and cross-references it with Context7 to make sure the approach is still current.

After you ship something great, DevMemory captures the solution — 20-80 lines of production code, the reasoning behind it, what alternatives were rejected and why — and stores it for your next project.

The result: a project that took 2 months to build now takes 1 week, because every hard-won decision is preserved and reusable.

## The Problem

Most knowledge bases are graveyards of abstract descriptions:

> "Used energy system with regeneration"

DevMemory stores what actually matters:

> **Energy Lazy Regen + Atomic Spend** — Computed energy via `Math.floor(elapsed/tickMs)` at read time. Atomic spend via SQL `WHERE energy >= cost`. Zero race conditions. REJECTED: cron job (15% stale reads at 100 concurrent), Redis INCRBY (didn't survive restart).

Every entry includes: **real code** + **WHY it works** + **what was REJECTED** + **when NOT to use it**.

## Installation

### Quick Install (macOS / Linux)

```bash
curl -sSL https://raw.githubusercontent.com/6zxa9/DevMemory/main/install.sh | bash
```

### Quick Install (Windows PowerShell)

```powershell
irm https://raw.githubusercontent.com/6zxa9/DevMemory/main/install.ps1 | iex
```

### Manual Install

If you prefer to install manually or want to inspect what goes where:

**1. Clone the repo:**

```bash
git clone https://github.com/6zxa9/DevMemory.git
cd DevMemory
```

**2. Copy files to Claude Code directories:**

```bash
# CLI tool
mkdir -p ~/.claude/tools
cp tools/pinecone-store.py ~/.claude/tools/
cp tools/requirements.txt ~/.claude/tools/

# Skill
mkdir -p ~/.claude/skills/rag-knowledge
cp skills/rag-knowledge/SKILL.md ~/.claude/skills/rag-knowledge/

# Rule (auto-activates in every project)
mkdir -p ~/.claude/rules
cp rules/rag-knowledge.md ~/.claude/rules/
```

**3. Install Python dependencies:**

```bash
pip install pinecone python-dotenv
```

### Set Up Pinecone Credentials

Create `~/.claude/tools/.env`:

```env
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_HOST=your_pinecone_host_url
```

### Verify Installation

```bash
python ~/.claude/tools/pinecone-store.py info
```

You should see your index stats with namespace counts. If you see an error, check your `.env` credentials.

DevMemory will now automatically activate in every Claude Code project. No configuration needed.

## The Core Workflow

1. **AUTO-READ** — Before implementing any non-trivial task, DevMemory queries Pinecone for existing solutions with real code.

2. **COMPARE** — Found solutions are cross-referenced with Context7 (live library docs) to check for API changes, deprecations, or better approaches.

3. **SUGGEST** — The agent presents options: use the proven solution, adopt the newer approach, or combine both. Not blind copying — informed choice.

4. **AUTO-WRITE** — After a successful implementation (confirmed by user), DevMemory captures the solution with production code, reasoning, and rejected alternatives.

**These activate automatically.** The rule in `~/.claude/rules/rag-knowledge.md` ensures every project gets this workflow without configuration.

## What Gets Stored

### Design Patterns (`design_patterns` namespace)

Production-proven solutions with code:

```json
{
  "id": "code__energy_lazy_regen_atomic_spend",
  "name": "Energy Lazy Regeneration + Atomic Spend",
  "domain": "economy",
  "description": "CONTEXT: ... WHAT WORKED: ... REJECTED: ... LIMITATIONS: ...",
  "implementation_notes": "FILE: server/src/services/energy.ts\n\n```typescript\nexport async function spendEnergy(playerId, amount) {\n  await regenEnergy(playerId);\n  const result = await db.update(players)\n    .set({ energy: sql`energy - ${amount}` })\n    .where(and(eq(players.id, playerId), gte(players.energy, amount)))\n    .returning({ energy: players.energy });\n  return result.length > 0;\n}\n```\n\nWHY: SQL WHERE makes spend atomic.\nREJECTED: cron job (race conditions)."
}
```

### Dev Lessons (`dev_lessons` namespace)

Production bugs with root cause and prevention:

```json
{
  "id": "bug__redis_eviction_leaderboard",
  "title": "Redis allkeys-lru evicts leaderboard data",
  "pattern": "allkeys-lru evicts sorted sets under load",
  "rule": "Set noeviction, add backfill on startup",
  "context": "Full incident story with fix code...",
  "severity": "critical"
}
```

### Also available

| Namespace | Contents |
|-----------|----------|
| `competitors` | Competitive scans (tech, API, gameplay) |
| `game_audits` | Game audit scorecards (10 dimensions) |
| `project_docs` | Key project documents (GDD, specs) |

## Quality Principles

**Store:**
- Solutions with concrete code, proven in production
- Non-obvious platform workarounds
- Formulas and numbers found through iteration
- Architectural decisions with rationale and rejected alternatives

**Don't store:**
- Obvious things from documentation
- Code without "why" context
- Intermediate/untested solutions
- Standard CRUD patterns

**The test:** If this entry saves 2+ days of work 6 months from now — store it. If not — don't pollute the base.

## CLI Reference

```bash
# Search (READ)
python ~/.claude/tools/pinecone-store.py query "energy system" --ns all -v
python ~/.claude/tools/pinecone-store.py query "race condition" --ns dev_lessons --json

# Store (WRITE)
python ~/.claude/tools/pinecone-store.py store-patterns /tmp/patterns.json
python ~/.claude/tools/pinecone-store.py store-lessons /tmp/lessons.json
python ~/.claude/tools/pinecone-store.py store-audit /tmp/audit.json
python ~/.claude/tools/pinecone-store.py store-docs /tmp/doc.md

# Manage
python ~/.claude/tools/pinecone-store.py info
python ~/.claude/tools/pinecone-store.py list --ns design_patterns
python ~/.claude/tools/pinecone-store.py delete --id "old_entry"
python ~/.claude/tools/pinecone-store.py delete --prefix "deprecated_"
```

## What's Inside

### Skill

- **rag-knowledge** — Bidirectional RAG workflow: AUTO-READ before tasks, AUTO-WRITE after success, COMPARE with Context7 for freshness

### Rule

- **rag-knowledge.md** — Global rule that activates the skill in every project automatically

### CLI Tool

- **pinecone-store.py** — Full-featured Pinecone CLI with 5 namespaces, batch upsert, `_text` metadata for RAG retrieval, `--json` output, `--filter`, delete, list commands

## Philosophy

- **Code over descriptions** — Every entry includes 20-80 lines of real production code
- **WHY over WHAT** — Not just what was built, but why this approach and what was rejected
- **Verify before trust** — Cross-reference with Context7 to catch outdated patterns
- **Quality over quantity** — One entry that saves 2 days > ten entries that save 2 minutes
- **Production-proven only** — No theoretical solutions, no untested code

## Pinecone Setup

DevMemory uses [Pinecone](https://www.pinecone.io/) as its vector database with the `Multilingual_E5_Large` embedding model (hosted by Pinecone).

### Creating an index

1. Sign up at [pinecone.io](https://www.pinecone.io/)
2. Create an index with:
   - **Dimensions:** 1024
   - **Metric:** cosine
   - **Embedding model:** Multilingual_E5_Large (Pinecone hosted)
3. Copy your API key and host URL to `~/.claude/tools/.env`

## Contributing

1. Fork the repository
2. Add your patterns/improvements
3. Follow the entry format in [`docs/ENTRY-FORMAT.md`](docs/ENTRY-FORMAT.md)
4. Submit a PR

## License

MIT License — see [LICENSE](LICENSE) file for details.
