#!/bin/bash
# DevMemory SessionStart Hook
# Outputs a reminder that gets injected into Claude's context at session start

cat <<'EOF'
[DevMemory Active] RAG knowledge base is connected.
Before implementing any non-trivial task:
  python ~/.claude/tools/pinecone-store.py query "<task keywords>" --ns all --top-k 5 -v
After user says "отлично"/"запиши"/"сохрани" → offer to save solution to Pinecone.
Cross-check found solutions with Context7 (resolve-library-id → query-docs).
EOF

exit 0
