# Evaluation Report

Generated: 2026-08-27 20:13:24 UTC

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | 12 |
| Passed | 10 |
| Failed | 2 |
| Pass Rate | 83.3% |
| Average Score | 0.96 |
| Average Latency | 9074ms |

## Task 1 — Triage Agent

| Test ID | Description | Status | Score | LLM Judge | Latency |
|---------|-------------|--------|-------|-----------|---------|
| T1-01 | P1 DataBridge Pro connection timeout — should clas | ❌ FAIL | 0.80 | 1.00 | 4285ms |
| T1-02 | Billing question — seat count discrepancy | ✅ PASS | 1.00 | 1.00 | 4508ms |
| T1-03 | SSO SAML assertion expired — should match auth KB  | ❌ FAIL | 0.75 | 1.00 | 3866ms |
| T1-04 | Feature request — scheduled workflow enhancement | ✅ PASS | 1.00 | 1.00 | 4133ms |
| T1-05 | New user onboarding — CSV import not working | ✅ PASS | 1.00 | 1.00 | 4258ms |
| T1-ADV-01 ⚠️ | ADVERSARIAL: Ambiguous ticket with no clear produc | ✅ PASS | 1.00 | 0.50 | 19537ms |
| T1-ADV-02 ⚠️ | ADVERSARIAL: Ticket body in non-English (Spanish) | ✅ PASS | 1.00 | 1.00 | 4114ms |

## Task 2 — Account Summariser

| Test ID | Description | Status | Score | LLM Judge | Latency |
|---------|-------------|--------|-------|-----------|---------|
| T2-01 | Churning account — should detect high churn risk | ✅ PASS | 1.00 | 0.50 | 4824ms |
| T2-02 | At-risk account — should have flagged risks with e | ✅ PASS | 1.00 | 1.00 | 4937ms |
| T2-03 | Healthy account — should show positive indicators | ✅ PASS | 1.00 | 1.00 | 49609ms |
| T2-04 | New account — should reflect onboarding context | ✅ PASS | 1.00 | 0.00 | 4818ms |
| T2-ADV-01 ⚠️ | ADVERSARIAL: Non-existent account ID | ✅ PASS | 1.00 | N/A | 0ms |

## Detailed Results

### T1-01 — P1 DataBridge Pro connection timeout — should classify as P1 Bug

**Status:** FAIL ❌ | **Score:** 0.80 | **Latency:** 4285ms

| Criterion | Result | Detail |
|-----------|--------|--------|
| urgency=P1 or P2 | ✅ | urgency = P1 matches ['P1', 'P2'] |
| category=Bug or Performance | ✅ | category = Bug matches ['Bug', 'Performance'] |
| product=DataBridge Pro | ✅ | product = DataBridge Pro matches expected |
| kb_match.matched=True | ❌ | kb_match.matched = None, expected True |
| draft_response non-empty | ✅ | Field 'draft_response' present: Hi there,

I understand your |

### T1-02 — Billing question — seat count discrepancy

**Status:** PASS ✅ | **Score:** 1.00 | **Latency:** 4508ms

| Criterion | Result | Detail |
|-----------|--------|--------|
| category=Billing | ✅ | category = Billing matches expected |
| urgency=P3 or P4 | ✅ | urgency = P3 matches ['P3', 'P4'] |
| responder_team=tier1-billing | ✅ | responder_team = tier1-billing matches expected |
| draft_response non-empty | ✅ | Field 'draft_response' present: Hello,

Thank you for reachi |

### T1-03 — SSO SAML assertion expired — should match auth KB doc

**Status:** FAIL ❌ | **Score:** 0.75 | **Latency:** 3866ms

| Criterion | Result | Detail |
|-----------|--------|--------|
| category=Bug or Integration | ✅ | category = Bug matches ['Bug', 'Integration'] |
| kb_match.matched=True | ❌ | kb_match.matched = None, expected True |
| draft_response non-empty | ✅ | Field 'draft_response' present: Hello,

Thank you for reachi |
| product non-empty | ✅ | Field 'product' present: SecureVault |

### T1-04 — Feature request — scheduled workflow enhancement

**Status:** PASS ✅ | **Score:** 1.00 | **Latency:** 4133ms

| Criterion | Result | Detail |
|-----------|--------|--------|
| category=Feature Request | ✅ | category = Feature Request matches expected |
| product=WorkflowEngine | ✅ | product = WorkflowEngine matches expected |
| urgency=P3 or P4 | ✅ | urgency = P4 matches ['P3', 'P4'] |
| draft_response non-empty | ✅ | Field 'draft_response' present: Hello,

