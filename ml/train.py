import os
import time
import json
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
    accuracy_score,
    roc_auc_score
)

from preprocess import prepare_dataframe, combine_fields, clean_text


def train_job_fraud_model(
    data_path: str = "ml/data/fake_job_postings.csv",
    model_save_path: str = "ml/model.pkl",
    metrics_save_path: str = "ml/metrics.json"
):
    print("=" * 60)
    print("JobShield AI — ML Training Pipeline")
    print("=" * 60)
    
    start_time = time.time()
    
    # 1. Load dataset
    print(f"\n[1/6] Loading dataset from {data_path}...")
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Dataset not found at {data_path}")
    
    df = pd.read_csv(data_path)
    print(f"Loaded {len(df):,} job postings. Columns: {len(df.columns)}")
    
    # 2. Check target and distribution
    target_col = "fraudulent"
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in dataset")
        
    counts = df[target_col].value_counts().to_dict()
    fraud_pct = (counts.get(1, 0) / len(df)) * 100
    print(f"Target distribution -> Legitimate (0): {counts.get(0, 0):,}, Fraudulent (1): {counts.get(1, 0):,} ({fraud_pct:.2f}%)")
    
    # 3. Preprocess and combine text fields
    print("\n[2/6] Preprocessing and combining text fields (title, company_profile, description, requirements, benefits)...")
    X_text = prepare_dataframe(df)
    y = df[target_col].values
    
    # 4. Stratified Train-Test Split (80% train, 20% test)
    print("\n[3/6] Performing Stratified Train-Test Split (80% train / 20% test, random_state=42)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X_text, y, test_size=0.20, random_state=42, stratify=y
    )
    print(f"Training set: {len(X_train):,} samples (Fraudulent: {sum(y_train):,})")
    print(f"Testing set:  {len(X_test):,} samples (Fraudulent: {sum(y_test):,})")
    
    # 5. Build ML Pipeline: TF-IDF + Logistic Regression with balanced class weighting
    print("\n[4/6] Training TF-IDF + Logistic Regression with balanced class weights...")
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=12000,
            sublinear_tf=True,
            stop_words="english",
            min_df=2
        )),
        ("classifier", LogisticRegression(
            class_weight="balanced",
            C=1.5,
            max_iter=1000,
            random_state=42
        ))
    ])
    
    pipeline.fit(X_train, y_train)
    train_time = time.time() - start_time
    print(f"Model training completed in {train_time:.2f} seconds.")
    
    # 6. Evaluation on held-out test set
    print("\n[5/6] Evaluating model on HELD-OUT test set (unseen data)...")
    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]
    
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, pos_label=1)
    rec = recall_score(y_test, y_pred, pos_label=1)
    f1 = f1_score(y_test, y_pred, pos_label=1)
    roc_auc = roc_auc_score(y_test, y_proba)
    cm = confusion_matrix(y_test, y_pred)
    report = classification_report(y_test, y_pred, target_names=["Legitimate (0)", "Fraudulent (1)"], digits=4)
    
    print("-" * 50)
    print(f"Accuracy:        {acc * 100:.2f}%")
    print(f"Precision (Fake):{prec * 100:.2f}%")
    print(f"Recall (Fake):   {rec * 100:.2f}%")
    print(f"F1-Score (Fake): {f1 * 100:.2f}%")
    print(f"ROC-AUC:         {roc_auc:.4f}")
    print("\nConfusion Matrix [TN, FP; FN, TP]:")
    print(cm)
    print(f"  True Negatives (Legit classified as Legit):   {cm[0, 0]}")
    print(f"  False Positives (Legit classified as Fraud):  {cm[0, 1]}")
    print(f"  False Negatives (Fraud classified as Legit):  {cm[1, 0]}")
    print(f"  True Positives (Fraud classified as Fraud):   {cm[1, 1]}")
    print("\nFull Classification Report:")
    print(report)
    print("-" * 50)
    
    # Save artifacts
    print(f"\n[6/6] Saving model and metrics...")
    model_artifact = {
        "pipeline": pipeline,
        "model_version": "1.0.0",
        "algorithm": "TF-IDF (1-2 ngrams, 12000 features) + Logistic Regression (class_weight=balanced, C=1.5)",
        "features": ["title", "company_profile", "description", "requirements", "benefits"],
        "metrics": {
            "accuracy": float(acc),
            "precision": float(prec),
            "recall": float(rec),
            "f1_score": float(f1),
            "roc_auc": float(roc_auc),
            "confusion_matrix": cm.tolist(),
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "train_fraud_samples": int(sum(y_train)),
            "test_fraud_samples": int(sum(y_test))
        }
    }
    
    joblib.dump(model_artifact, model_save_path)
    print(f"Model pipeline saved to: {model_save_path}")
    
    with open(metrics_save_path, "w") as f:
        json.dump(model_artifact["metrics"], f, indent=2)
    print(f"Metrics saved to: {metrics_save_path}")
    
    # Generalization sanity test
    run_generalization_checks(pipeline)
    
    return model_artifact


