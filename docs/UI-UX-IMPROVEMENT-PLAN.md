# UI/UX Improvement Plan
## Enterprise Application Modernization Copilot

**Version**: 1.0  
**Date**: 2026-05-28  
**Status**: Planning Phase

---

## Executive Summary

The current UI is functional but lacks visibility into workflow execution, progress tracking, and user guidance. This plan outlines comprehensive UI/UX improvements to create an enterprise-grade, IBM Carbon Design System-aligned interface that provides transparency, control, and confidence throughout the migration workflow.

---

## Current State Analysis

### What Works ✅
- Project selection and creation
- Document upload functionality
- Basic workflow execution trigger
- IBM Carbon Design System foundation

### Pain Points ❌
1. **No Workflow Visibility**: Users cannot see what's happening during execution
2. **No Progress Tracking**: No indication of which phase is active or completed
3. **No Real-Time Feedback**: Users don't know if the system is working or stuck
4. **No Error Visibility**: Errors are hidden in console logs
5. **No State Inspection**: Cannot view extracted facts, questions, or intermediate results
6. **No Human Review Interface**: No way to review and approve intake drafts
7. **Poor Information Architecture**: All data dumped in JSON format
8. **No Guidance**: Users don't know what to do next

---

## Design Principles

### 1. **Transparency First**
- Show what the system is doing at all times
- Display progress, not just results
- Make AI reasoning visible and understandable

### 2. **Enterprise Trust**
- Professional, structured, IBM-aligned design
- Clear data provenance and confidence scores
- Audit trail for all decisions

### 3. **Progressive Disclosure**
- Show high-level overview by default
- Allow drill-down into details on demand
- Don't overwhelm with information

### 4. **Actionable Insights**
- Every screen should have a clear next action
- Guide users through the workflow
- Provide context-sensitive help

---

## Proposed UI Architecture

### Screen Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                     App Shell (Persistent)                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Header: Logo | Project Selector | Health Status      │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Left Nav: Dashboard | Documents | Workflow | Review  │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                   Main Content Area                   │  │
│  │                                                        │  │
│  │  [Dynamic content based on selected nav item]        │  │
│  │                                                        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Detailed Screen Designs

### 1. **Dashboard Screen** (New)

**Purpose**: High-level project overview and status at a glance

**Components**:

