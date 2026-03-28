FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl build-essential && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pytest ruff mypy

WORKDIR /workspace
CMD ["sleep", "infinity"]
