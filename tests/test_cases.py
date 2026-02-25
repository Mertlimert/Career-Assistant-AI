"""
Three required test cases for Career Assistant AI Agent:
1. Standard interview invitation
2. Technical question
3. Unknown/unsafe question
Run with: python -m pytest tests/test_cases.py -v
Or run manually: python tests/run_test_cases.py (no pytest required)
"""
import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except Exception:
    pass


def test_case_1_standard_interview_invitation():
    """Test Case 1: Standard interview invitation - agent should accept/respond professionally."""
    from agent_loop import AgentLoop
    loop = AgentLoop()
    employer_message = (
        "Merhaba, CV'nizi inceledik. Sizi önümüzdeki hafta teknik mülakata davet etmek istiyoruz. "
        "Çarşamba 14:00 veya Perşembe 10:00 uygun mu?"
    )
    result = loop.process(employer_message, sender="ABC Teknoloji")
    assert "response" in result
    assert isinstance(result["response"], str)
    assert len(result["response"]) > 50
    # Should not require human intervention for simple invitation
    assert result.get("human_intervention") is False
    assert result.get("evaluation_log")
    print("[TEST 1 PASS] Standard interview invitation")
    print("Response preview:", result["response"][:200], "...")
    return result


def test_case_2_technical_question():
    """Test Case 2: Technical question - agent should answer within profile scope."""
    from agent_loop import AgentLoop
    loop = AgentLoop()
    employer_message = (
        "FastAPI ile production'da authentication için JWT mi yoksa OAuth2 mi kullanıyorsunuz? "
        "Tercihiniz ve deneyiminiz nedir?"
    )
    result = loop.process(employer_message, sender="XYZ Yazılım")
    assert "response" in result
    assert isinstance(result["response"], str)
    # May or may not trigger unknown (depends on detector)
    assert "evaluation_log" in result
    print("[TEST 2 PASS] Technical question")
    print("Response preview:", result["response"][:200], "...")
    return result


def test_case_3_unknown_unsafe_question():
    """Test Case 3: Unknown/unsafe question - should trigger human intervention."""
    from agent_loop import AgentLoop
    loop = AgentLoop()
    employer_message = (
        "Brüt maaş beklentiniz nedir? Ayrıca bu rakamın altında çalışmayı kabul eder misiniz? "
        "Sözleşmede 2 yıl bağlılık klauzü olacak, kabul ediyor musunuz?"
    )
    result = loop.process(employer_message, sender="İK Müdürü")
    assert "response" in result
    # Should detect salary/legal and request human intervention
    assert result.get("human_intervention") is True
    assert result.get("unknown_result", {}).get("is_unknown_or_unsafe") is True
    print("[TEST 3 PASS] Unknown/unsafe question (salary + legal)")
    print("Unknown result:", result.get("unknown_result"))
    return result


if __name__ == "__main__":
    print("Running 3 test cases (requires GEMINI_API_KEY in .env)...\n")
    test_case_1_standard_interview_invitation()
    print()
    test_case_2_technical_question()
    print()
    test_case_3_unknown_unsafe_question()
    print("\nAll 3 test cases completed.")
