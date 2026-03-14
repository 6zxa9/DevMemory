#!/bin/bash
# DevMemory Installer
# Usage: curl -sSL https://raw.githubusercontent.com/6zxa9/DevMemory/main/install.sh | bash

set -e

CLAUDE_DIR="$HOME/.claude"
TOOLS_DIR="$CLAUDE_DIR/tools"
SKILLS_DIR="$CLAUDE_DIR/skills/rag-knowledge"
RULES_DIR="$CLAUDE_DIR/rules"

echo "=== DevMemory Installer ==="
echo ""

# Create directories
mkdir -p "$TOOLS_DIR" "$SKILLS_DIR" "$RULES_DIR"

# Download files
BASE_URL="https://raw.githubusercontent.com/6zxa9/DevMemory/main"

echo "[1/4] Installing CLI tool..."
curl -sSL "$BASE_URL/tools/pinecone-store.py" -o "$TOOLS_DIR/pinecone-store.py"
curl -sSL "$BASE_URL/tools/requirements.txt" -o "$TOOLS_DIR/requirements.txt"

echo "[2/4] Installing skill..."
curl -sSL "$BASE_URL/skills/rag-knowledge/SKILL.md" -o "$SKILLS_DIR/SKILL.md"

echo "[3/4] Installing rule..."
curl -sSL "$BASE_URL/rules/rag-knowledge.md" -o "$RULES_DIR/rag-knowledge.md"

echo "[4/4] Installing Python dependencies..."
pip install -q pinecone python-dotenv 2>/dev/null || pip3 install -q pinecone python-dotenv 2>/dev/null || {
  echo "  Warning: Could not install Python deps. Run manually:"
  echo "  pip install pinecone python-dotenv"
}

echo ""
echo "=== Installation complete ==="
echo ""
echo "Next steps:"
echo "  1. Create ~/.claude/tools/.env with your Pinecone credentials:"
echo "     PINECONE_API_KEY=your_key"
echo "     PINECONE_HOST=your_host"
echo ""
echo "  2. Verify: python ~/.claude/tools/pinecone-store.py info"
echo ""
echo "DevMemory will now automatically activate in every Claude Code project."
