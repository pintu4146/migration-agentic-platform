# Phase 5: Intake & Review Agents with Human-in-the-Loop

## Overview

Phase 5 implements the Intake Draft Agent and Review/Validation Agent, along with the human-in-the-loop review mechanism. These agents synthesize extracted facts into a human-readable intake document and validate it before migration planning.

## Objectives

1. **Implement Intake Draft Agent**
   - Synthesize facts into structured intake document
   - Include executive summary, current state, dependencies, constraints
   - Preserve evidence references
   - Format for human review

2. **Implement Review/Validation Agent**
   - Hybrid validation (rules + LLM)
   - Check for contradictions and unsupported claims
   - Verify completeness
   - Flag issues for human attention

3. **Build Human Review Interface**
   - Display intake draft with evidence links
   - Allow inline comments and edits
   - Track review status
   - Support approval/rejection workflow

4. **Implement Review Checkpoint**
   - Pause workflow for human review
   - Resume after approval
   - Handle rejection and iteration

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  LangGraph Workflow                          │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │          Intake Draft Agent Node                        │ │
│  │  - Synthesize facts into document                       │ │
│  │  - Format with evidence references                      │ │
│  │  - Return state patch                                   │ │
│  └────────────┬───────────────────────────────────────────┘ │
│               │                                              │
│  ┌────────────▼───────────────────────────────────────────┐ │
│  │        Review/Validation Agent Node                     │ │
│  │  - Rule-based validation (fast)                         │ │
│  │  - LLM semantic validation (thorough)                   │ │
│  │  - Flag issues                                          │ │
│  └────────────┬───────────────────────────────────────────┘ │
│               │                                              │
│  ┌────────────▼───────────────────────────────────────────┐ │
│  │         Human Review Gate                               │ │
│  │  - Pause workflow                                       │ │
│  │  - Wait for human approval                              │ │
│  │  - Resume on approval                                   │ │
│  └────────────┬───────────────────────────────────────────┘ │
│               │                                              │
│               ▼                                              │
│      Continue to Migration Planning                          │
└──────────────────────────────────────────────────────────────┘
                        │
        ┌───────────────▼────────────────┐
        │   Human Review Interface       │
        │   (React + Carbon Design)      │
        │                                 │
        │  - Display intake draft         │
        │  - Show validation flags        │
        │  - Allow comments/edits         │
        │  - Approve/Reject workflow      │
        └─────────────────────────────────┘
```

## Implementation

### 1. Intake Draft Agent

```python
# backend/app/agents/intake_draft_agent.py
from typing import Dict, Any, List
import logging
from datetime import datetime
from langsmith import traceable

from ..llm.provider import LLMProvider
from ..orchestration.state import MigrationState

logger = logging.getLogger(__name__)

