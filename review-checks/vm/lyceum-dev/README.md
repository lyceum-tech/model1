# Lyceum Docker development machine

This is a Linux development container for the sibling `../lyceum` checkout. It
uses Lyceum's pinned Python and `mise` tool versions and includes the native
build dependencies, Redis, Docker CLI, Buildx, and Compose needed by its lint
and test tasks.

From `review-checks`:

```bash
./vm/lyceum-dev/dev build
./vm/lyceum-dev/dev shell
```

The checkout is bind-mounted, so edits and Git operations affect the same files
on the host. The container runs as the calling user's UID and GID. A named
volume preserves the container home, including `mise`, `uv`, Go, and pre-commit
caches, while tool binaries from the image remain under `/opt/mise`.

Run the same task groups as Lyceum CI:

```bash
./vm/lyceum-dev/dev pre-commit
./vm/lyceum-dev/dev lint
./vm/lyceum-dev/dev test
./vm/lyceum-dev/dev integration
```

Or run all four sequentially:

```bash
./vm/lyceum-dev/dev check
```

`pre-commit` checks every file. To reproduce CI's per-commit checks for a pull
request, provide revisions available in the checkout:

```bash
./vm/lyceum-dev/dev pre-commit-range origin/main HEAD
```

Run an arbitrary command without starting an interactive shell:

```bash
./vm/lyceum-dev/dev exec mise run //stream_execlet:test-fast
./vm/lyceum-dev/dev exec python --version
```

Set `LYCEUM_DEV_REPO` to another absolute or relative checkout path when the
default sibling checkout is not the one to use. The image build context follows
that checkout, so its own `mise.toml` and lockfile select the tools;
`LYCEUM_DEV_DOCKERFILE` can override the trusted Dockerfile location when
needed. `MISE_JOBS` and `GO_TEST_INTEGRATION_PARALLEL` can be overridden in the
environment.

`stack-review --dev-vm USER@HOST --dev-tests PR` uses this wrapper on the remote
runtime host with an immutable PR archive. It supplies results to review rule 3
and never forwards the host's `LYCEUM_DEV_GNUPG` setting to candidate code. See
the top-level README for that workflow.

## Docker and credentials

Integration tests use sibling containers through the host Docker socket. Host
networking lets tests reach their published ports on `localhost`, and mounting
the checkout at the same absolute path in both environments keeps Docker bind
paths valid. Consequently this setup requires the checkout and Docker daemon
to be on the same Linux host.

Access to the Docker socket is effectively host root access, and host networking
does not isolate services. Use this environment only for code you would trust
on the host itself. No host credentials are copied into the image or mounted by
default. Tasks that decrypt SOPS files or pull private images additionally need
the corresponding GPG key or registry login configured in the container home.
To share an existing GPG keyring explicitly for a command, set
`LYCEUM_DEV_GNUPG`; the directory is mounted read-write so GPG can manage its
agent sockets and lock files:

```bash
LYCEUM_DEV_GNUPG="$HOME/.gnupg" ./vm/lyceum-dev/dev check
```

This gives the container access to private keys as well as public keyring data.
Do not use it with untrusted code.

The wrapper skips `renovate-fix-config` and `teamcity-settings` for pre-commit,
matching Lyceum's CI. Set `SKIP` explicitly to change that list.

Use `./vm/lyceum-dev/dev compose config` to inspect the generated configuration,
and `./vm/lyceum-dev/dev compose down` to remove the development container and
network resources. The persistent home volume is retained unless Compose is
explicitly run with `--volumes`.
