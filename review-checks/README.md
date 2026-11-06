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

## Validate this project

```bash
uv run --project review-checks python -m unittest discover -s review-checks/tests -v
```
