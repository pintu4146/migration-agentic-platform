# Agent Orchestration Deep Analysis

## Overview

This document provides a detailed analysis of each agent in the migration copilot system, including their specific tasks, reasoning processes, prompt engineering strategies, and trade-off considerations.

## Agent Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Supervisor Agent                          │
│  Role: Orchestrator & Router                                │
│  Reasoning: Phase-based decision making                     │
└────────┬────────────────────────────────────────────────────┘
         │
         ├──► Context Retrieval Agent
         ├──► Extraction Agent
         ├──► Questionnaire Agent
         ├──► Intake Draft Agent
         ├──► Review/Validation Agent
         └──► Migration Planning Agent
```

---

## 1. Supervisor Agent (Orchestrator)

### **Primary Responsibility**
Route workflow to the appropriate agent based on current phase and state.

### **Specific Tasks**
1. Read current workflow state
2. Determine next phase based on completion criteria
3. Route to appropriate agent
4. Handle errors and retries
5. Manage workflow checkpoints

### **Reasoning Process**

```python
def route_next_node(state: MigrationState) -> str:
    """
    Decision Tree:
    
    IF phase == INIT:
        → context_retrieval
    
    ELIF phase == CONTEXT_RETRIEVAL:
        IF context_pack exists AND normalized_docs not empty:
            → extraction
        ELSE:
            → error (missing context)
    
    ELIF phase == EXTRACTION:
        IF extracted_facts exists AND confidence_scores exists:
            → questionnaire
        ELSE:
            → error (extraction failed)
    
    ELIF phase == QUESTIONNAIRE:
        IF missing_questions generated:
            → intake_draft
        ELSE:
            → error (questionnaire failed)
    
    ELIF phase == INTAKE_DRAFT:
        IF intake_draft exists:
            → human_review_gate
        ELSE:
            → error (draft failed)
    
    ELIF phase == HUMAN_REVIEW:
        IF human_reviewed == True:
            → migration_planning
        ELSE:
            → human_review_gate (wait)
    
    ELIF phase == MIGRATION_PLANNING:
        IF migration_plan exists:
            → validation
        ELSE:
            → error (planning failed)
    
    ELIF phase == VALIDATION:
        → complete
    
    ELSE:
        → error (unknown phase)
    """
```

### **Prompt Strategy**
**No LLM needed** - Pure logic-based routing

### **Trade-offs**

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **Logic-based routing** | ✅ Deterministic<br>✅ Fast<br>✅ No LLM cost | ❌ Inflexible<br>❌ Hard-coded rules | ✅ **CHOSEN** |
| **LLM-based routing** | ✅ Flexible<br>✅ Adaptive | ❌ Slow<br>❌ Expensive<br>❌ Non-deterministic | ❌ Rejected |

**Rationale:** Workflow routing should be deterministic and fast. LLM adds unnecessary complexity and cost.

---

## 2. Context Retrieval Agent

### **Primary Responsibility**
Fetch and normalize documents from Confluence via MCP connector.

### **Specific Tasks**
1. Select appropriate retrieval profile
2. Fetch documents from Confluence
3. Parse attachments (PDF, DOCX, Excel)
4. Normalize into standard format
5. Generate embeddings
6. Store in vector database
7. Create evidence map

### **Reasoning Process**

```
Input: MCP retrieval profile
↓
Fetch from Confluence API
↓
Parse documents by type:
  - HTML pages → extract text
  - PDF → PyMuPDF extraction
  - DOCX → python-docx extraction
  - Excel → pandas extraction
↓
Normalize to standard schema:
  {
    source_id: str,
    source_type: str,
    title: str,
    content: str,
    url: str,
    metadata: {...}
  }
