# Entry Format Reference

## Design Patterns (store-patterns)

```json
{
  "source": "project_name",
  "date": "YYYY-MM-DD",
  "patterns": [
    {
      "id": "code__snake_case_name",
      "name": "Human Readable Name",
      "domain": "backend|frontend|fullstack|platform|architecture|economy|retention|monetization|core_loop|performance|polish|virality|session_design",
      "description": "CONTEXT: problem being solved. WHAT WORKED: concrete solution. WHY: rationale. REJECTED: alternatives and why not. LIMITATIONS: when not to use.",
      "mechanics": ["keyword1", "keyword2", "keyword3"],
      "examples": ["Project X: path/to/file.ts — functionName()"],
      "competitors_using": [],
      "effectiveness": "critical|high|medium",
      "implementation_notes": "FILE: path/to/file.ts\n\n```typescript\n// Key code (20-80 lines)\nexport function solution() {\n  // ...\n}\n```\n\nWHY: explanation.\nREJECTED: what didn't work and why."
    }
  ]
}
```

## Dev Lessons (store-lessons)

```json
{
  "project": "project_name",
  "date": "YYYY-MM-DD",
  "lessons": [
    {
      "id": "bug__snake_case_name",
      "title": "Short description",
      "category": "infrastructure|backend|frontend|telegram|game_design|ci_cd|security|fullstack",
      "tags": ["tag1", "tag2"],
      "pattern": "What went wrong (root cause)",
      "rule": "How to do it right (prevention rule)",
      "context": "Full story: what happened, how found, how fixed.\nCode: ```lang\n// fix\n```",
      "severity": "critical|high|medium|low"
    }
  ]
}
```

## Game Audits (store-audit)

```json
{
  "game": "Game Name",
  "date": "YYYY-MM-DD",
  "version": "1.0",
  "verdict": "SHIP|ITERATE|PIVOT",
  "overall_score": 7.5,
  "dimensions": [
    {
      "name": "FTUE",
      "score": 8,
      "observations": ["..."],
      "problems": [{"description": "...", "impact": "HIGH", "effort": "2d"}],
      "recommendations": ["..."]
    }
  ],
  "top_wins": ["..."],
  "critical_fixes": ["..."]
}
```

## Quality Checklist

Before storing any entry, verify:

- [ ] Contains real code (20-80 lines), not just description
- [ ] Includes WHY this approach was chosen
- [ ] Lists REJECTED alternatives with reasons
- [ ] Specifies LIMITATIONS (when NOT to use)
- [ ] Has been tested in production
- [ ] Would save 2+ days of work if found 6 months later