```
┌─────────────────────────────────────────────────────────────┐
│ Project: [Project Name]                    [Start Workflow] │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Workflow Status                                      │   │
│  │                                                       │   │
│  │  Phase: Human Review                                 │   │
│  │  Status: ⏸ Paused - Awaiting Review                 │   │
│  │  Progress: ████████░░ 80%                           │   │
│  │                                                       │   │
│  │  ✅ Context Retrieved (1 document)                   │   │
│  │  ✅ Facts Extracted (32 facts, 98% confidence)       │   │
│  │  ✅ Questions Generated (2 high-priority)            │   │
│  │  ✅ Intake Draft Created                             │   │
│  │  ⏸ Human Review Pending                             │   │
│  │  ⏳ Migration Planning (Not Started)                 │   │
│  │                                                       │   │
│  │  [View Details] [Resume Workflow]                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Documents    │  │ Extracted    │  │ Open         │     │
│  │              │  │ Facts        │  │ Questions    │     │
│  │   1 file     │  │   32 facts   │  │   2 items    │     │
│  │              │  │              │  │              │     │
│  │ [View]       │  │ [View]       │  │ [View]       │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Recent Activity                                      │   │
│  │                                                       │   │
│  │  • 14:53:07 - Workflow paused for human review      │   │
│  │  • 14:53:07 - Intake draft created                  │   │
│  │  • 14:53:07 - 2 questions generated                 │   │
│  │  • 14:53:00 - 32 facts extracted                    │   │
│  │  • 14:52:24 - 1 document retrieved                  │   │
│  │                                                       │   │
│  │  [View Full Log]                                     │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Key Features**:
- **Workflow Progress Stepper**: Visual representation of phases
- **Status Cards**: Quick metrics for documents, facts, questions
- **Activity Timeline**: Recent workflow events
- **Action Buttons**: Context-aware next steps

---

### 2. **Workflow Execution Screen** (Enhanced)

**Purpose**: Real-time workflow execution with live updates

**Components**:

```
┌─────────────────────────────────────────────────────────────┐
│ Workflow Execution                          [Pause] [Cancel] │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Progress Stepper                                     │   │
│  │                                                       │   │
│  │  ✅ Context ──> ✅ Extract ──> ✅ Questions ──>      │   │
│  │  ✅ Intake ──> ⏸ Review ──> ⏳ Planning ──> ⏳ Done  │   │
│  │                     ▲                                 │   │
│  │                  Current                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Current Phase: Human Review                          │   │
│  │                                                       │   │
│  │  Status: ⏸ Paused                                    │   │
│  │  Reason: Waiting for human review of intake draft    │   │
│  │                                                       │   │
│  │  Next Action: Review the intake document and         │   │
│  │               approve or request changes              │   │
│  │                                                       │   │
│  │  [Go to Review Screen]                               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Execution Log (Live)                                 │   │
│  │                                                       │   │
│  │  14:53:07 ⏸ Workflow paused for human review        │   │
│  │  14:53:07 ✅ Intake draft created successfully       │   │
│  │  14:53:07 ✅ Generated 2 high-priority questions     │   │
│  │  14:53:00 ✅ Extracted 32 facts (98% confidence)     │   │
│  │  14:52:24 ✅ Retrieved 1 document from Qdrant        │   │
│  │  14:52:20 ⚠️  MCP returned no documents              │   │
│  │  14:52:19 ℹ️  Starting context retrieval             │   │
│  │                                                       │   │
│  │  [Export Log] [Filter]                               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Phase Details                                        │   │
│  │                                                       │   │
│  │  Context Retrieval:                                  │   │
│  │    • Source: uploaded_documents                      │   │
│  │    • Documents: 1                                    │   │
│  │    • Duration: 5s                                    │   │
│  │                                                       │   │
│  │  Fact Extraction:                                    │   │
│  │    • Facts: 32                                       │   │
│  │    • Avg Confidence: 98%                             │   │
│  │    • Categories: 7                                   │   │
│  │    • Duration: 36s                                   │   │
│  │                                                       │   │
│  │  [View All Details]                                  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Key Features**:
- **Live Progress Stepper**: Shows current phase with visual indicators
- **Real-Time Log**: WebSocket-based live updates
- **Phase Details**: Expandable details for each completed phase
- **Contextual Actions**: Next steps based on current state

---

### 3. **Extracted Facts Screen** (New)

**Purpose**: View and validate extracted facts with confidence scores

**Components**:

```
┌─────────────────────────────────────────────────────────────┐
│ Extracted Facts                    [Export] [Filter] [Sort]  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Summary: 32 facts extracted | Avg confidence: 98%          │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Category Tabs                                        │   │
│  │                                                       │   │
│  │  [Technical Stack (6)] [Dependencies (5)]            │   │
│  │  [Runtime Config (4)] [Deployment (5)]               │   │
│  │  [Architecture (4)] [Security (4)] [Risks (4)]       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Technical Stack (6 facts)                            │   │
│  │                                                       │   │
│  │  ┌───────────────────────────────────────────────┐  │   │
│  │  │ Programming Languages                          │  │   │
│  │  │                                                 │  │   │
│  │  │ Fact: The application requires Java            │  │   │
│  │  │       Development Kit (JDK)                     │  │   │
│  │  │                                                 │  │   │
│  │  │ Confidence: ████████████████████ 100%          │  │   │
│  │  │                                                 │  │   │
│  │  │ Evidence: "Required Jdk"                        │  │   │
│  │  │ Source: README.md (line 3)                      │  │   │
│  │  │                                                 │  │   │
│  │  │ [View Source] [Flag Issue]                      │  │   │
│  │  └───────────────────────────────────────────────┘  │   │
│  │                                                       │   │
│  │  ┌───────────────────────────────────────────────┐  │   │
│  │  │ Frameworks and Libraries                       │  │   │
│  │  │                                                 │  │   │
│  │  │ Fact: The application is built using           │  │   │
│  │  │       Spring Boot                               │  │   │
│  │  │                                                 │  │   │
│  │  │ Confidence: ████████████████████ 100%          │  │   │
│  │  │                                                 │  │   │
│  │  │ Evidence: "Check out the Spring boot           │  │   │
│  │  │            application"                         │  │   │
│  │  │ Source: README.md (line 5)                      │  │   │
│  │  │                                                 │  │   │
│  │  │ [View Source] [Flag Issue]                      │  │   │
│  │  └───────────────────────────────────────────────┘  │   │
│  │                                                       │   │
│  │  [Show 4 more facts...]                              │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Key Features**:
- **Category Tabs**: Organize facts by category
- **Confidence Visualization**: Progress bars for confidence scores
- **Evidence Tracing**: Link back to source documents
- **Fact Validation**: Allow users to flag incorrect facts
- **Export Options**: CSV, JSON, PDF formats

---

### 4. **Questions Screen** (New)

**Purpose**: View generated questions and track answers

**Components**:

```
┌─────────────────────────────────────────────────────────────┐
│ Migration Questions              [Export] [Filter] [Answer]  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Summary: 2 questions | 2 high priority | 0 answered        │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Filter: [All] [High Priority] [Unanswered]          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Question 1 of 2                          🔴 HIGH     │   │
│  │                                                       │   │
│  │  What is the current method used for deploying      │   │
│  │  the application to production environments?         │   │
│  │                                                       │   │
│  │  Why this matters:                                   │   │
│  │  Understanding the current deployment method is      │   │
│  │  critical for designing a compatible or improved     │   │
│  │  deployment strategy in the target environment.      │   │
│  │                                                       │   │
│  │  Suggested sources:                                  │   │
│  │  • DevOps team                                       │   │
│  │  • SRE team                                          │   │
│  │  • CI/CD pipeline configurations                     │   │
│  │  • Deployment scripts                                │   │
│  │                                                       │   │
│  │  Related gap: deployment_strategy.current_method     │   │
│  │                                                       │   │
│  │  ┌─────────────────────────────────────────────┐   │   │
│  │  │ Answer (optional)                            │   │
│  │  │                                               │   │
│  │  │ [Text area for answer]                       │   │
│  │  │                                               │   │
│  │  │ [Save Answer]                                │   │
│  │  └─────────────────────────────────────────────┘   │   │
│  │                                                       │   │
│  │  Status: ⏳ Unanswered                               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Question 2 of 2                          🔴 HIGH     │   │
│  │                                                       │   │
│  │  What is the primary architectural style of the      │   │
│  │  application?                                         │   │
│  │                                                       │   │
│  │  [Expand to view details...]                         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  [Previous] [Next] [Mark All as Reviewed]                   │
└─────────────────────────────────────────────────────────────┘
```

**Key Features**:
- **Priority Indicators**: Visual priority badges
- **Contextual Help**: Why each question matters
- **Suggested Sources**: Where to find answers
- **Inline Answering**: Answer questions directly in UI
- **Progress Tracking**: Show answered vs unanswered

---

### 5. **Intake Review Screen** (New - Critical)

**Purpose**: Review and approve the generated intake document

**Components**:

```
┌─────────────────────────────────────────────────────────────┐
│ Intake Document Review                [Export PDF] [Print]   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Review Status: ⏸ Pending Review                     │   │
│  │                                                       │   │
│  │ This intake document was automatically generated     │   │
│  │ based on 32 extracted facts. Please review for      │   │
│  │ accuracy and completeness before proceeding.         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Table of Contents                                    │   │
│  │                                                       │   │
│  │  1. Executive Summary                                │   │
│  │  2. Current State                                    │   │
│  │  3. Technical Stack                                  │   │
│  │  4. Dependencies                                     │   │
│  │  5. Architecture                                     │   │
│  │  6. Security & Compliance                            │   │
│  │  7. Open Questions                                   │   │
│  │  8. Risks & Assumptions                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 1. Executive Summary                                 │   │
│  │                                                       │   │
│  │ Project: pintu-test                                  │   │
│  │ Application Type: Spring Boot Banking Application    │   │
│  │ Current Environment: Local Development               │   │
│  │                                                       │   │
│  │ This application is an Agentic AI banking system     │   │
│  │ built with Spring Boot and Java. It connects to a    │   │
│  │ local Ollama3 AI model server for intelligent        │   │
│  │ transaction processing and customer support.         │   │
│  │                                                       │   │
│  │ [Add Comment] [Flag Issue]                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 2. Current State                                     │   │
│  │                                                       │   │
│  │ Technical Stack:                                     │   │
│  │  • Language: Java (JDK required)                     │   │
│  │  • Framework: Spring Boot                            │   │
│  │  • Build Tool: Maven                                 │   │
│  │  • AI Integration: Ollama3 local model               │   │
│  │                                                       │   │
│  │ Deployment:                                          │   │
│  │  • Current: Local development (localhost:8080)       │   │
│  │  • Method: Manual (not specified)                    │   │
│  │  • CI/CD: Not mentioned                              │   │
│  │                                                       │   │
│  │ [Add Comment] [Flag Issue]                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  [Continue reading...]                                       │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Review Actions                                       │   │
│  │                                                       │   │
│  │  ┌─────────────────────────────────────────────┐   │   │
│  │  │ Comments (0)                                 │   │   │
│  │  │                                               │   │   │
│  │  │ [Add a comment about this intake document]  │   │   │
│  │  │                                               │   │   │
│  │  │ [Post Comment]                               │   │   │
│  │  └─────────────────────────────────────────────┘   │   │
│  │                                                       │   │
│  │  [❌ Request Changes] [✅ Approve & Continue]        │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Key Features**:
- **Structured Document**: Clear sections with table of contents
- **Inline Comments**: Add comments to specific sections
- **Flag Issues**: Mark sections that need attention
- **Approval Workflow**: Approve or request changes
- **Export Options**: PDF, Word, Markdown

