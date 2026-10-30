import os
import re
import json
import urllib.request
from html.parser import HTMLParser

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_DIR = os.path.join(BASE_DIR, "demo")

def extract_from_html(html_path):
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Simple regex extraction mirroring the content script selectors
    def get_inner_text(elem_id):
        m = re.search(rf'id=["\']{elem_id}["\'][^>]*>(.*?)</(?:div|h1|h2|p|span|strong|a)', html, re.DOTALL | re.IGNORECASE)
        if m:
            clean = re.sub(r'<[^>]+>', ' ', m.group(1))
            return re.sub(r'\s+', ' ', clean).strip()
        return ""

    title = get_inner_text("job-title")
    company = get_inner_text("company-name")
    salary = get_inner_text("job-salary")
    description = get_inner_text("job-description")
    requirements = get_inner_text("job-requirements")
    email = get_inner_text("recruiter-email")
    
    app_link_match = re.search(r'id=["\']application-link["\'][^>]*href=["\']([^"\']+)["\']', html, re.IGNORECASE)
    app_link = app_link_match.group(1) if app_link_match else ""

    return {
        "title": title,
        "company": company,
        "salary": salary,
        "description": description,
        "requirements": requirements,
        "recruiter_email": email,
        "application_link": app_link
    }

def test_all_demo_pages():
    test_cases = [
        ("genuine_software_engineer.html", "LOW", "Genuine Software Engineer"),
        ("genuine_data_analyst.html", "LOW", "Genuine Data Analyst"),
        ("suspicious_wfh_data_entry.html", "HIGH", "Suspicious WFH Data Entry"),
        ("scam_registration_fee.html", "HIGH", "Scam Registration Fee"),
        ("unrealistic_salary_no_exp.html", ["HIGH", "MEDIUM"], "Unrealistic Salary No Exp")
    ]

    print("=" * 65)
    print("Testing End-to-End Analysis on Demo Job HTML Files")
    print("=" * 65)

    all_passed = True
    for filename, expected_level, label in test_cases:
        path = os.path.join(DEMO_DIR, filename)
        extracted = extract_from_html(path)

        data = json.dumps(extracted).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:8000/analyze",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        res = urllib.request.urlopen(req)
        result = json.loads(res.read())

        risk_level = result["risk_level"]
        risk_score = result["risk_score"]
        ml_score = result["ml_score"]
        rule_score = result["rule_score"]

        if isinstance(expected_level, list):
            passed = risk_level in expected_level
        else:
            passed = risk_level == expected_level

        status = "[PASS]" if passed else "[FAIL]"
        if not passed:
            all_passed = False

        print(f"\n{status} {label} ({filename})")
        print(f"  Extracted Title:   {extracted['title']}")
        print(f"  Extracted Company: {extracted['company']}")
        print(f"  Risk Level:        {risk_level} (Expected: {expected_level})")
        print(f"  Risk Score:        {risk_score}/100 [ML: {ml_score}%, Rule: {rule_score}/100]")
        print(f"  Warnings ({len(result['warnings'])}):")
        for w in result['warnings'][:2]:
            print(f"    - {w}")
        print(f"  Positive Signals ({len(result['positive_signals'])}):")
        for p in result['positive_signals'][:2]:
            print(f"    + {p}")

    print("\n" + "=" * 65)
    if all_passed:
        print("ALL 5 DEMO JOB PAGES PASSED RISK CRITERIA!")
    else:
        print("SOME TESTS FAILED")
    print("=" * 65)

if __name__ == "__main__":
    test_all_demo_pages()
