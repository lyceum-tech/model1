FROM python:3.13.7-slim@sha256:5f55cdf0c5d9dc1a415637a5ccc4a9e18663ad203673173b8cda8f8dcacef689

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        build-essential \
        ca-certificates \
        curl \
        docker-cli \
        git \
        gnupg \
        libatomic1 \
        libffi-dev \
        make \
        openssh-client \
        pkg-config \
        redis-server \
        unzip \
        xz-utils \
    && rm -rf /var/lib/apt/lists/*

ARG BUILDX_VERSION=0.30.1
ARG COMPOSE_VERSION=2.40.3
RUN set -euo pipefail; \
    case "$(uname -m)" in \
        x86_64) buildx_arch=amd64; compose_arch=x86_64 ;; \
        aarch64|arm64) buildx_arch=arm64; compose_arch=aarch64 ;; \
        *) echo "unsupported architecture: $(uname -m)" >&2; exit 1 ;; \
    esac; \
    download_dir=$(mktemp -d); \
    trap 'rm -rf -- "$download_dir"' EXIT; \
    buildx_asset="buildx-v${BUILDX_VERSION}.linux-${buildx_arch}"; \
    buildx_release="https://github.com/docker/buildx/releases/download/v${BUILDX_VERSION}"; \
    curl --fail --location --silent --show-error --output "$download_dir/$buildx_asset" \
        "$buildx_release/$buildx_asset"; \
    curl --fail --location --silent --show-error --output "$download_dir/buildx-checksums.txt" \
        "$buildx_release/checksums.txt"; \
    expected=$(awk -v filename="$buildx_asset" \
        '{name=$2; sub(/^\*/, "", name); if (name == filename) print $1}' \
        "$download_dir/buildx-checksums.txt"); \
    [[ "$expected" =~ ^[0-9a-f]{64}$ ]]; \
    echo "$expected  $download_dir/$buildx_asset" | sha256sum --check -; \
    install -d -m 0755 /usr/local/lib/docker/cli-plugins; \
    install -m 0755 "$download_dir/$buildx_asset" /usr/local/lib/docker/cli-plugins/docker-buildx; \
    compose_asset="docker-compose-linux-${compose_arch}"; \
    compose_release="https://github.com/docker/compose/releases/download/v${COMPOSE_VERSION}"; \
    curl --fail --location --silent --show-error --output "$download_dir/$compose_asset" \
        "$compose_release/$compose_asset"; \
    curl --fail --location --silent --show-error --output "$download_dir/compose-checksums.txt" \
        "$compose_release/checksums.txt"; \
    expected=$(awk -v filename="$compose_asset" \
        '{name=$2; sub(/^\*/, "", name); if (name == filename) print $1}' \
        "$download_dir/compose-checksums.txt"); \
    [[ "$expected" =~ ^[0-9a-f]{64}$ ]]; \
    echo "$expected  $download_dir/$compose_asset" | sha256sum --check -; \
    install -m 0755 "$download_dir/$compose_asset" /usr/local/lib/docker/cli-plugins/docker-compose; \
    docker buildx version; \
    docker compose version

ARG MISE_RELEASE_URL=https://github.com/jdx/mise/releases/download
COPY mise.toml /lyceum/
COPY mise/scripts/install-mise.bash mise/scripts/mise-version.bash /lyceum/mise/scripts/
RUN MISE_INSTALL_PATH=/usr/local/bin/mise /lyceum/mise/scripts/install-mise.bash

ENV MISE_DATA_DIR=/opt/mise \
    MISE_TASK_OUTPUT=keep-order \
    MISE_TRUSTED_CONFIG_PATHS=/lyceum \
    PATH="/opt/mise/shims:$PATH"
COPY mise.toml mise.lock /lyceum/
WORKDIR /lyceum
RUN mise install \
    && chmod -R a+rX /opt/mise \
    && printf '%s\n' 'export PATH="/opt/mise/shims:$PATH"' > /etc/profile.d/lyceum-dev.sh

ARG UID=1000
ARG GID=1000
ARG DOCKER_GID=124
RUN groupadd --gid "$GID" lyceum \
    && groupadd --gid "$DOCKER_GID" docker \
    && useradd --uid "$UID" --gid "$GID" --groups docker --create-home --shell /bin/bash lyceum \
    && install -d -m 0755 -o lyceum -g lyceum /home/lyceum/.cache

USER lyceum
ENV HOME=/home/lyceum
CMD ["bash", "-l"]
