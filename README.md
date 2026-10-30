<<<<<<< HEAD
# JobShield AI 🛡️
### A Cybersecurity-Based Browser Extension for Job Fraud Risk Assessment

JobShield AI is an end-to-end cyber threat assessment prototype designed to detect and flag fraudulent recruitment advertisements and deceptive job postings in real time. It combines machine learning text analysis, heuristic rule-based risk detection, and safety-overridden hybrid scoring to protect job seekers.

---

## 1. System Architecture

```
Job Posting Webpage (LinkedIn, Indeed, Portal)
                     │
                     ▼
          Chrome Browser Extension (Manifest V3)
                     │
                     ▼ DOM Extraction
          FastAPI Backend (http://127.0.0.1:8000)
                     │
       ┌─────────────┴─────────────┐
       ▼                           ▼
  ML Model Pipeline         Rule Engine (R1–R10)
  (TF-IDF + LogReg)         (Critical / High / Med / Low)
       │                           │
       └─────────────┬─────────────┘
                     ▼
           Hybrid Risk Engine
   [Final = 0.65 × ML + 0.35 × Rule]
         (with Safety Floors)
                     │
                     ▼
          Structured JSON Response
                     │
                     ▼
          Popup Extension UI (Color-Coded)
```

---

## 2. Key Implemented Features

1. **Machine Learning Model (`ml/`)**:
   - Trained on the Kaggle EMCSC Fake Job Postings dataset (17,880 records).
   - Stratified 80/20 train/test split preventing data leakage.
   - Text normalization and concatenation across `title`, `company_profile`, `description`, `requirements`, and `benefits`.
   - Feature extraction via n-gram TF-IDF (`ngram_range=(1, 2)`, 12,000 max features, sublinear term frequency).
   - Classifier: Logistic Regression with balanced class weighting (`class_weight='balanced'`) to handle extreme ~4.8% class imbalance.
   - Model persistence via Joblib (`ml/model.pkl`).

2. **Heuristic Rule-Based Risk Engine (`backend/rules.py`)**:
   - **R1 (Critical)**: Registration fees, security deposits, training fees.
   - **R2 (Critical)**: Requests for OTPs, passwords, bank accounts, or sensitive IDs.
   - **R3 (Medium)**: Personal free webmail domains (`gmail.com`, `yahoo.com`, etc.) used by corporate recruiters.
   - **R4 (High)**: WhatsApp/Telegram-only recruitment communication.
   - **R5 (Medium)**: Disproportionate/unrealistic compensation for zero-experience or low-skill roles.
   - **R6 (High)**: Instant selection, direct joining without interview, or guaranteed income claims.
   - **R7 (Low)**: Artificial urgency or scarcity pressure ("limited seats", "hurry up").
   - **R8 (Low)**: Missing or anonymous company profile.
   - **R9 (Low)**: Vague or minimal job description (< 30 words).
   - **R10 (Medium)**: Suspicious URLs, unencrypted HTTP endpoints, or link shorteners (`bit.ly`, `tinyurl.com`).
   - **Positive Consistency Indicators**: Corporate domain emails, detailed responsibilities, structured requirements, verified HTTPS application portals.

3. **Hybrid Risk Scoring & Safety Engine (`backend/scoring.py`)**:
   - Configurable formula: `Final Score = (0.65 × ML Score) + (0.35 × Rule Score)`.
   - Normalization: 0 to 100.
   - Risk Tiers:
     - **0 – 34**: LOW RISK (Green)
     - **35 – 65**: MEDIUM RISK (Amber)
     - **66 – 100**: HIGH RISK (Red)
   - **Critical Overrides**: If Critical rules (R1 upfront fees, R2 credentials) trigger, the score is automatically floored at **≥ 75 (High Risk)** regardless of ML confidence.
   - **Insufficient Information Handling**: Postings with fewer than 12 words return `INSUFFICIENT_INFO` rather than false low-risk confidence.

4. **FastAPI Backend Server (`backend/app.py`)**:
   - `GET /health`: Returns service status, loaded model metadata, and training metrics.
   - `POST /analyze`: Accepts extracted job attributes and returns comprehensive risk breakdown, warnings with evidence, positive signals, explanation, recommendations, and disclaimers.
   - Full CORS support for Chrome Extension communication.
   - Built-in static hosting for demo portal at `/demo`.

5. **Chrome Manifest V3 Extension (`extension/`)**:
   - Modern dark-mode cybersecurity user interface.
   - One-click active tab DOM extraction with semantic fallbacks.
   - Dynamic real-time backend status badge (Online / Degraded / Offline).
   - Safe DOM manipulation (prevents XSS vulnerabilities).
   - Color-coded risk meter and component breakdown cards.

6. **Interactive Demo Portal (`demo/`)**:
   - `index.html`: Portal dashboard with quick-launch links.
   - `genuine_software_engineer.html`: Low risk enterprise engineering posting.
   - `genuine_data_analyst.html`: Low risk retail analytics posting.
   - `suspicious_wfh_data_entry.html`: High risk WhatsApp instant-hiring scheme.
   - `scam_registration_fee.html`: Critical risk upfront deposit scam.
   - `unrealistic_salary_no_exp.html`: High risk $200/hr no-skill posting.

---

## 3. Actual ML Evaluation Results (Held-Out Test Set)

Evaluated on 3,576 held-out test samples (20% stratified test split):

| Metric | Score |
|---|---|
| **Accuracy** | **98.01%** |
| **Precision (Fraudulent Class)** | **74.06%** |
| **Recall (Fraudulent Class)** | **90.75%** |
| **F1-Score (Fraudulent Class)** | **81.56%** |
| **ROC-AUC** | **0.9920** |

### Confusion Matrix

