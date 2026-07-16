"""`python -m mediscan.evaluation` -> print the extraction + grounding reports."""

from mediscan.evaluation.extraction import format_extraction_report, run_extraction_eval
from mediscan.evaluation.grounding import format_grounding_report, run_grounding_eval

if __name__ == "__main__":
    print(format_extraction_report(run_extraction_eval()))
    print(format_grounding_report(run_grounding_eval()))
