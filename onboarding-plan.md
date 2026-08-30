# Agent Onboarding Plan — IBM Migration Copilot

**Purpose**: This plan onboards a new AI agent (Bob / any AI coding agent) onto the IBM Migration Copilot project. It captures everything discovered from reading all documentation, bug history, architecture decisions, coding standards, and project state. The goal is: "Read this plan + the listed files → be fully productive immediately."

**Project Status**: ✅ STABLE — Phases 1–5 complete. Ready for Phase 6.

> ⚠️ **Correction from initial plan**: Phase 5 is FULLY IMPLEMENTED (not just the next target). Both intake_draft_agent.py (425 lines), review_validation_agent.py (492 lines), and HumanReview.jsx (305 lines) are production-ready. Phase 6 (Migration Planning Agent) is the true next target — it is a confirmed stub. See Sub-Task 5 for detail.

---

## Top-Level Overview

The **IBM Migration Copilot** is an enterprise-grade Agentic AI application built to automate cloud migration planning. It ingests project files and Confluence documentation, extracts structured facts via LLM, generates targeted questionnaires, drafts intake documents, and ultimately produces a cloud migration strategy — all through a supervisor-led, multi-agent LangGraph workflow with real-time SSE streaming to a React/IBM Carbon frontend.

**Tech Stack Summary**:
- **Backend**: Python 3.10+, FastAPI, LangGraph 0.0.20, LangChain 0.1.4, OpenAI / Gemini (with fallback), Redis (state), Qdrant (vectors), LangSmith (tracing)
- **Frontend**: React 18.2, IBM Carbon Design System, Vite 5, Axios, SSE hooks
- **Infrastructure**: Podman (Redis + Qdrant containers)
- **Key Files**: `backend/app/orchestration/`, `backend/app/agents/`, `backend/app/providers/`, `frontend/src/pages/`

**Scope**: This plan covers what an agent needs to know before touching any code — mental model, verified current state, mandatory rules, patterns, and where everything lives.

---

## Sub-Task 1: Understand Project Identity & Purpose

**Intent**: Establish a clear mental model of *what this project is* and *why it exists*, so every code decision is grounded in the correct domain context.

**Expected Outcomes**:
- Agent can explain the system end-to-end without referencing documentation.
- Agent understands the IBM enterprise context (IBM Carbon UI, IBM Context Studio MCP, enterprise migration use case).
- Agent knows the project is a POC aiming for a production pilot demo.

**Todo List**:
1. Read [`docs/00-architecture-overview.md`](docs/00-architecture-overview.md) — system design & component interactions.
2. Read [`docs/PROJECT_ARCHITECTURE_PRESENTATION.md`](docs/PROJECT_ARCHITECTURE_PRESENTATION.md) — Slides 1–6 give the clearest problem/solution summary.
3. Read [`README.md`](README.md) — quick start and project overview.
4. Internalize the value proposition: **Config files + Confluence docs → AI agents → Structured migration plan + Human review**.

**Relevant Context**:
- The system automates a manual, time-consuming enterprise process.
- IBM Carbon Design System is non-negotiable for UI (enterprise contract requirement).
- LangSmith tracing is live — every LLM call is observable.

**Status**: `[ ] pending`

---

## Sub-Task 2: Learn the Mandatory Rules (CRITICAL — Read Before Any Code)

**Intent**: Internalize the 10 critical rules that exist because bugs were introduced, fixed, and *re-introduced*. These rules are the highest-priority knowledge for any agent touching this codebase.

**Expected Outcomes**:
- Agent can recite the 5 most critical rules from memory before writing any code.
- Agent applies the pre-commit checklist before every change.
- Zero regressions of previously fixed bugs.

