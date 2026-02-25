"""
Three required test cases for Career Assistant AI Agent:
1. Standard interview invitation → AI responds professionally
2. Technical question → AI responds within profile scope
3. Unknown/unsafe question (salary + legal) → Human intervention triggered

Run with: python -m pytest tests/test_cases.py -v
Or manually: python tests/run_test_cases.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except Exception:
    pass


def test_case_1_standard_interview_invitation():
    """Test Case 1: Standard interview invitation - AI should respond, no human intervention."""
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
    assert result.get("human_intervention") is False
    assert result.get("escalation_id") is None
    assert result.get("evaluation_log")

    print("[TEST 1 PASS] Standard interview invitation")
    print(f"  Human intervention: {result.get('human_intervention')}")
    print(f"  Response preview: {result['response'][:200]}...")
    if result.get("evaluation_log"):
        last = result["evaluation_log"][-1]
        print(f"  Score: {last.get('total_score')}/100, Approved: {last.get('approved')}")
    return result


def test_case_2_technical_question():
    """Test Case 2: Technical question within profile scope - AI should answer."""
    from agent_loop import AgentLoop
    loop = AgentLoop()
    employer_message = (
        "FastAPI ile production'da authentication için JWT mi yoksa OAuth2 mi kullanıyorsunuz? "
        "Tercihiniz ve deneyiminiz nedir?"
    )
    result = loop.process(employer_message, sender="XYZ Yazılım")

    assert "response" in result
    assert isinstance(result["response"], str)
    assert len(result["response"]) > 30
    assert "evaluation_log" in result

    print("[TEST 2 PASS] Technical question")
    print(f"  Human intervention: {result.get('human_intervention')}")
    print(f"  Response preview: {result['response'][:200]}...")
    if result.get("evaluation_log"):
        last = result["evaluation_log"][-1]
        print(f"  Score: {last.get('total_score')}/100, Approved: {last.get('approved')}")
    return result


def test_case_3_unknown_unsafe_question():
    """Test Case 3: Salary + legal question - should trigger human intervention, NO AI response."""
    from agent_loop import AgentLoop, keyword_risk_check
    loop = AgentLoop()
    employer_message = (
        "Brüt maaş beklentiniz nedir? Ayrıca bu rakamın altında çalışmayı kabul eder misiniz? "
        "Sözleşmede 2 yıl bağlılık klauzü olacak, kabul ediyor musunuz?"
    )

    kw = keyword_risk_check(employer_message)
    assert kw is not None, "Keyword check should detect salary/legal risk"
    print(f"  Keyword check: {kw['reason']} (category: {kw['category']})")

    result = loop.process(employer_message, sender="İK Müdürü")

    assert "response" in result
    assert result.get("human_intervention") is True
    assert result.get("escalation_id") is not None
    assert result.get("unknown_result", {}).get("is_unknown_or_unsafe") is True
    assert len(result.get("evaluation_log", [])) == 0

    print("[TEST 3 PASS] Unknown/unsafe question (salary + legal)")
    print(f"  Human intervention: {result.get('human_intervention')}")
    print(f"  Escalation ID: {result.get('escalation_id')}")
    print(f"  Category: {result.get('unknown_result', {}).get('category')}")
    print(f"  AI generated response: No (placeholder only)")
    return result


if __name__ == "__main__":
    print("=" * 60)
    print("Career Assistant AI Agent - 3 Test Senaryosu")
    print("=" * 60)
    print()

    test_case_1_standard_interview_invitation()
    print()
    test_case_2_technical_question()
    print()
    test_case_3_unknown_unsafe_question()

    print()
    print("=" * 60)
    print("All 3 test cases PASSED.")
    print("=" * 60)
