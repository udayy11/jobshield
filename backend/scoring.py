from typing import Dict, Any, List


class HybridScoringEngine:
    """
    Hybrid Risk Scoring Engine.
    Combines ML prediction and Rule engine analysis with safety overrides.
    """

    def __init__(
        self,
        ml_weight: float = 0.65,
        rule_weight: float = 0.35,
        low_threshold: int = 34,
        high_threshold: int = 65,
    ):
        self.ml_weight = ml_weight
        self.rule_weight = rule_weight
        self.low_threshold = low_threshold
        self.high_threshold = high_threshold

        # Rule severity weight mappings (points out of 100)
        self.severity_weights = {
            "Critical": 45,
            "High": 30,
            "Medium": 20,
            "Low": 10,
        }

    def compute_rule_score(self, warnings: List[Dict[str, Any]]) -> float:
        """
        Calculates a 0-100 score based on triggered rules and their severities.
        Uses non-linear saturation so multiple warnings escalate appropriately.
        """
        if not warnings:
            return 0.0

        raw_points = 0
        has_critical = False
        has_high = False

        for w in warnings:
            sev = w.get("severity", "Low")
            pts = self.severity_weights.get(sev, 10)
            raw_points += pts
            if sev == "Critical":
                has_critical = True
            elif sev == "High":
                has_high = True

        # Base normalization capped at 100
        score = min(100.0, float(raw_points))

        # Enforce minimum rule floor for severe threats
        if has_critical:
            score = max(80.0, score)
        elif has_high:
            score = max(55.0, score)

        return round(score, 1)

    def calculate(
        self,
        ml_score: float,
        warnings: List[Dict[str, Any]],
        positive_signals: List[Dict[str, Any]],
        ml_available: bool = True,
        is_insufficient_info: bool = False
    ) -> Dict[str, Any]:
        """
        Combines ML and Rule scores into a final explainable risk assessment.
        """
        rule_score = self.compute_rule_score(warnings)

        if is_insufficient_info:
            return {
                "risk_level": "INSUFFICIENT_INFO",
                "risk_score": 50,
                "ml_score": int(round(ml_score)) if ml_available else None,
                "rule_score": int(round(rule_score)),
                "weights": {"ml": self.ml_weight if ml_available else 0.0, "rule": self.rule_weight if ml_available else 1.0},
                "warnings": [w["name"] + f" ({w['severity']}): " + w["explanation"] for w in warnings],
                "detailed_warnings": warnings,
                "positive_signals": [p["name"] + ": " + p["explanation"] for p in positive_signals],
                "detailed_positive_signals": positive_signals,
                "explanation": "Insufficient job details provided. An accurate fraud risk assessment cannot be reliably established.",
                "recommendations": [
                    "Request complete, formal job description with official corporate credentials before proceeding.",
                    "Do not share personal documents or financial details on incomplete job postings."
                ],
                "disclaimer": "This assessment is decision-support only and is not proof of fraud or legitimacy. Never consider any employer 'verified' solely on text signals."
            }

        # Calculate hybrid weighted score
        if ml_available:
            weighted_score = (self.ml_weight * ml_score) + (self.rule_weight * rule_score)
        else:
            # Fallback to pure rule score if ML unavailable
            weighted_score = rule_score

        # Check for Critical rule overrides (R1: Upfront fees, R2: OTP/Bank credentials)
        # Critical indicators prevent system from ever showing Low Risk
        critical_warnings = [w for w in warnings if w.get("severity") == "Critical"]
        high_warnings = [w for w in warnings if w.get("severity") == "High"]

        if critical_warnings:
            # Floor at High Risk (>= 75)
            final_score = max(75.0, weighted_score)
        elif high_warnings and weighted_score < 50.0:
            # Floor at Medium Risk (>= 50)
            final_score = max(50.0, weighted_score)
        else:
            final_score = weighted_score

        final_score = round(min(100.0, max(0.0, final_score)), 1)

        # Determine Risk Level
        if final_score <= self.low_threshold:
            risk_level = "LOW"
        elif final_score <= self.high_threshold:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"

        # Generate synthesis explanation
        explanation = self._build_explanation(risk_level, final_score, ml_score, rule_score, warnings, positive_signals, ml_available)

        # Generate actionable safety recommendations
        recommendations = self._build_recommendations(risk_level, warnings)

        return {
            "risk_level": risk_level,
            "risk_score": int(round(final_score)),
            "ml_score": int(round(ml_score)) if ml_available else None,
            "rule_score": int(round(rule_score)),
            "weights": {
                "ml": self.ml_weight if ml_available else 0.0,
                "rule": self.rule_weight if ml_available else 1.0
            },
            "warnings": [w["name"] + f" ({w['severity']}): " + w["explanation"] for w in warnings],
            "detailed_warnings": warnings,
            "positive_signals": [p["name"] + ": " + p["explanation"] for p in positive_signals],
            "detailed_positive_signals": positive_signals,
            "explanation": explanation,
            "recommendations": recommendations,
            "disclaimer": "This assessment is decision-support only and is not proof of fraud or legitimacy. Never consider any employer 'verified' solely on text signals."
        }

    def _build_explanation(
        self,
        risk_level: str,
        final_score: float,
        ml_score: float,
        rule_score: float,
        warnings: List[Dict[str, Any]],
        positive_signals: List[Dict[str, Any]],
        ml_available: bool
    ) -> str:
        parts = []
        if not ml_available:
            parts.append("Note: ML inference was unavailable; assessment is derived exclusively from heuristic risk rules.")

        if risk_level == "HIGH":
            critical_names = [w["name"] for w in warnings if w["severity"] in ["Critical", "High"]]
            if critical_names:
                parts.append(f"High risk indicators detected: {', '.join(critical_names[:3])}.")
            else:
                parts.append("Significant linguistic patterns consistent with deceptive recruitment were identified.")
        elif risk_level == "MEDIUM":
            parts.append("Elevated risk signals detected. The posting displays questionable elements requiring verification.")
        else:
            if positive_signals:
                parts.append(f"Low risk indicators observed. Displays {len(positive_signals)} standard recruitment consistency signals.")
            else:
                parts.append("No immediate fraud patterns detected. General diligence is still advised.")

        return " ".join(parts)

    def _build_recommendations(
        self,
        risk_level: str,
        warnings: List[Dict[str, Any]]
    ) -> List[str]:
        recs = []
        warning_ids = {w.get("id") for w in warnings}

        if "R1" in warning_ids:
            recs.append("NEVER pay registration, training, or equipment fees for a job opportunity.")
        if "R2" in warning_ids:
            recs.append("DO NOT disclose banking passwords, OTPs, or government IDs before official, verified employment.")
        if "R4" in warning_ids:
            recs.append("Avoid interviews conducted solely over WhatsApp or Telegram; request formal communication channels.")
        if "R3" in warning_ids:
            recs.append("Verify recruiter identity through official corporate channels, not free webmail domains.")
        if "R10" in warning_ids:
            recs.append("Do not click shortened or non-HTTPS URLs without verifying the destination domain.")

        if risk_level == "HIGH":
            recs.append("Exercise extreme caution before sharing any contact details, resume, or credentials.")
            recs.append("Independently verify company registration on official business registries.")
        elif risk_level == "MEDIUM":
            recs.append("Cross-check this job opening on the company's official corporate careers page.")
            recs.append("Ensure communication originates from the organization's verified domain.")
        else:
            recs.append("Standard caution: Confirm job listings on the official corporate careers portal.")
            recs.append("Never share sensitive banking or personal information during early stage screening.")

        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for r in recs:
            if r not in seen:
                seen.add(r)
                deduped.append(r)
        return deduped[:4]
