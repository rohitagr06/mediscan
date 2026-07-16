"""`python -m mediscan.evaluation` -> print the extraction-recall report."""

from mediscan.evaluation.extraction import format_extraction_report, run_extraction_eval

if __name__ == "__main__":
    print(format_extraction_report(run_extraction_eval()))