↓
Generate embeddings (OpenAI/Gemini)
↓
Store in Qdrant
↓
Return: context_pack + normalized_docs
```

### **Prompt Strategy**
**No LLM needed** - Pure data processing

### **Trade-offs**

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **Direct API + parsing** | ✅ Fast<br>✅ Reliable<br>✅ No LLM cost | ❌ Limited to structured data | ✅ **CHOSEN** |
| **LLM-based extraction** | ✅ Handles unstructured data | ❌ Slow<br>❌ Expensive<br>❌ Unreliable | ❌ Rejected |

**Rationale:** Document fetching and parsing is deterministic. LLM not needed.

---

## 3. Extraction Agent

### **Primary Responsibility**
Extract structured technical facts from normalized documents.

### **Specific Tasks**
1. Analyze normalized documents
2. Extract technical stack (languages, frameworks, databases)
3. Extract dependencies and versions
4. Extract deployment configuration
5. Extract security/compliance requirements
6. Extract architectural decisions
7. Identify risks and constraints
8. Assign confidence scores
9. Map facts to evidence sources

### **Reasoning Process**

```
Input: normalized_docs (list of documents)
↓
LLM Analysis:
  "You are a technical architect analyzing application documentation.
   Extract structured facts about the application's technical stack,
   dependencies, deployment, security, and architecture.
   
   For each fact, provide:
   - The fact itself
   - Confidence level (0.0-1.0)
   - Source document IDs as evidence"
↓
Structured Output (JSON):
  {
    technical_stack: {
      languages: ["Java", "JavaScript"],
      frameworks: ["Spring Boot", "React"],
      databases: ["PostgreSQL", "Redis"],
      infrastructure: ["AWS EC2", "S3"]
    },
    dependencies: [
      {name: "spring-boot", version: "2.7.0", type: "framework"},
      ...
    ],
    deployment_strategy: {
      current_environment: "on-premise",
      deployment_method: "manual",
      scaling_approach: "vertical"
    },
    security_compliance: {
      authentication: "LDAP",
      authorization: "RBAC",
      compliance_requirements: ["SOC2", "HIPAA"]
    },
    risks: [
      {
        risk: "Legacy Java version (1.8)",
        severity: "high",
        mitigation: "Upgrade to Java 17"
      }
    ]
  }
↓
Calculate confidence scores:
  - Multiple sources = high confidence
  - Single source = medium confidence
  - Inferred = low confidence
↓
Build evidence map:
  {
    "technical_stack.languages.Java": ["doc_123", "doc_456"],
    "dependencies.spring-boot": ["doc_789"]
  }
↓
Return: extracted_facts + confidence_scores + evidence_map
```

### **Prompt Engineering**

```python
EXTRACTION_SYSTEM_PROMPT = """
You are an expert technical architect specializing in application modernization.

Your task is to analyze technical documentation and extract structured facts about:
1. Technical stack (languages, frameworks, databases, infrastructure)
2. Dependencies and their versions
3. Deployment and scaling strategies
4. Security and compliance requirements
5. Architectural patterns and decisions
6. Known risks and constraints

CRITICAL RULES:
- Only extract facts explicitly stated in the documents
- Do NOT infer or assume information
- Assign confidence scores based on evidence strength:
  * 1.0 = Multiple sources confirm
  * 0.7 = Single authoritative source
  * 0.5 = Mentioned but not detailed
  * 0.3 = Implied or inferred
- Always cite source document IDs
- If information is missing, mark as "unknown" with confidence 0.0

OUTPUT FORMAT:
Return valid JSON matching the provided schema.
"""

