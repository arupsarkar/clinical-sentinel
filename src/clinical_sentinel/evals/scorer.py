"""Deterministic scorer: golden label vs. one extraction. No API calls.

Principle 8 applied to evaluation itself: everything comparable by
rule is compared by rule. The LLM-judge (later chunk) is reserved for
the one genuinely fuzzy field (event_description faithfulness).

Normalization decisions live HERE — in diffable, testable code — not
in the agent prompt. The golden files' notes are the spec; this module
is the implementation of those rulings.
"""

from clinical_sentinel.evals.models import CaseEvalResult, FieldResult, GoldenCase
from clinical_sentinel.models.intake import IntakeExtraction

# Ruling (002): free-text reporter descriptions map to canonical categories.
# Substring match, first hit wins; order matters (check specific before generic).
_REPORTER_CATEGORY_MAP: list[tuple[str, str]] = [
    ("physician", "physician"), ("oncologist", "physician"), ("doctor", "physician"),
    ("pharmacist", "pharmacist"),
    ("nurse", "nurse"),
    ("consumer", "consumer"), ("family", "consumer"), ("daughter", "consumer"),
    ("patient", "consumer"),
]


def _normalize_reporter(free_text: str | None) -> str:
    if not free_text:
        return ""
    lowered = free_text.lower()
    for needle, category in _REPORTER_CATEGORY_MAP:
        if needle in lowered:
            return category
    return "other_hcp"


def _normalize_initials(value: str | None) -> str:
    # Ruling (003): 'M.K' == 'M.K.' — case-insensitive, trailing period ignored.
    return (value or "").strip().rstrip(".").upper()


def _check(field: str, expected, actual, *, must_not_invent: bool = False) -> FieldResult:
    """Compare one field. Hallucination = golden says absent, system supplied."""
    invented = must_not_invent and expected is None and actual is not None
    passed = (expected == actual) and not invented
    return FieldResult(
        field=field,
        expected=str(expected),
        actual=str(actual),
        passed=passed,
        is_hallucination=invented,
    )


def score_extraction(golden: GoldenCase, extraction: IntakeExtraction) -> CaseEvalResult:
    exp = golden.expected
    mni = set(golden.must_not_invent)

    fields = [
        _check("suspect_drug", exp.suspect_drug, extraction.suspect_drug),
        _check("patient.age_years", exp.patient.age_years, extraction.patient.age_years,
               must_not_invent="patient.age_years" in mni),
        _check("patient.sex", exp.patient.sex, extraction.patient.sex,
               must_not_invent="patient.sex" in mni),
        _check("patient.initials",
               _normalize_initials(exp.patient.initials) or None,
               _normalize_initials(extraction.patient.initials) or None,
               must_not_invent="patient.initials" in mni),
        _check("reporter_category", exp.reporter_category,
               _normalize_reporter(extraction.reporter_type)),
        _check("is_complete", exp.is_complete, extraction.is_complete()),
    ]
    return CaseEvalResult(source=golden.source, fields=fields)