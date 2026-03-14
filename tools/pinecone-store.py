#!/usr/bin/env python3
"""
Pinecone Vector Storage — Global RAG Knowledge Base

Namespaces:
  competitors      — competitor scan data (tech, API, gameplay)
  game_audits      — game audit findings (10 dimensions)
  dev_lessons      — development patterns, bugs, solutions
  design_patterns  — game design patterns (retention, economy, UX)
  project_docs     — key project documents (GDD, masterplan, specs)

Usage:
  # Store
  python pinecone-store.py store data/competitor.json          # competitors
  python pinecone-store.py store-audit audit.json              # game_audits
  python pinecone-store.py store-lessons lessons.json          # dev_lessons
  python pinecone-store.py store-patterns patterns.json        # design_patterns
  python pinecone-store.py store-docs doc/file.md              # project_docs

  # Query
  python pinecone-store.py query "retention mechanics" --ns all -v
  python pinecone-store.py query "Redis bugs" --ns dev_lessons --json
  python pinecone-store.py query "tech stack" --filter competitor=webapp_duckmyduck_com

  # Manage
  python pinecone-store.py info
  python pinecone-store.py list --ns design_patterns
  python pinecone-store.py delete --id "pattern__old_entry"
  python pinecone-store.py delete --ns dev_lessons --prefix "lesson__old_"
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

# Fix #2: Unicode on Windows (cp1251/cp1252 → utf-8)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from pinecone import Pinecone, EmbedModel

PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
PINECONE_HOST = os.environ["PINECONE_HOST"]

# All available namespaces
NS_COMPETITORS = "competitors"
NS_AUDITS = "game_audits"
NS_LESSONS = "dev_lessons"
NS_PATTERNS = "design_patterns"
NS_DOCS = "project_docs"
ALL_NAMESPACES = [NS_COMPETITORS, NS_AUDITS, NS_LESSONS, NS_PATTERNS, NS_DOCS]

# Fix #4: Pinecone upsert batch limit
UPSERT_BATCH_SIZE = 96

# Fix #6: Max metadata text size (Pinecone limit ~40KB per vector metadata)
MAX_TEXT_IN_METADATA = 9000


def _client():
    pc = Pinecone(api_key=PINECONE_API_KEY)
    idx = pc.Index(host=PINECONE_HOST)
    return pc, idx


def _embed_and_upsert(pc, idx, chunks: list[dict], namespace: str):
    """Embed texts and upsert to Pinecone with batching."""
    if not chunks:
        return

    # Fix #6: Store text in metadata for RAG retrieval
    for c in chunks:
        c["metadata"]["_text"] = c["text"][:MAX_TEXT_IN_METADATA]

    texts = [c["text"] for c in chunks]
    print(f"  Embedding {len(texts)} chunks into '{namespace}'...")
    emb = pc.inference.embed(
        model=EmbedModel.Multilingual_E5_Large,
        inputs=texts,
        parameters={"input_type": "passage", "truncate": "END"},
    )
    vectors = [(c["id"], emb.data[i].values, c["metadata"]) for i, c in enumerate(chunks)]

    # Fix #4: Batch upsert
    for batch_start in range(0, len(vectors), UPSERT_BATCH_SIZE):
        batch = vectors[batch_start : batch_start + UPSERT_BATCH_SIZE]
        idx.upsert(vectors=batch, namespace=namespace)

    print(f"  Upserted {len(vectors)} vectors:")
    for v in vectors:
        print(f"    {v[0]}")


def _slug(text: str) -> str:
    """Convert text to a safe ID slug."""
    return re.sub(r"[^a-zA-Z0-9]", "_", text)[:80]


def _safe_join(val) -> str:
    if isinstance(val, list):
        return ", ".join(str(v) for v in val)
    if isinstance(val, str):
        return val
    return str(val) if val else ""


# ══════════════════════════════════════════════════════════════════════════════
# NS: competitors (existing logic)
# ══════════════════════════════════════════════════════════════════════════════

def _competitor_chunks(data: dict) -> list[dict]:
    domain = data.get("domain", "unknown")
    url = data.get("url", "")
    base_meta = {"competitor": domain, "url": url, "scan_date": data.get("scan_date", "")}
    chunks = []

    # L1: overview
    tech_lines = [f"{c}: {', '.join(t.keys())}" for c, t in data.get("tech_stack", {}).items()]
    overview = (
        f"Competitor: {domain}\nURL: {url}\n"
        f"Title: {data.get('page_info', {}).get('title', '')}\n"
        f"Tech: {'; '.join(tech_lines)}\n"
        f"API endpoints: {len(data.get('api_endpoints', []))}\n"
        f"Methods: {', '.join(data.get('methods_used', []))}\n"
        f"Domains: {', '.join(data.get('page_info', {}).get('request_domains', []))}"
    )
    chunks.append({
        "id": f"{domain}__overview",
        "text": overview,
        "metadata": {**base_meta, "category": "overview", "level": "overview"},
    })

    # L2: tech stack
    if data.get("tech_stack"):
        detail = json.dumps(data["tech_stack"], indent=2, ensure_ascii=False)
        chunks.append({
            "id": f"{domain}__tech_stack",
            "text": f"Tech stack for {domain}:\n{detail}",
            "metadata": {**base_meta, "category": "tech_stack", "level": "detail",
                         "raw": detail[:9_000]},
        })

    # L2: API endpoints
    if data.get("api_endpoints"):
        lines = [f"API endpoints for {domain}:"]
        for ep in data["api_endpoints"][:30]:
            line = f"  {ep.get('method','GET')} {ep.get('path','')} -> {ep.get('status','?')}"
            sample = ep.get("response_sample")
            if sample:
                line += f"\n    {json.dumps(sample, ensure_ascii=False)[:500]}"
            lines.append(line)
        chunks.append({
            "id": f"{domain}__api",
            "text": "\n".join(lines),
            "metadata": {**base_meta, "category": "api_structure", "level": "detail",
                         "count": str(len(data["api_endpoints"]))},
        })

    # L2: API replay
    if data.get("api_replay_results"):
        lines = [f"API replay for {domain}:"]
        for r in data["api_replay_results"]:
            s = r.get("status", "err")
            lines.append(f"  {r.get('method','?')} {r.get('url','')} -> {s}")
            if r.get("response"):
                resp_str = json.dumps(r["response"], ensure_ascii=False) if isinstance(r["response"], dict) else str(r["response"])
                lines.append(f"    {resp_str[:500]}")
        chunks.append({
            "id": f"{domain}__api_replay",
            "text": "\n".join(lines),
            "metadata": {**base_meta, "category": "api_structure", "level": "detail", "type": "replay",
                         "ok": str(sum(1 for x in data["api_replay_results"] if x.get("status", 0) < 400))},
        })

    # L2: network patterns
    if data.get("network_requests"):
        by_type = {}
        domains_set = set()
        for req in data["network_requests"]:
            rt = req.get("resource_type", "other")
            by_type[rt] = by_type.get(rt, 0) + 1
            netloc = urlparse(req.get("url", "")).netloc
            if netloc:
                domains_set.add(netloc)
        chunks.append({
            "id": f"{domain}__network",
            "text": (f"Network for {domain}:\nTypes: {json.dumps(by_type)}\n"
                     f"Domains: {', '.join(sorted(domains_set))}\nTotal: {len(data['network_requests'])}"),
            "metadata": {**base_meta, "category": "network", "level": "detail"},
        })

    # L2: page content
    pi = data.get("page_info", {})
    if pi:
        chunks.append({
            "id": f"{domain}__page",
            "text": (f"Page for {domain}:\nTitle: {pi.get('title','')}\n"
                     f"HTML size: {pi.get('html_length',0)}\n"
                     f"Scripts: {len(pi.get('script_urls',[]))}\n"
                     f"Meta: {json.dumps(pi.get('meta_tags',[])[:20], ensure_ascii=False)}"),
            "metadata": {**base_meta, "category": "page", "level": "detail"},
        })

    # L2: game info (enriched)
    gi = data.get("game_info", {})
    if gi:
        gi_text = (
            f"Game info for {domain}:\n"
            f"Name: {gi.get('name','')}\nGenre: {gi.get('genre','')}\n"
            f"Description: {gi.get('description','')}\n"
            f"MAU: {gi.get('mau','')}\nGrowth: {gi.get('growth','')}\n"
            f"Status: {gi.get('status','')}\nTeam: {gi.get('team','')}\n"
            f"Bot: {gi.get('bot','')}"
        )
        chunks.append({
            "id": f"{domain}__game_info",
            "text": gi_text,
            "metadata": {**base_meta, "category": "game_info", "level": "detail",
                         "genre": gi.get("genre", ""), "mau": gi.get("mau", "")},
        })

    # L2: gameplay mechanics (enriched)
    gp = data.get("gameplay", {})
    if gp:
        econ = gp.get("economy", {}) if isinstance(gp.get("economy"), dict) else {}
        soc = gp.get("social", {}) if isinstance(gp.get("social"), dict) else {}
        ret = gp.get("retention", {}) if isinstance(gp.get("retention"), dict) else {}
        mon = gp.get("monetization", {}) if isinstance(gp.get("monetization"), dict) else {}

        gp_text = (
            f"Gameplay for {domain}:\n"
            f"Core loop: {gp.get('core_loop','')}\n"
            f"Currencies: {_safe_join(econ.get('currencies',[]))}\n"
            f"Earning: {_safe_join(econ.get('earning',[]))}\n"
            f"Spending: {_safe_join(econ.get('spending',[]))}\n"
            f"Sinks: {_safe_join(econ.get('sinks',[]))}\n"
            f"Progression: {gp.get('progression',{}).get('system','') if isinstance(gp.get('progression'), dict) else gp.get('progression','')}\n"
            f"Social key mechanic: {soc.get('key_mechanic','')}\n"
            f"Social features: {_safe_join(soc.get('features',[]))}\n"
            f"Retention timers: {_safe_join(ret.get('timers',[]))}\n"
            f"Retention hooks: {_safe_join(ret.get('hooks',[]))}\n"
            f"Monetization model: {mon.get('model','')}\n"
            f"Revenue streams: {_safe_join(mon.get('revenue_streams',[]))}"
        )
        chunks.append({
            "id": f"{domain}__gameplay",
            "text": gp_text,
            "metadata": {**base_meta, "category": "gameplay", "level": "detail",
                         "core_loop": gp.get("core_loop", "")[:500]},
        })

    # L2: reviews (enriched)
    rev = data.get("reviews", {})
    if rev:
        rev_text = (
            f"Reviews for {domain}:\n"
            f"Rating: {rev.get('coinspot_rating','')}\n"
            f"Positive: {', '.join(rev.get('positive',[]))}\n"
            f"Negative: {', '.join(rev.get('negative',[]))}"
        )
        chunks.append({
            "id": f"{domain}__reviews",
            "text": rev_text,
            "metadata": {**base_meta, "category": "reviews", "level": "detail",
                         "rating": rev.get("coinspot_rating", "")},
        })

    return chunks


# ══════════════════════════════════════════════════════════════════════════════
# NS: game_audits
# ══════════════════════════════════════════════════════════════════════════════

def _audit_chunks(data: dict) -> list[dict]:
    game = data.get("game", "unknown")
    date = data.get("date", "")
    slug = _slug(f"{game}_{date}")
    base_meta = {
        "game": game, "audit_date": date,
        "version": data.get("version", ""),
        "verdict": data.get("verdict", ""),
    }
    chunks = []

    # L1: overview scorecard
    dims = data.get("dimensions", [])
    dim_lines = [f"  {d['name']}: {d.get('score','?')}/10" for d in dims]
    overview = (
        f"Game Audit: {game} ({date})\n"
        f"Version: {data.get('version','')}\n"
        f"Verdict: {data.get('verdict','')}\n"
        f"Overall: {data.get('overall_score','?')}/10\n"
        f"Scores:\n" + "\n".join(dim_lines) + "\n"
        f"Top wins: {', '.join(data.get('top_wins',[]))}\n"
        f"Critical fixes: {', '.join(data.get('critical_fixes',[]))}"
    )
    chunks.append({
        "id": f"audit__{slug}__overview",
        "text": overview,
        "metadata": {**base_meta, "category": "overview", "level": "overview",
                     "overall_score": str(data.get("overall_score", ""))},
    })

    # L2: each dimension
    for d in dims:
        dim_name = d.get("name", "unknown")
        dim_slug = _slug(dim_name)
        problems_text = ""
        for p in d.get("problems", []):
            problems_text += f"\n  - {p.get('description','')} (impact: {p.get('impact','')}, effort: {p.get('effort','')})"

        dim_text = (
            f"Audit dimension '{dim_name}' for {game} ({date}):\n"
            f"Score: {d.get('score','?')}/10\n"
            f"Observations: {'; '.join(d.get('observations',[]))}\n"
            f"Problems:{problems_text}\n"
            f"Recommendations: {'; '.join(d.get('recommendations',[]))}\n"
            f"References: {'; '.join(d.get('references',[]))}"
        )
        chunks.append({
            "id": f"audit__{slug}__{dim_slug}",
            "text": dim_text,
            "metadata": {**base_meta, "category": f"dimension_{dim_slug}", "level": "detail",
                         "dimension": dim_name, "score": str(d.get("score", ""))},
        })

    # L2: action plan
    ap = data.get("action_plan", {})
    if ap:
        lines = []
        for priority, items in ap.items():
            for item in (items if isinstance(items, list) else [items]):
                lines.append(f"  [{priority.upper()}] {item}")
        if lines:
            chunks.append({
                "id": f"audit__{slug}__action_plan",
                "text": f"Action plan for {game} ({date}):\n" + "\n".join(lines),
                "metadata": {**base_meta, "category": "action_plan", "level": "detail"},
            })

    return chunks


# ══════════════════════════════════════════════════════════════════════════════
# NS: dev_lessons
# ══════════════════════════════════════════════════════════════════════════════

def _lesson_chunks(data: dict) -> list[dict]:
    project = data.get("project", "unknown")
    date = data.get("date", "")
    chunks = []

    lessons = data.get("lessons", [])
    cats = {}
    for l in lessons:
        cat = l.get("category", "general")
        cats[cat] = cats.get(cat, 0) + 1

    # L1: overview
    overview = (
        f"Development lessons for {project} ({date}):\n"
        f"Total lessons: {len(lessons)}\n"
        f"Categories: {json.dumps(cats)}\n"
        f"Topics: {', '.join(l.get('title','')[:60] for l in lessons[:15])}"
    )
    chunks.append({
        "id": f"lessons__{_slug(project)}__overview",
        "text": overview,
        "metadata": {"project": project, "date": date, "category": "overview",
                     "level": "overview", "count": str(len(lessons))},
    })

    # L2: each lesson
    for l in lessons:
        lid = l.get("id", _slug(l.get("title", "unknown")))
        tags = l.get("tags", [])
        text = (
            f"Lesson: {l.get('title','')}\n"
            f"Project: {project}\n"
            f"Category: {l.get('category','')}\n"
            f"Tags: {', '.join(tags)}\n"
            f"Pattern: {l.get('pattern','')}\n"
            f"Rule: {l.get('rule','')}\n"
            f"Context: {l.get('context','')}\n"
            f"Severity: {l.get('severity','')}"
        )
        chunks.append({
            "id": f"lesson__{_slug(project)}__{lid}",
            "text": text,
            "metadata": {
                "project": project, "date": date,
                "category": l.get("category", "general"),
                "level": "detail",
                "severity": l.get("severity", ""),
                "tags": ", ".join(tags),
            },
        })

    return chunks


# ══════════════════════════════════════════════════════════════════════════════
# NS: design_patterns
# ══════════════════════════════════════════════════════════════════════════════

def _pattern_chunks(data: dict) -> list[dict]:
    source = data.get("source", "unknown")
    date = data.get("date", "")
    chunks = []
    patterns = data.get("patterns", [])

    # L1: overview
    domains = {}
    for p in patterns:
        d = p.get("domain", "general")
        domains[d] = domains.get(d, 0) + 1

    chunks.append({
        "id": f"patterns__{_slug(source)}__overview",
        "text": (
            f"Game design patterns from {source} ({date}):\n"
            f"Total: {len(patterns)}\n"
            f"Domains: {json.dumps(domains)}\n"
            f"Patterns: {', '.join(p.get('name','')[:50] for p in patterns[:15])}"
        ),
        "metadata": {"source": source, "date": date, "category": "overview",
                     "level": "overview", "count": str(len(patterns))},
    })

    # L2: each pattern
    for p in patterns:
        pid = p.get("id", _slug(p.get("name", "unknown")))
        text = (
            f"Game Design Pattern: {p.get('name','')}\n"
            f"Domain: {p.get('domain','')}\n"
            f"Description: {p.get('description','')}\n"
            f"Mechanics: {', '.join(p.get('mechanics',[]))}\n"
            f"Examples: {'; '.join(p.get('examples',[]))}\n"
            f"Competitors using: {', '.join(p.get('competitors_using',[]))}\n"
            f"Effectiveness: {p.get('effectiveness','')}\n"
            f"Implementation notes: {p.get('implementation_notes','')}"
        )
        chunks.append({
            "id": f"pattern__{_slug(source)}__{pid}",
            "text": text,
            "metadata": {
                "source": source, "date": date,
                "category": p.get("domain", "general"),
                "level": "detail",
                "effectiveness": p.get("effectiveness", ""),
                "pattern_name": p.get("name", ""),
            },
        })

    return chunks


# ══════════════════════════════════════════════════════════════════════════════
# NS: project_docs — markdown documents chunked by sections
# ══════════════════════════════════════════════════════════════════════════════

def _doc_chunks(file_path: Path) -> list[dict]:
    """Chunk a markdown file by H1/H2 sections."""
    content = file_path.read_text(encoding="utf-8")
    fname = file_path.stem
    slug = _slug(fname)
    base_meta = {
        "file": file_path.name,
        "path": str(file_path),
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    chunks = []

    # L1: overview (first 2000 chars)
    chunks.append({
        "id": f"doc__{slug}__overview",
        "text": f"Document: {file_path.name}\n\n{content[:2000]}",
        "metadata": {**base_meta, "category": "overview", "level": "overview",
                     "length": str(len(content))},
    })

    # L2: sections split by ## headers
    sections = re.split(r'\n(?=##?\s)', content)
    for i, section in enumerate(sections):
        section = section.strip()
        if not section or len(section) < 50:
            continue
        header_match = re.match(r'^#{1,3}\s+(.+)', section)
        header = header_match.group(1).strip() if header_match else f"section_{i}"
        sec_slug = _slug(header)

        chunks.append({
            "id": f"doc__{slug}__{sec_slug}_{i}",
            "text": f"Document '{file_path.name}', section '{header}':\n\n{section[:3000]}",
            "metadata": {**base_meta, "category": "section", "level": "detail",
                         "section": header},
        })

    return chunks


# ══════════════════════════════════════════════════════════════════════════════
# Commands: Store
# ══════════════════════════════════════════════════════════════════════════════

def cmd_store(files: list[str]):
    """Store competitor scan JSONs."""
    pc, idx = _client()
    for fpath in files:
        data = json.loads(Path(fpath).read_text(encoding="utf-8"))
        chunks = _competitor_chunks(data)
        _embed_and_upsert(pc, idx, chunks, NS_COMPETITORS)


def cmd_store_audit(files: list[str]):
    """Store game audit JSONs."""
    pc, idx = _client()
    for fpath in files:
        data = json.loads(Path(fpath).read_text(encoding="utf-8"))
        chunks = _audit_chunks(data)
        _embed_and_upsert(pc, idx, chunks, NS_AUDITS)


def cmd_store_lessons(files: list[str]):
    """Store dev lessons JSONs."""
    pc, idx = _client()
    for fpath in files:
        data = json.loads(Path(fpath).read_text(encoding="utf-8"))
        chunks = _lesson_chunks(data)
        _embed_and_upsert(pc, idx, chunks, NS_LESSONS)


def cmd_store_patterns(files: list[str]):
    """Store design pattern JSONs."""
    pc, idx = _client()
    for fpath in files:
        data = json.loads(Path(fpath).read_text(encoding="utf-8"))
        chunks = _pattern_chunks(data)
        _embed_and_upsert(pc, idx, chunks, NS_PATTERNS)


def cmd_store_docs(files: list[str]):
    """Store markdown docs, chunked by sections."""
    pc, idx = _client()
    for fpath in files:
        p = Path(fpath)
        if not p.exists():
            print(f"  SKIP: {fpath} not found")
            continue
        chunks = _doc_chunks(p)
        _embed_and_upsert(pc, idx, chunks, NS_DOCS)


# ══════════════════════════════════════════════════════════════════════════════
# Commands: Query
# ══════════════════════════════════════════════════════════════════════════════

def _parse_filter(filter_str: str | None) -> dict | None:
    """Parse --filter 'key=value' into Pinecone filter dict."""
    if not filter_str:
        return None
    parts = filter_str.split("=", 1)
    if len(parts) != 2:
        return None
    return {parts[0].strip(): {"$eq": parts[1].strip()}}


def cmd_query(question: str, top_k: int = 10, namespace: str | None = None,
              filter_str: str | None = None, verbose: bool = False,
              json_output: bool = False):
    """Query one or all namespaces."""
    pc, idx = _client()
    emb = pc.inference.embed(
        model=EmbedModel.Multilingual_E5_Large,
        inputs=[question],
        parameters={"input_type": "query", "truncate": "END"},
    )
    vec = emb.data[0].values

    namespaces = ALL_NAMESPACES if namespace == "all" else [namespace or NS_COMPETITORS]

    # Fix #5: Universal filter for any namespace
    filt = _parse_filter(filter_str)

    if not json_output:
        print(f"\nQuery: {question}")
        print(f"Searching: {', '.join(namespaces)}\n")

    all_matches = []
    for ns in namespaces:
        res = idx.query(vector=vec, top_k=top_k, namespace=ns,
                        include_metadata=True, filter=filt)
        for m in res.matches:
            all_matches.append((ns, m))

    # sort by score descending
    all_matches.sort(key=lambda x: x[1].score, reverse=True)
    top_results = all_matches[:top_k]

    # Fix #7: JSON output mode
    if json_output:
        results = []
        for ns, m in top_results:
            entry = {
                "id": m.id,
                "score": round(m.score, 4),
                "namespace": ns,
                "metadata": {k: v for k, v in (m.metadata or {}).items()},
            }
            results.append(entry)
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    # Human-readable output
    print(f"Results: {len(top_results)}\n")
    for ns, m in top_results:
        md = m.metadata or {}
        cat = md.get("category", md.get("dimension", "?"))
        level = md.get("level", "?")
        extra = ""
        if verbose:
            for key in ("pattern_name", "section", "dimension", "game", "project",
                        "source", "severity", "effectiveness"):
                if md.get(key):
                    extra += f" {key}={md[key]}"
        print(f"  [{m.score:.3f}] [{ns}] {m.id}  ({cat}, {level}){extra}")

        # Fix #1: Show stored text in verbose mode
        if verbose and md.get("_text"):
            text_preview = md["_text"][:300].replace("\n", "\n    ")
            print(f"    {text_preview}...")


# ══════════════════════════════════════════════════════════════════════════════
# Commands: Manage
# ══════════════════════════════════════════════════════════════════════════════

def cmd_info():
    """Show index stats."""
    _, idx = _client()
    stats = idx.describe_index_stats()
    print(f"Total vectors: {stats.total_vector_count}")
    ns = stats.namespaces
    if ns:
        for name, info in ns.items():
            print(f"  {name}: {info.vector_count} vectors")
    else:
        print("  No namespaces found")


def cmd_list(namespace: str, prefix: str | None = None, limit: int = 50):
    """List vector IDs in a namespace."""
    _, idx = _client()
    # Pinecone list API with prefix
    kwargs = {"namespace": namespace}
    if prefix:
        kwargs["prefix"] = prefix

    try:
        results = idx.list(**kwargs)
        ids = []
        for page in results:
            if isinstance(page, list):
                ids.extend(v if isinstance(v, str) else v.get("id", str(v)) for v in page)
            else:
                ids.append(str(page))
            if len(ids) >= limit:
                break

        print(f"\nVectors in '{namespace}'" + (f" (prefix='{prefix}')" if prefix else "") + f":\n")
        for vid in ids[:limit]:
            print(f"  {vid}")
        print(f"\nTotal shown: {min(len(ids), limit)}")
    except Exception as e:
        print(f"Error listing vectors: {e}")
        print("Tip: list requires Pinecone Serverless index")


def cmd_delete(namespace: str, vector_id: str | None = None,
               prefix: str | None = None, delete_all: bool = False):
    """Delete vectors from a namespace."""
    _, idx = _client()

    if delete_all:
        idx.delete(delete_all=True, namespace=namespace)
        print(f"Deleted ALL vectors from '{namespace}'")
    elif vector_id:
        idx.delete(ids=[vector_id], namespace=namespace)
        print(f"Deleted vector '{vector_id}' from '{namespace}'")
    elif prefix:
        # List + delete by IDs matching prefix
        try:
            results = idx.list(namespace=namespace, prefix=prefix)
            ids = []
            for page in results:
                if isinstance(page, list):
                    ids.extend(v if isinstance(v, str) else v.get("id", str(v)) for v in page)
                else:
                    ids.append(str(page))

            if not ids:
                print(f"No vectors found with prefix '{prefix}' in '{namespace}'")
                return

            # Batch delete
            for i in range(0, len(ids), 100):
                batch = ids[i : i + 100]
                idx.delete(ids=batch, namespace=namespace)
            print(f"Deleted {len(ids)} vectors with prefix '{prefix}' from '{namespace}'")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Error: specify --id, --prefix, or --all")


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(
        description="Pinecone RAG Knowledge Base — Global CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Namespaces:
  competitors      Competitor scan data
  game_audits      Game audit findings
  dev_lessons      Development lessons & patterns
  design_patterns  Game design patterns
  project_docs     Project documentation

Examples:
  python pinecone-store.py store data/*.json
  python pinecone-store.py store-patterns patterns.json
  python pinecone-store.py query "retention mechanics" --ns all -v
  python pinecone-store.py query "Redis bugs" --ns dev_lessons --json
  python pinecone-store.py list --ns design_patterns
  python pinecone-store.py delete --ns dev_lessons --prefix "lesson__old_"
  python pinecone-store.py info
        """,
    )
    sub = ap.add_subparsers(dest="cmd")

    # store (competitors)
    s = sub.add_parser("store", help="Store competitor scan JSONs")
    s.add_argument("files", nargs="+")

    # store-audit
    sa = sub.add_parser("store-audit", help="Store game audit JSONs")
    sa.add_argument("files", nargs="+")

    # store-lessons
    sl = sub.add_parser("store-lessons", help="Store dev lessons JSONs")
    sl.add_argument("files", nargs="+")

    # store-patterns
    sp = sub.add_parser("store-patterns", help="Store design pattern JSONs")
    sp.add_argument("files", nargs="+")

    # store-docs
    sd = sub.add_parser("store-docs", help="Store markdown docs")
    sd.add_argument("files", nargs="+")

    # query
    q = sub.add_parser("query", help="Semantic query")
    q.add_argument("question")
    q.add_argument("--ns", default=None, help="Namespace (or 'all')")
    q.add_argument("--filter", dest="filter_str", default=None,
                   help="Filter: key=value (e.g. project=Pet Hotel v2)")
    q.add_argument("--top-k", type=int, default=10)
    q.add_argument("-v", "--verbose", action="store_true")
    q.add_argument("--json", dest="json_output", action="store_true",
                   help="Output as JSON array")

    # list
    ls = sub.add_parser("list", help="List vector IDs in namespace")
    ls.add_argument("--ns", required=True, help="Namespace")
    ls.add_argument("--prefix", default=None, help="ID prefix filter")
    ls.add_argument("--limit", type=int, default=50)

    # delete
    dl = sub.add_parser("delete", help="Delete vectors")
    dl.add_argument("--ns", required=True, help="Namespace")
    dl.add_argument("--id", dest="vector_id", help="Specific vector ID")
    dl.add_argument("--prefix", help="Delete all with this ID prefix")
    dl.add_argument("--all", dest="delete_all", action="store_true",
                    help="Delete ALL vectors in namespace")

    # info
    sub.add_parser("info", help="Show index stats")

    args = ap.parse_args()
    if args.cmd == "store":
        cmd_store(args.files)
    elif args.cmd == "store-audit":
        cmd_store_audit(args.files)
    elif args.cmd == "store-lessons":
        cmd_store_lessons(args.files)
    elif args.cmd == "store-patterns":
        cmd_store_patterns(args.files)
    elif args.cmd == "store-docs":
        cmd_store_docs(args.files)
    elif args.cmd == "query":
        cmd_query(args.question, args.top_k, args.ns,
                  args.filter_str, args.verbose, args.json_output)
    elif args.cmd == "list":
        cmd_list(args.ns, args.prefix, args.limit)
    elif args.cmd == "delete":
        cmd_delete(args.ns, args.vector_id, args.prefix, args.delete_all)
    elif args.cmd == "info":
        cmd_info()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
