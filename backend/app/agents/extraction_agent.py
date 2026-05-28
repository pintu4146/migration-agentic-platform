"""
Extraction Agent

Responsibilities:
- Parse unstructured context using LLM
- Extract migration-relevant facts
- Assign confidence scores
- Map facts to evidence sources

This agent uses LLM for structured extraction.
"""

from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import json

from ..providers.base import LLMProvider
from ..providers.factory import get_provider
from ..config import settings
from ..tracing.langsmith import trace_operation

logger = logging.getLogger(__name__)


class ExtractionAgent:
    """
    Extraction Agent - LLM-based fact extraction.
    
    Extracts structured facts from unstructured documentation
    with confidence scores and evidence mapping.
    """
    
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        """
        Initialize extraction agent.
        
        Args:
            llm_provider: Optional LLM provider (will be initialized in execute if None)
        """
        self.agent_name = "extraction_agent"
        self.llm = llm_provider
    
    @trace_operation("extraction_agent", run_type="chain", tags=["agent", "extraction", "llm"])
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute fact extraction.
        
        Args:
            state: Current workflow state
            
        Returns:
            State patch with extracted facts
        """
        
        logger.info(f"[{self.agent_name}] Starting fact extraction")
        
        try:
            # Validate project_id
            project_id = state.get("project_id")
            if not project_id:
                raise ValueError("project_id is required in state")
            
            logger.info(f"[{self.agent_name}] Processing project: {project_id}")
            
            # Initialize LLM provider if not set
            if self.llm is None:
                self.llm = await get_provider(prefer_primary=True)
            
            # Get normalized documents
            normalized_docs = state.get("normalized_docs", [])
            
            if not normalized_docs:
                raise ValueError("No normalized documents available for extraction")
            
            # Validate documents belong to correct project
            mismatched_docs = []
            for idx, doc in enumerate(normalized_docs):
                doc_project = doc.get("metadata", {}).get("project_id")
                if doc_project and doc_project != project_id:
                    mismatched_docs.append(f"doc[{idx}]: {doc_project}")
            
            if mismatched_docs:
                logger.error(
                    f"[{self.agent_name}] Found {len(mismatched_docs)} documents from wrong project: "
                    f"{', '.join(mismatched_docs[:5])}"
                )
                raise ValueError(
                    f"State corruption: {len(mismatched_docs)} documents belong to different projects"
                )
            
            logger.info(
                f"[{self.agent_name}] Validated {len(normalized_docs)} documents for project {project_id}"
            )
            
            # Build extraction prompt
            prompt = self._build_extraction_prompt(normalized_docs)
            
            # Call LLM with structured output
            extraction_result = await self.llm.generate_structured(
                prompt=prompt,
                schema=self._get_extraction_schema(),
                system_prompt="You are a technical analyst extracting migration-relevant facts from application documentation.",
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
            
            # Calculate statistics
            total_facts = sum(len(facts) for facts in extracted_facts.values())
            avg_confidence = sum(confidence_scores.values()) / len(confidence_scores) if confidence_scores else 0
            
            logger.info(
                f"[{self.agent_name}] Extracted {total_facts} facts "
                f"(avg confidence: {avg_confidence:.2f})"
            )
            
            # Return state patch
            return {
                "extracted_facts": extracted_facts,
                "confidence_scores": confidence_scores,
                "evidence_map": evidence_map,
                "phase": "questionnaire",
                "trace_metadata": {
                    **state.get("trace_metadata", {}),
                    "extraction": {
                        "facts_extracted": total_facts,
                        "avg_confidence": avg_confidence,
                        "categories": list(extracted_facts.keys()),
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
                "last_error": f"Fact extraction failed: {str(e)}",
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
    
    def _build_extraction_prompt(self, normalized_docs: List[Dict[str, Any]]) -> str:
        """Build extraction prompt from normalized documents"""
        
        # Combine document chunks (limit to avoid token overflow)
        context_parts = []
        total_chars = 0
        max_chars = 15000  # Leave room for prompt template
        
        for doc in normalized_docs[:10]:  # Limit to 10 documents
            # Handle both Document model format and dict format
            doc_id = doc.get('id', doc.get('source_id', 'unknown'))
            doc_title = doc.get('title', 'Untitled')
            doc_content = doc.get('content', doc.get('text', ''))
            
            doc_text = f"Document: {doc_title}\n"
            doc_text += f"Source ID: {doc_id}\n"
            doc_text += f"Content:\n{doc_content[:2000]}\n"  # Limit per doc
            
            if total_chars + len(doc_text) > max_chars:
                break
            
            context_parts.append(doc_text)
            total_chars += len(doc_text)
        
        context_text = "\n---\n".join(context_parts)
        
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

Return a JSON object with the structure defined in the schema.
"""
        
        return prompt
    
    def _get_extraction_schema(self) -> Dict[str, Any]:
        """Get JSON schema for structured extraction"""
        
        fact_schema = {
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
        
        return {
            "type": "object",
            "properties": {
                "technical_stack": {
                    "type": "array",
                    "items": fact_schema
                },
                "dependencies": {
                    "type": "array",
                    "items": fact_schema
                },
                "runtime_configuration": {
                    "type": "array",
                    "items": fact_schema
                },
                "deployment_strategy": {
                    "type": "array",
                    "items": fact_schema
                },
                "architectural_decisions": {
                    "type": "array",
                    "items": fact_schema
                },
                "security_compliance": {
                    "type": "array",
                    "items": fact_schema
                },
                "known_risks": {
                    "type": "array",
                    "items": fact_schema
                }
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
                # Add fact IDs and ensure category is set
                for i, fact in enumerate(facts):
                    fact["fact_id"] = f"{category}_{i:03d}"
                    if "category" not in fact:
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
                
                # Ensure confidence is in valid range
                confidence = max(0.0, min(1.0, confidence))
                
                confidence_scores[fact_id] = confidence
        
        return confidence_scores
    
    def _map_facts_to_evidence(
        self,
        extracted_facts: Dict[str, List[Dict[str, Any]]],
        normalized_docs: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, str]]]:
        """Map each fact to its evidence sources"""
        
        evidence_map = {}
        
        for category, facts in extracted_facts.items():
            for fact in facts:
                fact_id = fact["fact_id"]
                source_id = fact.get("source_id", "")
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
            if doc.get("source_id") == source_id:
                return doc.get("title", "Unknown")
        return "Unknown"


# Made with Bob
