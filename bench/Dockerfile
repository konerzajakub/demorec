# One image for every agent in the comparison: Python, Playwright Chromium, ffmpeg, git and
# the agent CLIs. Each run gets its own container with only its clone mounted at /work.
FROM node:22-bookworm

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv python3-pip ffmpeg git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Playwright and its Chromium with system dependencies, shared by all runs.
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright
RUN pip3 install --break-system-packages "playwright==1.58.0" pytest \
 && python3 -m playwright install --with-deps chromium \
 && chmod -R a+rX /opt/ms-playwright

ARG CODEX_VERSION=0.163.0
ARG CLAUDE_VERSION=2.1.310
RUN npm install -g "@openai/codex@${CODEX_VERSION}" "@anthropic-ai/claude-code@${CLAUDE_VERSION}"

# Agents run as a normal user. Claude Code refuses some modes as root.
RUN useradd -m -s /bin/bash bench
USER bench
WORKDIR /work
COPY --chown=bench entrypoint.sh /home/bench/entrypoint.sh
ENTRYPOINT ["bash", "/home/bench/entrypoint.sh"]
