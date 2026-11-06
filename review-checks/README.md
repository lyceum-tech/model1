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

Run the script as root and select both the Linux runtime account and the GitHub identity it already owns.
Use the `pierre/review-cli-existing-user` branch until this change is merged; after that, omit `--branch`.
For example, `pierre` is the Linux account whose `gh` login uses pierrot-la-lune:

```bash
sudo ./review-checks/vm/bootstrap.sh \
    --branch pierre/review-cli-existing-user \
    --runtime-user pierre \
    --github-user pierrot-la-lune
```

The script is idempotent. It reuses the selected Linux account and its home directory, creates `.stack-review/runs`
and `.stack-review/cache` there, clones model1 into `/opt/lyceum-stack-review`, and installs Python dependencies
into `.stack-review/venv`. `/usr/local/bin/stack-review` uses that installation. The default `--runtime-user` is
`stackreview`, which the script can create for a separate runtime; another account specified explicitly must
already exist. Docker membership grants effective host root access, so use only a dedicated disposable host.

The existing account keeps its normal home-based `gh` configuration. If `gh` has the requested GitHub identity,
the script selects it with `gh auth switch`; a `pierre` account already authenticated as pierrot-la-lune needs
no new login. Otherwise complete `gh auth login --web` as that GitHub user. For headless hosts, the script prints
the browser URL rather than requiring `xdg-open`. No personal access token is passed to the bootstrap, and the
identity is checked with `gh api user`.

To add SSH access to a different account, pass `--ssh-public-key FILE.pub`. The script appends a missing public
key without replacing existing `authorized_keys`; never supply a private key. With the example above, connect as
the existing account:

```bash
ssh pierre@HOST stack-review --help
```

Host preparation is separate from creating and testing an isolated per-PR Compose environment. The bootstrap
does not expose an HTTP service, copy candidate secrets to the host, or run candidate code by itself.

## Validate this project

```bash
uv run --project review-checks python -m unittest discover -s review-checks/tests -v
```
