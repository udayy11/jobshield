import os
from typing import Dict, Any, List, Optional
import httpx
from dotenv import load_dotenv

# Load variables from .env if present
load_dotenv()


class LLMThreatExplainer:
    """
    AI / LLM Threat Explainer for JobShield AI.
    Prioritizes Groq API (e.g. LLaMA 3.3 70B / 3.1 8B) for ultra-fast, structured cyber briefings.
    Falls back to Gemini or an internal threat intelligence engine if keys are absent.
    """

    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY") or ""
        self.gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        
        # Groq configuration
        self.groq_endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

        # Gemini configuration (fallback)
        self.gemini_endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent"

    def explain(
        self,
        job_data: Dict[str, Any],
        risk_level: str,
        risk_score: int,
        warnings: List[Dict[str, Any]],
        positive_signals: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        """Generates clean, bulleted, bolded AI risk analysis."""
        # Refresh environment in case .env was edited
        load_dotenv(override=True)

        # 1. Try Groq API first if key provided
        groq_key = os.getenv("GROQ_API_KEY") or self.groq_api_key
        if groq_key:
            try:
                groq_res = self._call_groq(groq_key, job_data, risk_level, risk_score, warnings, positive_signals)
                if groq_res:
                    text, used_model = groq_res
                    if text and len(text.strip()) > 20:
                        return {
                            "explanation": text.strip(),
                            "source": f"Groq ({used_model})"
                        }
            except Exception as e:
                print(f"[LLMExplainer] Groq API call error: {e}. Attempting secondary fallback.")

        # 2. Try Gemini API if key provided
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or self.gemini_api_key
        if gemini_key:
            try:
                gemini_text = self._call_gemini(gemini_key, job_data, risk_level, risk_score, warnings, positive_signals)
                if gemini_text and len(gemini_text.strip()) > 20:
                    return {
                        "explanation": gemini_text.strip(),
                        "source": "Gemini 3.5 Flash-Lite Threat Analyst"
                    }
            except Exception as e:
                print(f"[LLMExplainer] Gemini API error: {e}.")

        # 3. Built-in Structured Contextual Threat Engine (Always available, cleanly formatted)
        fallback_text = self._generate_contextual_explanation(
            job_data, risk_level, risk_score, warnings, positive_signals
        )
        return {
            "explanation": fallback_text,
            "source": "JobShield Threat Intelligence Engine"
        }

    def _call_groq(
        self,
        api_key: str,
        job: Dict[str, Any],
        risk_level: str,
        risk_score: int,
        warnings: List[Dict[str, Any]],
        positive_signals: List[Dict[str, Any]],
    ) -> Optional[str]:
        title = job.get("title") or "Unspecified Position"
        company = job.get("company") or "Unspecified Entity"
        salary = job.get("salary") or "Unspecified"
        email = job.get("recruiter_email") or "None"
        app_link = job.get("application_link") or "None"
        desc_snippet = (job.get("description") or "")[:350]

        warning_bullets = "\n".join([f"- {w.get('name')}: {w.get('explanation')}" for w in warnings]) or "None"
        positive_bullets = "\n".join([f"- {p.get('name')}: {p.get('explanation')}" for p in positive_signals]) or "Standard baseline"

        system_prompt = (
            "You are JobShield AI's Lead Cyber Threat Intelligence Analyst. "
            "Your output must be minimal, crisp, and high-impact. Avoid conversational filler, introductory remarks, or concluding remarks. "
            "Use clear bold headers, bullet points (•), and bold labels for every point."
        )

        user_prompt = f"""Evaluate this job listing:
Role: {title} | Company: {company} | Salary: {salary}
Contact: {email} | Application Link: {app_link}
Description: {desc_snippet}

Risk Metrics:
- Level: {risk_level} (Score: {risk_score}/100)
- Flags Detected:
{warning_bullets}
- Consistency Signals:
{positive_bullets}

Strictly format your response like this:

**Threat Assessment:**
<1 concise sentence summarizing the risk profile.>

**Key Indicators:**
• **<Indicator 1>:** <1 concise sentence explanation with evidence.>
• **<Indicator 2>:** <1 concise sentence explanation with evidence.>
• **<Indicator 3>:** <1 concise sentence explanation with evidence.>

**Recommended Action:**
• **<Action 1>:** <Specific safety instruction.>
• **<Action 2>:** <Verification step.>

Keep the entire output under 130 words. Bold key phrases."""

        candidates = [
            os.getenv("GROQ_MODEL", "").strip(),
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant"
        ]
        # Deduplicate while preserving order
        seen = set()
        models = [m for m in candidates if m and not (m in seen or seen.add(m))]

        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json"
        }

        with httpx.Client(timeout=8.0) as client:
            for model in models:
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 300
                }
                try:
                    resp = client.post(self.groq_endpoint, json=payload, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data["choices"][0]["message"]["content"]
                        return content, model
                    else:
                        print(f"[LLMExplainer] Groq model '{model}' returned HTTP {resp.status_code}, trying next model.")
                except Exception as e:
                    print(f"[LLMExplainer] Exception calling Groq model '{model}': {e}")

        return None

    def _call_gemini(
        self,
        api_key: str,
        job: Dict[str, Any],
        risk_level: str,
        risk_score: int,
        warnings: List[Dict[str, Any]],
        positive_signals: List[Dict[str, Any]],
    ) -> Optional[str]:
        title = job.get("title") or "Unspecified Position"
        company = job.get("company") or "Unspecified Entity"
        salary = job.get("salary") or "Unspecified"
        email = job.get("recruiter_email") or "None"
        desc_snippet = (job.get("description") or "")[:350]

        warning_bullets = "\n".join([f"- {w.get('name')}: {w.get('explanation')}" for w in warnings]) or "None"

        prompt = f"""You are JobShield AI's Lead Cyber Threat Analyst.
Analyze this job: '{title}' at '{company}' (Salary: {salary}, Email: {email}).
Risk: {risk_level} ({risk_score}/100).
Flags: {warning_bullets}

Format your response strictly as follows with bold labels and bullet points:

**Threat Assessment:**
<1 concise sentence.>

**Key Indicators:**
• **<Flag 1>:** <1 sentence explanation.>
• **<Flag 2>:** <1 sentence explanation.>

**Recommended Action:**
• **<Action 1>:** <1 sentence action.>
• **<Action 2>:** <1 sentence verification.>

Total text must be minimal (under 120 words). No filler text."""

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 300
            }
        }

        url = f"{self.gemini_endpoint}?key={api_key.strip()}"
        with httpx.Client(timeout=7.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            return None

    def _generate_contextual_explanation(
        self,
        job: Dict[str, Any],
        risk_level: str,
        risk_score: int,
        warnings: List[Dict[str, Any]],
        positive_signals: List[Dict[str, Any]],
    ) -> str:
        """Structured fallback intelligence engine with identical bold and bulleted layout."""
        title = job.get("title") or "the position"
        company = job.get("company") or "the employer"
        warning_ids = {w.get("id") for w in warnings}

        if risk_level == "HIGH":
            indicators = []
            if "R1" in warning_ids:
                indicators.append("• **Advance Fee Demand:** Solicits mandatory upfront registration or software license security deposits before hiring.")
            if "R2" in warning_ids:
                indicators.append("• **Credential Phishing:** Requests sensitive passwords, OTPs, or banking details during initial screening.")
            if "R4" in warning_ids:
                indicators.append("• **Off-Platform Chat:** Funnels recruitment communication strictly through WhatsApp or Telegram to avoid audit trails.")
            if "R5" in warning_ids or "R6" in warning_ids:
                indicators.append("• **Bait Compensation:** Promises unrealistic earnings with guaranteed placement without technical assessment.")
            if "R3" in warning_ids:
                indicators.append("• **Unverified Webmail:** Recruiter uses a free public email address rather than an authenticated corporate domain.")
            if "R10" in warning_ids:
                indicators.append("• **Obfuscated Link:** Routs applications through URL shorteners or insecure HTTP endpoints.")

            if not indicators:
                indicators.append("• **Deceptive Patterns:** Employs linguistic cues characteristic of mass fraudulent recruitment schemes.")

            return (
                f"**Threat Assessment:**\n"
                f"High risk profile identified for '{title}' with multiple indicators of recruitment fraud.\n\n"
                f"**Key Indicators:**\n"
                + "\n".join(indicators[:3]) + "\n\n"
                f"**Recommended Action:**\n"
                f"• **Do Not Pay:** Never transfer funds, security deposits, or purchase equipment for employment.\n"
                f"• **Independently Verify:** Cross-reference the company's verified corporate careers page before sharing credentials."
            )

        elif risk_level == "MEDIUM":
            return (
                f"**Threat Assessment:**\n"
                f"Moderate risk observed for '{title}' at {company}. The posting contains questionable recruitment practices.\n\n"
                f"**Key Indicators:**\n"
                f"• **Informal Screening:** Recruiter uses unverified contact pathways or lacks complete corporate credentials.\n"
                f"• **Limited Operational Scope:** Job requirements and responsibilities are vaguely defined.\n\n"
                f"**Recommended Action:**\n"
                f"• **Validate Identity:** Confirm recruiter credentials via LinkedIn or the organization's official email domain.\n"
                f"• **Withhold Sensitive Data:** Refrain from submitting government IDs or banking details until legitimacy is established."
            )

        elif risk_level == "INSUFFICIENT_INFO":
            return (
                f"**Threat Assessment:**\n"
                f"Inconclusive risk profile for '{title}'. Substantive job details are insufficient for full threat evaluation.\n\n"
                f"**Key Indicators:**\n"
                f"• **Minimal Content:** Contains fewer than 12 words of job duties or company background.\n"
                f"• **Unverifiable Entity:** Corporate entity name and application channels cannot be validated.\n\n"
                f"**Recommended Action:**\n"
                f"• **Request Documentation:** Request a formal, detailed job description before engaging.\n"
                f"• **Protect Privacy:** Do not forward resumes containing personal contact information."
            )

        else:
            return (
                f"**Threat Assessment:**\n"
                f"Low risk profile observed for '{title}' at {company}. The posting aligns with standard corporate recruitment practices.\n\n"
                f"**Key Indicators:**\n"
                f"• **Authentic Channels:** Uses institutional corporate email domains and encrypted HTTPS portals.\n"
                f"• **Structured Scope:** Details clear technical requirements, balanced compensation, and role responsibilities.\n\n"
                f"**Recommended Action:**\n"
                f"• **Standard Hygiene:** Apply exclusively through the company's official careers portal.\n"
                f"• **Credential Security:** Never share banking credentials during early-stage interviews."
            )


llm_explainer = LLMThreatExplainer()
