# Phase 4: Core Agent Implementation (Context, Extraction, Questionnaire)

## Overview

Phase 4 implements the three core agents that form the foundation of the migration analysis pipeline: Context Retrieval Agent, Extraction Agent, and Questionnaire Agent. These agents work together to gather context, extract structured facts, and identify information gaps.

## Objectives

1. **Implement Context Retrieval Agent**
   - Execute MCP retrieval using configured profiles
   - Normalize context into agent-consumable format
   - Preserve evidence references
   - Return state patch for orchestrator

2. **Implement Extraction Agent**
   - Parse unstructured context using LLM
   - Extract migration-relevant facts
   - Assign confidence scores
   - Map facts to evidence sources

3. **Implement Questionnaire Agent**
   - Identify low-confidence facts
   - Detect missing required fields
   - Generate prioritized questions
   - Map questions to evidence gaps

4. **Integrate with LangGraph Workflow**
   - Register agents as LangGraph nodes
   - Implement state patch returns
   - Add LangSmith tracing
   - Handle errors and retries

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  LangGraph Workflow                          │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Supervisor Node                            │ │
│  │         (Routes to appropriate agent)                   │ │
│  └────────────┬───────────────────────────────────────────┘ │
│               │                                              │
│  ┌────────────▼───────────────────────────────────────────┐ │
│  │         Context Retrieval Agent Node                    │ │
│  │  - Execute MCP retrieval                                │ │
│  │  - Normalize context                                    │ │
│  │  - Return state patch                                   │ │
│  └────────────┬───────────────────────────────────────────┘ │
│               │                                              │
│  ┌────────────▼───────────────────────────────────────────┐ │
│  │            Extraction Agent Node                        │ │
│  │  - Parse context with LLM                               │ │
│  │  - Extract structured facts                             │ │
│  │  - Assign confidence scores                             │ │
│  │  - Map to evidence                                      │ │
│  └────────────┬───────────────────────────────────────────┘ │
│               │                                              │
│  ┌────────────▼───────────────────────────────────────────┐ │
│  │          Questionnaire Agent Node                       │ │
│  │  - Identify gaps                                        │ │
│  │  - Generate questions                                   │ │
│  │  - Prioritize questions                                 │ │
│  │  - Return state patch                                   │ │
│  └────────────┬───────────────────────────────────────────┘ │
│               │                                              │
│               ▼                                              │
│      Return to Supervisor                                    │
└──────────────────────────────────────────────────────────────┘
```

## Implementation

### 1. Context Retrieval Agent

```python
# backend/app/agents/context_retrieval_agent.py
from typing import Dict, Any
import logging
from langsmith import traceable

from ..mcp.connector import MCPConnector
from ..mcp.normalizer import ContextNormalizer
from ..mcp.config import MCPConfig, RetrievalProfile
from ..orchestration.state import MigrationState

logger = logging.getLogger(__name__)

