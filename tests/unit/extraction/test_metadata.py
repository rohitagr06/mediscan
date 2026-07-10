"""Tests for reading patient sex/age from report header text.

Covers the real header formats seen in sample reports (Tata 1mg, Labsmart)
plus the honest "unknown when silent" contract.
"""

from mediscan.extraction.metadata import extract_patient_context
from mediscan.schemas import Sex


def test_reads_tata_style_age_gender():
    pc = extract_patient_context("Age/Gender : 33/Male")
    assert pc.sex is Sex.MALE
    assert pc.age == 33


def test_reads_labsmart_style_age_sex_single_letter():
    pc = extract_patient_context("Age / Sex : 27 YRS / M")
    assert pc.sex is Sex.MALE
    assert pc.age == 27


def test_reads_female_full_word():
    assert extract_patient_context("Sex: Female").sex is Sex.FEMALE


def test_reads_female_single_letter_abbreviation():
    assert extract_patient_context("Age / Sex : 41 YRS / F").sex is Sex.FEMALE


def test_female_not_misread_as_male():
    # "female" contains "male" but a word boundary must prevent a MALE match.
    assert extract_patient_context("Gender : Female").sex is Sex.FEMALE


def test_unknown_when_no_sex_stated():
    pc = extract_patient_context("Patient Name : John Doe\nHemoglobin 15 g/dL 13-17")
    assert pc.sex is Sex.UNKNOWN
    assert pc.age is None


def test_stray_sex_word_without_label_is_ignored():
    # a "male"/"female" mention that is NOT on a sex/gender line must not be
    # read as the patient's sex (it could be a reference-range note).
    text = "Reference ranges for males differ from females in some panels."
    assert extract_patient_context(text).sex is Sex.UNKNOWN


def test_sex_found_among_many_lines():
    text = (
        "TATA 1MG HYDERABAD\n"
        "Name : Ms. Test Patient\n"
        "Age/Gender : 41/Female\n"
        "Sample Type : Whole Blood-EDTA\n"
    )
    pc = extract_patient_context(text)
    assert pc.sex is Sex.FEMALE
    assert pc.age == 41
