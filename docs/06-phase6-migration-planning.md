# Phase 6: Migration Planning Agent & Final Validation

## Overview

Phase 6 implements the Migration Planning Agent that generates a comprehensive migration strategy and cloud infrastructure recommendations based on the reviewed intake document. This is the final agent in the workflow before output generation.

## Objectives

1. **Implement Migration Planning Agent**
   - Hybrid approach (template + LLM)
   - Select appropriate migration strategy
   - Generate phased migration plan
   - Provide cloud infrastructure recommendations
   - Include rollback strategy and risk mitigation

2. **Implement Final Validation**
   - Validate migration plan completeness
   - Check for logical consistency
   - Verify all requirements addressed
   - Flag any remaining gaps

3. **Generate Structured Output**
   - Export migration plan in multiple formats
   - Include all evidence references
   - Provide execution timeline
   - Add cost estimates

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  LangGraph Workflow                          │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │      Migration Planning Agent Node                      │ │
│  │  - Select migration strategy                            │ │
│  │  - Generate phased plan                                 │ │
│  │  - Cloud recommendations                                │ │
│  │  - Risk mitigation                                      │ │
│  └────────────┬───────────────────────────────────────────┘ │
│               │                                              │
│  ┌────────────▼───────────────────────────────────────────┐ │
│  │         Final Validation Node                           │ │
│  │  - Validate completeness                                │ │
│  │  - Check consistency                                    │ │
│  │  - Verify requirements                                  │ │
│  └────────────┬───────────────────────────────────────────┘ │
│               │                                              │
│               ▼                                              │
│          Complete Workflow                                   │
└──────────────────────────────────────────────────────────────┘
```

## Implementation

### 1. Migration Strategy Templates

```python
# backend/app/agents/migration_templates.py
from typing import Dict, Any
from enum import Enum

class MigrationStrategy(str, Enum):
    REHOST = "rehost"  # Lift-and-shift
    REPLATFORM = "replatform"  # Containerize + managed services
    REFACTOR = "refactor"  # Rearchitecture

REHOST_TEMPLATE = {
    "strategy": "Rehost (Lift-and-Shift)",
    "description": "Migrate application to cloud with minimal changes",
    "phases": [
        {
            "name": "Preparation",
            "duration_weeks": 2,
            "tasks": [
                "Set up cloud account and networking",
                "Configure IAM roles and policies",
                "Provision compute instances",
                "Set up monitoring and logging",
                "Create backup and disaster recovery plan"
            ]
        },
        {
            "name": "Migration",
            "duration_weeks": 3,
            "tasks": [
                "Migrate databases with minimal downtime",
                "Deploy application to cloud instances",
                "Configure load balancers and auto-scaling",
                "Migrate data and files",
                "Update DNS and routing"
            ]
        },
        {
            "name": "Validation",
            "duration_weeks": 2,
            "tasks": [
                "Run integration tests",
                "Perform load testing",
                "Validate data integrity",
                "Monitor performance metrics",
                "Train operations team"
            ]
        }
    ],
    "cloud_services": {
        "compute": ["EC2", "Auto Scaling Groups"],
        "storage": ["EBS", "S3"],
        "database": ["RDS", "ElastiCache"],
        "networking": ["VPC", "ELB", "Route 53"],
        "monitoring": ["CloudWatch", "CloudTrail"]
    },
    "pros": [
        "Fastest migration path",
        "Lowest risk",
        "Minimal code changes",
        "Quick time to value"
    ],
    "cons": [
        "Limited cloud optimization",
        "May not leverage cloud-native features",
        "Potential for higher long-term costs"
    ]
}

