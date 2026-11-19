# syntax=docker/dockerfile:1.7
#
# Reproducible test toolchain for this repository. It pins the same runtimes as
# .github/workflows/validate-openwiki.yml (Python 3.12, Node 22.18.0) and uses
# uv for Python dependencies.
#
#   docker compose run --rm tests      # required-CI parity (default target)
#   docker compose run --rm ui ui      # Chromium + WebKit acceptance
#
# Prefer compose.yaml or tools/docker/run.sh over raw docker commands.

FROM python:3.12-slim-bookworm AS base

ARG NODE_VERSION=22.18.0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    PATH=/opt/venv/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      diffutils \
      git \
      xz-utils \
 && rm -rf /var/lib/apt/lists/*

# Node.js from the official distribution, pinned to the required CI version.
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
      amd64) node_arch=x64 ;; \
      arm64) node_arch=arm64 ;; \
      *) echo "unsupported architecture: $arch" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${node_arch}.tar.xz" -o /tmp/node.tar.xz; \
    tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 --no-same-owner; \
    rm /tmp/node.tar.xz; \
    node --version; \
    npm --version

COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /uvx /usr/local/bin/

# Tests create throwaway Git repositories and run against a bind-mounted
# checkout owned by the host user.
RUN git config --system user.name "Knowledge Hub Tests" \
 && git config --system user.email "tests@knowledge-hub.invalid" \
 && git config --system --add safe.directory '*' \
 && git config --system init.defaultBranch main

# Python dependencies from the lockfile. The custom `ui` group is only
# installed in the ui stage.
WORKDIR /opt/uv-project
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

WORKDIR /workspace
COPY tools/docker/entrypoint.sh tools/docker/run-tests.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/run-tests.sh
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["ci"]

# Fast CI-parity image. Build this target for normal test runs:
#   docker build --target test -t knowledge-hub-tests .
FROM base AS test

# Build the pinned OKF validator once. entrypoint.sh copies node_modules and
# frontmatter.ts into the bind-mounted checkout when they are missing.
WORKDIR /opt/okf
COPY tools/okf/ ./
RUN sh setup.sh

WORKDIR /workspace

# Optional local browser acceptance image: Chromium and WebKit plus their OS
# dependencies. Required CI never builds or runs this stage.
FROM test AS ui

WORKDIR /opt/uv-project
RUN uv sync --frozen --group ui --no-install-project \
 && playwright install --with-deps chromium webkit \
 && rm -rf /var/lib/apt/lists/* /root/.cache/ms-playwright

WORKDIR /workspace