EXTRACTION_USER_PROMPT = """
Analyze the following technical documentation and extract structured facts.

Documents:
{documents}

Extract facts about:
- Technical stack
- Dependencies
- Deployment strategy
- Security/compliance
- Architecture
- Risks

For each fact, provide confidence score and source document IDs.
"""
```

### **Trade-offs**

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **LLM structured extraction** | ✅ Handles unstructured text<br>✅ Understands context<br>✅ Flexible | ❌ Expensive<br>❌ May hallucinate | ✅ **CHOSEN** |
| **Rule-based extraction** | ✅ Fast<br>✅ Cheap<br>✅ Deterministic | ❌ Brittle<br>❌ Limited to patterns | ❌ Rejected |
| **Hybrid (rules + LLM)** | ✅ Best of both | ❌ Complex<br>❌ Hard to maintain | ⚠️ Future consideration |

**Rationale:** Technical documentation is unstructured. LLM is necessary for semantic understanding. Confidence scores and evidence mapping mitigate hallucination risk.

**Cost Optimization:**
- Cache LLM responses (90% cost reduction on repeated analysis)
- Use cheaper model for initial pass, expensive model for validation
- Batch documents to reduce API calls

---

## 4. Questionnaire Agent

### **Primary Responsibility**
Identify gaps in extracted facts and generate prioritized questions.

### **Specific Tasks**
1. Analyze extracted facts
2. Check confidence scores
3. Identify missing critical information
4. Generate specific questions
5. Prioritize questions by importance
6. Map questions to missing evidence

### **Reasoning Process**

```
Input: extracted_facts + confidence_scores
↓
Identify gaps:
  - Facts with confidence < 0.5
  - Missing required fields
  - Contradictory information
  - Vague or incomplete data
↓
LLM Analysis:
  "You are a migration consultant conducting a discovery interview.
   
   Based on the extracted facts, identify what information is:
   - Missing entirely
   - Unclear or ambiguous
   - Low confidence
   - Critical for migration planning
   
   Generate specific, actionable questions to fill these gaps."
↓
Prioritize questions:
  Priority 1 (Critical): Blocks migration planning
  Priority 2 (High): Affects strategy decisions
  Priority 3 (Medium): Affects implementation details
  Priority 4 (Low): Nice to have
↓
Return: missing_questions + question_priorities
```

### **Prompt Engineering**

```python
QUESTIONNAIRE_SYSTEM_PROMPT = """
You are an experienced migration consultant conducting a discovery interview.

Your task is to identify gaps in the technical assessment and generate specific questions to fill those gaps.

QUESTION CATEGORIES:
1. Technical Stack: Missing versions, configurations, customizations
2. Dependencies: Undocumented libraries, internal dependencies
3. Deployment: CI/CD pipelines, deployment frequency, rollback procedures
4. Security: Authentication mechanisms, data encryption, compliance requirements
5. Architecture: Integration points, data flows, scalability constraints
6. Operations: Monitoring, logging, backup/recovery, disaster recovery

QUESTION QUALITY CRITERIA:
- Specific and actionable (not vague)
- Answerable by the application team
- Relevant to migration planning
- Prioritized by criticality

PRIORITY LEVELS:
- P1 (Critical): Blocks migration planning, must answer before proceeding
- P2 (High): Significantly affects migration strategy
- P3 (Medium): Affects implementation details
- P4 (Low): Nice to have, doesn't block progress

OUTPUT FORMAT:
Return JSON array of questions with priority and rationale.
"""

