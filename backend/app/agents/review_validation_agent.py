"""
Review/Validation Agent

Responsibilities:
- Validate intake draft for contradictions
- Check for unsupported claims
- Verify completeness
- Flag items needing human attention
- Generate validation report

This agent uses LLM for validation logic.
"""

from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from ..providers.base import LLMProvider
from ..providers.factory import get_provider
from ..config import settings
from ..tracing.langsmith import trace_operation

logger = logging.getLogger(__name__)


class ReviewValidationAgent:
    """
    Review/Validation Agent - LLM-based intake validation.
    
    Validates intake draft for quality, completeness, and consistency
    before human review.
    """
    
    # Validation criteria
    VALIDATION_CRITERIA = [
        "completeness",
        "consistency",
        "evidence_support",
        "clarity",
        "actionability"
    ]
    
    # Severity levels
    SEVERITY_CRITICAL = "CRITICAL"
    SEVERITY_HIGH = "HIGH"
    SEVERITY_MEDIUM = "MEDIUM"
    SEVERITY_LOW = "LOW"
    
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        """
        Initialize review validation agent.
        
        Args:
            llm_provider: Optional LLM provider (will be initialized in execute if None)
        """
        self.agent_name = "review_validation_agent"
        self.llm = llm_provider
    
    @trace_operation("review_validation_agent", run_type="chain", tags=["agent", "validation", "llm"])
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute intake draft validation.
        
        Args:
            state: Current workflow state
            
        Returns:
            State patch with validation results
        """
        
        logger.info(f"[{self.agent_name}] Starting intake draft validation")
        
        try:
            # Validate project_id
            project_id = state.get("project_id")
            if not project_id:
                raise ValueError("project_id is required in state")
            
            logger.info(f"[{self.agent_name}] Processing project: {project_id}")
            
            # Initialize LLM provider if not set
            if self.llm is None:
                self.llm = await get_provider(prefer_primary=True)
            
            # Get required data from state
            intake_draft = state.get("intake_draft")
            extracted_facts = state.get("extracted_facts", {})
            confidence_scores = state.get("confidence_scores", {})
            evidence_map = state.get("evidence_map", {})
            
            if not intake_draft:
                raise ValueError("No intake draft available for validation")
            
            logger.info(
                f"[{self.agent_name}] Validating intake draft for project {project_id}"
            )
            
            # Perform validation checks
            validation_results = await self._perform_validation(
                intake_draft,
                extracted_facts,
                confidence_scores,
                evidence_map
            )
            
            # Generate review flags
            review_flags = self._generate_review_flags(validation_results)
            
            # Calculate validation score
            validation_score = self._calculate_validation_score(validation_results)
            
            # Determine if human review is required
            requires_human_review = self._requires_human_review(validation_results)
            
            logger.info(
                f"[{self.agent_name}] Validation complete "
                f"(score: {validation_score:.1%}, flags: {len(review_flags)}, "
                f"requires_review: {requires_human_review})"
            )
            
            # Return state patch (NO state_version increment - LangGraph handles it)
            return {
                "validation_results": validation_results,
                "review_flags": review_flags,
                "phase": "validation",
                "trace_metadata": {
                    **state.get("trace_metadata", {}),
                    "validation": {
                        "validation_score": validation_score,
                        "flags_count": len(review_flags),
                        "requires_human_review": requires_human_review,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                },
                "last_committed_by": self.agent_name,
                "last_committed_at": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error: {str(e)}", exc_info=True)
            raise
    
    async def _perform_validation(
        self,
        intake_draft: Dict[str, Any],
        extracted_facts: Dict[str, Any],
        confidence_scores: Dict[str, float],
        evidence_map: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        Perform comprehensive validation of intake draft.
        
        Args:
            intake_draft: Intake draft to validate
            extracted_facts: Original extracted facts
            confidence_scores: Confidence scores for facts
            evidence_map: Evidence mapping
            
        Returns:
            Validation results
        """
        # Build validation prompt
        prompt = self._build_validation_prompt(
            intake_draft,
            extracted_facts,
            confidence_scores,
            evidence_map
        )
        
        # Call LLM for validation
        validation_result = await self.llm.generate_structured(
            prompt=prompt,
            schema=self._get_validation_schema(),
            system_prompt="You are a technical reviewer validating an application modernization intake document for quality, completeness, and consistency.",
            temperature=0.1,  # Very low for consistency
            metadata={
                "agent": self.agent_name,
                "task": "intake_validation"
            }
        )
        
        # Enrich validation results
        validation_results = {
            **validation_result,
            "validated_at": datetime.utcnow().isoformat(),
            "validated_by": self.agent_name,
            "validation_version": "1.0"
        }
        
        return validation_results
    
    def _build_validation_prompt(
        self,
        intake_draft: Dict[str, Any],
        extracted_facts: Dict[str, Any],
        confidence_scores: Dict[str, float],
        evidence_map: Dict[str, List[str]]
    ) -> str:
        """
        Build prompt for validation.
        
        Args:
            intake_draft: Intake draft to validate
            extracted_facts: Original facts
            confidence_scores: Confidence scores
            evidence_map: Evidence mapping
            
        Returns:
            Formatted prompt string
        """
        # Format intake draft sections
        intake_text = ""
        for section_name in [
            "executive_summary",
            "current_state",
            "dependencies",
            "constraints",
            "assumptions",
            "risks",
            "recommendations"
        ]:
            if section_name in intake_draft:
                intake_text += f"\n## {section_name.replace('_', ' ').title()}\n"
                section_data = intake_draft[section_name]
                if isinstance(section_data, str):
                    intake_text += f"{section_data}\n"
                elif isinstance(section_data, list):
                    for item in section_data[:10]:  # Limit items
                        intake_text += f"- {item}\n"
                elif isinstance(section_data, dict):
                    for key, value in list(section_data.items())[:10]:
                        intake_text += f"- {key}: {value}\n"
        
        # Calculate statistics
        total_facts = sum(
            len(facts) if isinstance(facts, list) else 1
            for facts in extracted_facts.values()
        )
        avg_confidence = sum(confidence_scores.values()) / len(confidence_scores) if confidence_scores else 0.0
        low_confidence_count = sum(1 for score in confidence_scores.values() if score < 0.7)
        
        prompt = f"""
Validate the following intake document for application modernization:

# Intake Document
{intake_text}

# Source Data Statistics
- Total facts extracted: {total_facts}
- Average confidence: {avg_confidence:.2f}
- Low confidence facts: {low_confidence_count}
- Evidence sources: {len(evidence_map)}

# Validation Instructions

Perform the following validation checks:

1. **Completeness Check**
   - Are all required sections present and populated?
   - Are there any obvious gaps in information?
   - Are open questions properly documented?

2. **Consistency Check**
   - Are there any contradictions within the document?
   - Do the recommendations align with identified risks?
   - Are assumptions consistent with stated constraints?

3. **Evidence Support Check**
   - Are claims supported by extracted facts?
   - Are low-confidence areas properly flagged?
   - Are assumptions clearly marked as such?

4. **Clarity Check**
   - Is the language clear and professional?
   - Are technical terms properly explained?
   - Is the document actionable?

5. **Risk Assessment**
   - Are all significant risks identified?
   - Are risk severities appropriate?
   - Are mitigation strategies provided?

For each validation criterion, provide:
- Pass/Fail status
- Severity of any issues (CRITICAL, HIGH, MEDIUM, LOW)
- Specific findings
- Recommendations for improvement

Format the output as structured JSON.
"""
        
        return prompt
    
    def _get_validation_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for validation results.
        
        Returns:
            JSON schema dict
        """
        return {
            "type": "object",
            "properties": {
                "overall_status": {
                    "type": "string",
                    "enum": ["PASS", "PASS_WITH_WARNINGS", "FAIL"],
                    "description": "Overall validation status"
                },
                "completeness": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["PASS", "FAIL"]},
                        "score": {"type": "number", "minimum": 0, "maximum": 1},
                        "findings": {"type": "array", "items": {"type": "string"}},
                        "missing_sections": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "consistency": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["PASS", "FAIL"]},
                        "score": {"type": "number", "minimum": 0, "maximum": 1},
                        "contradictions": {"type": "array", "items": {"type": "string"}},
                        "alignment_issues": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "evidence_support": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["PASS", "FAIL"]},
                        "score": {"type": "number", "minimum": 0, "maximum": 1},
                        "unsupported_claims": {"type": "array", "items": {"type": "string"}},
                        "low_confidence_areas": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "clarity": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["PASS", "FAIL"]},
                        "score": {"type": "number", "minimum": 0, "maximum": 1},
                        "unclear_sections": {"type": "array", "items": {"type": "string"}},
                        "improvement_suggestions": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "risk_assessment": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["PASS", "FAIL"]},
                        "score": {"type": "number", "minimum": 0, "maximum": 1},
                        "critical_risks_identified": {"type": "boolean"},
                        "mitigation_coverage": {"type": "string"}
                    }
                },
                "critical_issues": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "issue": {"type": "string"},
                            "severity": {"type": "string", "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"]},
                            "category": {"type": "string"},
                            "recommendation": {"type": "string"}
                        }
                    }
                },
                "recommendations": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": [
                "overall_status",
                "completeness",
                "consistency",
                "evidence_support",
                "clarity",
                "risk_assessment",
                "critical_issues",
                "recommendations"
            ]
        }
    
    def _generate_review_flags(
        self,
        validation_results: Dict[str, Any]
    ) -> List[str]:
        """
        Generate review flags from validation results.
        
        Args:
            validation_results: Validation results
            
        Returns:
            List of review flags
        """
        flags = []
        
        # Check overall status
        overall_status = validation_results.get("overall_status", "FAIL")
        if overall_status == "FAIL":
            flags.append("VALIDATION_FAILED")
        elif overall_status == "PASS_WITH_WARNINGS":
            flags.append("VALIDATION_WARNINGS")
        
        # Check critical issues
        critical_issues = validation_results.get("critical_issues", [])
        for issue in critical_issues:
            severity = issue.get("severity", "LOW")
            if severity == self.SEVERITY_CRITICAL:
                flags.append(f"CRITICAL: {issue.get('issue', 'Unknown issue')[:50]}")
            elif severity == self.SEVERITY_HIGH:
                flags.append(f"HIGH: {issue.get('issue', 'Unknown issue')[:50]}")
        
        # Check completeness
        completeness = validation_results.get("completeness", {})
        if completeness.get("status") == "FAIL":
            flags.append("INCOMPLETE_INTAKE")
        
        # Check consistency
        consistency = validation_results.get("consistency", {})
        contradictions = consistency.get("contradictions", [])
        if contradictions:
            flags.append(f"CONTRADICTIONS_FOUND: {len(contradictions)}")
        
        # Check evidence support
        evidence_support = validation_results.get("evidence_support", {})
        unsupported_claims = evidence_support.get("unsupported_claims", [])
        if unsupported_claims:
            flags.append(f"UNSUPPORTED_CLAIMS: {len(unsupported_claims)}")
        
        return flags
    
    def _calculate_validation_score(
        self,
        validation_results: Dict[str, Any]
    ) -> float:
        """
        Calculate overall validation score.
        
        Args:
            validation_results: Validation results
            
        Returns:
            Validation score (0.0 to 1.0)
        """
        scores = []
        
        for criterion in self.VALIDATION_CRITERIA:
            criterion_data = validation_results.get(criterion, {})
            score = criterion_data.get("score", 0.0)
            scores.append(score)
        
        # Calculate weighted average
        if scores:
            return sum(scores) / len(scores)
        
        return 0.0
    
    def _requires_human_review(
        self,
        validation_results: Dict[str, Any]
    ) -> bool:
        """
        Determine if human review is required.
        
        Args:
            validation_results: Validation results
            
        Returns:
            True if human review is required
        """
        # Always require human review for FAIL status
        overall_status = validation_results.get("overall_status", "FAIL")
        if overall_status == "FAIL":
            return True
        
        # Check for critical issues
        critical_issues = validation_results.get("critical_issues", [])
        for issue in critical_issues:
            if issue.get("severity") in [self.SEVERITY_CRITICAL, self.SEVERITY_HIGH]:
                return True
        
        # Check validation score
        validation_score = self._calculate_validation_score(validation_results)
        if validation_score < 0.7:
            return True
        
        # Default: require human review for POC
        return True


# Made with Bob