import os
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from model_loader import model_manager
from rules import RuleEngine
from scoring import HybridScoringEngine

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

    assessment["extracted_summary"] = {
        "title": title[:60] if title else "(Not detected)",
        "company": company[:50] if company else "(Not detected)",
        "word_count": combined_words,
        "has_salary": bool(salary),
        "has_recruiter_email": bool(recruiter_email),
        "has_application_link": bool(application_link)
    }

    return assessment


# Mount demo pages if directory exists
demo_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo")
if os.path.exists(demo_dir):
    app.mount("/demo", StaticFiles(directory=demo_dir, html=True), name="demo")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)