```
                      Predicted Legit (0)    Predicted Fraud (1)
Actual Legit (0)             3,348                   55
Actual Fraud (1)                16                  157
```

- **True Negatives**: 3,348 legitimate jobs correctly classified.
- **False Positives**: 55 legitimate jobs flagged as fraud.
- **False Negatives**: 16 fraudulent jobs missed by ML alone (safeguarded by the Rule Engine).
- **True Positives**: 157 fraudulent jobs correctly detected.

---

## 4. API Endpoints

### 1. `GET /health`
Returns backend health status, model persistence state, and test evaluation metrics.

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_version": "1.0.0",
  "algorithm": "TF-IDF (1-2 ngrams, 12000 features) + Logistic Regression (class_weight=balanced, C=1.5)",
  "model_metrics": {
    "accuracy": 0.9801,
    "precision": 0.7406,
    "recall": 0.9075,
    "f1_score": 0.8156,
    "roc_auc": 0.9920
  }
}
```

### 2. `POST /analyze`
Accepts job attributes and returns risk analysis.

**Sample Request:**
```json
{
  "title": "Online Typing Specialist",
  "company": "Apex Freelance Group",
  "description": "Convert scanned PDFs into Word files. Candidates must pay a mandatory $150 refundable registration fee before onboarding.",
  "requirements": "Basic typing, security deposit required.",
  "salary": "$50/hour",
  "recruiter_email": "apexrecruiter@gmail.com",
  "application_link": "http://pay-fee.freeportal.in"
}
```

**Sample Response:**
```json
{
  "risk_level": "HIGH",
  "risk_score": 75,
  "ml_score": 28,
  "rule_score": 100,
  "warnings": [
    "Upfront Payment or Deposit Required (Critical): Legitimate employers never demand registration fees, security deposits, or training payments from job seekers.",
    "Personal Email for Recruitment (Medium): Recruiter contact uses a free public email service (apexrecruiter@gmail.com) rather than a verified corporate email domain."
  ],
  "positive_signals": [
    "Identified Company Name: Job posting provides a named corporate entity: Apex Freelance Group."
  ],
  "explanation": "High risk indicators detected: Upfront Payment or Deposit Required, Personal Email for Recruitment.",
  "recommendations": [
    "NEVER pay registration, training, or equipment fees for a job opportunity.",
    "Verify recruiter identity through official corporate channels, not free webmail domains."
  ],
  "disclaimer": "This assessment is decision-support only and is not proof of fraud or legitimacy. Never consider any employer 'verified' solely on text signals."
}
```

---

## 5. Project File Structure

```
JobShield/
├── ml/
│   ├── data/
│   │   └── fake_job_postings.csv    # Kaggle dataset
│   ├── preprocess.py                # Text normalization and feature concatenation
│   ├── train.py                     # ML pipeline training and evaluation
│   ├── model.pkl                    # Serialized Joblib model artifact
│   └── metrics.json                 # Test metrics
│
├── backend/
│   ├── app.py                       # FastAPI application & endpoints
│   ├── model_loader.py              # Model caching and inference manager
│   ├── rules.py                     # Rule Engine (R1–R10 + positive signals)
│   └── scoring.py                   # Hybrid Risk Engine & safety overrides
│
├── extension/
│   ├── manifest.json                # Chrome Manifest V3 configuration
│   ├── content.js                   # DOM text extraction script
│   ├── popup.html                   # Extension popup interface
│   ├── popup.css                    # Cyber theme styling
│   ├── popup.js                     # Extension client logic & API caller
│   ├── generate_icons.py            # PNG icon generator
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
│
├── demo/
│   ├── index.html                   # Test job portal index
│   ├── genuine_software_engineer.html
│   ├── genuine_data_analyst.html
│   ├── suspicious_wfh_data_entry.html
│   ├── scam_registration_fee.html
│   └── unrealistic_salary_no_exp.html
│
├── tests/
│   ├── test_backend.py              # Automated backend and edge case tests
│   └── test_demo_pages.py           # End-to-end demo jobs validation
│
├── requirements.txt                 # Python dependencies
└── README.md                        # Documentation
```

---

## 6. How to Run the Project

### Step 1: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: (Optional) Re-train the Model
The model is already pre-trained and saved in `ml/model.pkl`. To re-train:
```bash
python ml/train.py
```

### Step 3: Run the FastAPI Backend Server
```bash
python -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port 8000
```
- API Docs: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`
- Demo job portal: `http://127.0.0.1:8000/demo/index.html`

### Step 4: Run Automated Tests
```bash
python tests/test_backend.py
python tests/test_demo_pages.py
```

---

## 7. How to Load the Extension in Google Chrome

1. Open **Google Chrome**.
2. Navigate to `chrome://extensions/` in the URL bar.
3. Enable **Developer mode** toggle in the top-right corner.
4. Click **Load unpacked** in the top-left toolbar.
5. Select the `c:\Coding\JobShield\extension` folder.
6. The **JobShield AI** extension icon will appear in your Chrome toolbar.
7. Open any demo job from `http://127.0.0.1:8000/demo/index.html`.
8. Click the JobShield AI extension icon and click **CHECK JOB RISK**!

---

## 8. Unimplemented Features & Future Scope

In accordance with prototype time constraints and strict guidelines, the following advanced enhancements remain for future phases:
- User accounts and history persistence database.
- Dedicated scraper integrations for proprietary LinkedIn / Indeed shadow DOMs.
- WHOIS domain age lookup for recruiter email domains.
- Advanced SHAP explainability visualizations.
- Multi-language NLP support.
=======
# jobshield
micro project
>>>>>>> 76b370f8e79b4800c45fa9e3f06b95ee64ff8626
