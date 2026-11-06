"""Rule 12: Customer URL network boundary. Observations are evaluated, never collected from candidate files."""

import ipaddress

from review_rules.common import scenarios

PREFIXES = ("iris/", "app/", "daedalus_go/", "infra/")
REQUIRED = ("public", "loopback", "private", "metadata", "ipv6", "redirect", "dns-rebinding")


def evaluate_one(f):
    if not f["hops"]:
        return None
    for hop in f["hops"]:
        address = ipaddress.ip_address(hop["dial_ip"])
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
            address = address.ipv4_mapped
        if hop["connected"] and not address.is_global:
            return False
    return True


def evaluate(facts):
    """Classify complete candidate-bound observations, with missing evidence yellow."""
    return scenarios(facts, REQUIRED, evaluate_one)


def check(before, after, paths, facts):
    """The reporter supplies only trusted, commit-bound observations for relevant changes."""
    return evaluate(facts)
