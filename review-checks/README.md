# Stack review

`stack-review` runs the 17 advisory checks from Lyceum stack 4515 against one GitHub pull request. Without `--dev-vm`, it is a local, read-only replacement for the per-rule PR stack: it does not publish PR comments or descriptions, execute candidate code, or contribute to branch protection.

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

## Build and probe on a Linux Docker host

After bootstrapping a host with the runtime support described below, run this from your normal workstation:

```bash
stack-review --dev-vm pierre@horn https://github.com/lyceum-tech/lyceum/pull/4292
```

The workstation reads the PR metadata from GitHub and evaluates static checks from an immutable Git snapshot. The independently authenticated host clones Lyceum, archives the exact `head.sha`, builds the candidate `inference-proxy`, and verifies the resulting image's trusted revision label. `--repo` and `--cache-dir` affect only the local static snapshot, never the remote candidate. `--observations` cannot be combined with `--dev-vm`.

The first runtime slice exercises one `plain` chat scenario: a non-streaming completion followed by a streamed completion through the candidate proxy to a deterministic fake OpenAI-compatible backend. It compares text, model identity, usage, finish reason, and normal SSE termination. Rule 9 also requires `tools`, `search`, and `stop-string`, so a successful plain comparison leaves rule 9 yellow and explicitly identifies those missing scenarios. It is not a claim that the whole stack, production inference, or unrelated Execlet credential changes have passed.

This slice does not run the tools, hosted-search, or stop-string scenarios; it does not use a real model or external provider. Missing or inconclusive evidence stays yellow. A genuine comparison mismatch is red. No public ports are published, real credentials are used, or production/shared-development services contacted.

Runtime resources have unique Compose project names and a per-host run lock. Candidate builds do not receive the host Docker socket or production/shared-development credentials. Runtime containers are non-root, read-only, drop Linux capabilities, and share an internal-only network with the fake control plane and Redis. Every response is size- and time-bounded. Raw prompts, provider responses, and synthetic credentials are not included in observations. The collector emits only allowed comparison facts bound to the complete base SHA, head SHA, and policy SHA.

Cleanup always attempts `docker compose down --volumes --remove-orphans`, including after build, startup, probe, or timeout failures. Cached images are retained. Cleanup failure is an operational failure rather than a successful observation. The host agent also has a hard timeout; the local SSH command is batch-only and uses the existing SSH configuration and known hosts.

## Prepare a Linux Docker host

Use a dedicated Ubuntu 24.04 or Debian host for untrusted candidate builds. Do not use shared development, staging, or production infrastructure: membership in the Docker group grants effective host root access. The bootstrap can use an existing Docker daemon, or install Docker and Compose v2 when absent.

Run the script as root, selecting the Linux account and the GitHub identity it owns. With the runtime change installed on model1 `main`, update an existing `pierre` installation whose `gh` login is pierrot-la-lune:

```bash
sudo /opt/lyceum-stack-review/review-checks/vm/bootstrap.sh \
    --runtime-user pierre \
    --github-user pierrot-la-lune
```

For a new checkout, run `sudo ./review-checks/vm/bootstrap.sh` with the same options instead. `--branch NAME` is available when testing another trusted model1 revision. The remote agent must use the same runtime policy revision as the workstation; a policy mismatch is rejected rather than producing a stale report.

The script is idempotent. It creates `.stack-review/runs` and `.stack-review/cache` in the selected account's home, clones model1 into `/opt/lyceum-stack-review`, and installs Python dependencies into `.stack-review/venv`. `/usr/local/bin/stack-review` and `/usr/local/bin/stack-review-runtime` use that installation. The default `--runtime-user` is `stackreview`, which the script can create; another explicitly selected account must already exist.

The existing account keeps its normal home-based `gh` configuration. If `gh` has the requested GitHub identity, the script selects it with `gh auth switch`; a `pierre` account already authenticated as pierrot-la-lune needs no new login. Otherwise complete `gh auth login --web` as that GitHub user. For headless hosts, the script prints the browser URL instead of requiring `xdg-open`. No personal access token is used; the identity is checked with `gh api user`.

To authorize SSH access, append your public key once:

```bash
sudo /opt/lyceum-stack-review/review-checks/vm/bootstrap.sh \
    --runtime-user pierre \
    --github-user pierrot-la-lune \
    --ssh-public-key /tmp/stack-review.pub
```

The script appends a missing public key without replacing existing `authorized_keys`; never supply a private key. Then verify the intended OS account:

```bash
ssh pierre@horn stack-review-runtime --help
```

Bootstrapping alone does not expose an HTTP service, copy candidate secrets, or run candidate code.

## Validate this project

```bash
uv run --project review-checks python -m unittest discover -s review-checks/tests -v
```

The unit and lifecycle tests use local HTTP servers and a fake Docker executable; they do not require a Docker daemon. Compose syntax is checked separately by `docker compose config`. A real candidate build still requires an authorized Linux Docker host.
