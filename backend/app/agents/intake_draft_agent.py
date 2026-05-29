"""
Intake Draft Agent

Responsibilities:
- Generate structured intake document from extracted facts
- Include summary, current state, dependencies, constraints
- Add assumptions, risks, and open questions
- Format output for human review

This agent uses LLM for document generation.
"""

from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from ..providers.base import LLMProvider
from ..providers.factory import get_provider
from ..config import settings
from ..tracing.langsmith import trace_operation

logger = logging.getLogger(__name__)


class IntakeDraftAgent:
    """
    Intake Draft Agent - LLM-based intake document generation.
    
    Generates a comprehensive intake document from extracted facts
    and gap analysis, ready for human review.
    """
    
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        """
        Initialize intake draft agent.
        
        Args:
            llm_provider: Optional LLM provider (will be initialized in execute if None)
        """
        self.agent_name = "intake_draft_agent"
        self.llm = llm_provider
    
    @trace_operation("intake_draft_agent", run_type="chain", tags=["agent", "intake", "llm"])
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute intake draft generation.
        
        Args:
            state: Current workflow state
            
        Returns:
            State patch with intake draft
        """
        
        logger.info(f"[{self.agent_name}] Starting intake draft generation")
        
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
            extracted_facts = state.get("extracted_facts", {})
            confidence_scores = state.get("confidence_scores", {})
            gap_analysis = state.get("gap_analysis", {})
            missing_questions = state.get("missing_questions", [])
            evidence_map = state.get("evidence_map", {})
            
            if not extracted_facts:
                raise ValueError("No extracted facts available for intake draft")
            
            logger.info(
                f"[{self.agent_name}] Generating intake draft with {len(extracted_facts)} fact categories "
                f"and {len(missing_questions)} open questions"
            )
            
            # Build intake draft prompt
            prompt = self._build_intake_prompt(
                extracted_facts,
                confidence_scores,
                gap_analysis,
                missing_questions,
                evidence_map
            )
            
            # Generate intake draft using LLM
            intake_result = await self.llm.generate_structured(
                prompt=prompt,
                schema=self._get_intake_schema(),
                system_prompt="You are a technical documentation specialist creating a comprehensive intake document for application modernization.",
                temperature=0.2,  # Low for consistency
                metadata={
                    "agent": self.agent_name,
                    "task": "intake_draft_generation",
                    "fact_categories": len(extracted_facts),
                    "open_questions": len(missing_questions)
                }
            )
            
            # Process and structure intake draft
            intake_draft = self._process_intake_draft(intake_result, state)
            
            # Calculate completeness score
            completeness_score = self._calculate_completeness(
                extracted_facts,
                confidence_scores,
                missing_questions
            )
            
            logger.info(
                f"[{self.agent_name}] Generated intake draft "
                f"(completeness: {completeness_score:.1%})"
            )
            
            # Return state patch (NO state_version increment - LangGraph handles it)
            return {
                "intake_draft": intake_draft,
                "phase": "intake_draft",
                "trace_metadata": {
                    **state.get("trace_metadata", {}),
                    "intake_draft": {
                        "completeness_score": completeness_score,
                        "sections_generated": len(intake_draft.get("sections", [])),
                        "open_questions_count": len(missing_questions),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                },
                "last_committed_by": self.agent_name,
                "last_committed_at": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error: {str(e)}", exc_info=True)
            raise
    
    def _build_intake_prompt(
        self,
        extracted_facts: Dict[str, Any],
        confidence_scores: Dict[str, float],
        gap_analysis: Dict[str, Any],
        missing_questions: List[Dict[str, Any]],
        evidence_map: Dict[str, List[str]]
    ) -> str:
        """
        Build prompt for intake draft generation.
        
        Args:
            extracted_facts: Extracted facts by category
            confidence_scores: Confidence scores for facts
            gap_analysis: Gap analysis summary
            missing_questions: List of open questions
            evidence_map: Mapping of facts to evidence sources
            
        Returns:
            Formatted prompt string
        """
        # Format facts by category
        facts_text = ""
        for category, facts in extracted_facts.items():
            facts_text += f"\n## {category.replace('_', ' ').title()}\n"
            if isinstance(facts, list):
                for fact in facts:
                    if isinstance(fact, dict):
                        fact_id = fact.get("id", "unknown")
                        confidence = confidence_scores.get(fact_id, 0.0)
                        facts_text += f"- {fact.get('description', str(fact))} (confidence: {confidence:.2f})\n"
                    else:
                        facts_text += f"- {fact}\n"
            elif isinstance(facts, dict):
                for key, value in facts.items():
                    facts_text += f"- {key}: {value}\n"
        
        # Format open questions
        questions_text = ""
        high_priority_questions = [q for q in missing_questions if q.get("priority") == "HIGH"]
        medium_priority_questions = [q for q in missing_questions if q.get("priority") == "MEDIUM"]
        
        if high_priority_questions:
            questions_text += "\n### High Priority Questions\n"
            for q in high_priority_questions[:10]:  # Limit to top 10
                questions_text += f"- {q.get('question', 'N/A')}\n"
        
        if medium_priority_questions:
            questions_text += "\n### Medium Priority Questions\n"
            for q in medium_priority_questions[:5]:  # Limit to top 5
                questions_text += f"- {q.get('question', 'N/A')}\n"
        
        # Format gap analysis
        gap_text = ""
        if gap_analysis:
            gap_text = f"""