**Todo List**:
1. Read [`.agents/CRITICAL_BUGS_MEMORY.md`](.agents/CRITICAL_BUGS_MEMORY.md) — **read every line, not just the summary**.
2. Commit these 5 rules to working memory:
   - **Rule 1 (Datetime)**: `datetime.utcnow().isoformat()` — NEVER pass datetime objects into JSON structures.
   - **Rule 2 (State Init)**: Initialize ALL `MigrationState` fields in `create_initial_state()` — even if `None`.
   - **Rule 3 (Pause Flag)**: Human review node MUST set `"human_reviewed": False` — without it the supervisor loops forever (`GraphRecursionError`).
   - **Rule 4 (Markdown Strip)**: Strip ` ```json ` before parsing any LLM JSON response — Gemini always wraps JSON.
   - **Rule 5 (Method Names)**: Verify method names match across all callers — `retrieve_context()` not `execute()`.
3. Read the Pre-Commit Checklist at the bottom of [`.agents/CRITICAL_BUGS_MEMORY.md`](.agents/CRITICAL_BUGS_MEMORY.md) and apply it to every PR.

**Relevant Context**:
- Bug #4 and Bug #9 were the SAME bug that was fixed, then regressed. This is why the `.agents/` directory exists.
- The `DateTimeEncoder` safety net exists in [`backend/app/storage/redis_client.py`](backend/app/storage/redis_client.py) but is not a substitute for correct datetime handling upstream.
- `MigrationState` schema lives in [`backend/app/orchestration/state.py`](backend/app/orchestration/state.py).
- Workflow pause logic lives in [`backend/app/orchestration/workflow.py`](backend/app/orchestration/workflow.py) and [`backend/app/orchestration/supervisor.py`](backend/app/orchestration/supervisor.py).

**Status**: `[ ] pending`

---

## Sub-Task 3: Understand the Architecture & Design Patterns

**Intent**: Understand the 9 core architectural patterns used throughout the codebase so that new code follows established conventions rather than introducing inconsistent approaches.

**Expected Outcomes**:
- Agent knows which pattern to use for each type of change (new agent, new state field, new workflow node, new UI component, new LLM call).
- Agent never duplicates logic that's already abstracted (e.g., never calls OpenAI directly — always through the provider factory).

**Todo List**:
1. Read [`.agents/ARCHITECTURE_PATTERNS.md`](.agents/ARCHITECTURE_PATTERNS.md) — all 9 patterns.
2. Understand the **Supervisor Pattern**: Supervisor is the ONLY router; agents never call each other directly.
3. Understand the **State Transaction Pattern**: Every state update is a patch dict with `state_version + 1` and `updated_at` ISO string.
4. Understand the **Provider Abstraction Pattern**: All LLM calls go through `backend/app/providers/factory.py` — never instantiate OpenAI/Gemini clients directly in agents.
5. Understand the **Hybrid SSE Architecture**: LangGraph `astream()` → Redis sync → SSE polling every 500ms → Frontend.
6. Understand the **Human-in-the-Loop Pattern**: `human_reviewed=False` pauses workflow; setting it to `True` via the review API resumes it.
7. Read [`.agents/CODING_STANDARDS.md`](.agents/CODING_STANDARDS.md) — covers Python type hints (mandatory), docstrings (mandatory for public methods), logging, async patterns, React component structure, SCSS with explicit IBM Carbon colors.

**Relevant Context**:
- Provider factory: [`backend/app/providers/factory.py`](backend/app/providers/factory.py) — circuit breaker with auto-fallback.
- LangGraph workflow: [`backend/app/orchestration/workflow.py`](backend/app/orchestration/workflow.py).
- Supervisor routing: [`backend/app/orchestration/supervisor.py`](backend/app/orchestration/supervisor.py).
- State schema: [`backend/app/orchestration/state.py`](backend/app/orchestration/state.py).
- SSE endpoint: [`backend/app/api/orchestration.py`](backend/app/api/orchestration.py).
- SSE frontend hook: [`frontend/src/hooks/`](frontend/src/hooks/) (useWorkflowSSE).

**Status**: `[ ] pending`

---

## Sub-Task 4: Map the Codebase Layout

**Intent**: Know where every logical concern lives so the agent can navigate to the right file immediately without searching.

**Expected Outcomes**:
- Agent can answer "where would I add X?" for any common task without searching.
- Agent never creates files in wrong directories.

**Todo List**:
1. Understand the backend layout by inspecting [`backend/app/`](backend/app/):
   - `config.py` — Pydantic Settings; all env vars declared here.
   - `main.py` — FastAPI entry point; mounts all routers.
   - `agents/` — One file per agent (context_retrieval, extraction, questionnaire, intake_draft, review_validation).
   - `orchestration/` — workflow.py (LangGraph graph), supervisor.py (routing), state.py (TypedDict), state_manager.py (Redis sync).
   - `providers/` — base.py (interface), openai_provider.py, gemini_provider.py, factory.py (circuit breaker).
   - `api/` — REST endpoint modules (orchestration, documents, projects, mcp).
   - `storage/` — redis_client.py, qdrant_store.py.
   - `parsers/` — multi-format document parsing (PDF, DOCX, Excel, Markdown, Properties).
   - `mcp/` — MCP connector for Confluence / IBM Context Studio.
   - `tracing/` — LangSmith integration.
2. Understand the frontend layout by inspecting [`frontend/src/`](frontend/src/):
   - `App.jsx` — routing.
   - `pages/` — Dashboard, DocumentUpload, WorkflowExecution, ExtractedFacts, HumanReview.
   - `services/` — Axios API client.
   - `hooks/` — SSE streaming hook.
3. Understand the docs layout by reviewing [`docs/`](docs/) listing.
4. Know the `.agents/` directory: this is the persistent memory system — update it when discovering new critical rules.

**Relevant Context**:
- Environment config: [`backend/.env`](backend/.env) (active file in workspace).
- Container setup: [`backend/podman-compose.yml`](backend/podman-compose.yml).
- Frontend config: [`frontend/vite.config.js`](frontend/vite.config.js) (proxy to backend :8000).
- Tests: [`backend/tests/`](backend/tests/), run with `pytest -v`.

**Status**: `[ ] pending`

---

## Sub-Task 5: Understand Current Workflow State & Phase Roadmap

**Intent**: Know exactly where the project currently is in its 8-phase roadmap and what is/isn't implemented, to avoid building on top of placeholder stubs or duplicating completed work.

> ⚠️ **Verified state (re-confirmed by deep code read)**: Phase 5 is fully implemented — NOT the next target. Phase 6 is the true next target.

**Verified Phase Status** (evidence from actual code files):

| Phase | Status | Evidence |
|-------|--------|----------|
| 1–4: Foundation → Core Agents | ✅ Complete | Full implementation |
| 5: Intake & Review | ✅ **Fully Implemented** | `intake_draft_agent.py` (425 lines real LLM calls), `review_validation_agent.py` (492 lines, 5-criteria validation), `HumanReview.jsx` (305 lines, approve/reject modals), `POST /api/orchestration/resume` working |
| 6: Migration Planning | ⏳ **Placeholder stub** | `_migration_planning_node()` returns `{"placeholder": "Phase 6 implementation"}` — no `migration_planning_agent.py` file exists, no frontend viewer |
| 7: UI Enhancements | ❌ Not started | No MigrationPlan.jsx, no dashboard enhancements |
| 8: Testing & Demo | ❌ Not started | Planned |

**Expected Outcomes**:
- Agent knows Phases 1–5 are complete and stable.
- Agent knows **Phase 6 (Migration Planning Agent) is the true next implementation target**.
- Agent knows what the workflow state looks like after a successful run (state_version 0→11, 8 transitions, 0 errors).
- Agent knows Phase 5 human review is wired and working — don't re-implement it.

**Todo List**:
1. Read [`docs/04-phase4-core-agents.md`](docs/04-phase4-core-agents.md) — confirms all core agents are implemented.
2. Read [`docs/05-phase5-intake-review.md`](docs/05-phase5-intake-review.md) — understand what Phase 5 delivered (already complete).
3. Read [`docs/06-phase6-migration-planning.md`](docs/06-phase6-migration-planning.md) — **this is the implementation spec for the next phase**. Defines 3 migration strategies (Rehost, Replatform, Refactor), template-based selection, LLM customization, cloud service recommendations.
4. Read [`docs/PAUSE_RESUME_IMPLEMENTATION.md`](docs/PAUSE_RESUME_IMPLEMENTATION.md) — understand the pause/resume mechanics (already working for human review).
5. Read [`docs/SSE_IMPLEMENTATION.md`](docs/SSE_IMPLEMENTATION.md) — understand how real-time streaming works.
6. Understand the `MigrationState` version progression: a healthy run increments `state_version` from 0 to ~11 across 8 phase transitions, zero errors.

**Relevant Context**:
- The workflow pauses at `HUMAN_REVIEW` phase and waits for `POST /api/orchestration/resume` with `{human_reviewed: true, review_approved: true}`.
- Resume endpoint in [`backend/app/api/orchestration.py`](backend/app/api/orchestration.py) — `POST /resume` accepts `ResumeWorkflowRequest` with arbitrary `updates` dict.
- After human approval, supervisor routes to `migration_planning` node — currently a stub returning a placeholder dict.
- Phase 6 scope: implement `MigrationPlanningAgent`, create `migration_planning_agent.py`, build `MigrationPlan.jsx` frontend viewer, add route to `App.jsx`.
- LangSmith traces are at `https://smith.langchain.com` with `LANGCHAIN_API_KEY`.
- SSE stream endpoint: `GET /api/orchestration/state/{project_id}/stream`.
- `docs/phase-wise/`, `docs/fixes/`, and `docs/workflow/` directories exist but are **empty**.

