#!/usr/bin/env bash
set -euo pipefail

readonly RUNTIME_USER=stackreview
readonly RUNTIME_HOME=/var/lib/stack-review
readonly SOURCE_DIR=/opt/lyceum-stack-review
readonly EXECUTABLE=/usr/local/bin/stack-review
readonly GH_VERSION=2.103.3

repository=https://github.com/lyceum-tech/model1.git
branch=main
ssh_public_key=

usage() {
    cat <<'EOF'
Usage: sudo bash bootstrap.sh [--branch NAME] [--ssh-public-key FILE.pub]

Prepare an existing Ubuntu or Debian Docker host for stack-review.
The default branch is main. The optional public key authorizes SSH access
for the stackreview account; private keys must never be copied to the host.
EOF
}

die() {
    echo "bootstrap: $*" >&2
    exit 1
}

while (($#)); do
    case "$1" in
        --branch)
            (($# >= 2)) || die "--branch requires a value"
            branch=$2
            shift 2
            ;;
        --repository)
            (($# >= 2)) || die "--repository requires a value"
            repository=$2
            shift 2
            ;;
        --ssh-public-key)
            (($# >= 2)) || die "--ssh-public-key requires a value"
            ssh_public_key=$2
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "unknown argument: $1"
            ;;
    esac
done

[[ "$branch" =~ ^[A-Za-z0-9][A-Za-z0-9._/-]*$ && "$branch" != *..* && "$branch" != */ ]] ||
    die "invalid branch name"
[[ "$repository" =~ ^https://[A-Za-z0-9.-]+/[A-Za-z0-9._/-]+\.git$ ]] ||
    die "repository must be an HTTPS Git URL"
[[ "$(uname -s)" == Linux ]] || die "an existing Linux Docker host is required"
((EUID == 0)) || die "run with sudo on the Docker host"
command -v apt-get >/dev/null || die "Ubuntu or Debian with apt-get is required"

export DEBIAN_FRONTEND=noninteractive
packages=(ca-certificates curl git python3 python3-venv util-linux)
if ! command -v docker >/dev/null || ! docker compose version >/dev/null 2>&1; then
    packages+=(docker.io docker-compose-v2)
fi
apt-get update
apt-get install -y --no-install-recommends "${packages[@]}"

command -v docker >/dev/null || die "Docker installation failed"
docker compose version >/dev/null || die "Docker Compose v2 is required"
docker info >/dev/null || die "the system Docker daemon is not available"
if ! command -v gh >/dev/null; then
    case "$(uname -m)" in
        x86_64) architecture=amd64 ;;
        aarch64|arm64) architecture=arm64 ;;
        *) die "unsupported machine architecture: $(uname -m)" ;;
    esac
    archive="gh_${GH_VERSION}_linux_${architecture}.tar.gz"
    download_dir=$(mktemp -d)
    trap 'rm -rf -- "$download_dir"' EXIT
    release="https://github.com/cli/cli/releases/download/v${GH_VERSION}"
    curl --fail --location --silent --show-error --output "$download_dir/$archive" "$release/$archive"
    curl --fail --location --silent --show-error --output "$download_dir/checksums.txt" \
        "$release/gh_${GH_VERSION}_checksums.txt"
    expected=$(awk -v name="$archive" '$2 == name {print $1}' "$download_dir/checksums.txt")
    [[ "$expected" =~ ^[0-9a-f]{64}$ ]] || die "could not verify the GitHub CLI download"
    actual=$(sha256sum "$download_dir/$archive" | awk '{print $1}')
    [[ "$actual" == "$expected" ]] || die "GitHub CLI checksum mismatch"
    tar -xzf "$download_dir/$archive" -C "$download_dir"
    install -m 0755 "$download_dir/gh_${GH_VERSION}_linux_${architecture}/bin/gh" /usr/local/bin/gh
    rm -rf -- "$download_dir"
    trap - EXIT
fi

if ! getent group docker >/dev/null; then
    groupadd docker
fi
if ! id -u "$RUNTIME_USER" >/dev/null 2>&1; then
    useradd --create-home --home-dir "$RUNTIME_HOME" --shell /bin/bash --user-group "$RUNTIME_USER"
fi
[[ "$(getent passwd "$RUNTIME_USER" | cut -d: -f6)" == "$RUNTIME_HOME" ]] ||
    die "the existing $RUNTIME_USER account has an unexpected home directory"
usermod --append --groups docker "$RUNTIME_USER"
install -d -m 0750 -o "$RUNTIME_USER" -g "$RUNTIME_USER" "$RUNTIME_HOME/runs" "$RUNTIME_HOME/cache"

if [[ -n "$ssh_public_key" ]]; then
    [[ "$ssh_public_key" == *.pub && -f "$ssh_public_key" && -r "$ssh_public_key" ]] ||
        die "--ssh-public-key must name a readable .pub file"
    install -d -m 0700 -o "$RUNTIME_USER" -g "$RUNTIME_USER" "$RUNTIME_HOME/.ssh"
    install -m 0600 -o "$RUNTIME_USER" -g "$RUNTIME_USER" "$ssh_public_key" "$RUNTIME_HOME/.ssh/authorized_keys"
fi

as_runtime_user() {
    runuser -u "$RUNTIME_USER" -- "$@"
}

if ! as_runtime_user gh auth status --hostname github.com >/dev/null 2>&1; then
    echo "Authenticate $RUNTIME_USER through GitHub CLI for access to model1 and Lyceum." >&2
    as_runtime_user gh auth login --hostname github.com --git-protocol https --web </dev/tty ||
        die "GitHub authentication failed; rerun with a terminal or authenticate gh as $RUNTIME_USER first"
    as_runtime_user gh auth setup-git --hostname github.com
fi

[[ ! -L "$SOURCE_DIR" ]] || die "$SOURCE_DIR must not be a symbolic link"
if [[ -d "$SOURCE_DIR/.git" ]]; then
    [[ "$(git -C "$SOURCE_DIR" remote get-url origin)" == "$repository" ]] ||
        die "$SOURCE_DIR belongs to a different repository"
    as_runtime_user git -C "$SOURCE_DIR" remote set-url origin "$repository"
    as_runtime_user git -C "$SOURCE_DIR" fetch --depth 1 origin "$branch"
    as_runtime_user git -C "$SOURCE_DIR" checkout --detach FETCH_HEAD
else
    [[ ! -e "$SOURCE_DIR" ]] || die "$SOURCE_DIR already exists and is not an installation"
    install -d -m 0755 -o "$RUNTIME_USER" -g "$RUNTIME_USER" "$SOURCE_DIR"
    as_runtime_user git clone --depth 1 --branch "$branch" "$repository" "$SOURCE_DIR"
fi

as_runtime_user python3 -m venv "$RUNTIME_HOME/venv"
as_runtime_user "$RUNTIME_HOME/venv/bin/python" -m pip install --disable-pip-version-check \
    "$SOURCE_DIR/review-checks"
if [[ -L "$EXECUTABLE" ]]; then
    [[ "$(readlink "$EXECUTABLE")" == "$RUNTIME_HOME/venv/bin/stack-review" ]] ||
        die "$EXECUTABLE points to another executable"
elif [[ -e "$EXECUTABLE" ]]; then
    die "$EXECUTABLE already exists and was not installed by this script"
else
    ln -s "$RUNTIME_HOME/venv/bin/stack-review" "$EXECUTABLE"
fi

as_runtime_user docker info --format 'Docker server {{.ServerVersion}} is accessible to stackreview'
as_runtime_user git -C "$SOURCE_DIR" log -1 --format='Installed model1 commit %H'
"$EXECUTABLE" --help >/dev/null
echo "Bootstrap complete. GitHub authentication is managed by gh as $RUNTIME_USER."
