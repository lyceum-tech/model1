"""Evidence handling shared by advisory scenario evaluators."""


def verdict(color, reason):
    """Keep report messages fixed; never echo captured requests or credentials."""
    return {"status": color, "reason": reason}


def scenarios(facts, required, evaluate):
    """Missing, duplicate, errored, or unrecognized observations cannot become green."""
    if not isinstance(facts, list):
        return verdict("yellow", "Candidate-bound scenario observations are unavailable")
    seen = set()
    unknown = False
    for fact in facts:
        if not isinstance(fact, dict) or fact.get("scenario") not in required or fact.get("error"):
            unknown = True
            continue
        name = fact["scenario"]
        if name in seen:
            unknown = True
        seen.add(name)
        try:
            result = evaluate(fact)
        except (ValueError, TypeError, KeyError, ArithmeticError):
            result = None
        if result is False:
            return verdict("red", "Observed behavior violates the rule")
        if result is not True:
            unknown = True
    if unknown or seen != set(required):
        return verdict("yellow", "Scenario observations are incomplete or inconclusive")
    return verdict("green", "All required candidate-bound scenarios satisfy the rule")
