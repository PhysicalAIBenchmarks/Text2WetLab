FROM python:3.10-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash ca-certificates curl git jq nodejs npm procps ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g node@22.22.0 @anthropic-ai/claude-code@2.1.288 \
    && node --version \
    && claude --version

RUN pip install --no-cache-dir anthropic==0.72.0

RUN python -m venv /opt/ot \
    && /opt/ot/bin/pip install --no-cache-dir opentrons==7.5.0 opentrons-shared-data==7.5.0 "pydantic<2" \
    && ln -s /opt/ot/bin/opentrons_simulate /usr/local/bin/opentrons_simulate \
    && opentrons_simulate --version

RUN python -m venv /opt/grader \
    && /opt/grader/bin/pip install --no-cache-dir "pydantic>=2.13" anthropic==0.72.0

COPY solution_hint.py /app/solution_hint.py

WORKDIR /app
