from backend.institutional_intelligence.setup_validator_models import SetupApprovalDecision, SetupValidationResult


class SetupApprovalEngine:
    def generate_decision(self, validation_result: SetupValidationResult) -> SetupApprovalDecision:
        critical_failure = any(not rule.passed and rule.severity == "CRITICAL" for rule in validation_result.rules)
        score = validation_result.overall_score
        confidence = validation_result.confidence
        if critical_failure or validation_result.readiness == "REJECTED":
            grade = "REJECTED"
            approved = False
            readiness = "REJECTED"
        elif score >= 85.0 and confidence >= 80.0 and validation_result.readiness == "APPROVED":
            grade = "INSTITUTIONAL_A_PLUS"
            approved = True
            readiness = "APPROVED"
        elif score >= 75.0 and validation_result.readiness == "APPROVED":
            grade = "INSTITUTIONAL_A"
            approved = True
            readiness = "APPROVED"
        elif score >= 65.0:
            grade = "INSTITUTIONAL_B"
            approved = False
            readiness = "CONDITIONAL"
        elif score >= 45.0:
            grade = "LOW_QUALITY"
            approved = False
            readiness = "WAIT"
        else:
            grade = "REJECTED"
            approved = False
            readiness = "REJECTED"
        return SetupApprovalDecision(
            approved=approved,
            approval_grade=grade,
            execution_readiness=readiness,
            simulation_eligible=approved,
            requires_confirmation=not approved,
            institutional_quality=grade.replace("_", " "),
            explanation=self._explanation(grade, validation_result),
        )

    def _explanation(self, grade: str, result: SetupValidationResult) -> str:
        if grade == "REJECTED":
            reasons = result.rejection_reasons or ["Required institutional gates did not pass."]
            return f"Simulation rejected: {'; '.join(reasons)}"
        if grade == "INSTITUTIONAL_A_PLUS":
            return "Institutional A Plus setup approved for simulation eligibility only."
        if grade == "INSTITUTIONAL_A":
            return "Institutional A setup approved for simulation eligibility only."
        if grade == "INSTITUTIONAL_B":
            return "Institutional B setup requires further confirmation before simulation."
        return "Low-quality setup remains under observation and is not simulation eligible."
