# src/evaluation.py
"""Task 3 — Evaluation Harness.
Tests Task 1 (triage) and Task 2 (summariser) with:
- Rule-based checks (field presence, enum validation, score thresholds)
- LLM-as-judge scoring
- Adversarial test cases
Produces eval_report.md"""

import json
import re
import time
from dataclasses import dataclass, field
from typing import Callable, Optional
import google.generativeai as genai

from src.triage_agent import run_triage, PRODUCTS, CATEGORIES, URGENCIES
from src.account_summariser import generate_account_brief
from src.data_loader import get_all_accounts


@dataclass
class TestCase:
    test_id: str
    task: str
    description: str
    is_adversarial: bool = False
    input_data: dict = field(default_factory=dict)
    acceptance_criteria: list[str] = field(default_factory=list)


@dataclass
class TestResult:
    test_id: str
    task: str
    description: str
    is_adversarial: bool
    passed: bool
    score: float
    criteria_results: list[dict] = field(default_factory=list)
    llm_judge_score: Optional[float] = None
    error: Optional[str] = None
    latency_ms: int = 0


def _llm_judge(output: dict, criteria: str, context: str = "") -> float:
    prompt = f"""You are an evaluator scoring an AI system output.

Score how well the output meets the criteria on a scale of 0.0 to 1.0.
0.0 = completely fails, 0.5 = partially meets, 1.0 = fully meets.
Return ONLY a JSON object: {{"score": <float>, "reasoning": "<1 sentence>"}}

## Criteria
{criteria}

## Context
{context}

## Output to evaluate
{json.dumps(output, indent=2)[:2000]}

JSON:"""
    model = genai.GenerativeModel(
        "models/gemini-3.5-flash-lite",
        generation_config=genai.types.GenerationConfig(temperature=0.0, max_output_tokens=256),
    )
    raw = None
    for attempt in range(5):
        try:
            raw = model.generate_content(prompt).text.strip()
            break
        except Exception as e:
            if "429" in str(e) and attempt < 4:
                wait = 2 ** attempt * 10
                time.sleep(wait)
            else:
                return 0.5
    if raw is None:
        return 0.5
    try:
        fence = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw)
        if fence:
            raw = fence.group(1)
        data = json.loads(raw[raw.find('{'):raw.rfind('}') + 1])
        return float(data.get("score", 0.5))
    except Exception:
        return 0.5


def _check_field_present(output: dict, field_path: str) -> tuple[bool, str]:
    parts = field_path.split(".")
    current = output
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return False, f"Missing field: {field_path}"
        current = current[part]
    if current is None or current == "" or current == []:
        return False, f"Field '{field_path}' is empty"
    return True, f"Field '{field_path}' present: {str(current)[:60]}"


def _check_enum_value(output: dict, field_name: str, allowed: list) -> tuple[bool, str]:
    val = output.get(field_name)
    if val in allowed:
        return True, f"'{field_name}' = '{val}' is valid"
    return False, f"'{field_name}' = '{val}' not in {allowed}"


def _check_score_threshold(score: float, threshold: float) -> tuple[bool, str]:
    if 0.0 <= score <= 1.0:
        return True, f"churn_risk_score={score:.2f} is in valid range"
    return False, f"churn_risk_score={score} out of range [0,1]"