**Status**: `[ ] pending`

---

## Sub-Task 6: Environment Setup & Quick Start Verification

**Intent**: Ensure the agent understands the local development environment requirements and can verify the system is running correctly before making changes.

**Expected Outcomes**:
- Agent knows all prerequisites and startup commands.
- Agent knows how to verify each component is healthy before running the workflow.
- Agent knows the known POC limitations and doesn't attempt to "fix" them (they're intentional).

**Todo List**:
1. Read [`backend/.env`](backend/.env) — understand all required environment variables:
   - `OPENAI_API_KEY` and/or `GEMINI_API_KEY` — at least one required.
   - `PRIMARY_PROVIDER` / `FALLBACK_PROVIDER` — controls LLM routing.
   - `LANGCHAIN_API_KEY` — optional, enables LangSmith tracing.
   - `REDIS_URL`, `QDRANT_URL` — infrastructure endpoints.
2. Understand startup sequence:
   1. `cd backend && ./start-containers.ps1` — starts Redis + Qdrant via Podman.
   2. `uvicorn app.main:app --reload` (backend, port 8000).
   3. `cd frontend && npm run dev` (frontend, port 3000).
3. Know the health check endpoints:
   - `GET http://localhost:8000/health` — backend alive.
   - `GET http://localhost:8000/health/providers` — LLM provider health.
   - `http://localhost:6333/dashboard` — Qdrant vectors.
   - `http://localhost:8000/docs` — Swagger UI.