def run_generalization_checks(pipeline):
    print("\n" + "=" * 60)
    print("Running Generalization & Sanity Checks on Unseen Examples")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "Genuine Senior Python Engineer",
            "title": "Senior Python Backend Engineer",
            "company": "DataStream Solutions Inc. - Enterprise analytics SaaS company founded in 2015 with 200+ employees globally.",
            "description": "We are seeking an experienced Backend Engineer to architect and build scalable REST and GraphQL APIs. You will collaborate with product designers, frontend engineers, and DevOps. Must have solid fundamentals in distributed systems, PostgreSQL, and AWS.",
            "requirements": "5+ years of experience with Python/FastAPI/Django. Strong experience with Docker, Kubernetes, and CI/CD pipelines. Bachelor's degree in Computer Science or equivalent practical experience.",
            "benefits": "Competitive salary $130,000-$160,000, 401(k) matching, comprehensive health insurance, 20 days PTO, annual learning stipend."
        },
        {
            "name": "Genuine Junior Data Analyst",
            "title": "Junior Data Analyst",
            "company": "Apex Market Intelligence - Retail consulting firm providing pricing analytics to Fortune 500 brands.",
            "description": "Looking for an analytical thinker to assist our insights team. You will clean datasets, create interactive Tableau dashboards, and present weekly metrics to team leads.",
            "requirements": "Proficiency in SQL and Excel. Basic knowledge of Python or R for data analysis. Strong verbal communication skills. Bachelor's in Mathematics, Statistics, Economics, or related.",
            "benefits": "Health & Dental coverage, hybrid schedule (2 days in office), mentoring program, career progression path."
        },
        {
            "name": "Suspicious WFH Data Entry (Guaranteed Income)",
            "title": "Work From Home Data Entry Clerk - Immediate Start!",
            "company": "Global Rapid Careers",
            "description": "Make $5,000 to $8,000 monthly working only 2 hours a day from home! No experience or qualifications needed. Instant hiring guaranteed for anyone with a computer or phone.",
            "requirements": "No previous skills or background required. Basic typing ability. Must start immediately today.",
            "benefits": "Daily cash payouts via wire transfer or gift cards."
        },
        {
            "name": "Registration Fee Scam Job",
            "title": "Online Typing and Proofreading Specialist",
            "company": "",
            "description": "Earn $50/hour copy-pasting documents and proofreading articles. All candidates are guaranteed acceptance upon paying a mandatory $150 refundable security deposit for onboarding software license.",
            "requirements": "Any laptop or smartphone. Willingness to deposit registration fee via Western Union or crypto.",
            "benefits": "Unlimited earning potential."
        },
        {
            "name": "Incomplete / Missing Info Job Posting",
            "title": "Assistant",
            "company": "",
            "description": "Need an assistant urgently. Good pay.",
            "requirements": "",
            "benefits": ""
        }
    ]
    
    for case in test_cases:
        text = combine_fields(
            title=case["title"],
            company=case["company"],
            description=case["description"],
            requirements=case["requirements"],
            benefits=case["benefits"]
        )
        proba = pipeline.predict_proba([text])[0, 1]
        pred = pipeline.predict([text])[0]
        label = "FRAUDULENT" if pred == 1 else "LEGITIMATE"
        print(f"\n[Case] {case['name']}")
        print(f"  -> Predicted Label: {label}")
        print(f"  -> ML Fraud Probability: {proba * 100:.2f}%")


if __name__ == "__main__":
    train_job_fraud_model()