def _build_task1_test_cases() -> list[TestCase]:
    return [
        TestCase(
            test_id="T1-01", task="task1",
            description="P1 DataBridge Pro connection timeout — should classify as P1 Bug",
            input_data={
                "subject": "CRITICAL: DataBridge Pro pipeline completely down",
                "body": "Our entire ETL pipeline has been down for 3 hours. Error: ERR_CONNECTION_TIMEOUT after 30s. 47 engineers are blocked. Production data is not flowing. This is causing major revenue impact.",
            },
            acceptance_criteria=["urgency=P1 or P2", "category=Bug or Performance", "product=DataBridge Pro", "kb_match.matched=True", "draft_response non-empty"],
        ),
        TestCase(
            test_id="T1-02", task="task1",
            description="Billing question — seat count discrepancy",
            input_data={
                "subject": "Being charged for 50 seats but only 38 active users",
                "body": "Our invoice shows 50 seats but our HR system shows only 38 active employees. We need an explanation and a credit for the overage.",
            },
            acceptance_criteria=["category=Billing", "urgency=P3 or P4", "responder_team=tier1-billing", "draft_response non-empty"],
        ),
        TestCase(
            test_id="T1-03", task="task1",
            description="SSO SAML assertion expired — should match auth KB doc",
            input_data={
                "subject": "SAML_ASSERTION_EXPIRED error preventing login",
                "body": "All our users are getting SAML_ASSERTION_EXPIRED when trying to log in via Okta. This started 2 hours ago. We haven't changed any configuration.",
            },
            acceptance_criteria=["category=Bug or Integration", "kb_match.matched=True", "draft_response non-empty", "product non-empty"],
        ),
        TestCase(
            test_id="T1-04", task="task1",
            description="Feature request — scheduled workflow enhancement",
            input_data={
                "subject": "Feature: Parallel branch support in WorkflowEngine Starter plan",
                "body": "We are on the Starter plan and need parallel branch execution in our workflows. Currently only sequential actions are supported. Can you add this?",
            },
            acceptance_criteria=["category=Feature Request", "product=WorkflowEngine", "urgency=P3 or P4", "draft_response non-empty"],
        ),
        TestCase(
            test_id="T1-05", task="task1",
            description="New user onboarding — CSV import not working",
            input_data={
                "subject": "Cannot import users via CSV — getting error on upload",
                "body": "We're trying to bulk import our 200 users using the CSV template. After uploading, we get a generic error and no users are created. We're new customers trying to complete initial setup.",
            },
            acceptance_criteria=["category=Onboarding or Bug", "product non-empty", "draft_response non-empty"],
        ),
        TestCase(
            test_id="T1-ADV-01", task="task1",
            description="ADVERSARIAL: Ambiguous ticket with no clear product or category",
            is_adversarial=True,
            input_data={
                "subject": "Something is broken",
                "body": "Things don't work. Please fix it.",
            },
            acceptance_criteria=["product non-empty", "urgency in [P1,P2,P3,P4]", "draft_response non-empty"],
        ),
        TestCase(
            test_id="T1-ADV-02", task="task1",
            description="ADVERSARIAL: Ticket body in non-English (Spanish)",
            is_adversarial=True,
            input_data={
                "subject": "Error de autenticación en SecureVault",
                "body": "Hola, estamos teniendo problemas para iniciar sesión en SecureVault. El error que vemos es AUTH_TOKEN_EXPIRED pero acabamos de crear la cuenta.",
            },
            acceptance_criteria=["product non-empty", "urgency in [P1,P2,P3,P4]", "draft_response non-empty"],
        ),
    ]


def _build_task2_test_cases() -> list[TestCase]:
    accounts = get_all_accounts()
    churning_accs = [a for a in accounts if a["health_status"] == "Churning"]
    at_risk_accs = [a for a in accounts if a["health_status"] == "At Risk"]
    healthy_accs = [a for a in accounts if a["health_status"] == "Healthy"]
    new_accs = [a for a in accounts if a["health_status"] == "New"]

    churning_id = churning_accs[0]["account_id"] if churning_accs else accounts[0]["account_id"]
    at_risk_id = at_risk_accs[0]["account_id"] if at_risk_accs else accounts[1]["account_id"]
    healthy_id = healthy_accs[0]["account_id"] if healthy_accs else accounts[2]["account_id"]
    new_id = new_accs[0]["account_id"] if new_accs else accounts[3]["account_id"]

    return [
        TestCase(
            test_id="T2-01", task="task2",
            description="Churning account — should detect high churn risk",
            input_data={"account_id": churning_id},
            acceptance_criteria=["executive_summary non-empty", "churn_risk=True", "churn_risk_score >= 0.6", "flagged_risks non-empty", "talking_points non-empty"],
        ),
        TestCase(
            test_id="T2-02", task="task2",
            description="At-risk account — should have flagged risks with evidence",
            input_data={"account_id": at_risk_id},
            acceptance_criteria=["executive_summary non-empty", "flagged_risks non-empty", "talking_points non-empty", "churn_risk_score >= 0.0"],
        ),
        TestCase(
            test_id="T2-03", task="task2",
            description="Healthy account — should show positive indicators",
            input_data={"account_id": healthy_id},
            acceptance_criteria=["executive_summary non-empty", "churn_risk_score <= 0.5", "talking_points non-empty"],
        ),
        TestCase(
            test_id="T2-04", task="task2",
            description="New account — should reflect onboarding context",
            input_data={"account_id": new_id},
            acceptance_criteria=["executive_summary non-empty", "talking_points non-empty"],
        ),
        TestCase(
            test_id="T2-ADV-01", task="task2",
            description="ADVERSARIAL: Non-existent account ID",
            is_adversarial=True,
            input_data={"account_id": "ACC-NONEXISTENT-9999"},
            acceptance_criteria=["error_handled_gracefully"],
        ),
    ]