REPLATFORM_TEMPLATE = {
    "strategy": "Replatform (Containerize + Managed Services)",
    "description": "Containerize application and use managed cloud services",
    "phases": [
        {
            "name": "Preparation",
            "duration_weeks": 3,
            "tasks": [
                "Containerize application components",
                "Set up container registry",
                "Configure Kubernetes/ECS cluster",
                "Design service mesh architecture",
                "Set up CI/CD pipeline for containers"
            ]
        },
        {
            "name": "Migration",
            "duration_weeks": 4,
            "tasks": [
                "Migrate to managed database services",
                "Deploy containerized application",
                "Configure service discovery and load balancing",
                "Implement secrets management",
                "Set up auto-scaling policies"
            ]
        },
        {
            "name": "Validation",
            "duration_weeks": 2,
            "tasks": [
                "Run comprehensive testing",
                "Validate container orchestration",
                "Monitor resource utilization",
                "Optimize container configurations",
                "Document operational procedures"
            ]
        }
    ],
    "cloud_services": {
        "compute": ["ECS/EKS", "Fargate"],
        "storage": ["S3", "EFS"],
        "database": ["RDS", "DynamoDB", "ElastiCache"],
        "networking": ["VPC", "ALB", "API Gateway"],
        "monitoring": ["CloudWatch", "X-Ray", "Container Insights"]
    },
    "pros": [
        "Better cloud optimization",
        "Improved scalability",
        "Reduced operational overhead",
        "Modern deployment practices"
    ],
    "cons": [
        "Requires containerization effort",
        "Learning curve for container orchestration",
        "More complex than rehost"
    ]
}

REFACTOR_TEMPLATE = {
    "strategy": "Refactor (Cloud-Native Rearchitecture)",
    "description": "Redesign application for cloud-native architecture",
    "phases": [
        {
            "name": "Design",
            "duration_weeks": 4,
            "tasks": [
                "Design microservices architecture",
                "Define API contracts",
                "Plan data migration strategy",
                "Design event-driven workflows",
                "Create security architecture"
            ]
        },
        {
            "name": "Development",
            "duration_weeks": 12,
            "tasks": [
                "Refactor monolith to microservices",
                "Implement serverless functions",
                "Build event-driven integrations",
                "Implement cloud-native patterns",
                "Develop comprehensive test suite"
            ]
        },
        {
            "name": "Migration",
            "duration_weeks": 4,
            "tasks": [
                "Gradual service migration",
                "Data migration with zero downtime",
                "Traffic routing and canary deployments",
                "Monitor and optimize performance",
                "Decommission legacy components"
            ]
        }
    ],
    "cloud_services": {
        "compute": ["Lambda", "ECS/EKS", "Fargate"],
        "storage": ["S3", "DynamoDB", "EFS"],
        "database": ["Aurora Serverless", "DynamoDB"],
        "messaging": ["SQS", "SNS", "EventBridge"],
        "networking": ["API Gateway", "ALB", "CloudFront"],
        "monitoring": ["CloudWatch", "X-Ray", "OpenTelemetry"]
    },
    "pros": [
        "Maximum cloud optimization",
        "Best scalability and resilience",
        "Lower long-term operational costs",
        "Modern architecture patterns"
    ],
    "cons": [
        "Longest timeline",
        "Highest initial cost",
        "Requires significant development effort",
        "Higher complexity"
    ]
}
```

### 2. Migration Planning Agent

```python
# backend/app/agents/migration_planning_agent.py
from typing import Dict, Any, List
import logging
from datetime import datetime
from langsmith import traceable

from ..llm.provider import LLMProvider
from ..orchestration.state import MigrationState
from .migration_templates import (
    MigrationStrategy,
    REHOST_TEMPLATE,
    REPLATFORM_TEMPLATE,
    REFACTOR_TEMPLATE
)

logger = logging.getLogger(__name__)

