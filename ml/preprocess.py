import re
import html
import pandas as pd


def clean_text(text: str) -> str:
    """Cleans and normalizes raw text for NLP model."""
    if not isinstance(text, str):
        return ""
    # Unescape HTML entities (&amp; -> &, &nbsp; -> space, etc.)
    text = html.unescape(text)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Normalize anonymized tokens like #URL_...# or #EMAIL_...# to general tokens
    text = re.sub(r"#URL_[a-f0-9]+#", " url_token ", text)
    text = re.sub(r"#EMAIL_[a-f0-9]+#", " email_token ", text)
    text = re.sub(r"#PHONE_[a-f0-9]+#", " phone_token ", text)
    # Lowercase
    text = text.lower()
    # Replace non-alphanumeric (except standard punctuation) with spaces
    text = re.sub(r"[^a-z0-9\s.,!?:;$/%-]", " ", text)
    # Collapse multiple whitespaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


def combine_fields(
    title: str = "",
    company: str = "",
    description: str = "",
    requirements: str = "",
    benefits: str = "",
) -> str:
    """Combines job posting fields into a single unified text string."""
    parts = []
    if title:
        parts.append(f"Title: {title}")
    if company:
        parts.append(f"Company: {company}")
    if description:
        parts.append(f"Description: {description}")
    if requirements:
        parts.append(f"Requirements: {requirements}")
    if benefits:
        parts.append(f"Benefits: {benefits}")
    
    combined = " | ".join(parts)
    return clean_text(combined)


def prepare_dataframe(df: pd.DataFrame) -> pd.Series:
    """Prepares and combines text columns from a DataFrame."""
    title = df["title"].fillna("").astype(str)
    company = df["company_profile"].fillna("").astype(str) if "company_profile" in df.columns else pd.Series([""] * len(df))
    desc = df["description"].fillna("").astype(str) if "description" in df.columns else pd.Series([""] * len(df))
    reqs = df["requirements"].fillna("").astype(str) if "requirements" in df.columns else pd.Series([""] * len(df))
    benefits = df["benefits"].fillna("").astype(str) if "benefits" in df.columns else pd.Series([""] * len(df))

    combined = (
        "Title: " + title +
        " | Company: " + company +
        " | Description: " + desc +
        " | Requirements: " + reqs +
        " | Benefits: " + benefits
    )
    return combined.apply(clean_text)
