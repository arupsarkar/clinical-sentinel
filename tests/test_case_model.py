"""Tests for the adverse event domain model.

Each test is a regulatory or structural claim, made permanent.
"""

from datetime import date

import pytest
from pydantic import ValidationError

from clinical_sentinel.models.case import AdverseEventCase, Patient, Seriousness


def make_valid_case(**overrides) -> AdverseEventCase:
    """Test factory: one canonical valid case, override what each test probes.

    Keeps tests focused on the ONE thing they assert instead of
    repeating boilerplate — the Object Mother pattern, in miniature.
    """
    defaults = dict(
        case_id="CS-2026-000001",
        received_date=date.today(),
        patient=Patient(age_years=54),
        reporter_type="physician",
        suspect_drug="Drugamab",
        event_description="severe rash",
    )
    return AdverseEventCase(**{**defaults, **overrides})


def test_valid_case_constructs():
    case = make_valid_case()
    assert case.case_id == "CS-2026-000001"


def test_new_case_is_not_serious_by_default():
    assert make_valid_case().is_serious is False


def test_seriousness_flags_make_case_serious():
    case = make_valid_case(seriousness=[Seriousness.HOSPITALIZATION])
    assert case.is_serious is True


def test_malformed_case_id_rejected():
    with pytest.raises(ValidationError):
        make_valid_case(case_id="bogus")


def test_unidentifiable_patient_rejected():
    """PV minimum criteria: a patient with no qualifiers is not a case."""
    with pytest.raises(ValidationError):
        make_valid_case(patient=Patient())


def test_single_qualifier_makes_patient_identifiable():
    """Any ONE of age/sex/initials suffices — the regulatory bar."""
    case = make_valid_case(patient=Patient(initials="AB"))
    assert case.patient.is_identifiable()