QUESTIONNAIRE_USER_PROMPT = """
Based on the following extracted facts and confidence scores, identify gaps and generate questions.

Extracted Facts:
{extracted_facts}

Confidence Scores:
{confidence_scores}

Generate specific questions for:
1. Facts with confidence < 0.5
2. Missing critical information
3. Unclear or ambiguous data
4. Contradictory information

For each question, provide:
- The question text
- Priority level (P1-P4)
- Rationale (why this question is important)
- Related fact (what fact this question helps clarify)
"""
```

### **Trade-offs**

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **LLM-generated questions** | ✅ Context-aware<br>✅ Specific<br>✅ Adaptive | ❌ May generate irrelevant questions | ✅ **CHOSEN** |
| **Template-based questions** | ✅ Fast<br>✅ Consistent | ❌ Generic<br>❌ Not context-aware | ❌ Rejected |
| **Hybrid (templates + LLM)** | ✅ Consistent + adaptive | ❌ Complex | ⚠️ Future consideration |

**Rationale:** Questions must be context-specific. LLM can understand what's missing based on extracted facts. Template questions are too generic.

**Quality Control:**
- Validate questions against a checklist
- Remove duplicate or similar questions
- Ensure questions are answerable
- Limit to top 20 questions (avoid overwhelming users)

---

## 5. Intake Draft Agent

### **Primary Responsibility**
Generate a comprehensive intake document from extracted facts and questions.

### **Specific Tasks**
1. Synthesize extracted facts
2. Organize into structured sections
3. Include evidence references
4. Highlight low-confidence areas
5. Include open questions
6. Add assumptions and constraints
7. Format for human review

### **Reasoning Process**

```
Input: extracted_facts + confidence_scores + missing_questions + evidence_map
↓
LLM Synthesis:
  "You are a technical writer creating a migration intake document.
   
   Synthesize the extracted facts into a clear, structured document
   that will be reviewed by stakeholders.
   
   Include:
   - Executive summary
   - Current state analysis
   - Technical stack details
   - Dependencies and integrations
   - Deployment and operations
   - Security and compliance
   - Risks and constraints
   - Open questions
   - Assumptions
   - Evidence references"
↓
Structure document:
  1. Executive Summary (2-3 paragraphs)
  2. Current State Analysis
  3. Technical Stack
  4. Dependencies & Integrations
  5. Deployment & Infrastructure
  6. Security & Compliance
  7. Risks & Constraints
  8. Open Questions (from questionnaire)
  9. Assumptions
  10. Evidence References
↓
Highlight areas needing attention:
  - Low confidence facts (< 0.5)
  - Missing critical information
  - Contradictions
  - High-risk items
↓
Return: intake_draft
```

### **Prompt Engineering**

```python
INTAKE_DRAFT_SYSTEM_PROMPT = """
You are an expert technical writer specializing in application modernization documentation.

Your task is to create a comprehensive, professional intake document that will be reviewed by:
- Technical stakeholders (architects, developers)
- Business stakeholders (product owners, executives)
- Migration team (consultants, engineers)

DOCUMENT REQUIREMENTS:
- Clear and concise language
- Structured with clear sections
- Evidence-based (cite sources)
- Highlight uncertainties
- Professional tone
- Actionable insights

SECTION GUIDELINES:

1. Executive Summary:
   - 2-3 paragraphs
   - High-level overview
   - Key findings
   - Critical risks

2. Current State Analysis:
   - Application purpose and users
   - Current architecture
   - Technology landscape
   - Operational characteristics

3. Technical Stack:
   - Languages and versions
   - Frameworks and libraries
   - Databases and data stores
   - Infrastructure and hosting

4. Dependencies & Integrations:
   - External dependencies
   - Internal dependencies
   - Integration points
   - Data flows

5. Deployment & Infrastructure:
   - Current deployment process
   - Infrastructure setup
   - Scaling approach
   - Monitoring and logging

6. Security & Compliance:
   - Authentication/authorization
   - Data protection
   - Compliance requirements
   - Security controls

7. Risks & Constraints:
   - Technical risks
   - Business constraints
   - Timeline considerations
   - Resource limitations

8. Open Questions:
   - Prioritized list
   - Rationale for each
   - Impact if unanswered

9. Assumptions:
   - What we're assuming
   - Confidence level
   - Impact if wrong

10. Evidence References:
    - Source documents
    - Confidence scores
    - Evidence mapping

FORMATTING:
- Use markdown
- Include tables for structured data
- Use bullet points for lists
- Highlight critical items with ⚠️
- Mark low-confidence items with ⚠️ Low Confidence
"""

