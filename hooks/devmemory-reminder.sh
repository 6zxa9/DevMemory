#!/bin/bash
# DevMemory Stop Hook
# Reminds Claude to query Pinecone before implementing and save after success
# Runs at session stop to verify DevMemory workflow was followed

# Read stdin (hook context)
input=$(cat)

# Output reminder as additional context
cat <<'REMINDER'
DevMemory Reminder:
- Did you query Pinecone before implementing? (python ~/.claude/tools/pinecone-store.py query "..." --ns all -v)
- If the user said "отлично"/"great"/"save" - did you offer to save the solution to Pinecone?
- If you found a solution in Pinecone - did you cross-check with Context7?
REMINDER

exit 0