class ContextRetrievalAgent:
    """
    Context Retrieval Agent - API-based, no LLM required.
    
    Responsibilities:
    - Execute MCP retrieval using configured profile
    - Normalize context into unified format
    - Preserve source IDs and evidence references
    - Return state patch for orchestrator
    """
    
    def __init__(self, mcp_config: MCPConfig):
        self.mcp_config = mcp_config
        self.agent_name = "context_retrieval_agent"
    
    @traceable(name="context_retrieval_agent", run_type="chain")
    async def execute(self, state: MigrationState) -> Dict[str, Any]:
        """
        Execute context retrieval.
        
        Args:
            state: Current workflow state
            
        Returns:
            State patch with retrieved context
        """
        
        logger.info(f"[{self.agent_name}] Starting context retrieval")
        
        try:
            # Get retrieval profile from state
            profile = self._get_retrieval_profile(state)
            
            # Execute MCP retrieval
            async with MCPConnector(self.mcp_config) as connector:
                context_pack = await connector.retrieve_context(profile)
            
            # Normalize context
            normalizer = ContextNormalizer(
                chunk_size=profile.chunk_size,
                chunk_overlap=profile.chunk_overlap
            )
            normalized_docs = normalizer.normalize_context_pack(context_pack)
            
            logger.info(
                f"[{self.agent_name}] Retrieved {len(normalized_docs)} documents"
            )
            
            # Return state patch
            return {
                "context_pack": context_pack,
                "normalized_docs": normalized_docs,
                "phase": "EXTRACTION",
                "trace_metadata": {
                    **state.get("trace_metadata", {}),
                    "context_retrieval": {
                        "documents_retrieved": len(normalized_docs),
                        "profile_used": profile.profile_name,
                        "timestamp": context_pack["retrieved_at"]
                    }
                }
            }
        
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error: {str(e)}")
            return {
                "phase": "ERROR",
                "last_error": f"Context retrieval failed: {str(e)}",
                "error_log": [
                    *state.get("error_log", []),
                    {
                        "agent": self.agent_name,
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ]
            }
    
    def _get_retrieval_profile(self, state: MigrationState) -> RetrievalProfile:
        """Get or create retrieval profile from state"""
        
        from ..mcp.config import CONTEXT_RETRIEVAL_PROFILE
        
        # Use profile from state if available
        if state.get("mcp_request_profile"):
            return RetrievalProfile(**state["mcp_request_profile"])
        
        # Otherwise use default
        return CONTEXT_RETRIEVAL_PROFILE
```

### 2. Extraction Agent

```python
# backend/app/agents/extraction_agent.py
from typing import Dict, Any, List
import logging
from datetime import datetime
from langsmith import traceable

from ..llm.provider import LLMProvider
from ..orchestration.state import MigrationState

logger = logging.getLogger(__name__)

class ExtractionAgent:
    """
    Extraction Agent - LLM-based fact extraction.
    
    Responsibilities:
    - Parse unstructured context using LLM
    - Extract migration-relevant facts
    - Assign confidence scores
    - Map facts to evidence sources
    """
    
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
        self.agent_name = "extraction_agent"
    
    @traceable(name="extraction_agent", run_type="chain")
    async def execute(self, state: MigrationState) -> Dict[str, Any]:
        """
        Execute fact extraction.
        
        Args:
            state: Current workflow state
            
        Returns:
            State patch with extracted facts
        """
        
        logger.info(f"[{self.agent_name}] Starting fact extraction")
        
        try:
            # Get normalized documents
            normalized_docs = state.get("normalized_docs", [])
            
            if not normalized_docs:
                raise ValueError("No normalized documents available for extraction")
            
            # Build extraction prompt
            prompt = self._build_extraction_prompt(normalized_docs)
            
            # Call LLM with structured output
            extraction_result = await self.llm.generate_structured(
                prompt=prompt,
                schema=self._get_extraction_schema(),
                temperature=0.1,  # Low for consistency
                metadata={
                    "agent": self.agent_name,
                    "task": "fact_extraction",
                    "document_count": len(normalized_docs)
                }
            )
            
            # Process extraction result
            extracted_facts = self._process_extraction(extraction_result, normalized_docs)
            
            # Assign confidence scores
            confidence_scores = self._calculate_confidence_scores(extracted_facts)
            
            # Map facts to evidence
            evidence_map = self._map_facts_to_evidence(extracted_facts, normalized_docs)
            
            logger.info(
                f"[{self.agent_name}] Extracted {len(extracted_facts)} facts"
            )
            
            # Return state patch
            return {
                "extracted_facts": extracted_facts,
                "confidence_scores": confidence_scores,
                "evidence_map": evidence_map,
                "phase": "QUESTIONNAIRE",
                "trace_metadata": {
                    **state.get("trace_metadata", {}),
                    "extraction": {
                        "facts_extracted": len(extracted_facts),
                        "avg_confidence": sum(confidence_scores.values()) / len(confidence_scores) if confidence_scores else 0,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            }
        
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error: {str(e)}")
            return {
                "phase": "ERROR",
                "last_error": f"Fact extraction failed: {str(e)}",
                "error_log": [
                    *state.get("error_log", []),
                    {
                        "agent": self.agent_name,
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ]
            }
    
    def _build_extraction_prompt(self, normalized_docs: List[Dict[str, Any]]) -> str:
        """Build extraction prompt from normalized documents"""
        
        # Combine document chunks
        context_text = "\n\n---\n\n".join([
            f"Document: {doc['title']}\n"
            f"Source ID: {doc['source_id']}\n"
            f"Content:\n{doc['full_text'][:2000]}"  # Limit per doc
            for doc in normalized_docs[:10]  # Limit total docs
        ])
        
        prompt = f"""You are a technical analyst extracting migration-relevant facts from application documentation.

CONTEXT DOCUMENTS:
{context_text}

EXTRACT THE FOLLOWING INFORMATION:

1. **Technical Stack**
   - Programming languages and versions
   - Frameworks and libraries
   - Runtime environments
   - Build tools

2. **Dependencies**
   - Internal services and APIs
   - External APIs and integrations
   - Databases and data stores
   - Message queues and event systems

3. **Runtime Configuration**
   - Environment variables
   - Configuration files
   - Feature flags
   - Secrets management

4. **Deployment Strategy**
   - Current deployment method
   - CI/CD pipeline
   - Infrastructure (servers, containers, etc.)
   - Scaling approach

5. **Architectural Decisions**
   - Design patterns used
   - Architectural style (monolith, microservices, etc.)
   - Communication patterns
   - Data flow

6. **Security & Compliance**
   - Authentication methods
   - Authorization approach
   - Data encryption
   - Compliance requirements (GDPR, HIPAA, etc.)

7. **Known Risks**
   - Technical debt
   - Deprecated dependencies
   - Performance bottlenecks
   - Known issues

For each fact:
- Provide a clear, specific statement
- Assign confidence score (0.0-1.0)
- Reference the source document ID
- Quote supporting evidence (exact text from document)

CONFIDENCE SCORING GUIDELINES:
- 1.0: Explicitly stated with clear evidence
- 0.8-0.9: Strongly implied with good evidence
- 0.6-0.7: Reasonably inferred from context
- 0.4-0.5: Weakly supported or ambiguous
- 0.0-0.3: Speculative or uncertain

OUTPUT FORMAT:
Return a JSON object with the following structure:
{{
  "technical_stack": [
    {{
      "category": "language",
      "fact": "Application uses Java 8",
      "confidence": 0.95,
      "source_id": "src_abc123",
      "evidence": "pom.xml line 15: <java.version>1.8</java.version>"
    }}
  ],
  "dependencies": [...],
  "runtime_configuration": [...],
  "deployment_strategy": [...],
  "architectural_decisions": [...],
  "security_compliance": [...],
  "known_risks": [...]
}}
"""
        
        return prompt
    
    def _get_extraction_schema(self) -> Dict[str, Any]:
        """Get JSON schema for structured extraction"""
        
        return {
            "type": "object",
            "properties": {
                "technical_stack": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string"},
                            "fact": {"type": "string"},
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                            "source_id": {"type": "string"},
                            "evidence": {"type": "string"}
                        },
                        "required": ["category", "fact", "confidence", "source_id"]
                    }
                },
                "dependencies": {"type": "array", "items": {"type": "object"}},
                "runtime_configuration": {"type": "array", "items": {"type": "object"}},
                "deployment_strategy": {"type": "array", "items": {"type": "object"}},
                "architectural_decisions": {"type": "array", "items": {"type": "object"}},
                "security_compliance": {"type": "array", "items": {"type": "object"}},
                "known_risks": {"type": "array", "items": {"type": "object"}}
            },
            "required": ["technical_stack", "dependencies"]
        }
    
    def _process_extraction(
        self,
        extraction_result: Dict[str, Any],
        normalized_docs: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Process and validate extraction result"""
        
        # Flatten all facts into single structure
        all_facts = {}
        
        for category, facts in extraction_result.items():
            if isinstance(facts, list):
                # Add fact IDs
                for i, fact in enumerate(facts):
                    fact["fact_id"] = f"{category}_{i:03d}"
                    fact["category"] = category
                
                all_facts[category] = facts
        
        return all_facts
    
    def _calculate_confidence_scores(
        self,
        extracted_facts: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, float]:
        """Calculate confidence scores for each fact"""
        
        confidence_scores = {}
        
        for category, facts in extracted_facts.items():
            for fact in facts:
                fact_id = fact["fact_id"]
                confidence = fact.get("confidence", 0.5)
                confidence_scores[fact_id] = confidence
        
        return confidence_scores
    
    def _map_facts_to_evidence(
        self,
        extracted_facts: Dict[str, List[Dict[str, Any]]],
        normalized_docs: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """Map each fact to its evidence sources"""
        
        evidence_map = {}
        
        for category, facts in extracted_facts.items():
            for fact in facts:
                fact_id = fact["fact_id"]
                source_id = fact.get("source_id")
                evidence = fact.get("evidence", "")
                
                evidence_map[fact_id] = [
                    {
                        "source_id": source_id,
                        "evidence_text": evidence,
                        "document_title": self._get_doc_title(source_id, normalized_docs)
                    }
                ]
        
        return evidence_map
    
    def _get_doc_title(self, source_id: str, normalized_docs: List[Dict[str, Any]]) -> str:
        """Get document title from source ID"""
        for doc in normalized_docs:
            if doc["source_id"] == source_id:
                return doc["title"]
        return "Unknown"
```

### 3. Questionnaire Agent

```python
# backend/app/agents/questionnaire_agent.py
from typing import Dict, Any, List
import logging
from datetime import datetime
from langsmith import traceable

from ..llm.provider import LLMProvider
from ..orchestration.state import MigrationState

logger = logging.getLogger(__name__)

class QuestionnaireAgent:
    """
    Questionnaire Agent - LLM-based gap analysis.
    
    Responsibilities:
    - Identify low-confidence facts
    - Detect missing required fields
    - Generate prioritized questions
    - Map questions to evidence gaps
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
    
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
        self.agent_name = "questionnaire_agent"
    
    @traceable(name="questionnaire_agent", run_type="chain")
    async def execute(self, state: MigrationState) -> Dict[str, Any]:
        """
        Execute gap analysis and question generation.
        
        Args:
            state: Current workflow state
            
        Returns:
            State patch with generated questions
        """
        
        logger.info(f"[{self.agent_name}] Starting gap analysis")
        
        try:
            # Get extracted facts and confidence scores
            extracted_facts = state.get("extracted_facts", {})
            confidence_scores = state.get("confidence_scores", {})
            
            if not extracted_facts:
                raise ValueError("No extracted facts available for gap analysis")
            
            # Identify gaps
            low_confidence_facts = self._identify_low_confidence_facts(
                extracted_facts,
                confidence_scores
            )
            missing_fields = self._identify_missing_fields(extracted_facts)
            
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
            
            logger.info(
                f"[{self.agent_name}] Generated {len(prioritized_questions)} questions"
            )
            
            # Return state patch
            return {
                "missing_questions": prioritized_questions,
                "question_priorities": {q["question_id"]: q["priority_score"] for q in prioritized_questions},
                "phase": "INTAKE_DRAFT",
                "trace_metadata": {
                    **state.get("trace_metadata", {}),
                    "questionnaire": {
                        "questions_generated": len(prioritized_questions),
                        "high_priority_count": sum(1 for q in prioritized_questions if q["priority"] == "HIGH"),
                        "low_confidence_facts": len(low_confidence_facts),
                        "missing_fields": len(missing_fields),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            }
        
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error: {str(e)}")
            return {
                "phase": "ERROR",
                "last_error": f"Question generation failed: {str(e)}",
                "error_log": [
                    *state.get("error_log", []),
                    {
                        "agent": self.agent_name,
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ]
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
                fact_id = fact["fact_id"]
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
        
        # Format extracted facts
        facts_summary = "\n".join([
            f"- {category}: {len(facts)} facts"
            for category, facts in extracted_facts.items()
        ])
        
        # Format low confidence facts
        low_conf_summary = "\n".join([
            f"- {fact['fact']} (confidence: {fact['confidence']:.2f})"
            for fact in low_confidence_facts[:10]
        ])
        
        # Format missing fields
        missing_summary = "\n".join([f"- {field}" for field in missing_fields])
        
        prompt = f"""You are a migration analyst identifying information gaps and generating clarifying questions.

EXTRACTED FACTS SUMMARY:
{facts_summary}

LOW CONFIDENCE FACTS (<{self.LOW_CONFIDENCE_THRESHOLD}):
{low_conf_summary}

MISSING REQUIRED FIELDS:
{missing_summary}

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

OUTPUT FORMAT:
{{
  "questions": [
    {{
      "question": "What authentication method does the application currently use?",
      "reason": "Required to design cloud IAM integration and security architecture",
      "suggested_source": "Check application.properties, security configuration files, or authentication middleware",
      "priority": "HIGH",
      "related_fact_id": "security_compliance_001",
      "gap_type": "missing_field"
    }}
  ]
}}
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
            question_text = question["question"].lower()
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
```

### 4. LangGraph Integration

```python
# backend/app/orchestration/workflow.py
from langgraph.graph import StateGraph, END
from typing import Dict, Any

from .state import MigrationState, WorkflowPhase
from ..agents.context_retrieval_agent import ContextRetrievalAgent
from ..agents.extraction_agent import ExtractionAgent
from ..agents.questionnaire_agent import QuestionnaireAgent

def create_core_agents_workflow(
    context_agent: ContextRetrievalAgent,
    extraction_agent: ExtractionAgent,
    questionnaire_agent: QuestionnaireAgent
) -> StateGraph:
    """Create LangGraph workflow with core agents"""
    
    # Create graph
    workflow = StateGraph(MigrationState)
    
    # Add nodes
    workflow.add_node("context_retrieval", context_agent.execute)
    workflow.add_node("extraction", extraction_agent.execute)
    workflow.add_node("questionnaire", questionnaire_agent.execute)
    
    # Add edges
    workflow.add_edge("context_retrieval", "extraction")
    workflow.add_edge("extraction", "questionnaire")
    workflow.add_edge("questionnaire", END)
    
    # Set entry point
    workflow.set_entry_point("context_retrieval")
    
    return workflow.compile()
```

## Testing Phase 4

```python
# tests/test_core_agents.py
import pytest
from backend.app.agents.context_retrieval_agent import ContextRetrievalAgent
from backend.app.agents.extraction_agent import ExtractionAgent
from backend.app.agents.questionnaire_agent import QuestionnaireAgent

@pytest.mark.asyncio
async def test_context_retrieval_agent(mock_mcp_config, mock_state):
    """Test context retrieval agent"""
    
    agent = ContextRetrievalAgent(mock_mcp_config)
    result = await agent.execute(mock_state)
    
    assert "context_pack" in result
    assert "normalized_docs" in result
    assert result["phase"] == "EXTRACTION"

@pytest.mark.asyncio
async def test_extraction_agent(mock_llm_provider, mock_state_with_context):
    """Test extraction agent"""
    
    agent = ExtractionAgent(mock_llm_provider)
    result = await agent.execute(mock_state_with_context)
    
    assert "extracted_facts" in result
    assert "confidence_scores" in result
    assert "evidence_map" in result
    assert result["phase"] == "QUESTIONNAIRE"

@pytest.mark.asyncio
async def test_questionnaire_agent(mock_llm_provider, mock_state_with_facts):
    """Test questionnaire agent"""
    
    agent = QuestionnaireAgent(mock_llm_provider)
    result = await agent.execute(mock_state_with_facts)
    
    assert "missing_questions" in result
    assert "question_priorities" in result
    assert result["phase"] == "INTAKE_DRAFT"
    
    # Verify prioritization
    questions = result["missing_questions"]
    assert questions[0]["priority_score"] >= questions[-1]["priority_score"]
```

## Success Criteria

- ✅ Context Retrieval Agent successfully fetches and normalizes context
- ✅ Extraction Agent extracts structured facts with confidence scores
- ✅ Questionnaire Agent identifies gaps and generates prioritized questions
- ✅ All agents return proper state patches
- ✅ LangSmith tracing captures all agent executions
- ✅ Error handling works correctly
- ✅ Agents integrate with LangGraph workflow

## Next Steps

Proceed to **Phase 5: Intake & Review Agents with Human-in-the-Loop** to implement the intake draft generation and validation agents.