INTAKE_DRAFT_USER_PROMPT = """
Create a comprehensive intake document based on the following information:

Extracted Facts:
{extracted_facts}

Confidence Scores:
{confidence_scores}

Open Questions:
{missing_questions}

Evidence Map:
{evidence_map}

Generate a professional intake document following the structure and guidelines provided.

CRITICAL REQUIREMENTS:
- Cite evidence for all facts
- Highlight low-confidence items (< 0.5)
- Include all open questions
- List assumptions clearly
- Professional, clear language
"""
```

### **Trade-offs**

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **LLM-generated document** | ✅ Natural language<br>✅ Context-aware<br>✅ Professional | ❌ May miss details<br>❌ Expensive | ✅ **CHOSEN** |
| **Template-based document** | ✅ Fast<br>✅ Consistent<br>✅ Complete | ❌ Rigid<br>❌ Not adaptive | ❌ Rejected |
| **Hybrid (template + LLM)** | ✅ Structure + flexibility | ❌ Complex | ⚠️ Future consideration |

**Rationale:** Intake document needs to be readable and context-aware. LLM can synthesize information naturally. Templates are too rigid for varied applications.

**Quality Control:**
- Validate all sections present
- Check evidence citations
- Verify confidence scores included
- Ensure questions are listed
- Review for clarity and completeness

---

## 6. Review/Validation Agent

### **Primary Responsibility**
Validate intake draft for contradictions, unsupported claims, and completeness.

### **Specific Tasks**
1. Check for contradictions
2. Verify evidence support
3. Validate completeness
4. Flag unsupported claims
5. Check confidence alignment
6. Generate review flags

### **Reasoning Process**

```
Input: intake_draft + extracted_facts + evidence_map
↓
Contradiction Check:
  - Compare facts within document
  - Check for conflicting statements
  - Verify consistency across sections
↓
Evidence Verification:
  - Check all claims have evidence
  - Verify confidence scores match evidence strength
  - Flag unsupported assertions
↓
Completeness Check:
  - Verify all required sections present
  - Check critical fields populated
  - Ensure questions are comprehensive
↓
LLM Analysis:
  "You are a quality assurance reviewer for technical documentation.
   
   Review the intake document for:
   - Internal contradictions
   - Unsupported claims
   - Missing critical information
   - Inconsistencies
   - Clarity issues
   
   Generate specific review flags for items needing attention."
↓
Return: validation_results + review_flags
```

### **Prompt Engineering**

```python
REVIEW_SYSTEM_PROMPT = """
You are a senior quality assurance reviewer specializing in technical documentation.

Your task is to review the intake document and identify issues that need attention before approval.

REVIEW CRITERIA:

1. Contradictions:
   - Conflicting statements within the document
   - Facts that don't align with evidence
   - Inconsistent terminology

2. Unsupported Claims:
   - Statements without evidence
   - High confidence without strong evidence
   - Assumptions presented as facts

3. Completeness:
   - Missing required sections
   - Incomplete critical information
   - Insufficient detail for decision-making

4. Clarity:
   - Ambiguous statements
   - Unclear terminology
   - Confusing structure

5. Consistency:
   - Inconsistent formatting
   - Inconsistent terminology
   - Inconsistent confidence levels

REVIEW FLAGS:
- CRITICAL: Blocks approval, must fix
- HIGH: Should fix before approval
- MEDIUM: Should address but not blocking
- LOW: Nice to fix, not critical

OUTPUT FORMAT:
Return JSON with:
- contradictions: list of contradictory statements
- unsupported_claims: list of claims without evidence
- completeness_issues: list of missing/incomplete items
- review_flags: list of all issues with severity
"""