4. Know the known intentional POC limitations (do NOT fix without a task):
   - In-memory state (no PostgreSQL persistence).
   - No authentication / multi-tenancy.
   - 43 dependency vulnerabilities (tracked, deferred).
   - Qdrant vectors lost on restart.

**Relevant Context**:
- Container compose: [`backend/podman-compose.yml`](backend/podman-compose.yml).
- Container setup guide: [`backend/CONTAINER_SETUP.md`](backend/CONTAINER_SETUP.md).
- Backend requirements: [`backend/requirements.txt`](backend/requirements.txt).
- Frontend package: [`frontend/package.json`](frontend/package.json).
- If containers won't start: `podman network rm mig26-network && ./start-containers.ps1`.

**Status**: `[ ] pending`

---

## Sub-Task 7: Understand AWS Bedrock Migration Roadmap (Future Direction)

**Intent**: Be aware of the future technical direction (AWS Bedrock migration) so that architectural decisions made today don't create unnecessary friction for that future migration.

**Expected Outcomes**:
- Agent knows the future architecture target (Bedrock Agents + Knowledge Bases + DynamoDB + Step Functions).
- Agent writes new code with clean provider abstractions that won't need to be torn apart during migration.
- Agent can discuss the migration path intelligently.

**Todo List**:
1. Read [`docs/AWS_BEDROCK_LEARNING_PLAN.md`](docs/AWS_BEDROCK_LEARNING_PLAN.md) — full migration strategy and component mapping.
2. Understand the component mapping:
   - `LangGraph StateGraph` → AWS Step Functions.
   - `Qdrant` → Bedrock Knowledge Bases (OpenSearch Serverless).
   - `OpenAI/Gemini` → Bedrock Claude 3 (via `langchain_aws.ChatBedrock`).
   - `Redis state` → DynamoDB.
   - `LangSmith` → CloudWatch + X-Ray.
   - `SSE with Redis` → API Gateway WebSocket + EventBridge.
