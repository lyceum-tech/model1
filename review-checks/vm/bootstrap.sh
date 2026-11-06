#!/usr/bin/env bash
set -euo pipefail

readonly SOURCE_DIR=/opt/lyceum-stack-review
readonly EXECUTABLE=/usr/local/bin/stack-review
readonly GH_VERSION=2.103.3
readonly BUILDX_VERSION=0.30.1

repository=https://github.com/lyceum-tech/model1.git
branch=main
github_user=
runtime_user=stackreview
ssh_public_key=

usage() {
    cat <<'EOF'
Usage: sudo bash bootstrap.sh --github-user NAME [--runtime-user NAME] [--branch NAME] [--ssh-public-key FILE.pub]

Prepare an existing Ubuntu or Debian Docker host for stack-review.
--runtime-user selects the Linux account that owns the gh configuration.
It defaults to stackreview; specify an existing account to reuse its gh login.
--github-user selects the existing GitHub identity independently of Linux users.
The default source branch is main. Private keys must never be copied to the host.
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
        --github-user)
            (($# >= 2)) || die "--github-user requires a value"
            github_user=$2
            shift 2
            ;;
        --runtime-user)
            (($# >= 2)) || die "--runtime-user requires a value"
            runtime_user=$2
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
[[ "$github_user" =~ ^[A-Za-z0-9]([A-Za-z0-9-]{0,37}[A-Za-z0-9])?$ ]] ||
    die "--github-user is required and must be a valid GitHub username"
[[ "$runtime_user" =~ ^[a-z_][a-z0-9_-]*\$?$ ]] || die "invalid Linux runtime username"
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
if ! id -u "$runtime_user" >/dev/null 2>&1; then
    [[ "$runtime_user" == stackreview ]] || die "the selected Linux runtime account must already exist"
    useradd --create-home --home-dir /var/lib/stack-review --shell /bin/bash --user-group stackreview
fi
[[ "$(id -u "$runtime_user")" != 0 ]] || die "the root account cannot run candidate workloads"
runtime_home=$(getent passwd "$runtime_user" | cut -d: -f6)
runtime_group=$(id -gn "$runtime_user")
[[ "$runtime_home" == /* && "$runtime_home" != / && -d "$runtime_home" && -n "$runtime_group" ]] ||
    die "the selected runtime account has no usable home directory"
usermod --append --groups docker "$runtime_user"
runtime_dir="$runtime_home/.stack-review"
install -d -m 0750 -o "$runtime_user" -g "$runtime_group" "$runtime_dir/runs" "$runtime_dir/cache"

if [[ -n "$ssh_public_key" ]]; then
    [[ "$ssh_public_key" == *.pub && -f "$ssh_public_key" && -r "$ssh_public_key" ]] ||
        die "--ssh-public-key must name a readable .pub file"
    [[ ! -L "$runtime_home/.ssh" ]] || die "the runtime SSH directory must not be a symbolic link"
    authorized_keys="$runtime_home/.ssh/authorized_keys"
    [[ ! -L "$authorized_keys" && ( -f "$authorized_keys" || ! -e "$authorized_keys" ) ]] ||
        die "the runtime authorized_keys path is not a regular file"
    install -d -m 0700 -o "$runtime_user" -g "$runtime_group" "$runtime_home/.ssh"
    if [[ ! -e "$authorized_keys" ]]; then
        install -m 0600 -o "$runtime_user" -g "$runtime_group" /dev/null "$authorized_keys"
    fi
    if ! grep -Fqx -f "$ssh_public_key" "$authorized_keys"; then
        cat "$ssh_public_key" >> "$authorized_keys"
    fi
    chown "$runtime_user:$runtime_group" "$authorized_keys"
    chmod 0600 "$authorized_keys"
fi

as_runtime_user() {
    runuser -u "$runtime_user" -- env HOME="$runtime_home" USER="$runtime_user" LOGNAME="$runtime_user" "$@"
}

if ! as_runtime_user gh auth switch --hostname github.com --user "$github_user" >/dev/null 2>&1; then
    echo "Sign in through GitHub CLI as $github_user for access to model1 and Lyceum." >&2
    as_runtime_user env BROWSER=echo gh auth login --hostname github.com --git-protocol https --web </dev/tty ||
        die "GitHub authentication failed; rerun with a terminal or authenticate gh as $runtime_user first"
fi
[[ "$(as_runtime_user gh api user --jq .login)" == "$github_user" ]] ||
    die "gh authenticated an unexpected GitHub identity instead of $github_user"
as_runtime_user gh auth setup-git --hostname github.com

install_buildx_if_needed() {
    local current_version architecture archive release download_dir expected actual
    current_version=$(docker buildx version 2>/dev/null | sed -nE '1s/^github.com\/docker\/buildx v?([^ ]+).*$/\1/p')
    if dpkg --compare-versions "$current_version" ge 0.17 2>/dev/null; then
        return
    fi
    case "$(uname -m)" in
        x86_64) architecture=amd64 ;;
        aarch64|arm64) architecture=arm64 ;;
        *) die "unsupported machine architecture: $(uname -m)" ;;
    esac
    archive="buildx-v${BUILDX_VERSION}.linux-${architecture}"
    release="https://github.com/docker/buildx/releases/download/v${BUILDX_VERSION}"
    download_dir=$(mktemp -d)
    trap 'rm -rf -- "$download_dir"' EXIT
    chown "$runtime_user:$runtime_group" "$download_dir"
    as_runtime_user curl --fail --location --silent --show-error --output "$download_dir/$archive" \
        "$release/$archive"
    as_runtime_user curl --fail --location --silent --show-error --output "$download_dir/checksums.txt" \
        "$release/checksums.txt"
    expected=$(as_runtime_user awk -v filename="$archive" \
        '{ name=$2; sub(/^\*/, "", name); if (name == filename) print $1 }' "$download_dir/checksums.txt")
    [[ "$expected" =~ ^[0-9a-f]{64}$ ]] || die "could not verify the Buildx download"
    actual=$(as_runtime_user sha256sum "$download_dir/$archive" | awk '{print $1}')
    [[ "$actual" == "$expected" ]] || die "Buildx checksum mismatch"
    install -d -m 0755 /usr/local/lib/docker/cli-plugins
    install -m 0755 "$download_dir/$archive" /usr/local/lib/docker/cli-plugins/docker-buildx
    rm -rf -- "$download_dir"
    trap - EXIT
}
install_buildx_if_needed

[[ ! -L "$SOURCE_DIR" ]] || die "$SOURCE_DIR must not be a symbolic link"
if [[ -d "$SOURCE_DIR/.git" ]]; then
    [[ "$(git -C "$SOURCE_DIR" remote get-url origin)" == "$repository" ]] ||
        die "$SOURCE_DIR belongs to a different repository"
    as_runtime_user git -C "$SOURCE_DIR" remote set-url origin "$repository"
    as_runtime_user git -C "$SOURCE_DIR" fetch --depth 1 origin "$branch"
    as_runtime_user git -C "$SOURCE_DIR" checkout --detach FETCH_HEAD
else
    [[ ! -e "$SOURCE_DIR" ]] || die "$SOURCE_DIR already exists and is not an installation"
    install -d -m 0755 -o "$runtime_user" -g "$runtime_group" "$SOURCE_DIR"
    as_runtime_user git clone --depth 1 --branch "$branch" "$repository" "$SOURCE_DIR"
fi

as_runtime_user python3 -m venv "$runtime_dir/venv"
as_runtime_user "$runtime_dir/venv/bin/python" -m pip install --disable-pip-version-check \
    "$SOURCE_DIR/review-checks"
executable_target="$runtime_dir/venv/bin/stack-review"
if [[ -L "$EXECUTABLE" ]]; then
    current_target=$(readlink "$EXECUTABLE")
    [[ "$current_target" == "$executable_target" || "$current_target" == /var/lib/stack-review/venv/bin/stack-review ]] ||
        die "$EXECUTABLE points to another executable"
    ln -sfn "$executable_target" "$EXECUTABLE"
elif [[ -e "$EXECUTABLE" ]]; then
    die "$EXECUTABLE already exists and was not installed by this script"
else
    ln -s "$executable_target" "$EXECUTABLE"
fi

docker_version=$(as_runtime_user docker info --format '{{.ServerVersion}}')
buildx_version=$(as_runtime_user docker buildx version | sed -nE '1s/^github.com\/docker\/buildx v?([^ ]+).*$/\1/p')
dpkg --compare-versions "$buildx_version" ge 0.17 2>/dev/null ||
    die "Buildx 0.17 or newer must be accessible to $runtime_user"
echo "Docker server $docker_version and Buildx $buildx_version are accessible to $runtime_user"
as_runtime_user git -C "$SOURCE_DIR" log -1 --format='Installed model1 commit %H'
"$EXECUTABLE" --help >/dev/null
echo "Bootstrap complete. $runtime_user uses gh as $github_user."