REVIEW_USER_PROMPT = """
Review the following intake document for quality issues.

Intake Document:
{intake_draft}

Extracted Facts (for verification):
{extracted_facts}

Evidence Map (for verification):
{evidence_map}

Identify:
1. Contradictions or inconsistencies
2. Unsupported claims or assertions
3. Missing or incomplete information
4. Clarity or ambiguity issues

For each issue, provide:
- Issue description
- Severity (CRITICAL/HIGH/MEDIUM/LOW)
- Location in document
- Suggested fix
"""
```

### **Trade-offs**

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **LLM-based review** | ✅ Semantic understanding<br>✅ Context-aware<br>✅ Finds subtle issues | ❌ May miss obvious issues<br>❌ Expensive | ✅ **CHOSEN** |
| **Rule-based validation** | ✅ Fast<br>✅ Catches obvious issues<br>✅ Cheap | ❌ Misses semantic issues<br>❌ Brittle | ❌ Rejected |
| **Hybrid (rules + LLM)** | ✅ Comprehensive<br>✅ Fast + thorough | ❌ Complex | ✅ **RECOMMENDED** |

**Rationale:** Semantic review requires LLM. However, combine with rule-based checks for obvious issues (missing sections, broken links, etc.).

**Hybrid Approach:**
```python
# Rule-based checks (fast, cheap)
def rule_based_validation(intake_draft):
    issues = []
    
    # Check required sections
    required_sections = [
        "Executive Summary",
        "Technical Stack",
        "Dependencies",
        "Security & Compliance"
    ]
    for section in required_sections:
        if section not in intake_draft:
            issues.append({
                "type": "missing_section",
                "severity": "CRITICAL",
                "description": f"Missing required section: {section}"
            })
    
    # Check evidence citations
    if "Evidence References" not in intake_draft:
        issues.append({
            "type": "missing_evidence",
            "severity": "HIGH",
            "description": "No evidence references section"
        })
    
    return issues

# LLM-based checks (semantic, expensive)
async def llm_based_validation(intake_draft, extracted_facts):
    # Check for contradictions, unsupported claims, etc.
    pass

# Combined validation
async def validate_intake(intake_draft, extracted_facts):
    # Fast rule-based checks first
    rule_issues = rule_based_validation(intake_draft)
    
    # If critical issues found, return immediately
    if any(issue["severity"] == "CRITICAL" for issue in rule_issues):
        return {"issues": rule_issues, "status": "failed"}
    
    # Semantic LLM checks
    llm_issues = await llm_based_validation(intake_draft, extracted_facts)
    
    return {
        "issues": rule_issues + llm_issues,
        "status": "passed" if not llm_issues else "needs_review"
    }
```

---

## 7. Migration Planning Agent

### **Primary Responsibility**
Generate comprehensive migration plan with cloud recommendations.

### **Specific Tasks**
1. Analyze approved intake document
2. Determine migration strategy
3. Create phased approach
4. Recommend cloud infrastructure
5. Map current → target architecture
6. Define data migration strategy
7. Create testing strategy
8. Define rollback plan
9. Identify risks and mitigations
10. Estimate timeline and resources

### **Reasoning Process**

```
Input: intake_draft (approved) + extracted_facts
↓
Strategy Selection:
  IF legacy tech + tight coupling:
    → Re-architect (modernize)
  ELIF modern tech + loose coupling:
    → Re-platform (lift-and-shift with optimization)
  ELIF simple app + time-sensitive:
    → Lift-and-shift (minimal changes)
↓
Cloud Provider Selection:
  Consider:
  - Current infrastructure
  - Compliance requirements
  - Team expertise
  - Cost constraints
  
  Recommend: AWS / Azure / GCP
↓
LLM Planning:
  "You are a cloud migration architect.
   
   Based on the approved intake document, create a comprehensive
   migration plan including:
   - Migration strategy and rationale
   - Phased approach with timeline
   - Cloud infrastructure recommendations
   - Service mapping (current → target)
   - Data migration strategy
   - Testing and validation approach
   - Rollback procedures
   - Risk mitigation
   - Success criteria"
