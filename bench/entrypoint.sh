#!/usr/bin/env bash
# Installs the mounted clone into its own venv, then runs one agent on /work/bench/prompt.txt.
# AGENT is "claude" or "codex", MODEL is the model id, EFFORT the reasoning level.
set -u
cd /work
python3 -m venv --system-site-packages .venv > /out/setup.log 2>&1
.venv/bin/pip install -q -e . >> /out/setup.log 2>&1
date -u +%Y-%m-%dT%H:%M:%SZ > /out/start.txt

case "$AGENT" in
  claude)
    claude -p --model "$MODEL" --effort "$EFFORT" --output-format json \
      --permission-mode acceptEdits \
      --allowedTools "Bash" "Read" "Edit" "Write" "Glob" "Grep" \
      < bench/prompt.txt > /out/agent.json 2> /out/agent.err
    ;;
  codex)
    codex exec -m "$MODEL" -c model_reasoning_effort="$EFFORT" \
      --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check --json \
      -o /out/last.txt - < bench/prompt.txt > /out/agent.jsonl 2> /out/agent.err
    ;;
esac
echo $? > /out/exit.txt
date -u +%Y-%m-%dT%H:%M:%SZ > /out/end.txt
