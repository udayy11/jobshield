import re
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

# Common personal/free email domains
PERSONAL_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
    "rediffmail.com", "aol.com", "zoho.com", "mail.com", "protonmail.com",
    "yandex.com", "gmx.com"
}

# Suspicious URL shorteners or questionable domains
URL_SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "buff.ly",
    "is.gd", "cutt.ly", "linktr.ee", "rb.gy", "shorturl.at"
}


class RuleEngine:
    """
    JobShield AI Rule-based Risk Engine.
    Detects suspicious indicators (R1-R10) and positive consistency signals.
    """

    def analyze(self, job: Dict[str, Any]) -> Dict[str, Any]:
        title = (job.get("title") or "").strip()
        company = (job.get("company") or "").strip()
        description = (job.get("description") or "").strip()
        requirements = (job.get("requirements") or "").strip()
        salary = (job.get("salary") or "").strip()
        email = (job.get("recruiter_email") or "").strip().lower()
        application_link = (job.get("application_link") or "").strip()

        # Combine text for broader pattern scanning
        full_text = f"{title}\n{company}\n{description}\n{requirements}\n{salary}\n{email}\n{application_link}".strip()
        full_text_lower = full_text.lower()

        warnings = []
        positive_signals = []

        # -------------------------------------------------------------
        # R1: Registration fees, security deposits, training fees (Critical)
        # -------------------------------------------------------------
        fee_patterns = [
            r"(?:registration|processing|application|training|onboarding|equipment|verification)\s+fee[s]?",
            r"security\s+deposit",
            r"refundable\s+(?:deposit|amount|fee)",
            r"(?:pay|deposit|transfer|send)\s+(?:money|\$|inr|rs\.?|usd|\d+)",
            r"mandatory\s+(?:investment|deposit|fee)",
            r"pay\s+before\s+joining"
        ]
        r1_evidence = self._find_first_match(fee_patterns, full_text)
        if r1_evidence:
            warnings.append({
                "id": "R1",
                "name": "Upfront Payment or Deposit Required",
                "severity": "Critical",
                "explanation": "Legitimate employers never demand registration fees, security deposits, or training payments from job seekers.",
                "evidence": r1_evidence
            })

        # -------------------------------------------------------------
        # R2: Requests for OTP, passwords, bank details or sensitive IDs (Critical)
        # -------------------------------------------------------------
        sensitive_patterns = [
            r"\b(?:otp|one[- ]time[- ]password)\b",
            r"(?:bank\s+account|debit\s+card|credit\s+card|cvv|pin\s+number)",
            r"(?:send|share|provide)\s+(?:your\s+)?(?:password|credentials|banking\s+details)",
            r"(?:aadhaar|ssn|social\s+security\s+number)\s+(?:card|details|photo|number)"
        ]
        r2_evidence = self._find_first_match(sensitive_patterns, full_text)
        if r2_evidence:
            warnings.append({
                "id": "R2",
                "name": "Sensitive Financial or Identity Request",
                "severity": "Critical",
                "explanation": "The posting solicits passwords, OTPs, direct banking credentials, or sensitive government IDs before hiring.",
                "evidence": r2_evidence
            })

        # -------------------------------------------------------------
        # R3: Personal email domains used as company recruiters (Medium)
        # -------------------------------------------------------------
        extracted_emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", full_text)
        if email:
            extracted_emails.append(email)
        
        personal_email_found = None
        corporate_email_found = None
        for em in extracted_emails:
            domain = em.split("@")[-1].lower()
            if domain in PERSONAL_EMAIL_DOMAINS:
                personal_email_found = em
                break
            elif "." in domain and domain not in ["example.com", "test.com"]:
                corporate_email_found = em

        if personal_email_found:
            warnings.append({
                "id": "R3",
                "name": "Personal Email for Recruitment",
                "severity": "Medium",
                "explanation": f"Recruiter contact uses a free public email service ({personal_email_found}) rather than a verified corporate email domain.",
                "evidence": personal_email_found
            })
        elif corporate_email_found:
            positive_signals.append({
                "name": "Corporate Domain Email",
                "explanation": f"Recruitment communication references an institutional domain ({corporate_email_found}).",
                "evidence": corporate_email_found
            })

        # -------------------------------------------------------------
        # R4: WhatsApp/Telegram-only communication (High)
        # -------------------------------------------------------------
        chat_patterns = [
            r"(?:contact|message|chat|reach\s+us|apply)\s+(?:via|on|through)?\s*(?:whatsapp|telegram)",
            r"(?:t\.me\/|wa\.me\/|chat\.whatsapp\.com\/)",
            r"whatsapp\s+(?:only|number|no\.?|call)",
            r"telegram\s+(?:only|username|id)"
        ]
        r4_evidence = self._find_first_match(chat_patterns, full_text)
        if r4_evidence:
            warnings.append({
                "id": "R4",
                "name": "Informal Messaging Recruitment",
                "severity": "High",
                "explanation": "Job applications or interviews conducted strictly over WhatsApp or Telegram frequently indicate unverified, fraudulent schemes.",
                "evidence": r4_evidence
            })

        # -------------------------------------------------------------
        # R5: Unrealistic salary with no experience or skills required (Medium)
        # -------------------------------------------------------------
        unrealistic_salary_patterns = [
            r"(?:earn|salary|make|payout|income)\s*(?::|\-|\$|rs\.?|inr)?\s*(?:50000|100000|\$5,?000|\$8,?000|\$10,?000|10\s*lpa|15\s*lpa|20\s*lpa|50\s*per\s*hour)",
            r"(?:daily|weekly)\s+cash\s+payout",
            r"(?:earn|make)\s+\$?[0-9,]+\s+(?:daily|per\s+day)"
        ]
        no_exp_patterns = [
            r"no\s+(?:prior\s+)?experience(?:\s+required|\s+needed)?",
            r"no\s+skills?\s+(?:required|needed)",
            r"anyone\s+can\s+apply",
            r"zero\s+experience"
        ]
        
        salary_match = self._find_first_match(unrealistic_salary_patterns, full_text)
        no_exp_match = self._find_first_match(no_exp_patterns, full_text)
        
        if (salary_match and no_exp_match) or (no_exp_match and "5,000" in full_text):
            evidence_str = f"High compensation claims with '{no_exp_match}'"
            warnings.append({
                "id": "R5",
                "name": "Disproportionate Compensation vs Low Qualifications",
                "severity": "Medium",
                "explanation": "Outsized financial compensation promised for low-skill, zero-experience positions is a hallmark fraud tactic.",
                "evidence": evidence_str
            })
        elif salary and not salary_match:
            positive_signals.append({
                "name": "Reasonable Compensation Disclosure",
                "explanation": "Compensation is specified without exaggerated get-rich claims.",
                "evidence": salary
            })

        # -------------------------------------------------------------
        # R6: Instant selection or guaranteed income (High)
        # -------------------------------------------------------------
        guarantee_patterns = [
            r"guaranteed\s+(?:income|selection|job|employment|placement)",
            r"instant\s+(?:selection|hiring|offer|appointment)",
            r"100%\s+selection",
            r"direct\s+joining\s+without\s+interview",
            r"immediate\s+offer\s+letter"
        ]
        r6_evidence = self._find_first_match(guarantee_patterns, full_text)
        if r6_evidence:
            warnings.append({
                "id": "R6",
                "name": "Guaranteed Hiring or Instant Selection",
                "severity": "High",
                "explanation": "Legitimate organizations conduct interviews and background checks; guaranteed or instant hiring claims are deceptive.",
                "evidence": r6_evidence
            })

        # -------------------------------------------------------------
        # R7: Urgent application pressure or limited seats (Low)
        # -------------------------------------------------------------
        urgency_patterns = [
            r"urgent\s+(?:opening|requirement|hiring)",
            r"limited\s+(?:seats|vacancies|slots)",
            r"apply\s+(?:immediately|today|now)\s+(?:or\s+lose|before\s+it\s+closes)",
            r"hurry\s+up",
            r"only\s+\d+\s+slots\s+left"
        ]
        r7_evidence = self._find_first_match(urgency_patterns, full_text)
        if r7_evidence:
            warnings.append({
                "id": "R7",
                "name": "Artificial Urgency or Scarcity Pressure",
                "severity": "Low",
                "explanation": "The posting creates high-pressure urgency ('urgent opening', 'limited vacancies') to bypass candidate due diligence.",
                "evidence": r7_evidence
            })

        # -------------------------------------------------------------
        # R8: Missing or insufficient company information (Low)
        # -------------------------------------------------------------
        company_clean = re.sub(r"[^a-zA-Z0-9]", "", company)
        if len(company_clean) < 3 or company.lower() in ["n/a", "confidential", "hiring company", "company"]:
            warnings.append({
                "id": "R8",
                "name": "Missing or Anonymous Company Identity",
                "severity": "Low",
                "explanation": "The employer profile lacks a verifiable corporate entity name or organizational background.",
                "evidence": company if company else "Company name field empty"
            })
        else:
            positive_signals.append({
                "name": "Identified Company Name",
                "explanation": f"Job posting provides a named corporate entity: {company}.",
                "evidence": company
            })

        # -------------------------------------------------------------
        # R9: Vague job description (Low)
        # -------------------------------------------------------------
        desc_word_count = len(description.split())
        req_word_count = len(requirements.split())
        if desc_word_count < 30 and req_word_count < 15:
            warnings.append({
                "id": "R9",
                "name": "Vague or Minimal Job Description",
                "severity": "Low",
                "explanation": f"The job description is brief ({desc_word_count} words) with minimal operational responsibilities or technical depth.",
                "evidence": f"Total description length: {desc_word_count} words"
            })
        else:
            if desc_word_count >= 50:
                positive_signals.append({
                    "name": "Detailed Job Responsibilities",
                    "explanation": f"Comprehensive description provided ({desc_word_count} words) outlining tasks and scope.",
                    "evidence": f"{desc_word_count} words in description"
                })
            if req_word_count >= 20:
                positive_signals.append({
                    "name": "Structured Role Requirements",
                    "explanation": f"Specific skills and qualifications are detailed ({req_word_count} words).",
                    "evidence": f"{req_word_count} words in requirements"
                })

        # -------------------------------------------------------------
        # R10: Suspicious application URLs or URL shorteners (Medium)
        # -------------------------------------------------------------
        urls = re.findall(r"https?://[^\s<>\"']+", full_text)
        if application_link:
            urls.append(application_link)
        
        suspicious_url_found = None
        valid_https_found = None
        for u in urls:
            try:
                parsed = urlparse(u)
                netloc = parsed.netloc.lower()
                if any(shortener in netloc for shortener in URL_SHORTENERS):
                    suspicious_url_found = u
                    break
                elif parsed.scheme == "http" and "localhost" not in netloc and "127.0.0.1" not in netloc:
                    suspicious_url_found = u
                    break
                elif parsed.scheme == "https":
                    valid_https_found = u
            except Exception:
                continue

        if suspicious_url_found:
            warnings.append({
                "id": "R10",
                "name": "Suspicious or Obfuscated Application URL",
                "severity": "Medium",
                "explanation": f"Application link uses a URL shortener or unencrypted HTTP endpoint ({suspicious_url_found}), obscuring true destination.",
                "evidence": suspicious_url_found
            })
        elif valid_https_found:
            positive_signals.append({
                "name": "Encrypted HTTPS Application Link",
                "explanation": "Application routing utilizes standard secure HTTPS protocols.",
                "evidence": valid_https_found
            })

        return {
            "warnings": warnings,
            "positive_signals": positive_signals
        }

    def _find_first_match(self, patterns: List[str], text: str) -> Optional[str]:
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                # Return snippet around match
                start = max(0, match.start() - 15)
                end = min(len(text), match.end() + 25)
                snippet = text[start:end].replace("\n", " ").strip()
                return f"...{snippet}..."
        return None
