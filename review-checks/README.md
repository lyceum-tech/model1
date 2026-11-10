# Stack review

`stack-review` runs the 17 advisory checks from Lyceum stack 4515 plus eight static security checks (18–25) derived from the 2026-10-30 security audit against one GitHub pull request. Without `--dev-vm`, it is a local, read-only replacement for the per-rule PR stack: it does not publish PR comments or descriptions, execute candidate code, or contribute to branch protection.

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

## Security audit checks (18–25)

Checks 18–25 are static, policy-driven snapshot checks like checks 1–3: they need no runtime observations and never execute candidate code. Their patterns, path scopes, and thresholds live in the trusted `security` section of `src/review_rules/policy.json`; candidate files cannot weaken them. They are diff-aware like check 2's reference rule: a check is red only when the candidate introduces or worsens a violation relative to the base snapshot. Violations already present in the base are listed in the JSON findings with kind `pre-existing` and stay green. Findings carry audit ids (`SEC-F01`, …), a path, and a line number; matched content is never echoed, so a detected key or credential does not leak into the report.

Each check would have gone red on the pull request that introduced the corresponding audit finding. `tests/test_security_gates.py` proves this with audit-shaped fixtures at the real repository paths, clean counterparts, and pre-existing/worsened/fixed transitions. Coverage below is per finding of `security/security-audit-2026103.md` section 6; "partial" names the statically detectable slice only.

| Check | Audit findings | Coverage |
|---|---|---|
| 18 Workload isolation and model-code trust | F01 privileged containers; F15 `--trust-remote-code`, containers without `RunAsNonRoot` | F01 full; F15 partial (egress, admission policy, and DGD-rendered pods are not static) |
| 19 Secrets in source and logs | F02 embedded private keys, decrypted-credential logging; F20 whole job/request object logging | F02 full for source-embedded keys and the audited log shapes; F20 partial (CI log artifacts and SQL data-access auditing excluded) |
| 20 Storage version and session lifetime | F03 MinIO pinned before the 2025-10-15 session-policy fix; F04 `MaxValiditySeconds` above 900, API-key lookup without `expires_at` | Static slice; session values computed at runtime from token expiry are not resolved |
| 21 CI federation and standing privilege | F05 org-wide `repository_owner` WIF binding; F12 standing `roles/owner`; F22 mutable `@main` actions, stale-review settings off | F12 partial (SOPS recipient breadth and CI key custody are process controls) |
| 22 Network exposure and plaintext transport | F06 public firewall rules for SSH/Consul ports, all-ports tailnet VPC grants; F09 HTTPS upstreams without `proxy_ssl_verify on`; F13 plaintext `redis://`/`amqp://`/internal `http://` endpoints | Declared rules only; inherited and provider-side rules are not visible statically |
| 23 Service identity, mesh and endpoint auth | F07 shared wildcard Iris leaf, CA/leaf lifetimes above policy maxima; F08 Dynamo builder without endpoint-auth; F10 Consul bound to all interfaces without ACL/TLS verification declarations | F08 static slice (a builder that gains auth must still be runtime-tested per the audit) |
| 24 SSH bootstrap and VM handover | F11 disabled SSH host-key verification; F24 non-exclusive customer `authorized_key` handover | F24 partial (provider/hypervisor access is not a guest-file property) |
| 25 Platform hardening and lifecycle declarations | F14 k3s without `secrets-encryption`; F17 raw filesystems without a LUKS declaration; F18 unattended upgrades disabled; F19 `:latest`/undigested image references; F21 Cloud SQL instances without backups/PITR | Partial: absence guards and removal regressions; patch execution, restore drills, and fleet state are runtime evidence |

Findings F16 and F23 have no static signal — per-site firmware/BMC/physical evidence and measured tenant placement cannot be read from repository declarations — so no check claims them; they remain evidence-capture workstreams in the audit plan. A green 18–25 row therefore means "this PR introduced no new declared violation", not "the finding is remediated": closure still needs the runtime and operational evidence the audit requires.

## Develop Lyceum in Docker

Use the Linux development container to run Lyceum's complete lint and test task groups against the sibling `../lyceum` checkout:

```bash
./review-checks/vm/lyceum-dev/dev build
./review-checks/vm/lyceum-dev/dev shell
./review-checks/vm/lyceum-dev/dev check
```

The checkout remains editable on the host, and the container runs as the host user. Integration tests share the host Docker socket and network, so use this only on a dedicated development machine with code you trust. See `review-checks/vm/lyceum-dev/README.md` for individual commands, cache handling, and credential requirements.

## Build and probe on a Linux Docker host

After bootstrapping a host with the runtime support described below, run this from your normal workstation:

```bash
stack-review --dev-vm pierre@horn https://github.com/lyceum-tech/lyceum/pull/4292
```

The workstation reads the PR metadata from GitHub and evaluates static checks from an immutable Git snapshot. The independently authenticated host clones Lyceum, archives the exact `head.sha`, builds the candidate `inference-proxy`, and verifies the resulting image's trusted revision label. `--repo` and `--cache-dir` affect only the local static snapshot, never the remote candidate. `--observations` cannot be combined with `--dev-vm`.

