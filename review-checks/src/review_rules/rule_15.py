"""Rule 15: Historical billing correctness. Observations are evaluated, never collected from candidate files."""

from datetime import datetime
from decimal import Decimal

from review_rules.common import scenarios

PREFIXES = ("croesus/", "db/", "app/", "infra/services/hydra-autoscaler/")
REQUIRED = ("effective-date", "historical-update", "historical-delete", "rounding", "preexisting-price")


def evaluate_one(f):
    kind = f["scenario"]
    if kind in ("historical-update", "historical-delete"):
        return f["rejected"] is True and f["rows_after"] == f["rows_before"]
    if kind == "preexisting-price":
        return f["migration_succeeded"] is True and f["rows_preserved"] is True
    if kind == "effective-date":
        instant = datetime.fromisoformat(f["price_at"])
        eligible = [
            (datetime.fromisoformat(row["valid_from"]), Decimal(row["price"]))
            for row in f["prices"]
            if datetime.fromisoformat(row["valid_from"]) <= instant
        ]
        if not eligible:
            return f["tally_rejected"] is True
        return Decimal(f["amount"]) == max(eligible)[1] * Decimal(f["quantity"])
    owed = max(-Decimal(f["ending_balance"]), Decimal(0)).quantize(Decimal("0.01"))
    if any(line["kind"] == "credit" and Decimal(line["amount"]) > 0 for line in f["lines"]):
        return False
    return sum((Decimal(line["amount"]) for line in f["lines"]), Decimal(0)) == owed


def evaluate(facts):
    """Classify complete candidate-bound observations, with missing evidence yellow."""
    return scenarios(facts, REQUIRED, evaluate_one)


def check(before, after, paths, facts):
    """The reporter supplies only trusted, commit-bound observations for relevant changes."""
    return evaluate(facts)
