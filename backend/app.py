import os
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from model_loader import model_manager
from rules import RuleEngine
from scoring import HybridScoringEngine
from llm_explainer import llm_explainer

app = FastAPI(
    title="JobShield AI Backend",
    description="Cybersecurity-Based Browser Extension API for Job Fraud Risk Assessment",
    version="1.0.0"
)

# Enable CORS for Chrome Extension and local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins including chrome-extension://
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rule_engine = RuleEngine()
scoring_engine = HybridScoringEngine(ml_weight=0.65, rule_weight=0.35)


class JobAnalysisRequest(BaseModel):
    title: Optional[str] = Field(default="", description="Job title")
    company: Optional[str] = Field(default="", description="Company name")
    description: Optional[str] = Field(default="", description="Job description / responsibilities")
    requirements: Optional[str] = Field(default="", description="Job requirements or skills")
    salary: Optional[str] = Field(default="", description="Salary range or compensation details")
    location: Optional[str] = Field(default="", description="Job location")
    job_type: Optional[str] = Field(default="", description="Employment type (Full-time, Contract, etc.)")
    recruiter_email: Optional[str] = Field(default="", description="Contact or recruiter email")
    application_link: Optional[str] = Field(default="", description="Application URL or portal link")


class JobAnalysisResponse(BaseModel):
    risk_level: str
    risk_score: int
    ml_score: Optional[int]
    rule_score: int
    warnings: List[str]
    positive_signals: List[str]
    explanation: str
    recommendations: List[str]
    disclaimer: str
    llm_explanation: Optional[str] = None
    llm_source: Optional[str] = None
    detailed_warnings: Optional[List[Dict[str, Any]]] = None
    detailed_positive_signals: Optional[List[Dict[str, Any]]] = None
    extracted_summary: Optional[Dict[str, Any]] = None


@app.get("/")
def root():
    return {
        "service": "JobShield AI Backend",
        "status": "online",
        "documentation": "/docs",
        "health": "/health"
    }


@app.get("/health")
def health_check():
    info = model_manager.get_info()
    return {
        "status": "healthy" if info["loaded"] else "degraded",
        "model_loaded": info["loaded"],
        "model_version": info["version"],
        "algorithm": info["algorithm"],
        "model_metrics": info["metrics"],
        "error": info["error"]
    }


@app.post("/analyze", response_model=JobAnalysisResponse)
def analyze_job(payload: JobAnalysisRequest):
    # Convert Pydantic model to dictionary
    job_data = payload.model_dump()

    title = (job_data.get("title") or "").strip()
    company = (job_data.get("company") or "").strip()
    description = (job_data.get("description") or "").strip()
    requirements = (job_data.get("requirements") or "").strip()
    salary = (job_data.get("salary") or "").strip()
    recruiter_email = (job_data.get("recruiter_email") or "").strip()
    application_link = (job_data.get("application_link") or "").strip()

    # Calculate total substantive content
    combined_words = len(f"{title} {company} {description} {requirements} {salary}".split())

    # Completely empty check
    if combined_words == 0 and not recruiter_email and not application_link:
        raise HTTPException(
            status_code=400,
            detail="No job information provided. Please provide job title, description, or other posting details."
        )

    # Insufficient information threshold check (< 12 words)
    is_insufficient = combined_words < 12

    # Step 1: Rule Engine Analysis
    rule_results = rule_engine.analyze(job_data)
    warnings = rule_results["warnings"]
    positive_signals = rule_results["positive_signals"]

    # Step 2: ML Model Inference
    ml_score, ml_available = model_manager.predict_fraud_risk(job_data)

    # Step 3: Hybrid Scoring
    assessment = scoring_engine.calculate(
        ml_score=ml_score,
        warnings=warnings,
        positive_signals=positive_signals,
        ml_available=ml_available,
        is_insufficient_info=is_insufficient
    )

    # Step 4: AI / LLM Threat Explanation
    llm_result = llm_explainer.explain(
        job_data=job_data,
        risk_level=assessment["risk_level"],
        risk_score=assessment["risk_score"],
        warnings=warnings,
        positive_signals=positive_signals
    )
    assessment["llm_explanation"] = llm_result["explanation"]
    assessment["llm_source"] = llm_result["source"]

    location = (job_data.get("location") or "").strip()
    job_type = (job_data.get("job_type") or "").strip()

    # Determine company domain & legitimacy check
    company_domain = ""
    is_domain_verified = False
    if recruiter_email and "@" in recruiter_email:
        company_domain = recruiter_email.split("@")[-1].lower()
    elif application_link and "://" in application_link:
        try:
            from urllib.parse import urlparse
            company_domain = urlparse(application_link).netloc.lower()
            if company_domain.startswith("www."):
                company_domain = company_domain[4:]
        except Exception:
            pass

    from rules import PERSONAL_EMAIL_DOMAINS, URL_SHORTENERS
    if company_domain and company_domain not in PERSONAL_EMAIL_DOMAINS and company_domain not in URL_SHORTENERS and "." in company_domain:
        is_domain_verified = True

    assessment["extracted_summary"] = {
        "title": title or "Not specified",
        "company": company or "Not specified",
        "location": location or "Location not specified",
        "salary": salary or "Not specified",
        "job_type": job_type or "Full-time",
        "recruiter_email": recruiter_email or "Not provided",
        "application_link": application_link or "",
        "company_domain": company_domain or "Not detected",
        "is_domain_verified": is_domain_verified,
        "word_count": combined_words
    }

    return assessment


# Mount demo pages if directory exists
demo_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo")
if os.path.exists(demo_dir):
    app.mount("/demo", StaticFiles(directory=demo_dir, html=True), name="demo")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)
