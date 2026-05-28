"""
Questionnaire Agent

Responsibilities:
- Identify low-confidence facts
- Detect missing required fields
- Generate prioritized questions
- Map questions to evidence gaps

This agent uses LLM for question generation.
"""

from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from ..providers.base import LLMProvider
from ..providers.factory import get_provider
from ..config import settings
from ..tracing.langsmith import trace_operation

logger = logging.getLogger(__name__)


class QuestionnaireAgent:
    """
    Questionnaire Agent - LLM-based gap analysis.
    
    Identifies information gaps and generates prioritized questions
    to fill those gaps.
    """
    
    # Required fields for migration planning
    REQUIRED_FIELDS = [
        "technical_stack.language",
        "technical_stack.framework",
        "dependencies.databases",
        "deployment_strategy.current_method",
        "security_compliance.authentication",
        "architectural_decisions.architecture_style"
    ]
    
    # Confidence threshold for flagging
    LOW_CONFIDENCE_THRESHOLD = 0.7
    
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        """
        Initialize questionnaire agent.
        
        Args:
            llm_provider: Optional LLM provider (will be initialized in execute if None)
        """
        self.agent_name = "questionnaire_agent"
        self.llm = llm_provider
    
    @trace_operation("questionnaire_agent", run_type="chain", tags=["agent", "questionnaire", "llm"])
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute gap analysis and question generation.
        
        Args:
            state: Current workflow state
            
        Returns:
            State patch with generated questions
        """
        
        logger.info(f"[{self.agent_name}] Starting gap analysis")
        
        try:
            # Validate project_id
            project_id = state.get("project_id")
            if not project_id:
                raise ValueError("project_id is required in state")
            
            logger.info(f"[{self.agent_name}] Processing project: {project_id}")
            
            # Initialize LLM provider if not set
            if self.llm is None:
                self.llm = await get_provider(prefer_primary=True)
            
            # Get extracted facts and confidence scores
            extracted_facts = state.get("extracted_facts", {})
            confidence_scores = state.get("confidence_scores", {})
            
            if not extracted_facts:
                raise ValueError("No extracted facts available for gap analysis")
            
            logger.info(
                f"[{self.agent_name}] Analyzing {len(confidence_scores)} facts for project {project_id}"
            )
            
            # Identify gaps
            low_confidence_facts = self._identify_low_confidence_facts(
                extracted_facts,
                confidence_scores
            )
            missing_fields = self._identify_missing_fields(extracted_facts)
            
            logger.info(
                f"[{self.agent_name}] Found {len(low_confidence_facts)} low-confidence facts "
                f"and {len(missing_fields)} missing fields"
            )
            
            # Build questionnaire prompt
            prompt = self._build_questionnaire_prompt(
                extracted_facts,
                low_confidence_facts,
                missing_fields
            )
            
            # Generate questions using LLM
            questions_result = await self.llm.generate_structured(
                prompt=prompt,
                schema=self._get_question_schema(),
                system_prompt="You are a migration analyst identifying information gaps and generating clarifying questions.",
                temperature=0.3,  # Slightly higher for variety
                metadata={
                    "agent": self.agent_name,
                    "task": "question_generation",
                    "gaps_identified": len(low_confidence_facts) + len(missing_fields)
                }
            )
            
            # Process and prioritize questions
            questions = self._process_questions(questions_result)
            prioritized_questions = self._prioritize_questions(questions)
            
            # Calculate statistics
            high_priority_count = sum(1 for q in prioritized_questions if q.get("priority") == "HIGH")
            
            logger.info(
                f"[{self.agent_name}] Generated {len(prioritized_questions)} questions "
                f"({high_priority_count} high priority)"
            )
            
            # Return state patch
            return {
                "missing_questions": prioritized_questions,
                "question_priorities": {q["question_id"]: q["priority_score"] for q in prioritized_questions},
                "gap_analysis": {
                    "low_confidence_facts": len(low_confidence_facts),
                    "missing_fields": len(missing_fields),
                    "total_gaps": len(low_confidence_facts) + len(missing_fields)
                },
                "phase": "questionnaire",
                "trace_metadata": {
                    **state.get("trace_metadata", {}),
                    "questionnaire": {
                        "questions_generated": len(prioritized_questions),
                        "high_priority_count": high_priority_count,
                        "low_confidence_facts": len(low_confidence_facts),
                        "missing_fields": len(missing_fields),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                },
                "last_committed_by": self.agent_name,
                "last_committed_at": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error: {str(e)}", exc_info=True)
            return {
                "phase": "error",
                "last_error": f"Question generation failed: {str(e)}",
                "error_log": [
                    *state.get("error_log", []),
                    {
                        "agent": self.agent_name,
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ],
                "last_committed_by": self.agent_name,
                "last_committed_at": datetime.utcnow().isoformat()
            }
    
    def _identify_low_confidence_facts(
        self,
        extracted_facts: Dict[str, List[Dict[str, Any]]],
        confidence_scores: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Identify facts with confidence below threshold"""
        
        low_confidence = []
        
        for category, facts in extracted_facts.items():
            for fact in facts:
                fact_id = fact.get("fact_id", "")
                confidence = confidence_scores.get(fact_id, 0.0)
                
                if confidence < self.LOW_CONFIDENCE_THRESHOLD:
                    low_confidence.append({
                        **fact,
                        "confidence": confidence,
                        "gap_type": "low_confidence"
                    })
        
        return low_confidence
    
    def _identify_missing_fields(
        self,
        extracted_facts: Dict[str, List[Dict[str, Any]]]
    ) -> List[str]:
        """Identify required fields that are missing"""
        
        missing = []
        
        for required_field in self.REQUIRED_FIELDS:
            category, field = required_field.split(".", 1)
            
            # Check if category exists
            if category not in extracted_facts:
                missing.append(required_field)
                continue
            
            # Check if field exists in category
            facts = extracted_facts[category]
            field_found = any(
                field.lower() in fact.get("category", "").lower() or
                field.lower() in fact.get("fact", "").lower()
                for fact in facts
            )
            
            if not field_found:
                missing.append(required_field)
        
        return missing
    
    def _build_questionnaire_prompt(
        self,
        extracted_facts: Dict[str, List[Dict[str, Any]]],
        low_confidence_facts: List[Dict[str, Any]],
        missing_fields: List[str]
    ) -> str:
        """Build prompt for question generation"""
        
        # Format extracted facts summary
        facts_summary = "\n".join([
            f"- {category}: {len(facts)} facts"
            for category, facts in extracted_facts.items()
        ])
        
        # Format low confidence facts
        low_conf_summary = "\n".join([
            f"- {fact['fact']} (confidence: {fact['confidence']:.2f})"
            for fact in low_confidence_facts[:10]  # Limit to 10
        ])
        
        # Format missing fields
        missing_summary = "\n".join([f"- {field}" for field in missing_fields])
        
        prompt = f"""You are a migration analyst identifying information gaps and generating clarifying questions.

EXTRACTED FACTS SUMMARY:
{facts_summary}

LOW CONFIDENCE FACTS (<{self.LOW_CONFIDENCE_THRESHOLD}):
{low_conf_summary if low_conf_summary else "None"}

MISSING REQUIRED FIELDS:
{missing_summary if missing_summary else "None"}

GENERATE CLARIFYING QUESTIONS:

For each gap (low confidence fact or missing field):
1. Formulate a specific, actionable question
2. Explain why this information is needed for migration planning
3. Suggest where to find the answer (documentation, code, team member, etc.)
4. Assign priority based on impact:
   - HIGH: Blocks migration planning (e.g., authentication method, database type)
   - MEDIUM: Affects migration strategy (e.g., data volume, traffic patterns)
   - LOW: Nice-to-have for optimization (e.g., team preferences, naming conventions)

PRIORITIZATION RULES:
- HIGH priority: Information required to make architectural decisions
- MEDIUM priority: Information that affects cost, timeline, or risk
- LOW priority: Information that improves quality but isn't blocking

Generate questions that will help fill these gaps and enable confident migration planning.
"""
        
        return prompt
    
    def _get_question_schema(self) -> Dict[str, Any]:
        """Get JSON schema for question generation"""
        
        return {
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string"},
                            "reason": {"type": "string"},
                            "suggested_source": {"type": "string"},
                            "priority": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]},
                            "related_fact_id": {"type": "string"},
                            "gap_type": {"type": "string"}
                        },
                        "required": ["question", "reason", "priority"]
                    }
                }
            },
            "required": ["questions"]
        }
    
    def _process_questions(self, questions_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process and add IDs to questions"""
        
        questions = questions_result.get("questions", [])
        
        for i, question in enumerate(questions):
            question["question_id"] = f"q_{i:03d}"
        
        return questions
    
    def _prioritize_questions(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prioritize questions using scoring system.
        
        Scoring:
        - Blocks migration: +10 points
        - Affects cost: +7 points
        - Affects timeline: +5 points
        - Affects architecture: +5 points
        - Nice-to-have: +1 point
        """
        
        for question in questions:
            score = 0
            question_text = question.get("question", "").lower()
            reason = question.get("reason", "").lower()
            
            # Base score from priority
            priority_scores = {"HIGH": 10, "MEDIUM": 5, "LOW": 1}
            score += priority_scores.get(question.get("priority", "LOW"), 1)
            
            # Additional scoring based on keywords
            if any(kw in question_text or kw in reason for kw in ["authentication", "security", "database"]):
                score += 5  # Critical infrastructure
            
            if any(kw in question_text or kw in reason for kw in ["cost", "pricing", "volume"]):
                score += 3  # Cost impact
            
            if any(kw in question_text or kw in reason for kw in ["deadline", "timeline", "schedule"]):
                score += 3  # Timeline impact
            
            question["priority_score"] = score
        
        # Sort by priority score (descending)
        return sorted(questions, key=lambda q: q["priority_score"], reverse=True)


# Made with Bob