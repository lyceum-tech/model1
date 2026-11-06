"""Rule 16: Scoped CI publishing credentials. Observations are evaluated, never collected from candidate files."""

from review_rules.common import scenarios

PREFIXES = ("infra/terraform/", ".github/", ".teamcity/")
REQUIRED = ("registry-scope", "untrusted-branch", "production-release")


def evaluate_one(f):
    writers = {
        "roles/artifactregistry.writer",
        "roles/artifactregistry.repoAdmin",
        "roles/artifactregistry.admin",
        "roles/editor",
        "roles/owner",
    }
    for grant in f["grants"]:
        if grant["principal"] not in f["ci_principals"] or grant["role"] not in writers:
            continue
        if grant["scope"] != "repository" or grant["resource"] not in f["allowed_repositories"]:
            return False
        if grant["production"] and not set(grant["allowed_branches"]) <= {"refs/heads/main"}:
            return False
    return True


def evaluate(facts):
    """Classify complete candidate-bound observations, with missing evidence yellow."""
    return scenarios(facts, REQUIRED, evaluate_one)


def check(before, after, paths, facts):
    """The reporter supplies only trusted, commit-bound observations for relevant changes."""
    return evaluate(facts)
