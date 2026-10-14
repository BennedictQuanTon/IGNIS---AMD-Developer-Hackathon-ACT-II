"""Blocks any sentence whose numbers are not bound to a matching fact in the same snapshot."""

import re

from ignis_wo.contracts import FactRow, ReportClaim
from ignis_wo.render.templates import SLOT_PATTERN, format_value, render

NUMBER_WORDS = (
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
    "sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety "
    "hundred thousand million billion once twice thrice single double triple half dozen couple "
    "first second third fourth fifth sixth seventh eighth ninth tenth"
)
ROMAN_NUMERALS = "ii iii iv vi vii viii ix xi xii"
BANNED_WORDS = "risk risks probability probable probably likely likelihood chance chances predict predicted prediction"


def word_pattern(words: str) -> str:
    alternatives = "|".join(words.split())
    return rf"\b({alternatives})\b"


NUMBER_PATTERN = re.compile(r"\d|%|" + word_pattern(NUMBER_WORDS + " " + ROMAN_NUMERALS), re.IGNORECASE)
BANNED_PATTERN = re.compile(word_pattern(BANNED_WORDS), re.IGNORECASE)


def check_claim(claim: ReportClaim, known: dict[str, FactRow], snapshot_id: str) -> list[str]:
    errors = []
    fixed_text = SLOT_PATTERN.sub(" ", claim.template)
    number = NUMBER_PATTERN.search(fixed_text)
    if number:
        errors.append(f"number {number.group(0)!r} outside a fact slot")
    banned = BANNED_PATTERN.search(claim.text)
    if banned:
        errors.append(f"banned wording {banned.group(0)!r}; this is triage priority, not a prediction")

    fact_values = {}
    for slot in claim.slots:
        fact = known.get(slot.fact_id)
        if fact is None or fact.snapshot_id != snapshot_id:
            errors.append(f"slot {slot.role}: fact {slot.fact_id} is not in snapshot {snapshot_id}")
            continue
        if fact.kind != slot.expected_kind or fact.unit != slot.expected_unit:
            errors.append(f"slot {slot.role}: expected {slot.expected_kind}/{slot.expected_unit}, got {fact.kind}/{fact.unit}")
        for key, value in claim.subject_scope.items():
            if fact.scope.get(key) != value:
                errors.append(f"slot {slot.role}: fact scope {fact.scope} does not match {key}={value!r}")
        if fact.status != "computed":
            errors.append(f"slot {slot.role}: fact {slot.fact_id} was not computed")
            continue
        fact_values[slot.role] = format_value(fact)

    if not errors and render(claim.template, fact_values, claim.labels) != claim.text:
        errors.append("rendered text does not match the bound fact values")
    return errors


def check_claims(claims: list[ReportClaim], facts: list[FactRow], snapshot_id: str) -> dict[str, list[str]]:
    known = {fact.fact_id: fact for fact in facts}
    failures = {}
    for claim in claims:
        errors = check_claim(claim, known, snapshot_id)
        if errors:
            failures[claim.claim_id] = errors
    return failures