↓
Structure plan:
  1. Migration Strategy
  2. Phased Approach (with timeline)
  3. Cloud Infrastructure Recommendations
  4. Service Mapping
  5. Data Migration Strategy
  6. Testing Strategy
  7. Rollback Plan
  8. Risk Mitigation
  9. Dependencies & Prerequisites
  10. Success Criteria
  11. Cost Estimate
↓
Return: migration_plan
```

### **Prompt Engineering**

```python
MIGRATION_PLANNING_SYSTEM_PROMPT = """
You are a senior cloud migration architect with expertise in AWS, Azure, and GCP.

Your task is to create a comprehensive, actionable migration plan based on an approved intake document.

MIGRATION STRATEGIES:

1. Lift-and-Shift (Rehost):
   - Minimal changes
   - Fast migration
   - Use when: Time-sensitive, simple app, low risk tolerance
   - Cloud services: EC2/VMs, managed databases

2. Re-platform (Lift-Tinker-Shift):
   - Some optimization
   - Moderate changes
   - Use when: Want cloud benefits, moderate complexity
   - Cloud services: Managed services, containers

3. Re-architect (Modernize):
   - Significant changes
   - Cloud-native
   - Use when: Legacy tech, scalability needs, long-term investment
   - Cloud services: Serverless, microservices, managed services

CLOUD PROVIDER SELECTION:
- AWS: Broadest services, mature ecosystem
- Azure: Microsoft stack, enterprise integration
- GCP: Data/ML focus, Kubernetes-native

PLAN STRUCTURE:

1. Migration Strategy:
   - Chosen strategy (lift-and-shift / re-platform / re-architect)
   - Rationale
   - Trade-offs

2. Phased Approach:
   - Phase 1: Assessment & Planning (2-4 weeks)
   - Phase 2: Infrastructure Setup (2-4 weeks)
   - Phase 3: Application Migration (4-8 weeks)
   - Phase 4: Testing & Validation (2-4 weeks)
   - Phase 5: Cutover & Go-Live (1-2 weeks)
   - Phase 6: Post-Migration Optimization (ongoing)

3. Cloud Infrastructure:
   - Compute (EC2, Lambda, App Service, etc.)
   - Storage (S3, Blob Storage, Cloud Storage)
   - Database (RDS, Aurora, Cosmos DB, Cloud SQL)
   - Networking (VPC, Load Balancers, CDN)
   - Security (IAM, KMS, Security Groups)
   - Monitoring (CloudWatch, Azure Monitor, Cloud Monitoring)

4. Service Mapping:
   - Current service → Target service
   - Configuration changes
   - Data migration approach

5. Data Migration:
   - Strategy (online/offline, incremental/full)
   - Tools (AWS DMS, Azure Data Factory, etc.)
   - Validation approach
   - Rollback procedure

6. Testing Strategy:
   - Unit testing
   - Integration testing
   - Performance testing
   - Security testing
   - User acceptance testing

7. Rollback Plan:
   - Rollback triggers
   - Rollback procedure
   - Data recovery
   - Communication plan

8. Risk Mitigation:
   - Identified risks
   - Mitigation strategies
   - Contingency plans

9. Success Criteria:
   - Performance metrics
   - Availability targets
   - Cost targets
   - User satisfaction

CRITICAL REQUIREMENTS:
- Base recommendations on intake document facts
- Consider compliance requirements
- Account for team expertise
- Provide realistic timelines
- Include cost estimates
- Be specific (not generic)
"""