### Gap Analysis Summary
- Low confidence facts: {gap_analysis.get('low_confidence_facts', 0)}
- Missing required fields: {gap_analysis.get('missing_fields', 0)}
- Total gaps identified: {gap_analysis.get('total_gaps', 0)}
"""
        
        prompt = f"""
Generate a comprehensive intake document for application modernization based on the following information:

# Extracted Facts
{facts_text}

# Information Gaps
{gap_text}

# Open Questions
{questions_text}

# Instructions
Create a structured intake document with the following sections:

1. **Executive Summary**: Brief overview of the application and modernization scope
2. **Current State**: Detailed description of current technical stack, architecture, and deployment
3. **Dependencies**: External systems, databases, APIs, and third-party services
4. **Constraints**: Technical, business, or regulatory constraints
5. **Assumptions**: Key assumptions made based on available information
6. **Risks**: Identified risks and concerns
7. **Open Questions**: Prioritized list of questions that need answers
8. **Recommendations**: Initial recommendations for next steps

For each section:
- Use clear, professional language
- Cite confidence levels where relevant
- Flag areas with low confidence or missing information
- Be specific and actionable

Format the output as a structured JSON document.
"""
        
        return prompt
    
    def _get_intake_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for intake draft structure.
        
        Returns:
            JSON schema dict
        """
        return {
            "type": "object",
            "properties": {
                "executive_summary": {
                    "type": "string",
                    "description": "Brief overview of application and modernization scope"
                },
                "current_state": {
                    "type": "object",
                    "properties": {
                        "technical_stack": {"type": "string"},
                        "architecture": {"type": "string"},
                        "deployment": {"type": "string"},
                        "scale": {"type": "string"}
                    }
                },
                "dependencies": {
                    "type": "object",
                    "properties": {
                        "databases": {"type": "array", "items": {"type": "string"}},
                        "external_apis": {"type": "array", "items": {"type": "string"}},
                        "third_party_services": {"type": "array", "items": {"type": "string"}},
                        "internal_systems": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "constraints": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "description": {"type": "string"},
                            "impact": {"type": "string"}
                        }
                    }
                },
                "assumptions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "assumption": {"type": "string"},
                            "confidence": {"type": "string"},
                            "needs_validation": {"type": "boolean"}
                        }
                    }
                },
                "risks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "risk": {"type": "string"},
                            "severity": {"type": "string"},
                            "mitigation": {"type": "string"}
                        }
                    }
                },
                "open_questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string"},
                            "priority": {"type": "string"},
                            "category": {"type": "string"}
                        }
                    }
                },
                "recommendations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "recommendation": {"type": "string"},
                            "rationale": {"type": "string"},
                            "priority": {"type": "string"}
                        }
                    }
                }
            },
            "required": [
                "executive_summary",
                "current_state",
                "dependencies",
                "constraints",
                "assumptions",
                "risks",
                "open_questions",
                "recommendations"
            ]
        }
    
    def _process_intake_draft(
        self,
        intake_result: Dict[str, Any],
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process and enrich intake draft with metadata.
        
        Args:
            intake_result: Raw intake draft from LLM
            state: Current workflow state
            
        Returns:
            Processed intake draft
        """
        # Add metadata
        intake_draft = {
            **intake_result,
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "generated_by": self.agent_name,
                "project_id": state.get("project_id"),
                "version": "1.0",
                "status": "draft"
            }
        }
        
        # Add section summaries
        sections = []
        for section_name in [
            "executive_summary",
            "current_state",
            "dependencies",
            "constraints",
            "assumptions",
            "risks",
            "open_questions",
            "recommendations"
        ]:
            if section_name in intake_result:
                sections.append({
                    "name": section_name,
                    "completed": True,
                    "item_count": len(intake_result[section_name]) if isinstance(intake_result[section_name], (list, dict)) else 1
                })
        
        intake_draft["sections"] = sections
        
        return intake_draft
    
    def _calculate_completeness(
        self,
        extracted_facts: Dict[str, Any],
        confidence_scores: Dict[str, float],
        missing_questions: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate intake draft completeness score.
        
        Args:
            extracted_facts: Extracted facts
            confidence_scores: Confidence scores
            missing_questions: Open questions
            
        Returns:
            Completeness score (0.0 to 1.0)
        """
        # Count total facts
        total_facts = sum(
            len(facts) if isinstance(facts, list) else 1
            for facts in extracted_facts.values()
        )
        
        # Calculate average confidence
        avg_confidence = sum(confidence_scores.values()) / len(confidence_scores) if confidence_scores else 0.0
        
        # Calculate question penalty
        question_penalty = min(len(missing_questions) * 0.02, 0.3)  # Max 30% penalty
        
        # Calculate completeness
        completeness = (avg_confidence * 0.7) + ((1.0 - question_penalty) * 0.3)
        
        return max(0.0, min(1.0, completeness))


# Made with Bob