# DevMemory Installer for Windows
# Usage: irm https://raw.githubusercontent.com/6zxa9/DevMemory/main/install.ps1 | iex

$ErrorActionPreference = "Stop"

$CLAUDE_DIR = "$env:USERPROFILE\.claude"
$TOOLS_DIR = "$CLAUDE_DIR\tools"
$SKILLS_DIR = "$CLAUDE_DIR\skills\rag-knowledge"
$RULES_DIR = "$CLAUDE_DIR\rules"
$HOOKS_DIR = "$CLAUDE_DIR\hooks"

Write-Host "=== DevMemory Installer ===" -ForegroundColor Cyan
Write-Host ""

# Create directories
foreach ($dir in @($TOOLS_DIR, $SKILLS_DIR, $RULES_DIR, $HOOKS_DIR)) {
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
}

$BASE_URL = "https://raw.githubusercontent.com/6zxa9/DevMemory/main"

Write-Host "[1/5] Installing CLI tool..." -ForegroundColor Green
Invoke-WebRequest "$BASE_URL/tools/pinecone-store.py" -OutFile "$TOOLS_DIR\pinecone-store.py"
Invoke-WebRequest "$BASE_URL/tools/requirements.txt" -OutFile "$TOOLS_DIR\requirements.txt"

Write-Host "[2/5] Installing skill..." -ForegroundColor Green
Invoke-WebRequest "$BASE_URL/skills/rag-knowledge/SKILL.md" -OutFile "$SKILLS_DIR\SKILL.md"

Write-Host "[3/5] Installing rule..." -ForegroundColor Green
Invoke-WebRequest "$BASE_URL/rules/rag-knowledge.md" -OutFile "$RULES_DIR\rag-knowledge.md"

Write-Host "[4/5] Installing hooks..." -ForegroundColor Green
Invoke-WebRequest "$BASE_URL/hooks/devmemory-session-start.sh" -OutFile "$HOOKS_DIR\devmemory-session-start.sh"
Invoke-WebRequest "$BASE_URL/hooks/devmemory-reminder.sh" -OutFile "$HOOKS_DIR\devmemory-reminder.sh"

Write-Host "[5/5] Installing Python dependencies..." -ForegroundColor Green
try {
    pip install -q pinecone python-dotenv 2>$null
} catch {
    Write-Host "  Warning: Could not install Python deps. Run manually:" -ForegroundColor Yellow
    Write-Host "  pip install pinecone python-dotenv"
}

Write-Host ""
Write-Host "=== Installation complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. Create $TOOLS_DIR\.env with your Pinecone credentials:"
Write-Host "     PINECONE_API_KEY=your_key"
Write-Host "     PINECONE_HOST=your_host"
Write-Host ""
Write-Host "  2. Add hooks to ~/.claude/settings.json (see README for config)"
Write-Host ""
Write-Host "  3. Verify: python $TOOLS_DIR\pinecone-store.py info"
Write-Host ""
Write-Host "DevMemory will now automatically activate in every Claude Code project." -ForegroundColor Green