MIGRATION_PLANNING_USER_PROMPT = """
Create a comprehensive migration plan based on the following approved intake document.

Intake Document:
{intake_draft}

Technical Facts:
{extracted_facts}

Generate a detailed migration plan that includes:
1. Migration strategy with rationale
2. Phased approach with timeline estimates
3. Cloud infrastructure recommendations (specific services)
4. Service mapping (current → target)
5. Data migration strategy
6. Testing and validation approach
7. Rollback procedures
8. Risk mitigation strategies
9. Dependencies and prerequisites
10. Success criteria
11. Cost estimate (rough order of magnitude)

CRITICAL REQUIREMENTS:
- Be specific (not generic)
- Base on actual intake facts
- Consider compliance requirements
- Provide realistic timelines
- Include cost estimates
- Address identified risks
"""
```

### **Trade-offs**

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **LLM-generated plan** | ✅ Context-aware<br>✅ Comprehensive<br>✅ Adaptive | ❌ May be generic<br>❌ Expensive | ✅ **CHOSEN** |
| **Template-based plan** | ✅ Fast<br>✅ Consistent<br>✅ Complete | ❌ Generic<br>❌ Not adaptive | ❌ Rejected |
| **Hybrid (template + LLM)** | ✅ Structure + specificity | ❌ Complex | ✅ **RECOMMENDED** |

**Rationale:** Migration plans must be context-specific. LLM can tailor recommendations based on intake facts. However, use templates for structure and checklists.

**Hybrid Approach:**
```python
# Template provides structure
MIGRATION_PLAN_TEMPLATE = {
    "strategy": {
        "type": "",  # LLM fills
        "rationale": "",  # LLM fills
        "trade_offs": ""  # LLM fills
    },
    "phases": [
        {
            "name": "Assessment & Planning",
            "duration_weeks": 0,  # LLM estimates
            "activities": [],  # LLM fills
            "deliverables": [],  # LLM fills
            "dependencies": []  # LLM fills
        },
        # ... more phases
    ],
    "cloud_recommendations": {
        "provider": "",  # LLM selects
        "compute": [],  # LLM recommends
        "storage": [],  # LLM recommends
        "database": [],  # LLM recommends
        "networking": [],  # LLM recommends
        "security": [],  # LLM recommends
        "monitoring": []  # LLM recommends
    },
    # ... more sections
}

# LLM fills template with specific recommendations
async def generate_migration_plan(intake_draft, extracted_facts):
    prompt = f"""
    Fill the migration plan template with specific recommendations
    based on the intake document.
    
    Template: {MIGRATION_PLAN_TEMPLATE}
    Intake: {intake_draft}
    Facts: {extracted_facts}
    """
    
    plan = await llm.generate_structured(prompt, MIGRATION_PLAN_TEMPLATE)
    return plan
```

---

## Summary: Agent Orchestration Trade-offs

| Agent | LLM Required? | Cost | Complexity | Accuracy | Decision |
|-------|---------------|------|------------|----------|----------|
| **Supervisor** | ❌ No | Free | Low | 100% | Logic-based |
| **Context Retrieval** | ❌ No | Free | Medium | 100% | API + parsing |
| **Extraction** | ✅ Yes | $$$ | Medium | 85-95% | LLM + confidence scores |
| **Questionnaire** | ✅ Yes | $$ | Low | 90% | LLM-generated |
| **Intake Draft** | ✅ Yes | $$$ | Medium | 90% | LLM synthesis |
| **Review** | ✅ Hybrid | $$ | Medium | 95% | Rules + LLM |
| **Migration Planning** | ✅ Hybrid | $$$ | High | 85% | Template + LLM |

## Cost Optimization Strategies

1. **Caching**: Cache LLM responses (90% cost reduction)
2. **Batch Processing**: Combine multiple documents in one call
3. **Model Selection**: Use cheaper models for simple tasks
4. **Prompt Optimization**: Shorter prompts = lower cost
5. **Structured Output**: Use JSON mode to reduce tokens
6. **Fallback Models**: Use Gemini when OpenAI fails

## Quality Assurance Strategies

1. **Confidence Scores**: Track confidence for all extracted facts
2. **Evidence Mapping**: Link facts to source documents
3. **Human Review**: Mandatory review before migration planning
4. **Validation Agents**: Automated quality checks
5. **Traceability**: LangSmith traces for debugging

This analysis provides the foundation for finalizing the agent orchestration design!