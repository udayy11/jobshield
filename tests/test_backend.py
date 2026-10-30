import sys
import os
import json

# Add backend directory to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from fastapi.testclient import TestClient
from app import app
from rules import RuleEngine
from scoring import HybridScoringEngine

client = TestClient(app)


def test_health_endpoint():
    print("\n--- Test: GET /health ---")
    response = client.get("/health")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    print("Health response:", data)
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    assert "accuracy" in data["model_metrics"]
    print("[PASS] Health check passed!")


def test_analyze_genuine_software_engineer():
    print("\n--- Test: Genuine Software Engineer ---")
    payload = {
        "title": "Senior Python Backend Engineer",
        "company": "CloudScale Technologies Inc. - Enterprise SaaS platform provider",
        "description": "Architect and maintain high-throughput asynchronous microservices using Python FastAPI, PostgreSQL, and AWS Kubernetes. Participate in code reviews and architecture planning.",
        "requirements": "Bachelor's degree in Computer Science, 5+ years of Python backend experience, strong knowledge of distributed systems and Docker.",
        "salary": "₹28,00,000 - ₹35,00,000 PA",
        "recruiter_email": "careers@cloudscale-tech.com",
        "application_link": "https://cloudscale-tech.com/careers/backend-dev-2026"
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    print(f"Risk Level: {data['risk_level']} (Score: {data['risk_score']}/100, ML: {data['ml_score']}, Rule: {data['rule_score']})")
    print(f"Positive signals count: {len(data['positive_signals'])}")
    assert data["risk_level"] == "LOW", f"Expected LOW risk for genuine engineer, got {data['risk_level']}"
    assert data["risk_score"] <= 34
    print("[PASS] Genuine job test passed!")


def test_analyze_scam_registration_fee():
    print("\n--- Test: Scam Registration Fee (Critical R1 Override) ---")
    payload = {
        "title": "Online Typing and Proofreading Specialist",
        "company": "Apex Freelance Group",
        "description": "Convert scanned PDFs into Word files. Earn ₹500 per page. Candidates must pay a mandatory ₹2,500 refundable security deposit and registration fee for onboarding software license verification before joining.",
        "requirements": "Basic typing, willingness to deposit security deposit via Google Pay, bank account details required.",
        "salary": "₹45,000 - ₹60,000 per month",
        "recruiter_email": "apexhr.recruitment2026@gmail.com",
        "application_link": "http://pay-security-deposit.freejobsportal.in/register"
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    print(f"Risk Level: {data['risk_level']} (Score: {data['risk_score']}/100, ML: {data['ml_score']}, Rule: {data['rule_score']})")
    print(f"Triggered Warnings: {data['warnings']}")
    assert data["risk_level"] == "HIGH", f"Expected HIGH risk for fee scam, got {data['risk_level']}"
    assert data["risk_score"] >= 75, f"Critical rule R1 should floor score at >=75, got {data['risk_score']}"
    assert any("Upfront Payment" in w for w in data["warnings"])
    print("[PASS] Critical registration fee scam correctly flagged as HIGH RISK!")


def test_analyze_suspicious_wfh_data_entry():
    print("\n--- Test: Suspicious WFH Data Entry (Guaranteed Income & WhatsApp) ---")
    payload = {
        "title": "Work From Home Data Entry Operator - Immediate Start!",
        "company": "Global Quick Earn Careers",
        "description": "Hurry up! Work only 2 to 3 hours a day. Instant selection guaranteed! Daily cash payouts $5,000 to $8,000 monthly. Direct joining without interview!",
        "requirements": "No prior experience required! Zero educational qualifications needed. Must start immediately today.",
        "salary": "$5,000 to $8,000 monthly",
        "recruiter_email": "quickjobsofficial@gmail.com",
        "application_link": "https://wa.me/15550192834"
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    print(f"Risk Level: {data['risk_level']} (Score: {data['risk_score']}/100, ML: {data['ml_score']}, Rule: {data['rule_score']})")
    print(f"Warnings: {data['warnings']}")
    assert data["risk_level"] in ["HIGH", "MEDIUM"]
    assert data["risk_score"] >= 60
    assert any("Informal Messaging" in w for w in data["warnings"])
    assert any("Guaranteed Hiring" in w for w in data["warnings"])
    print("[PASS] Suspicious WFH job correctly flagged!")


def test_insufficient_information_handling():
    print("\n--- Test: Insufficient Job Information Handling ---")
    payload = {
        "title": "Assistant",
        "company": "",
        "description": "Call me.",
        "requirements": "",
        "salary": "",
        "recruiter_email": "",
        "application_link": ""
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    print(f"Risk Level: {data['risk_level']}, Score: {data['risk_score']}")
    print(f"Explanation: {data['explanation']}")
    assert data["risk_level"] == "INSUFFICIENT_INFO", f"Expected INSUFFICIENT_INFO, got {data['risk_level']}"
    print("[PASS] Insufficient info state correctly returned without false low risk!")


def test_empty_request_rejected():
    print("\n--- Test: Completely Empty Request ---")
    payload = {
        "title": "",
        "company": "",
        "description": "",
        "requirements": "",
        "salary": "",
        "recruiter_email": "",
        "application_link": ""
    }
    response = client.post("/analyze", json=payload)
    print("Response status:", response.status_code)
    assert response.status_code == 400
    print("[PASS] Empty request properly rejected with 400 Bad Request!")


if __name__ == "__main__":
    print("=" * 60)
    print("JobShield AI - Automated Backend & Risk Engine Test Suite")
    print("=" * 60)
    test_health_endpoint()
    test_analyze_genuine_software_engineer()
    test_analyze_scam_registration_fee()
    test_analyze_suspicious_wfh_data_entry()
    test_insufficient_information_handling()
    test_empty_request_rejected()
    print("\n" + "=" * 60)
    print("ALL AUTOMATED TESTS PASSED SUCCESSFULLY! (6/6)")
    print("=" * 60)