3. Understand the recommended hybrid migration approach: Replace LLM provider first (minimal code change), then vector store, then orchestration.
4. Design principle going forward: keep the provider abstraction layer (`backend/app/providers/`) clean — it's the primary migration seam.

**Relevant Context**:
- The `LLMProvider` base class in [`backend/app/providers/base.py`](backend/app/providers/base.py) is the exact interface that a future `BedrockProvider` would implement.
- The hybrid Bedrock integration (`langchain_aws.ChatBedrock` + existing LangGraph) is the lowest-risk first step.

**Status**: `[ ] pending`

---

## Sub-Task 8: Review All Fixes & Supplementary Docs

**Intent**: Absorb the detailed fix documentation to understand the exact code-level decisions behind each bug resolution, preventing subtle regressions from partial understanding.

**Expected Outcomes**:
- Agent understands not just *what* was fixed but *why* each fix is the correct approach.
- Agent can identify if new code violates any of the established patterns by pattern-matching against fix history.

**Todo List**:
1. List and scan [`docs/fixes/`](docs/fixes/) and [`docs/workflow/`](docs/workflow/) for any additional fix notes.
2. Read [`docs/SSE_REALTIME_ENHANCEMENTS.md`](docs/SSE_REALTIME_ENHANCEMENTS.md) — SSE hybrid architecture detailed.
3. Read [`docs/SSE_LANGGRAPH_STREAMING.md`](docs/SSE_LANGGRAPH_STREAMING.md) — LangGraph streaming integration.
4. Read [`.agents/TESTING_GUIDE.md`](.agents/TESTING_GUIDE.md) — full testing and debugging procedures; use this checklist before and after every code change.
5. Scan [`docs/09-single-point-of-failure-analysis.md`](docs/09-single-point-of-failure-analysis.md) — understand resilience risks and intentional trade-offs.
6. Scan [`docs/12-agent-orchestration-analysis.md`](docs/12-agent-orchestration-analysis.md) — deeper analysis of the multi-agent design.

**Relevant Context**:
- The `.agents/TESTING_GUIDE.md` contains a pre-demo checklist — use it before any stakeholder demo.
- `docs/phase-wise/`, `docs/fixes/`, and `docs/workflow/` directories exist but are **empty** — no files inside.

**Status**: `[ ] pending`

---

## Sub-Task 9: Write the Onboarding Summary (Self-Test)

**Intent**: After reading all documents, produce a self-test summary that proves the agent has absorbed the critical knowledge. This also serves as a quick-reference card for future sessions.

**Expected Outcomes**:
- A filled-in quick-reference card (see template below) that can be read in 2 minutes to restore context.
- The card is committed to `.agents/AGENT_QUICKREF.md` for persistence.

**Todo List**:
1. After completing Sub-Tasks 1–8, produce [`.agents/AGENT_QUICKREF.md`](.agents/AGENT_QUICKREF.md) with:
   - One-sentence project description.
   - Current phase (completed / next / planned).
   - 5 critical rules (paraphrased from memory).
   - 3 "never do this" anti-patterns.
   - Startup command sequence.
   - Top 5 files to open when debugging a workflow issue.
   - Top 3 files to open when debugging an LLM call issue.
   - AWS Bedrock migration status (not started / in progress / etc.).
2. Review the quick-ref card against `CRITICAL_BUGS_MEMORY.md` to verify no rules were missed.
3. Commit the file with message: `docs: add agent quick-reference onboarding card`.

**Relevant Context**:
- The `.agents/` directory is the persistent memory system — this file belongs there.
- Template stub is provided in [`onboarding-plan.md`](onboarding-plan.md) (this file) Appendix B.