class MigrationPlanningAgent:
    """
    Migration Planning Agent - Hybrid approach (template + LLM).
    
    Responsibilities:
    - Select appropriate migration strategy
    - Generate phased migration plan
    - Provide cloud infrastructure recommendations
    - Include rollback strategy and risk mitigation
    """
    
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
        self.agent_name = "migration_planning_agent"
    
    @traceable(name="migration_planning_agent", run_type="chain")
    async def execute(self, state: MigrationState) -> Dict[str, Any]:
        """
        Execute migration planning.
        
        Args:
            state: Current workflow state
            
        Returns:
            State patch with migration plan
        """
        
        logger.info(f"[{self.agent_name}] Starting migration planning")
        
        try:
            # Verify human review completed
            if not state.get("human_reviewed"):
                raise ValueError("Migration planning requires human-reviewed intake")
            
            intake_draft = state.get("intake_draft", {})
            extracted_facts = state.get("extracted_facts", {})
            
            # Phase 1: Select migration strategy (template-based)
            strategy = self._select_migration_strategy(intake_draft, extracted_facts)
            template = self._get_strategy_template(strategy)
            
            logger.info(f"[{self.agent_name}] Selected strategy: {strategy}")
            
            # Phase 2: Customize plan with LLM
            customized_plan = await self._customize_migration_plan(
                template,
                intake_draft,
                extracted_facts
            )
            
            # Phase 3: Generate cloud recommendations
            cloud_recommendations = await self._generate_cloud_recommendations(
                customized_plan,
                extracted_facts
            )
            
            # Phase 4: Add risk mitigation and rollback
            final_plan = self._add_risk_mitigation(
                customized_plan,
                cloud_recommendations,
                extracted_facts
            )
            
            logger.info(f"[{self.agent_name}] Migration plan generated")
            
            # Return state patch
            return {
                "migration_plan": final_plan,
                "phase": "VALIDATION",
                "trace_metadata": {
                    **state.get("trace_metadata", {}),
                    "migration_planning": {
                        "strategy": strategy,
                        "total_duration_weeks": sum(p["duration_weeks"] for p in final_plan["phases"]),
                        "cloud_services_count": len(final_plan.get("cloud_recommendations", {})),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            }
        
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error: {str(e)}")
            return {
                "phase": "ERROR",
                "last_error": f"Migration planning failed: {str(e)}",
                "error_log": [
                    *state.get("error_log", []),
                    {
                        "agent": self.agent_name,
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ]
            }
    
    def _select_migration_strategy(
        self,
        intake_draft: Dict[str, Any],
        extracted_facts: Dict[str, List[Dict[str, Any]]]
    ) -> MigrationStrategy:
        """
        Select migration strategy using decision matrix.
        
        Decision factors:
        - Application complexity
        - Modernization potential
        - Risk tolerance
        - Timeline constraints
        - Budget constraints
        """
        
        # Calculate complexity score (0-10)
        complexity_score = self._calculate_complexity(extracted_facts)
        
        # Calculate modernization potential (0-10)
        modernization_score = self._calculate_modernization_potential(extracted_facts)
        
        # Calculate risk score (0-10)
        risk_score = self._calculate_risk(extracted_facts)
        
        logger.info(
            f"Strategy selection scores - "
            f"Complexity: {complexity_score}, "
            f"Modernization: {modernization_score}, "
            f"Risk: {risk_score}"
        )
        
        # Decision matrix
        if complexity_score < 3 and risk_score < 3:
            return MigrationStrategy.REHOST
        
        elif complexity_score < 7 and modernization_score > 5:
            return MigrationStrategy.REPLATFORM
        
        elif modernization_score > 7:
            return MigrationStrategy.REFACTOR
        
        else:
            # Default to replatform (balanced approach)
            return MigrationStrategy.REPLATFORM
    
    def _calculate_complexity(self, extracted_facts: Dict[str, List[Dict[str, Any]]]) -> int:
        """Calculate application complexity score (0-10)"""
        
        score = 0
        
        # Check for monolithic architecture
        arch_facts = extracted_facts.get("architectural_decisions", [])
        if any("monolith" in fact.get("fact", "").lower() for fact in arch_facts):
            score += 3
        
        # Check for multiple databases
        dep_facts = extracted_facts.get("dependencies", [])
        db_count = sum(1 for fact in dep_facts if "database" in fact.get("category", "").lower())
        if db_count > 1:
            score += 2
        
        # Check for legacy dependencies
        tech_facts = extracted_facts.get("technical_stack", [])
        if any("legacy" in fact.get("fact", "").lower() or "deprecated" in fact.get("fact", "").lower() for fact in tech_facts):
            score += 2
        
        # Check for custom protocols
        if any("custom" in fact.get("fact", "").lower() and "protocol" in fact.get("fact", "").lower() for fact in dep_facts):
            score += 2
        
        # Check for stateful architecture
        if any("stateful" in fact.get("fact", "").lower() for fact in arch_facts):
            score += 1
        
        return min(score, 10)
    
    def _calculate_modernization_potential(self, extracted_facts: Dict[str, List[Dict[str, Any]]]) -> int:
        """Calculate modernization potential score (0-10)"""
        
        score = 0
        
        tech_facts = extracted_facts.get("technical_stack", [])
        arch_facts = extracted_facts.get("architectural_decisions", [])
        
        # Modern language/framework
        if any(lang in fact.get("fact", "").lower() for fact in tech_facts for lang in ["java 11", "java 17", "python 3", "node.js", "go"]):
            score += 3
        
        # Containerization ready
        if any("docker" in fact.get("fact", "").lower() or "container" in fact.get("fact", "").lower() for fact in tech_facts):
            score += 2
        
        # Microservices or modular architecture
        if any("microservice" in fact.get("fact", "").lower() or "modular" in fact.get("fact", "").lower() for fact in arch_facts):
            score += 3
        
        # API-driven
        if any("rest" in fact.get("fact", "").lower() or "api" in fact.get("fact", "").lower() for fact in arch_facts):
            score += 2
        
        return min(score, 10)
    
    def _calculate_risk(self, extracted_facts: Dict[str, List[Dict[str, Any]]]) -> int:
        """Calculate migration risk score (0-10)"""
        
        score = 0
        
        risk_facts = extracted_facts.get("known_risks", [])
        
        # Known technical debt
        if len(risk_facts) > 5:
            score += 3
        
        # Deprecated dependencies
        if any("deprecated" in fact.get("fact", "").lower() for fact in risk_facts):
            score += 2
        
        # Performance issues
        if any("performance" in fact.get("fact", "").lower() or "bottleneck" in fact.get("fact", "").lower() for fact in risk_facts):
            score += 2
        
        # Security concerns
        sec_facts = extracted_facts.get("security_compliance", [])
        if any(fact.get("confidence", 1.0) < 0.5 for fact in sec_facts):
            score += 3
        
        return min(score, 10)
    
    def _get_strategy_template(self, strategy: MigrationStrategy) -> Dict[str, Any]:
        """Get template for selected strategy"""
        
        templates = {
            MigrationStrategy.REHOST: REHOST_TEMPLATE,
            MigrationStrategy.REPLATFORM: REPLATFORM_TEMPLATE,
            MigrationStrategy.REFACTOR: REFACTOR_TEMPLATE
        }
        
        return templates[strategy]
    
    async def _customize_migration_plan(
        self,
        template: Dict[str, Any],
        intake_draft: Dict[str, Any],
        extracted_facts: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Customize migration plan template using LLM"""
        
        document_text = intake_draft.get("document_text", "")
        
        prompt = f"""You are a cloud migration architect customizing a migration plan.

MIGRATION STRATEGY TEMPLATE:
{template["strategy"]}

INTAKE DOCUMENT:
{document_text[:3000]}

CUSTOMIZE THE MIGRATION PLAN:

Based on the intake document, customize the template with:
1. Specific technical details from the application
2. Concrete infrastructure requirements
3. Detailed task breakdowns
4. Realistic timelines based on complexity
5. Specific cloud services for this application

For each phase:
- Add application-specific tasks
- Adjust duration based on complexity
- Include specific technologies mentioned in intake
- Add dependencies and prerequisites

OUTPUT FORMAT:
{{
  "strategy": "{template["strategy"]}",
  "rationale": "Why this strategy was chosen for this specific application",
  "phases": [
    {{
      "name": "Preparation",
      "duration_weeks": 2,
      "tasks": ["Specific task 1", "Specific task 2"],
      "dependencies": ["Prerequisite 1"],
      "success_criteria": ["Criterion 1"]
    }}
  ],
  "total_duration_weeks": 7,
  "estimated_effort_person_weeks": 20
}}
"""
        
        result = await self.llm.generate_structured(
            prompt=prompt,
            schema=self._get_plan_schema(),
            temperature=0.2,
            metadata={
                "agent": self.agent_name,
                "task": "plan_customization"
            }
        )
        
        return result
    
    async def _generate_cloud_recommendations(
        self,
        migration_plan: Dict[str, Any],
        extracted_facts: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Generate specific cloud infrastructure recommendations"""
        
        tech_facts = extracted_facts.get("technical_stack", [])
        dep_facts = extracted_facts.get("dependencies", [])
        
        # Build context for recommendations
        tech_summary = "\n".join([f"- {fact['fact']}" for fact in tech_facts[:10]])
        dep_summary = "\n".join([f"- {fact['fact']}" for fact in dep_facts[:10]])
        
        prompt = f"""You are a cloud architect recommending specific AWS services.

TECHNICAL STACK:
{tech_summary}

DEPENDENCIES:
{dep_summary}

MIGRATION STRATEGY:
{migration_plan["strategy"]}

PROVIDE SPECIFIC CLOUD RECOMMENDATIONS:

For each category, recommend specific AWS services with justification:

1. **Compute**: EC2, ECS, EKS, Lambda, Fargate
2. **Storage**: S3, EBS, EFS
3. **Database**: RDS, DynamoDB, Aurora, ElastiCache
4. **Networking**: VPC, ALB, NLB, API Gateway, CloudFront
5. **Security**: IAM, KMS, Secrets Manager, WAF
6. **Monitoring**: CloudWatch, X-Ray, CloudTrail
7. **CI/CD**: CodePipeline, CodeBuild, CodeDeploy

For each recommendation:
- Specify exact service and configuration
- Explain why it's appropriate
- Include sizing estimates
- Provide cost estimate (rough monthly)

OUTPUT FORMAT:
{{
  "compute": {{
    "service": "ECS with Fargate",
    "justification": "Application is containerized, Fargate removes server management",
    "configuration": "2 vCPU, 4GB RAM per task",
    "estimated_monthly_cost": "$150"
  }},
  ...
}}
"""
        
        result = await self.llm.generate_structured(
            prompt=prompt,
            schema=self._get_recommendations_schema(),
            temperature=0.2,
            metadata={
                "agent": self.agent_name,
                "task": "cloud_recommendations"
            }
        )
        
        return result
    
    def _add_risk_mitigation(
        self,
        migration_plan: Dict[str, Any],
        cloud_recommendations: Dict[str, Any],
        extracted_facts: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Add risk mitigation and rollback strategy"""
        
        risk_facts = extracted_facts.get("known_risks", [])
        
        return {
            **migration_plan,
            "cloud_recommendations": cloud_recommendations,
            "rollback_strategy": {
                "approach": "Blue-green deployment with traffic shifting",
                "steps": [
                    "Maintain parallel legacy environment during migration",
                    "Use DNS/load balancer for traffic routing",
                    "Monitor key metrics during cutover",
                    "Immediate rollback capability via traffic shift",
                    "Keep legacy environment for 30 days post-migration"
                ],
                "rollback_time": "< 5 minutes"
            },
            "risk_mitigation": [
                {
                    "risk": risk["fact"],
                    "severity": "HIGH" if risk.get("confidence", 1.0) < 0.5 else "MEDIUM",
                    "mitigation": f"Address during {migration_plan['phases'][0]['name']} phase"
                }
                for risk in risk_facts[:5]
            ],
            "success_metrics": [
                "Zero data loss during migration",
                "< 1 hour downtime",
                "Performance within 10% of baseline",
                "All functional tests passing",
                "Security compliance maintained"
            ]
        }
    
    def _get_plan_schema(self) -> Dict[str, Any]:
        """Get JSON schema for migration plan"""
        return {
            "type": "object",
            "properties": {
                "strategy": {"type": "string"},
                "rationale": {"type": "string"},
                "phases": {"type": "array"},
                "total_duration_weeks": {"type": "integer"},
                "estimated_effort_person_weeks": {"type": "integer"}
            },
            "required": ["strategy", "phases"]
        }
    
    def _get_recommendations_schema(self) -> Dict[str, Any]:
        """Get JSON schema for cloud recommendations"""
        return {
            "type": "object",
            "properties": {
                "compute": {"type": "object"},
                "storage": {"type": "object"},
                "database": {"type": "object"},
                "networking": {"type": "object"},
                "security": {"type": "object"},
                "monitoring": {"type": "object"}
            }
        }
```

### 3. Final Validation

```python
# backend/app/orchestration/final_validation.py
from typing import Dict, Any
import logging
from datetime import datetime

from ..orchestration.state import MigrationState

logger = logging.getLogger(__name__)

async def validate_migration_plan(state: MigrationState) -> Dict[str, Any]:
    """
    Final validation of migration plan.
    
    Checks:
    - All required sections present
    - Logical consistency
    - Completeness
    - Actionability
    """
    
    logger.info("Running final validation")
    
    migration_plan = state.get("migration_plan", {})
    
    validation_results = {
        "is_valid": True,
        "errors": [],
        "warnings": [],
        "validated_at": datetime.utcnow().isoformat()
    }
    
    # Check required sections
    required_sections = ["strategy", "phases", "cloud_recommendations", "rollback_strategy"]
    for section in required_sections:
        if section not in migration_plan:
            validation_results["errors"].append(f"Missing required section: {section}")
            validation_results["is_valid"] = False
    
    # Check phases
    if "phases" in migration_plan:
        if len(migration_plan["phases"]) < 2:
            validation_results["warnings"].append("Migration plan should have at least 2 phases")
        
        for phase in migration_plan["phases"]:
            if not phase.get("tasks"):
                validation_results["errors"].append(f"Phase '{phase.get('name')}' has no tasks")
                validation_results["is_valid"] = False
    
    # Check cloud recommendations
    if "cloud_recommendations" in migration_plan:
        if not migration_plan["cloud_recommendations"]:
            validation_results["warnings"].append("No cloud service recommendations provided")
    
    logger.info(f"Validation complete: {'PASS' if validation_results['is_valid'] else 'FAIL'}")
    
    return {
        "validation_results": validation_results,
        "phase": "COMPLETE" if validation_results["is_valid"] else "ERROR"
    }
```

## Testing Phase 6

```python
# tests/test_migration_planning.py
import pytest

@pytest.mark.asyncio
async def test_migration_planning_agent(mock_llm_provider, mock_state_reviewed):
    """Test migration planning agent"""
    
    from backend.app.agents.migration_planning_agent import MigrationPlanningAgent
    
    agent = MigrationPlanningAgent(mock_llm_provider)
    result = await agent.execute(mock_state_reviewed)
    
    assert "migration_plan" in result
    assert result["phase"] == "VALIDATION"
    assert "strategy" in result["migration_plan"]
    assert "phases" in result["migration_plan"]
    assert "cloud_recommendations" in result["migration_plan"]

@pytest.mark.asyncio
async def test_strategy_selection():
    """Test migration strategy selection logic"""
    
    from backend.app.agents.migration_planning_agent import MigrationPlanningAgent
    
    agent = MigrationPlanningAgent(mock_llm_provider)
    
    # Test rehost selection (low complexity, low risk)
    strategy = agent._select_migration_strategy(
        intake_draft={"complexity": "low"},
        extracted_facts={"technical_stack": [], "known_risks": []}
    )
    assert strategy == "rehost"

@pytest.mark.asyncio
async def test_final_validation(mock_state_with_plan):
    """Test final validation"""
    
    from backend.app.orchestration.final_validation import validate_migration_plan
    
    result = await validate_migration_plan(mock_state_with_plan)
    
    assert "validation_results" in result
    assert result["validation_results"]["is_valid"] == True
```

## Success Criteria

- ✅ Migration Planning Agent selects appropriate strategy
- ✅ Customized migration plan generated
- ✅ Cloud recommendations are specific and justified
- ✅ Rollback strategy included
- ✅ Risk mitigation addressed
- ✅ Final validation passes
- ✅ Complete workflow traced in LangSmith

## Next Steps

Proceed to **Phase 7: Frontend UI with IBM Carbon Design System** to build the user interface.