Add `--dev-tests` to run the complete Lyceum check suite in the development container after the runtime probe:

```bash
stack-review --dev-vm pierre@horn --dev-tests \
    https://github.com/lyceum-tech/lyceum/pull/4292
```

This opt-in mode has a three-hour deadline. It initializes a throwaway Git repository from the exact candidate archive, builds the development image using that archive's `mise.toml` and lockfile, then runs pre-commit, `//...:lint`, `//...:test-fast`, and `//...:test-integration`. Every group is attempted. Pre-commit edits are discarded before the subsequent groups. Rule 3 reports any failed groups by name; raw candidate output is not forwarded over SSH. A red group is a check result, while an inability to build or execute the runtime remains an operational failure.

The development checks share the runtime host's Docker socket and network for testcontainers, so they require the same dedicated trusted-host precautions as the direct development wrapper. The review runtime deliberately does not mount `LYCEUM_DEV_GNUPG` or otherwise provide personal credentials to candidate code. Consequently SOPS-dependent hooks and Terraform lint fail until the dedicated runtime host has an independently managed, review-appropriate decryption key. Do not copy a personal keyring to a host used for untrusted pull requests. For local trusted development only, the direct wrapper in `vm/lyceum-dev` does support an explicitly selected keyring.

The runtime probe exercises all four rule-9 chat scenarios: `plain`, `tools`, `search`, and `stop-string`. Each compares a non-streaming completion with a streamed completion through the candidate proxy to a deterministic fake OpenAI-compatible backend. Comparisons cover text, tool-call IDs and arguments, citation annotations, model identity, usage, finish reason, and normal SSE termination. Scenarios fail independently; an unsupported or malformed response is inconclusive, while a genuine complete/stream mismatch is red.

The same probe run also collects candidate-bound facts for rules 4, 5, 7, and 10, which otherwise stay yellow. Rule 4 checks response status and fields against fixed contract fixtures for the SDK chat surface, public model routing, and the tool-call response schema. Rule 5 varies `max_tokens` (absent, null, empty, wrong type, zero, negative, and conflicting `max_completion_tokens` alias); the fixture records the exact body the candidate forwards upstream, so rejection-before-forwarding and the forwarded canonical value are both observed, not inferred. Rule 10 records per-turn stream event kinds and arrival times for string, array, and object tool arguments across two turns, plus client cancellation, a malformed upstream stream, and queue pressure against the bounded routing limits. The candidate runs with a one-second stream heartbeat and the probe applies a three-second idle limit: the same three-times ratio as production's ten-second heartbeat and the rule's thirty-second limit, scaled down so slow-stream scenarios take seconds.

Rule 7 sends a per-run synthetic canary through four upstream failure modes the fixture can produce on demand: malformed JSON, an upstream timeout, a redirect whose target carries the canary, and an upstream 500 echoing it. The probe reports only whether the canary reached the client error. The host agent separately searches the candidate container's bounded log tail for each scenario canary and records only the search result; log content itself never leaves the runtime host. The timeout scenario waits out the candidate's configured chat timeout, so a probe run takes roughly a minute longer than the remaining scenarios combined.

Hosted search uses `web_search_options`, the proxy's internal search function, and an authenticated Linkup-compatible fixture. A per-run self-signed certificate maps `api.linkup.so` to that fixture on the internal-only network, with only its public certificate mounted read-only into the candidate. The search credential is synthetic and deleted with the run. No internet search, real model, or external provider is used. Successful probe evidence covers only the candidate inference proxy's behavior against these fixtures. It is not a claim that the whole stack, production inference, other services, or unrelated Execlet credential changes have passed. Rules 6, 8, and 11–17 still receive no runtime observations from this harness and remain yellow on scoped changes; rule 8 belongs with the `--dev-tests` container rather than the probe.

No public ports are published, real credentials are used, or production/shared-development services contacted. Missing or inconclusive evidence stays yellow.

Runtime resources have unique Compose project names and a per-host run lock. Candidate builds do not receive the host Docker socket or production/shared-development credentials. Runtime containers are non-root, read-only, drop Linux capabilities, and share an internal-only network with the fake control plane and Redis. Every response is size- and time-bounded. Raw prompts, provider responses, and synthetic credentials are not included in observations. The collector emits only allowed comparison facts bound to the complete base SHA, head SHA, and policy SHA.

Cleanup always attempts `docker compose down --volumes --remove-orphans`, including after build, startup, probe, or timeout failures. Cached images are retained. Cleanup failure is an operational failure rather than a successful observation. The host agent also has a hard timeout; the local SSH command is batch-only and uses the existing SSH configuration and known hosts.

## Prepare a Linux Docker host

Use a dedicated Ubuntu 24.04 or Debian host for untrusted candidate builds. Do not use shared development, staging, or production infrastructure: membership in the Docker group grants effective host root access. The bootstrap can use an existing Docker daemon, or install Docker and Compose v2 when absent. Compose requires Buildx 0.17 or newer; the bootstrap installs the checksum-verified upstream Buildx 0.30.1 plugin when the distribution version is older. Installer downloads need space on the root filesystem (including `/tmp`), while the Docker data root needs enough space for candidate images and build cache.

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