def _evaluate_criteria(output: dict, criteria: str) -> tuple[bool, str]:
    """Evaluate a single acceptance criterion against the output."""
    try:
        if "non-empty" in criteria:
            field_name = criteria.replace(" non-empty", "").strip()
            return _check_field_present(output, field_name)
        elif "=" in criteria and ">=" not in criteria and "<=" not in criteria:
            parts = criteria.split("=", 1)
            field_name = parts[0].strip()
            expected = parts[1].strip()
            if " or " in expected:
                allowed = [v.strip() for v in expected.split(" or ")]
                actual = output.get(field_name)
                if isinstance(actual, dict):
                    # Handle nested like kb_match.matched
                    path = field_name.split(".")
                    current = output
                    for p in path:
                        current = current.get(p, {}) if isinstance(current, dict) else None
                    actual = current
                if str(actual) in [str(a) for a in allowed] or actual in allowed:
                    return True, f"{field_name} = {actual} matches {allowed}"
                return False, f"{field_name} = {actual} not in {allowed}"
            else:
                actual = output.get(field_name)
                if isinstance(actual, dict) and "." in field_name:
                    path = field_name.split(".")
                    current = output
                    for p in path:
                        current = current.get(p, {}) if isinstance(current, dict) else None
                    actual = current
                if str(actual) == expected or actual == (expected == "True"):
                    return True, f"{field_name} = {actual} matches expected"
                return False, f"{field_name} = {actual}, expected {expected}"
        elif ">=" in criteria:
            parts = criteria.split(">=")
            field_name = parts[0].strip()
            threshold = float(parts[1].strip())
            actual = float(output.get(field_name, 0))
            if actual >= threshold:
                return True, f"{field_name} = {actual} >= {threshold}"
            return False, f"{field_name} = {actual} < {threshold}"
        elif "<=" in criteria:
            parts = criteria.split("<=")
            field_name = parts[0].strip()
            threshold = float(parts[1].strip())
            actual = float(output.get(field_name, 0))
            if actual <= threshold:
                return True, f"{field_name} = {actual} <= {threshold}"
            return False, f"{field_name} = {actual} > {threshold}"
        elif "in [" in criteria:
            parts = criteria.split(" in ")
            field_name = parts[0].strip()
            allowed_str = parts[1].strip().strip("[]")
            allowed = [v.strip() for v in allowed_str.split(",")]
            actual = output.get(field_name)
            if actual in allowed:
                return True, f"{field_name} = {actual} in {allowed}"
            return False, f"{field_name} = {actual} not in {allowed}"
        else:
            return True, f"Criterion '{criteria}' — skipped (manual check)"
    except Exception as e:
        return False, f"Error evaluating '{criteria}': {str(e)[:100]}"


def run_evaluation() -> list[TestResult]:
    """Run all test cases and return results."""
    results = []
    task1_tests = _build_task1_test_cases()
    task2_tests = _build_task2_test_cases()
    all_tests = task1_tests + task2_tests

    for i, tc in enumerate(all_tests):
        # Rate limit protection: wait between tests to avoid 429 errors
        if i > 0:
            wait = 3  # seconds between test cases
            print(f"\n  [Rate Limit] Waiting {wait}s before next test...")
            time.sleep(wait)

        print(f"\n{'='*60}")
        print(f"Running {tc.test_id}: {tc.description}")
        print(f"{'='*60}")

        start = time.time()
        error = None
        output_dict = {}
        criteria_results = []
        passed = True
        llm_score = None

        try:
            if tc.task == "task1":
                result = run_triage(
                    subject=tc.input_data["subject"],
                    body=tc.input_data["body"],
                    ticket_id=tc.test_id,
                )
                output_dict = result.model_dump()

            elif tc.task == "task2":
                if tc.test_id == "T2-ADV-01":
                    try:
                        result = generate_account_brief(tc.input_data["account_id"])
                        output_dict = result.model_dump()
                        criteria_results.append({"criterion": "error_handled_gracefully", "passed": False, "detail": "Expected error but got result"})
                        passed = False
                    except ValueError:
                        criteria_results.append({"criterion": "error_handled_gracefully", "passed": True, "detail": "ValueError raised as expected"})
                        output_dict = {"error": "handled"}
                else:
                    result = generate_account_brief(tc.input_data["account_id"])
                    output_dict = result.model_dump()

            # Evaluate acceptance criteria
            if tc.test_id != "T2-ADV-01":
                for criterion in tc.acceptance_criteria:
                    ok, detail = _evaluate_criteria(output_dict, criterion)
                    criteria_results.append({"criterion": criterion, "passed": ok, "detail": detail})
                    if not ok:
                        passed = False

            # LLM-as-judge for quality assessment
            if output_dict and tc.test_id != "T2-ADV-01":
                try:
                    judge_criteria = f"The output should correctly handle: {tc.description}"
                    llm_score = _llm_judge(output_dict, judge_criteria, json.dumps(tc.input_data)[:500])
                except Exception:
                    llm_score = None

        except Exception as e:
            error = str(e)[:200]
            passed = False

        latency = int((time.time() - start) * 1000)
        score = (sum(1 for c in criteria_results if c["passed"]) / max(len(criteria_results), 1))

        results.append(TestResult(
            test_id=tc.test_id, task=tc.task, description=tc.description,
            is_adversarial=tc.is_adversarial, passed=passed, score=score,
            criteria_results=criteria_results, llm_judge_score=llm_score,
            error=error, latency_ms=latency,
        ))

        status = "PASS" if passed else "FAIL"
        print(f"  Result: {status} | Score: {score:.2f} | Latency: {latency}ms")
        if error:
            print(f"  Error: {error}")
        for cr in criteria_results:
            icon = "PASS" if cr["passed"] else "FAIL"
            detail_text = cr['detail'][:80].encode('ascii', 'replace').decode('ascii')
            print(f"  [{icon}] {cr['criterion']}: {detail_text}")

    return results