**Status**: `[ ] pending`

---

## Appendix A: Verified Phase Status (Source of Truth)

| Phase | Implemented? | Key Files |
|-------|-------------|-----------|
| Phase 1–4 | ✅ Fully implemented | `backend/app/agents/`, `backend/app/orchestration/`, `backend/app/providers/` |
| Phase 5: Intake & Review | ✅ Fully implemented | `intake_draft_agent.py` (425 lines), `review_validation_agent.py` (492 lines), `HumanReview.jsx` (305 lines) |
| Phase 6: Migration Planning | ⏳ STUB ONLY | `_migration_planning_node()` in `workflow.py` returns `{"placeholder": "Phase 6 implementation"}` — no agent file, no frontend |
| Phase 7: UI Enhancements | ❌ Not started | Spec in `docs/07-phase7-frontend-ui.md` |
| Phase 8: Testing & Demo | ❌ Not started | Spec in `docs/08-phase8-testing-demo.md` |

---

## Appendix B: Agent Quick-Reference Card Template

```markdown
# Agent Quick Reference — IBM Migration Copilot

**Session Date**: <fill>
**Project Status**: STABLE — Phases 1–5 complete

## What This Project Is
<one sentence>

## Phase Roadmap
- ✅ Phases 1–5: Foundation, MCP, Orchestration, Core Agents, Intake & Review
- 🚧 Phase 6: Migration Planning Agent (NEXT — confirmed stub)
- ⏳ Phase 7: UI Enhancements (spec written, not started)
- ⏳ Phase 8: Testing & Demo (spec written, not started)

## 5 Critical Rules
1. **Datetime**: Always `.isoformat()` — never store datetime objects in state/JSON.
2. **State Init**: ALL MigrationState fields initialized in `create_initial_state()` — even `None` ones.
3. **Pause Flag**: `_human_review_node` MUST return `"human_reviewed": False` — or supervisor loops forever.
4. **JSON Parse**: Strip ` ```json ` from LLM responses before `json.loads()`.
5. **Method Names**: Verify caller and callee method names match across files.

## 3 Anti-Patterns (Never Do)
1. ❌ Call OpenAI/Gemini SDK directly in an agent — always use `providers/factory.py`.
2. ❌ Agent-to-agent direct calls — all communication goes through supervisor → state patches.
3. ❌ Hardcode colors in SCSS without explicit IBM Carbon values (`#161616`, `#0f62fe`).

## Startup Commands
```bash
cd backend && ./start-containers.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
cd ../frontend && npm run dev
```

## Top Files for Workflow Debugging
1. `backend/app/orchestration/workflow.py`
2. `backend/app/orchestration/supervisor.py`
3. `backend/app/orchestration/state.py`
4. `backend/app/storage/redis_client.py`
5. LangSmith traces at https://smith.langchain.com

## Top Files for LLM Call Debugging
1. `backend/app/providers/factory.py`
2. `backend/app/providers/gemini_provider.py` (markdown stripping)
3. LangSmith traces (every call logged)

## AWS Bedrock Migration Status
Not started. Planned incremental path:
1. Replace LLM provider (langchain_aws.ChatBedrock)
2. Qdrant → Bedrock Knowledge Bases
3. LangGraph → Step Functions + Bedrock Agents
```

---

## Appendix C: Pre-Commit Checklist (Copy Every Time)

```
- [ ] No datetime objects in JSON-serializable structures (use .isoformat())
- [ ] All state fields initialized in create_initial_state()
- [ ] LLM JSON responses have markdown stripping applied
- [ ] Workflow pause nodes set human_reviewed=False
- [ ] Method names verified to match caller expectations
- [ ] UI text has explicit IBM Carbon color values
- [ ] Field names match MigrationState schema exactly
- [ ] Type hints added to all new Python functions
- [ ] Docstrings added to all new public methods
- [ ] No direct OpenAI/Gemini SDK calls in agents
```

---

**Plan Written By**: Bob (AI Planning Agent)  
**Date**: 2026-05-28  
**Status**: Ready for implementation (read-only onboarding — no code changes required)
