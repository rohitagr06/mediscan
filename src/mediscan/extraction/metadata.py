"""Read patient metadata (sex, age) from a report's header text.

WHY THIS FILE EXISTS
    Sex-aware reference ranges (Sprint 6.5) need the patient's sex, and the
    honest source of that is the report itself. Real reports print it many
    ways — "Age/Gender : 33/Male", "Age / Sex : 27 YRS / M", "Sex: Female" —
    so the reader is deliberately tolerant. When no sex is stated it returns
    Sex.UNKNOWN; we never guess (#011).

    This reads ONLY metadata. It performs no medical judgement and touches
    nothing the deterministic engine decides.
"""

import re

from mediscan.schemas.patient import PatientContext, Sex

# A line worth inspecting for sex: one that carries a "sex" or "gender" label.
# Anchoring on the label keeps a stray "male"/"female" in a comment paragraph
# from being read as the patient's sex.
_SEX_CONTEXT = re.compile(r"\b(?:sex|gender)\b", re.IGNORECASE)

# Full words first ("Male" / "Female"); \b word-boundaries mean "male" does
# NOT match inside "female". The abbreviation forms ("/ M", ": F") catch the
# "27 YRS / M" style where only a single letter is printed.
_FEMALE = re.compile(r"\bfemale\b|[:/]\s*f\b", re.IGNORECASE)
_MALE = re.compile(r"\bmale\b|[:/]\s*m\b", re.IGNORECASE)

# Age: on a line that carries an "age" label, take the first 1-3 digit number
# within a short distance (so we don't grab an unrelated number far away).
_AGE_LABEL = re.compile(r"\bage\b", re.IGNORECASE)
_AGE_VALUE = re.compile(r"\bage\b[^\d]{0,20}(\d{1,3})", re.IGNORECASE)


def _read_sex(text: str) -> Sex:
    """Return the patient's sex, or Sex.UNKNOWN when the report is silent."""
    for line in text.splitlines():
        if not _SEX_CONTEXT.search(line):
            continue
        # Check FEMALE before MALE so "female" is never mis-read as male.
        if _FEMALE.search(line):
            return Sex.FEMALE
        if _MALE.search(line):
            return Sex.MALE
    return Sex.UNKNOWN


def _read_age(text: str) -> int | None:
    """Return the patient's age in years if stated on an 'age' line, else None."""
    for line in text.splitlines():
        if not _AGE_LABEL.search(line):
            continue
        match = _AGE_VALUE.search(line)
        if match is not None:
            age = int(match.group(1))
            if 0 <= age <= 150:
                return age
    return None


def extract_patient_context(text: str) -> PatientContext:
    """Read sex (and age, if present) from report text into a PatientContext.

    Args:
        text: The full extracted report text.

    Returns:
        A PatientContext; sex is Sex.UNKNOWN and age is None when not stated.
    """
    return PatientContext(sex=_read_sex(text), age=_read_age(text))