---

### 6. **Migration Plan Screen** (New)

**Purpose**: View the generated migration plan with recommendations

**Components**:

```
┌─────────────────────────────────────────────────────────────┐
│ Migration Plan                      [Export] [Share] [Edit]  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Plan Overview                                        │   │
│  │                                                       │   │
│  │  Strategy: Replatform (Lift, Tinker, and Shift)     │   │
│  │  Target: AWS Cloud                                   │   │
│  │  Duration: 8-12 weeks                                │   │
│  │  Risk Level: Medium                                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Migration Phases                                     │   │
│  │                                                       │   │
│  │  Phase 1: Assessment & Planning (2 weeks)            │   │
│  │    • Complete technical assessment                   │   │
│  │    • Design target architecture                      │   │
│  │    • Set up AWS environment                          │   │
│  │                                                       │   │
│  │  Phase 2: Infrastructure Setup (2 weeks)             │   │
│  │    • Provision AWS resources                         │   │
│  │    • Configure networking & security                 │   │
│  │    • Set up CI/CD pipeline                           │   │
│  │                                                       │   │
│  │  Phase 3: Application Migration (3 weeks)            │   │
│  │    • Containerize Spring Boot app                    │   │
│  │    • Deploy to ECS/EKS                               │   │
│  │    • Migrate Ollama3 to SageMaker                    │   │
│  │                                                       │   │
│  │  Phase 4: Testing & Validation (2 weeks)             │   │
│  │    • Functional testing                              │   │
│  │    • Performance testing                             │   │
│  │    • Security testing                                │   │
│  │                                                       │   │
│  │  Phase 5: Cutover & Go-Live (1 week)                 │   │
│  │    • Final data migration                            │   │
│  │    • DNS cutover                                     │   │
│  │    • Post-migration monitoring                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Cloud Infrastructure Recommendations                 │   │
│  │                                                       │   │
│  │  Compute:                                            │   │
│  │    • AWS ECS Fargate for Spring Boot app            │   │
│  │    • AWS SageMaker for Ollama3 model hosting        │   │
│  │                                                       │   │
│  │  Database:                                           │   │
│  │    • AWS RDS PostgreSQL (recommended)                │   │
│  │                                                       │   │
│  │  Networking:                                         │   │
│  │    • VPC with public/private subnets                 │   │
│  │    • Application Load Balancer                       │   │
│  │                                                       │   │
│  │  Security:                                           │   │
│  │    • AWS IAM for access control                      │   │
│  │    • AWS Secrets Manager for credentials             │   │
│  │    • AWS WAF for application firewall                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Risks & Mitigation                                   │   │
│  │                                                       │   │
│  │  🔴 HIGH: Ollama3 model compatibility with SageMaker │   │
│  │     Mitigation: Test model deployment early          │   │
│  │                                                       │   │
│  │  🟡 MEDIUM: No existing CI/CD pipeline               │   │
│  │     Mitigation: Implement AWS CodePipeline           │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Key Features**:
- **Visual Timeline**: Gantt chart or timeline view
- **Phase Details**: Expandable phase descriptions
- **Infrastructure Diagram**: Visual architecture diagram
- **Risk Matrix**: Color-coded risk assessment
- **Cost Estimation**: Projected cloud costs

---

## Technical Implementation Plan

### Phase 1: Core UI Infrastructure (Week 1)

**Tasks**:
1. Create new screen components
   - `DashboardScreen.tsx`
   - `WorkflowExecutionScreen.tsx`
   - `ExtractedFactsScreen.tsx`
   - `QuestionsScreen.tsx`
   - `IntakeReviewScreen.tsx`
   - `MigrationPlanScreen.tsx`

2. Implement navigation
   - Update `App.tsx` with routing
   - Create left navigation component
   - Add breadcrumb navigation

3. Create shared components
   - `ProgressStepper.tsx` - Workflow phase indicator
   - `StatusBadge.tsx` - Status indicators
   - `ConfidenceBar.tsx` - Confidence score visualization
   - `ActivityTimeline.tsx` - Event timeline
   - `FactCard.tsx` - Fact display card
   - `QuestionCard.tsx` - Question display card

### Phase 2: Real-Time Updates (Week 2)

**Tasks**:
1. Implement WebSocket connection
   - Create WebSocket service
   - Handle workflow events
   - Update UI in real-time

2. Add polling fallback
   - Poll workflow state every 2 seconds
   - Update progress indicators
   - Show live log updates

3. Create notification system
   - Toast notifications for events
   - Success/error/warning messages
   - Persistent notifications for important events

### Phase 3: Data Visualization (Week 2)

**Tasks**:
1. Implement fact visualization
   - Category tabs
   - Confidence score bars
   - Evidence linking
   - Source document preview

2. Implement question management
   - Priority indicators
   - Answer input forms
   - Progress tracking
   - Export functionality

3. Create intake document viewer
   - Structured document layout
   - Table of contents
   - Inline commenting
   - Approval workflow

### Phase 4: Polish & Testing (Week 3)

**Tasks**:
1. Add loading states
   - Skeleton screens
   - Progress indicators
   - Spinners for async operations

2. Add error handling
   - Error boundaries
   - Retry mechanisms
   - User-friendly error messages

3. Add empty states
   - No documents uploaded
   - No facts extracted
   - No questions generated

4. Accessibility improvements
   - Keyboard navigation
   - Screen reader support
   - ARIA labels
   - Focus management

5. Responsive design
   - Mobile-friendly layouts
   - Tablet optimization
   - Desktop optimization

---

## Success Metrics

### User Experience Metrics
- **Task Completion Rate**: >95% of users can complete workflow
- **Time to Insight**: <30 seconds to understand workflow status
- **Error Recovery**: <2 minutes to recover from errors
- **User Satisfaction**: >4.5/5 rating

### Technical Metrics
- **Page Load Time**: <2 seconds
- **Real-Time Update Latency**: <500ms
- **API Response Time**: <1 second
- **Error Rate**: <1%

---

## IBM Carbon Design System Alignment

### Components to Use
- **Buttons**: Primary, Secondary, Danger, Ghost
- **Data Tables**: For facts, questions, documents
- **Tabs**: For category navigation
- **Progress Indicators**: For workflow phases
- **Notifications**: For events and alerts
- **Modal**: For confirmations and forms
- **Accordion**: For expandable sections
- **Breadcrumb**: For navigation
- **Tag**: For status indicators
- **Tooltip**: For contextual help

### Color Palette
- **Primary**: IBM Blue (#0f62fe)
- **Success**: Green (#24a148)
- **Warning**: Yellow (#f1c21b)
- **Error**: Red (#da1e28)
- **Info**: Cyan (#0072c3)

### Typography
- **Headings**: IBM Plex Sans
- **Body**: IBM Plex Sans
- **Code**: IBM Plex Mono

---

## Next Steps

1. **Review & Approve Plan**: Get stakeholder approval
2. **Create Wireframes**: Detailed wireframes for each screen
3. **Implement Phase 1**: Core UI infrastructure
4. **User Testing**: Test with real users
5. **Iterate**: Refine based on feedback

---

## Appendix: Current UI Screenshots

*(To be added after implementation)*

---

**Document Version**: 1.0  
**Last Updated**: 2026-05-28  
**Author**: Migration Copilot Team  
**Status**: Ready for Implementation