Thank you for reachi |

### T1-05 — New user onboarding — CSV import not working

**Status:** PASS ✅ | **Score:** 1.00 | **Latency:** 4258ms

| Criterion | Result | Detail |
|-----------|--------|--------|
| category=Onboarding or Bug | ✅ | category = Onboarding matches ['Onboarding', 'Bug'] |
| product non-empty | ✅ | Field 'product' present: CloudSync |
| draft_response non-empty | ✅ | Field 'draft_response' present: Hi,

Welcome to CloudSync, a |

### T1-ADV-01 — ADVERSARIAL: Ambiguous ticket with no clear product or category

**Status:** PASS ✅ | **Score:** 1.00 | **Latency:** 19537ms

| Criterion | Result | Detail |
|-----------|--------|--------|
| product non-empty | ✅ | Field 'product' present: CloudSync |
| urgency in [P1,P2,P3,P4] | ✅ | urgency = P3 in ['P1', 'P2', 'P3', 'P4'] |
| draft_response non-empty | ✅ | Field 'draft_response' present: Hello,

Thank you for reachi |

### T1-ADV-02 — ADVERSARIAL: Ticket body in non-English (Spanish)

**Status:** PASS ✅ | **Score:** 1.00 | **Latency:** 4114ms

| Criterion | Result | Detail |
|-----------|--------|--------|
| product non-empty | ✅ | Field 'product' present: SecureVault |
| urgency in [P1,P2,P3,P4] | ✅ | urgency = P2 in ['P1', 'P2', 'P3', 'P4'] |
| draft_response non-empty | ✅ | Field 'draft_response' present: Hi,

Thank you for contactin |

### T2-01 — Churning account — should detect high churn risk

**Status:** PASS ✅ | **Score:** 1.00 | **Latency:** 4824ms

| Criterion | Result | Detail |
|-----------|--------|--------|
| executive_summary non-empty | ✅ | Field 'executive_summary' present: Pinnacle Systems is curre |
| churn_risk=True | ✅ | churn_risk = True matches expected |
| churn_risk_score >= 0.6 | ✅ | churn_risk_score = 0.9 >= 0.6 |
| flagged_risks non-empty | ✅ | Field 'flagged_risks' present: [{'risk_type': 'Executive Att |
| talking_points non-empty | ✅ | Field 'talking_points' present: [{'topic': 'Executive Stakeh |

### T2-02 — At-risk account — should have flagged risks with evidence

**Status:** PASS ✅ | **Score:** 1.00 | **Latency:** 4937ms

| Criterion | Result | Detail |
|-----------|--------|--------|
| executive_summary non-empty | ✅ | Field 'executive_summary' present: Omni Consumer Products cu |
| flagged_risks non-empty | ✅ | Field 'flagged_risks' present: [{'risk_type': 'Technical Esc |
| talking_points non-empty | ✅ | Field 'talking_points' present: [{'topic': 'Addressing 3 P1  |
| churn_risk_score >= 0.0 | ✅ | churn_risk_score = 0.9 >= 0.0 |

### T2-03 — Healthy account — should show positive indicators

**Status:** PASS ✅ | **Score:** 1.00 | **Latency:** 49609ms

| Criterion | Result | Detail |
|-----------|--------|--------|
| executive_summary non-empty | ✅ | Field 'executive_summary' present: Polaris Group demonstrate |
| churn_risk_score <= 0.5 | ✅ | churn_risk_score = 0.0 <= 0.5 |
| talking_points non-empty | ✅ | Field 'talking_points' present: [{'topic': 'Zero Support Esc |

### T2-04 — New account — should reflect onboarding context

**Status:** PASS ✅ | **Score:** 1.00 | **Latency:** 4818ms

| Criterion | Result | Detail |
|-----------|--------|--------|
| executive_summary non-empty | ✅ | Field 'executive_summary' present: Solaris Data is a new Ent |
| talking_points non-empty | ✅ | Field 'talking_points' present: [{'topic': 'Zero-Ticket Stab |

### T2-ADV-01 — ADVERSARIAL: Non-existent account ID

**Status:** PASS ✅ | **Score:** 1.00 | **Latency:** 0ms

| Criterion | Result | Detail |
|-----------|--------|--------|
| error_handled_gracefully | ✅ | ValueError raised as expected |
