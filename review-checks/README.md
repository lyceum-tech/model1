# Stack review

`stack-review` runs the 17 advisory checks from Lyceum stack 4515 against one GitHub pull request. It is a local, read-only replacement for the per-rule PR stack: it does not publish PR comments or descriptions, execute candidate code, or contribute to branch protection.

## Install

Requires Python 3.11 or newer, Git, an authenticated GitHub CLI (`gh`), and `uv`.

```bash
uv tool install ./review-checks
```

## Run

```bash
stack-review https://github.com/lyceum-tech/lyceum/pull/4292
```

Run from any directory. The command caches a partial Git repository under `${XDG_CACHE_HOME:-$HOME/.cache}/stack-review`. To use an existing clone instead:

```bash
stack-review --repo /path/to/lyceum 4292
stack-review --repo /path/to/repository --repository owner/name 42
```

Use `--json` for the complete report and `--cache-dir` to override the default cache. The terminal table explains each result and separates informative green/red verdicts from yellow results that are **not yet useful**. The CLI exits nonzero only for operational errors, not because a check is red.

Checks 4–17 require runtime observations for changed code in their declared scope. Without complete candidate-, base-, and policy-bound observations they intentionally remain yellow. Supply trusted observations with `--observations observations.json`; files from the candidate cannot alter that binding. Inspect `stack_review` policy and each rule's required scenario names before collecting observations.

## Prepare a Linux Docker host

Use a dedicated Ubuntu 24.04 or Debian host for untrusted candidate builds. Do not use shared development,
staging, or production infrastructure: membership in the Docker group grants effective host root access.
The bootstrap can use an existing Docker daemon, or install Docker and Compose v2 when they are absent.

Copy only an SSH **public** key to the host, then run the script as root. Use the
`pierre/review-cli-gh-identity` branch until the identity-selection change is merged; after that, omit
`--branch` to install `main`. Replace the example `--github-user` with your existing GitHub username:

```bash
scp ~/.ssh/id_ed25519.pub admin@HOST:/tmp/stack-review.pub
ssh -t admin@HOST \
    'sudo bash -s -- --branch pierre/review-cli-gh-identity --github-user pierrot-la-lune --ssh-public-key /tmp/stack-review.pub' \
    < review-checks/vm/bootstrap.sh
ssh admin@HOST rm /tmp/stack-review.pub
```

The script is idempotent. It creates the `stackreview` Linux account and `/var/lib/stack-review`, clones model1
into `/opt/lyceum-stack-review`, installs Python dependencies into a dedicated virtual environment, and
exposes `/usr/local/bin/stack-review`. If Docker or Compose is available it is left in place. GitHub CLI is
installed only when missing; a new download is pinned and checked against its published SHA-256 checksum.

The Linux account is deliberately separate from the GitHub identity. `--github-user` is required: if `gh`
already has that identity, the script selects it with `gh auth switch`. Otherwise complete GitHub CLI's
interactive web/device sign-in as that same GitHub user. The displayed device code can be entered in a browser
on your usual machine; no personal access token is passed to the bootstrap. The script verifies the resulting
identity with `gh api user`. Later runs reuse the selected identity and update the model1 checkout.

Connect using the configured account:

```bash
ssh stackreview@HOST stack-review --help
```

Host preparation is separate from creating and testing an isolated per-PR Compose environment. The bootstrap
does not expose an HTTP service, copy candidate secrets to the host, or run candidate code by itself.

## Validate this project

```bash
uv run --project review-checks python -m unittest discover -s review-checks/tests -v
```
