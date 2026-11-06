"""Rule 6: Prices and measurable usage. Observations are evaluated, never collected from candidate files."""

from decimal import Decimal

from review_rules.common import scenarios

PREFIXES = ("iris/", "croesus/", "app/")
REQUIRED = ("priced-request", "unsupported-price", "missing-measurement")


def evaluate_one(f):
    if f["vendor_called"] is False:
        return f["served"] is False
    if f["price_key"] not in f["available_prices"] or f["forwarded_dimension"] != f["priced_dimension"]:
        return False
    quantity = Decimal(str(f["quantity"]))
    if not quantity.is_finite() or quantity < 0:
        return False
    if f["served"]:
        return (quantity > 0 and f["usage_recorded"] is True) or f["accounting_failure_visible"] is True
    return True


def evaluate(facts):
    """Classify complete candidate-bound observations, with missing evidence yellow."""
    return scenarios(facts, REQUIRED, evaluate_one)


def check(before, after, paths, facts):
    """The reporter supplies only trusted, commit-bound observations for relevant changes."""
    return evaluate(facts)