class IntakeDraftAgent:
    """
    Intake Draft Agent - LLM-based document synthesis.
    
    Responsibilities:
    - Synthesize extracted facts into structured intake document
    - Include executive summary, current state, dependencies, constraints
    - Preserve evidence references
    - Format for human review
    """
    
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
        self.agent_name = "intake_draft_agent"
    
    @traceable(name="intake_draft_agent", run_type="chain")
    async def execute(self, state: MigrationState) -> Dict[str, Any]:
        """
        Execute intake document generation.
        
        Args:
            state: Current workflow state
            
        Returns:
            State patch with intake draft
        """
        
        logger.info(f"[{self.agent_name}] Starting intake draft generation")
        
        try:
            # Get required data from state
            extracted_facts = state.get("extracted_facts", {})
            missing_questions = state.get("missing_questions", [])
            evidence_map = state.get("evidence_map", {})
            confidence_scores = state.get("confidence_scores", {})
            
            if not extracted_facts:
                raise ValueError("No extracted facts available for intake draft")
            
            # Build intake prompt
            prompt = self._build_intake_prompt(
                extracted_facts,
                missing_questions,
                evidence_map,
                confidence_scores
            )
            
            # Generate intake document
            intake_draft = await self.llm.generate(
                prompt=prompt,
                temperature=0.2,  # Low for consistency
                max_tokens=4000,
                metadata={
                    "agent": self.agent_name,
                    "task": "intake_draft_generation"
                }
            )
            
            # Structure the intake document
            structured_intake = self._structure_intake(
                intake_draft,
                extracted_facts,
                missing_questions,
                evidence_map
            )
            
            logger.info(f"[{self.agent_name}] Generated intake draft")
            
            # Return state patch
            return {
                "intake_draft": structured_intake,
                "phase": "HUMAN_REVIEW",
                "trace_metadata": {
                    **state.get("trace_metadata", {}),
                    "intake_draft": {
                        "sections_count": len(structured_intake.get("sections", [])),
                        "open_questions_count": len(missing_questions),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            }
        
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error: {str(e)}")
            return {
                "phase": "ERROR",
                "last_error": f"Intake draft generation failed: {str(e)}",
                "error_log": [
                    *state.get("error_log", []),
                    {
                        "agent": self.agent_name,
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ]
            }
    
    def _build_intake_prompt(
        self,
        extracted_facts: Dict[str, List[Dict[str, Any]]],
        missing_questions: List[Dict[str, Any]],
        evidence_map: Dict[str, List[Dict[str, Any]]],
        confidence_scores: Dict[str, float]
    ) -> str:
        """Build prompt for intake document generation"""
        
        # Format facts by category
        facts_by_category = {}
        for category, facts in extracted_facts.items():
            facts_by_category[category] = [
                f"- {fact['fact']} (confidence: {confidence_scores.get(fact['fact_id'], 0):.2f})"
                for fact in facts
            ]
        
        # Format open questions
        questions_text = "\n".join([
            f"- [{q['priority']}] {q['question']}"
            for q in missing_questions[:15]
        ])
        
        prompt = f"""You are a technical writer creating a migration intake document for stakeholder review.

EXTRACTED FACTS:

Technical Stack:
{chr(10).join(facts_by_category.get('technical_stack', []))}

Dependencies:
{chr(10).join(facts_by_category.get('dependencies', []))}

Runtime Configuration:
{chr(10).join(facts_by_category.get('runtime_configuration', []))}

Deployment Strategy:
{chr(10).join(facts_by_category.get('deployment_strategy', []))}

Architectural Decisions:
{chr(10).join(facts_by_category.get('architectural_decisions', []))}

Security & Compliance:
{chr(10).join(facts_by_category.get('security_compliance', []))}

Known Risks:
{chr(10).join(facts_by_category.get('known_risks', []))}

OPEN QUESTIONS:
{questions_text}

CREATE A COMPREHENSIVE MIGRATION INTAKE DOCUMENT:

## Executive Summary
[2-3 sentences: What is being migrated, why, and key considerations]

## Current State

### Technical Stack
[List technologies with versions. Flag low-confidence items with ⚠️]

### Architecture Overview
[Describe current architecture. Include architectural style, key components, data flow]

### Dependencies
[List internal and external dependencies. Include databases, APIs, services]

### Runtime Configuration
[Describe configuration approach, environment variables, secrets management]

### Deployment Strategy
[Current deployment method, CI/CD pipeline, infrastructure]

## Migration Considerations

### Security & Compliance
[Authentication, authorization, data handling, compliance requirements]

### Known Risks & Technical Debt
[List identified risks with severity. Include technical debt, deprecated dependencies]

### Constraints
[Technical, business, and compliance constraints that affect migration]

### Assumptions
[Key assumptions made during analysis. Flag items needing verification]

## Open Questions
[List prioritized questions needing answers before migration planning]

## Recommendations
[Initial thoughts on migration approach based on current understanding]

FORMATTING RULES:
- Use markdown
- Keep technical but readable
- Flag low-confidence items (<0.7) with ⚠️
- Mark open questions with ❓
- Use bullet points for lists
- Include specific versions and details
- Be concise but comprehensive
- Avoid speculation - stick to extracted facts
"""
        
        return prompt
    
    def _structure_intake(
        self,
        intake_text: str,
        extracted_facts: Dict[str, List[Dict[str, Any]]],
        missing_questions: List[Dict[str, Any]],
        evidence_map: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Structure intake document with metadata"""
        
        return {
            "document_text": intake_text,
            "sections": self._extract_sections(intake_text),
            "facts_count": sum(len(facts) for facts in extracted_facts.values()),
            "open_questions_count": len(missing_questions),
            "evidence_references": evidence_map,
            "generated_at": datetime.utcnow().isoformat(),
            "status": "pending_review",
            "metadata": {
                "agent": self.agent_name,
                "version": 1
            }
        }
    
    def _extract_sections(self, intake_text: str) -> List[Dict[str, str]]:
        """Extract sections from markdown text"""
        
        sections = []
        current_section = None
        current_content = []
        
        for line in intake_text.split("\n"):
            if line.startswith("## "):
                # Save previous section
                if current_section:
                    sections.append({
                        "title": current_section,
                        "content": "\n".join(current_content).strip()
                    })
                
                # Start new section
                current_section = line[3:].strip()
                current_content = []
            else:
                current_content.append(line)
        
        # Save last section
        if current_section:
            sections.append({
                "title": current_section,
                "content": "\n".join(current_content).strip()
            })
        
        return sections
```

### 2. Review/Validation Agent

```python
# backend/app/agents/review_agent.py
from typing import Dict, Any, List
import logging
from datetime import datetime
from langsmith import traceable

from ..llm.provider import LLMProvider
from ..orchestration.state import MigrationState

logger = logging.getLogger(__name__)

class ReviewAgent:
    """
    Review/Validation Agent - Hybrid validation (rules + LLM).
    
    Responsibilities:
    - Rule-based validation (fast, deterministic)
    - LLM semantic validation (thorough)
    - Check for contradictions and unsupported claims
    - Verify completeness
    - Flag issues for human attention
    """
    
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
        self.agent_name = "review_agent"
    
    @traceable(name="review_agent", run_type="chain")
    async def execute(self, state: MigrationState) -> Dict[str, Any]:
        """
        Execute intake validation.
        
        Args:
            state: Current workflow state
            
        Returns:
            State patch with validation results
        """
        
        logger.info(f"[{self.agent_name}] Starting intake validation")
        
        try:
            intake_draft = state.get("intake_draft", {})
            extracted_facts = state.get("extracted_facts", {})
            
            if not intake_draft:
                raise ValueError("No intake draft available for validation")
            
            # Phase 1: Rule-based validation (fast)
            rule_flags = self._run_rule_validation(intake_draft, extracted_facts)
            
            # Phase 2: LLM semantic validation (thorough)
            semantic_flags = await self._run_llm_validation(intake_draft, extracted_facts)
            
            # Combine and prioritize flags
            all_flags = rule_flags + semantic_flags
            prioritized_flags = self._prioritize_flags(all_flags)
            
            # Determine if human review is required
            requires_review = len(prioritized_flags) > 0
            
            logger.info(
                f"[{self.agent_name}] Validation complete: {len(prioritized_flags)} flags"
            )
            
            # Return state patch
            return {
                "validation_results": {
                    "rule_based_flags": len(rule_flags),
                    "semantic_flags": len(semantic_flags),
                    "total_flags": len(prioritized_flags),
                    "requires_review": requires_review,
                    "validated_at": datetime.utcnow().isoformat()
                },
                "review_flags": prioritized_flags,
                "phase": "HUMAN_REVIEW",
                "trace_metadata": {
                    **state.get("trace_metadata", {}),
                    "validation": {
                        "flags_count": len(prioritized_flags),
                        "high_severity_count": sum(1 for f in prioritized_flags if f.get("severity") == "HIGH"),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            }
        
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error: {str(e)}")
            return {
                "phase": "ERROR",
                "last_error": f"Validation failed: {str(e)}",
                "error_log": [
                    *state.get("error_log", []),
                    {
                        "agent": self.agent_name,
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ]
            }
    
    def _run_rule_validation(
        self,
        intake_draft: Dict[str, Any],
        extracted_facts: Dict[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Run deterministic rule-based validation"""
        
        flags = []
        
        # Check 1: Required sections present
        required_sections = [
            "Executive Summary",
            "Current State",
            "Migration Considerations",
            "Open Questions"
        ]
        
        sections = intake_draft.get("sections", [])
        section_titles = [s["title"] for s in sections]
        
        for required in required_sections:
            if not any(required.lower() in title.lower() for title in section_titles):
                flags.append({
                    "type": "MISSING_SECTION",
                    "severity": "HIGH",
                    "description": f"Required section missing: {required}",
                    "location": "document_structure",
                    "resolution": f"Add {required} section to intake document"
                })
        
        # Check 2: Minimum content length
        document_text = intake_draft.get("document_text", "")
        if len(document_text) < 500:
            flags.append({
                "type": "INSUFFICIENT_CONTENT",
                "severity": "HIGH",
                "description": "Intake document is too short",
                "location": "document_length",
                "resolution": "Expand sections with more detail"
            })
        
        # Check 3: Low confidence facts count
        low_conf_count = sum(
            1 for facts in extracted_facts.values()
            for fact in facts
            if fact.get("confidence", 1.0) < 0.5
        )
        
        if low_conf_count > 5:
            flags.append({
                "type": "HIGH_UNCERTAINTY",
                "severity": "MEDIUM",
                "description": f"{low_conf_count} facts have very low confidence (<0.5)",
                "location": "extracted_facts",
                "resolution": "Verify low-confidence facts before proceeding"
            })
        
        # Check 4: Open questions count
        open_questions_count = intake_draft.get("open_questions_count", 0)
        if open_questions_count > 15:
            flags.append({
                "type": "TOO_MANY_GAPS",
                "severity": "MEDIUM",
                "description": f"{open_questions_count} open questions - significant information gaps",
                "location": "open_questions",
                "resolution": "Answer critical questions before migration planning"
            })
        
        return flags
    
    async def _run_llm_validation(
        self,
        intake_draft: Dict[str, Any],
        extracted_facts: Dict[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Run LLM-based semantic validation"""
        
        document_text = intake_draft.get("document_text", "")
        
        prompt = f"""You are a quality assurance analyst reviewing a migration intake document.

INTAKE DOCUMENT:
{document_text}

VALIDATE THE DOCUMENT FOR:

1. **Contradictions**: Are there conflicting statements?
2. **Unsupported Claims**: Are all claims backed by evidence or marked as assumptions?
3. **Logical Consistency**: Does the narrative make sense?
4. **Completeness**: Are critical details missing?
5. **Clarity**: Is the document clear and understandable?

For each issue found:
- Describe the issue clearly
- Specify location (section name)
- Suggest resolution
- Assign severity:
  - HIGH: Blocks migration planning
  - MEDIUM: Affects quality or accuracy
  - LOW: Minor improvement

OUTPUT FORMAT:
{{
  "issues": [
    {{
      "type": "CONTRADICTION",
      "severity": "HIGH",
      "description": "Document states Java 8 in Technical Stack but Java 11 in Deployment Strategy",
      "location": "Technical Stack / Deployment Strategy",
      "resolution": "Verify actual Java version in production environment"
    }}
  ]
}}
"""
        
        result = await self.llm.generate_structured(
            prompt=prompt,
            schema=self._get_validation_schema(),
            temperature=0.1,
            metadata={
                "agent": self.agent_name,
                "task": "semantic_validation"
            }
        )
        
        return result.get("issues", [])
    
    def _get_validation_schema(self) -> Dict[str, Any]:
        """Get JSON schema for validation results"""
        
        return {
            "type": "object",
            "properties": {
                "issues": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "severity": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]},
                            "description": {"type": "string"},
                            "location": {"type": "string"},
                            "resolution": {"type": "string"}
                        },
                        "required": ["type", "severity", "description"]
                    }
                }
            },
            "required": ["issues"]
        }
    
    def _prioritize_flags(self, flags: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize validation flags by severity"""
        
        severity_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        
        return sorted(
            flags,
            key=lambda f: severity_order.get(f.get("severity", "LOW"), 0),
            reverse=True
        )
```

### 3. Human Review Checkpoint

```python
# backend/app/orchestration/human_review.py
from typing import Dict, Any
import logging
from datetime import datetime
from langgraph.checkpoint import BaseCheckpointSaver

from .state import MigrationState

logger = logging.getLogger(__name__)

class HumanReviewCheckpoint:
    """
    Human review checkpoint for LangGraph workflow.
    
    Pauses workflow execution and waits for human approval.
    """
    
    def __init__(self, checkpoint_saver: BaseCheckpointSaver):
        self.checkpoint_saver = checkpoint_saver
    
    async def wait_for_review(self, state: MigrationState) -> Dict[str, Any]:
        """
        Pause workflow and wait for human review.
        
        Args:
            state: Current workflow state
            
        Returns:
            State patch after review
        """
        
        logger.info("Workflow paused for human review")
        
        # Check if already reviewed
        if state.get("human_reviewed"):
            logger.info("Human review already completed")
            return {
                "phase": "MIGRATION_PLANNING"
            }
        
        # Save checkpoint
        checkpoint_id = await self.checkpoint_saver.save(state)
        
        logger.info(f"Checkpoint saved: {checkpoint_id}")
        
        # Return state indicating waiting for review
        return {
            "phase": "HUMAN_REVIEW",
            "trace_metadata": {
                **state.get("trace_metadata", {}),
                "human_review": {
                    "checkpoint_id": checkpoint_id,
                    "waiting_since": datetime.utcnow().isoformat(),
                    "status": "pending"
                }
            }
        }
    
    async def resume_after_review(
        self,
        state: MigrationState,
        review_comments: List[str],
        approved: bool
    ) -> Dict[str, Any]:
        """
        Resume workflow after human review.
        
        Args:
            state: Current workflow state
            review_comments: Comments from reviewer
            approved: Whether intake was approved
            
        Returns:
            State patch with review results
        """
        
        if approved:
            logger.info("Intake approved - proceeding to migration planning")
            return {
                "human_reviewed": True,
                "review_comments": review_comments,
                "review_timestamp": datetime.utcnow().isoformat(),
                "phase": "MIGRATION_PLANNING",
                "trace_metadata": {
                    **state.get("trace_metadata", {}),
                    "human_review": {
                        "status": "approved",
                        "reviewed_at": datetime.utcnow().isoformat(),
                        "comments_count": len(review_comments)
                    }
                }
            }
        else:
            logger.info("Intake rejected - returning to intake draft")
            return {
                "human_reviewed": False,
                "review_comments": review_comments,
                "review_timestamp": datetime.utcnow().isoformat(),
                "phase": "INTAKE_DRAFT",
                "retry_count": state.get("retry_count", 0) + 1,
                "trace_metadata": {
                    **state.get("trace_metadata", {}),
                    "human_review": {
                        "status": "rejected",
                        "reviewed_at": datetime.utcnow().isoformat(),
                        "comments_count": len(review_comments)
                    }
                }
            }
```

### 4. FastAPI Review Endpoints

```python
# backend/app/api/review.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api/review", tags=["review"])

class ReviewSubmission(BaseModel):
    project_id: str
    approved: bool
    comments: List[str]
    edited_sections: Optional[Dict[str, str]] = None

@router.get("/intake/{project_id}")
async def get_intake_draft(project_id: str):
    """Get intake draft for review"""
    
    # Get state from state manager
    state = await state_manager.read_state(project_id)
    
    if not state.get("intake_draft"):
        raise HTTPException(status_code=404, detail="Intake draft not found")
    
    return {
        "project_id": project_id,
        "intake_draft": state["intake_draft"],
        "validation_flags": state.get("review_flags", []),
        "open_questions": state.get("missing_questions", []),
        "status": state.get("phase")
    }

@router.post("/submit")
async def submit_review(review: ReviewSubmission):
    """Submit human review"""
    
    # Get current state
    state = await state_manager.read_state(review.project_id)
    
    # Resume workflow with review results
    review_checkpoint = HumanReviewCheckpoint(checkpoint_saver)
    state_patch = await review_checkpoint.resume_after_review(
        state,
        review.comments,
        review.approved
    )
    
    # Commit state patch
    updated_state = await state_manager.commit_state_patch(
        patch=state_patch,
        expected_version=state["state_version"],
        committed_by="human_reviewer"
    )
    
    return {
        "project_id": review.project_id,
        "status": "approved" if review.approved else "rejected",
        "next_phase": updated_state["phase"]
    }
```

## Testing Phase 5

```python
# tests/test_intake_review.py
import pytest

@pytest.mark.asyncio
async def test_intake_draft_agent(mock_llm_provider, mock_state_with_facts):
    """Test intake draft generation"""
    
    from backend.app.agents.intake_draft_agent import IntakeDraftAgent
    
    agent = IntakeDraftAgent(mock_llm_provider)
    result = await agent.execute(mock_state_with_facts)
    
    assert "intake_draft" in result
    assert result["phase"] == "HUMAN_REVIEW"
    assert "sections" in result["intake_draft"]

@pytest.mark.asyncio
async def test_review_agent(mock_llm_provider, mock_state_with_intake):
    """Test validation agent"""
    
    from backend.app.agents.review_agent import ReviewAgent
    
    agent = ReviewAgent(mock_llm_provider)
    result = await agent.execute(mock_state_with_intake)
    
    assert "validation_results" in result
    assert "review_flags" in result

@pytest.mark.asyncio
async def test_human_review_checkpoint(mock_checkpoint_saver, mock_state):
    """Test human review checkpoint"""
    
    from backend.app.orchestration.human_review import HumanReviewCheckpoint
    
    checkpoint = HumanReviewCheckpoint(mock_checkpoint_saver)
    
    # Test pause
    result = await checkpoint.wait_for_review(mock_state)
    assert result["phase"] == "HUMAN_REVIEW"
    
    # Test resume (approved)
    result = await checkpoint.resume_after_review(
        mock_state,
        ["Looks good"],
        approved=True
    )
    assert result["human_reviewed"] == True
    assert result["phase"] == "MIGRATION_PLANNING"
```

## Success Criteria

- ✅ Intake Draft Agent generates comprehensive intake document
- ✅ Review Agent validates intake with hybrid approach
- ✅ Human review checkpoint pauses workflow correctly
- ✅ Review API endpoints work properly
- ✅ Workflow resumes after approval
- ✅ Rejection triggers iteration back to intake draft
- ✅ All actions traced in LangSmith

## Next Steps

Proceed to **Phase 6: Migration Planning Agent & Final Validation** to implement the migration planning agent.