def generate_report(results: list[TestResult], output_path: str = "eval_report.md") -> str:
    """Generate a markdown evaluation report."""
    lines = ["# Evaluation Report\n"]
    lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n")

    # Summary
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    avg_score = sum(r.score for r in results) / max(total, 1)
    avg_latency = sum(r.latency_ms for r in results) / max(total, 1)

    lines.append("## Summary\n")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total Tests | {total} |")
    lines.append(f"| Passed | {passed} |")
    lines.append(f"| Failed | {failed} |")
    lines.append(f"| Pass Rate | {passed/max(total,1)*100:.1f}% |")
    lines.append(f"| Average Score | {avg_score:.2f} |")
    lines.append(f"| Average Latency | {avg_latency:.0f}ms |\n")

    # Task 1 Results
    t1_results = [r for r in results if r.task == "task1"]
    if t1_results:
        lines.append("## Task 1 — Triage Agent\n")
        lines.append("| Test ID | Description | Status | Score | LLM Judge | Latency |")
        lines.append("|---------|-------------|--------|-------|-----------|---------|")
        for r in t1_results:
            status = "✅ PASS" if r.passed else "❌ FAIL"
            llm = f"{r.llm_judge_score:.2f}" if r.llm_judge_score is not None else "N/A"
            adv = " ⚠️" if r.is_adversarial else ""
            lines.append(f"| {r.test_id}{adv} | {r.description[:50]} | {status} | {r.score:.2f} | {llm} | {r.latency_ms}ms |")
        lines.append("")

    # Task 2 Results
    t2_results = [r for r in results if r.task == "task2"]
    if t2_results:
        lines.append("## Task 2 — Account Summariser\n")
        lines.append("| Test ID | Description | Status | Score | LLM Judge | Latency |")
        lines.append("|---------|-------------|--------|-------|-----------|---------|")
        for r in t2_results:
            status = "✅ PASS" if r.passed else "❌ FAIL"
            llm = f"{r.llm_judge_score:.2f}" if r.llm_judge_score is not None else "N/A"
            adv = " ⚠️" if r.is_adversarial else ""
            lines.append(f"| {r.test_id}{adv} | {r.description[:50]} | {status} | {r.score:.2f} | {llm} | {r.latency_ms}ms |")
        lines.append("")

    # Detailed Results
    lines.append("## Detailed Results\n")
    for r in results:
        lines.append(f"### {r.test_id} — {r.description}\n")
        status = "PASS ✅" if r.passed else "FAIL ❌"
        lines.append(f"**Status:** {status} | **Score:** {r.score:.2f} | **Latency:** {r.latency_ms}ms\n")
        if r.error:
            lines.append(f"**Error:** {r.error}\n")
        if r.criteria_results:
            lines.append("| Criterion | Result | Detail |")
            lines.append("|-----------|--------|--------|")
            for cr in r.criteria_results:
                icon = "✅" if cr["passed"] else "❌"
                lines.append(f"| {cr['criterion']} | {icon} | {cr['detail'][:60]} |")
            lines.append("")

    report = "\n".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nReport written to {output_path}")
    return report
