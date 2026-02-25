"""Run the 3 required test cases without pytest. Usage: python tests/run_test_cases.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from test_cases import (
    test_case_1_standard_interview_invitation,
    test_case_2_technical_question,
    test_case_3_unknown_unsafe_question,
)

if __name__ == "__main__":
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in .env")
        sys.exit(1)

    print("API Key: " + api_key[:10] + "..." + api_key[-4:])
    print()

    test_case_1_standard_interview_invitation()
    print()
    test_case_2_technical_question()
    print()
    test_case_3_unknown_unsafe_question()

    print()
    print("All 3 test cases completed successfully.")
