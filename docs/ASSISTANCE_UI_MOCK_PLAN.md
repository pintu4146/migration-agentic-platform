# Advanced Assistance UI — Mock Plan

**Scope**: Add a 4th "Advanced Assistance" tab to the existing `HumanReview.jsx` page.
Full mock UI — all API endpoints are replaceable stubs, wired to real endpoints later.
Context is isolated in its own hook, service file, and component tree. Zero changes to the existing 3 tabs.

**UI Framework**: IBM Carbon React (`@carbon/react 1.37.0`) — matches existing project.
**Theme**: `g100` (dark) — matches existing `App.jsx` global theme.
**Style Convention**: explicit `#161616` text, `#0f62fe` blue, `#f4f4f4` subtle backgrounds — per `CODING_STANDARDS.md`.

---

## Top-Level Overview

The Human Review page currently has 3 tabs (Review Flags / Intake Draft / Validation Results) and an Approve / Reject action flow.

This plan adds a **4th tab "Advanced Assistance"** that renders a fully self-contained chat panel. The panel is:
- **Isolated**: its own component tree, hook, service file, and SCSS — no changes to existing tabs
- **Mock-first**: all data comes from a `MOCK_MODE` flag; switching to real API is one line per call
- **Context-aware**: pre-loaded with the project's intake draft summary so the first message already has context
- **UX-consistent**: same Carbon tiles, accordions, tags, structured lists, gradients as the rest of HumanReview

### What Gets Built

```
frontend/src/
├── components/
│   └── AssistancePanel/
│       ├── index.jsx                ← Main panel (chat + input + context sidebar)
│       ├── ChatMessage.jsx          ← Single message bubble (user / assistant)
│       ├── ThinkingTrace.jsx        ← Collapsible CoT steps (Carbon Accordion)
│       ├── CommandBlock.jsx         ← Copyable command + output paste area
│       ├── ContextUploadZone.jsx    ← File drop + text paste ingestion
│       └── AssistancePanel.scss     ← All styles for this component tree
├── hooks/
│   └── useAssistance.js             ← State management + mock API calls
└── services/
    └── assistanceApi.js             ← All API calls (stubbed, easy to replace)
```

`HumanReview.jsx` — **2 additions only**:
1. Import `AssistancePanel`
2. Add 4th Carbon `Tab` + `TabPanel`

---

## Sub-Task 1: Service File — `assistanceApi.js`

**Intent**: Create all API call functions as stubs behind a `MOCK_MODE` flag. When `MOCK_MODE = true`, functions return realistic fake data after a simulated delay. When `MOCK_MODE = false`, they call the real backend endpoints. This is the ONLY file that changes when integrating the real backend.

**Expected Outcomes**:
- `frontend/src/services/assistanceApi.js` exists
- 5 exported async functions: `sendMessage`, `getHistory`, `clearHistory`, `uploadContext`, `listContextDocuments`
- Each function has a clear comment showing the real endpoint it maps to
- Mock data is realistic (matches the data shapes the backend will produce)
- Switching to real API = change `const MOCK_MODE = true` to `false`

**Todo List**:
1. Create `frontend/src/services/assistanceApi.js`
2. Define `MOCK_MODE = true` constant at top — one flag controls all mocks
3. Define `BASE_URL` pointing to `/api/assistance` (same proxy as existing `/api` calls in vite.config.js)
4. Implement `sendMessage(projectId, question)`:
   - Real: `POST /api/assistance/{projectId}/chat` → returns SSE stream
   - Mock: returns a `ReadableStream` (or async generator) that yields these events with 300ms delays:
     ```js
     { event_type: "thinking_step", data: { step: 1, action: "CHECK_STATE", description: "Checking extracted facts and intake draft...", confidence: 0.45 } }
     { event_type: "thinking_step", data: { step: 2, action: "SEARCH_QDRANT", description: "Searching uploaded project documents...", confidence: 0.72 } }
     { event_type: "answer_chunk", data: { chunk: "Based on the extracted facts, " } }
     { event_type: "answer_chunk", data: { chunk: "the application uses Spring Boot 2.7 with a PostgreSQL 13 database..." } }
     { event_type: "done", data: { sources_used: ["extracted_facts.tech_stack", "project_docs/pom.xml"], confidence: 0.72 } }
     ```
   - Second mock scenario (low confidence — triggers command request):
     ```js
     { event_type: "thinking_step", data: { step: 1, action: "CHECK_STATE", description: "Checking extracted facts...", confidence: 0.3 } }
     { event_type: "thinking_step", data: { step: 2, action: "SEARCH_QDRANT", description: "Searching project documents...", confidence: 0.25 } }
     { event_type: "thinking_step", data: { step: 3, action: "REQUEST_CONTEXT", description: "Insufficient context found. Generating diagnostic command..." } }
     { event_type: "command_request", data: { command: "mvn dependency:tree -Doutput=dep-tree.txt", shell: "powershell", description: "This will generate a full Maven dependency tree. Run in your project root.", context_type: "dependency_tree" } }
     { event_type: "done", data: { needs_more_context: true } }
     ```
   - Rotate between these two mock scenarios based on question content (if question contains "depend" → command scenario)
5. Implement `getHistory(projectId)`:
   - Real: `GET /api/assistance/{projectId}/history`
   - Mock: returns empty array `[]` on first call
6. Implement `clearHistory(projectId)`:
   - Real: `DELETE /api/assistance/{projectId}/history`
   - Mock: returns `{ cleared: true }`
7. Implement `uploadContext(projectId, payload)` where `payload = { text_content?, file?, context_type, description }`:
   - Real: `POST /api/assistance/{projectId}/context`
   - Mock: returns `{ chunks_added: 12, collection: "project_test", source_type: "command_output", description: payload.description }`
8. Implement `listContextDocuments(projectId)`:
   - Real: `GET /api/assistance/{projectId}/context`
   - Mock: returns `[]` (starts empty, grows as user adds context)

**Relevant Context**:
- `frontend/src/services/api.js` — follow the exact same pattern for BASE_URL, axios config, and error handling
- `frontend/vite.config.js` — proxy already covers `/api` → `http://localhost:8000`; no vite changes needed
- The mock `sendMessage` must return something the hook can iterate — use an async generator or emit events via a callback

**Status**: `[ ] pending`

---

## Sub-Task 2: Hook — `useAssistance.js`

**Intent**: Encapsulate all assistance state and side effects in a custom hook, following the exact same pattern as `useWorkflowSSE.js`. The hook manages the message list, streaming state, thinking steps, context documents, and error handling. `AssistancePanel` components are pure renderers — no fetch logic inside them.

**Expected Outcomes**:
- `frontend/src/hooks/useAssistance.js` exists
- Returns: `{ messages, isStreaming, currentThinkingSteps, contextDocuments, error, sendMessage, submitCommandOutput, uploadFile, clearHistory, loadHistory }`
- Each `message` object: `{ id, role: "user"|"assistant", content, thinkingTrace: [], sourcesUsed: [], needsMoreContext: bool, diagnosticCommand: null|{}, timestamp }`
- While streaming: `currentThinkingSteps` grows in real-time (each `thinking_step` event appends a step)
- After streaming ends: the completed message is pushed into `messages`, `currentThinkingSteps` clears
- Hook is isolated to `projectId` — if `projectId` changes, history reloads automatically
- Calling `loadHistory()` on mount populates `messages` from persisted history

**Todo List**:
1. Create `frontend/src/hooks/useAssistance.js`
2. State variables:
   - `messages` — array of message objects (starts from loaded history)
   - `isStreaming` — bool
   - `currentThinkingSteps` — array of steps for the in-progress assistant message
   - `currentAnswerChunks` — string accumulator for streaming answer text
   - `contextDocuments` — array of ingested context documents
   - `error` — string or null
3. `loadHistory(projectId)`:
   - Calls `assistanceApi.getHistory(projectId)`
   - Sets `messages` from result
4. `sendMessage(question)` async function:
   - Immediately appends `{ role: "user", content: question }` to messages
   - Sets `isStreaming = true`, clears `currentThinkingSteps`, clears `currentAnswerChunks`
   - Calls `assistanceApi.sendMessage(projectId, question)`
   - Iterates events from the stream:
     - `thinking_step` → append to `currentThinkingSteps`
     - `answer_chunk` → accumulate in `currentAnswerChunks`
     - `command_request` → store as `pendingCommand` in state
     - `done` → assemble final assistant message, push to `messages`, set `isStreaming = false`
   - Error: catches and sets `error`
5. `submitCommandOutput(output, contextType)`:
   - Calls `assistanceApi.uploadContext(projectId, { text_content: output, context_type: contextType, description: "Command output" })`
   - On success: appends a system message `{ role: "system", content: "✓ Context added: 12 chunks ingested" }`
   - Refreshes `contextDocuments`
   - Then automatically calls `sendMessage` with the last user question to retry
6. `uploadFile(file, contextType)`:
   - Creates FormData, calls `assistanceApi.uploadContext()`
   - Same success handling as `submitCommandOutput`
7. `clearHistory()`:
   - Calls `assistanceApi.clearHistory(projectId)`
   - Clears local `messages` state
8. `useEffect` on mount: calls `loadHistory()` and `listContextDocuments()`
9. `useEffect` on `projectId` change: reloads history

**Relevant Context**:
- `frontend/src/hooks/useWorkflowSSE.js` — follow the same hook structure, `useEffect` cleanup, error state pattern
- The mock `sendMessage` in `assistanceApi.js` uses an async generator — the hook needs to handle `for await...of` iteration

**Status**: `[ ] pending`

---

## Sub-Task 3: `ThinkingTrace.jsx` Component

**Intent**: Render the Chain-of-Thought steps for an assistant message. Each step shows its action icon, description, and confidence. Uses Carbon `Accordion` so the trace is collapsed by default and the user can expand it. Designed as a pure component — receives steps as props, no state.

**Expected Outcomes**:
- `frontend/src/components/AssistancePanel/ThinkingTrace.jsx` exists
- Collapsed by default, titled "View reasoning (N steps)"
- Each step shows: step number, action badge (colored tag), description text, confidence bar (if present)
- Action color coding:
  - `CHECK_STATE` → Carbon teal tag (`#009d9a`)
  - `SEARCH_QDRANT` → Carbon cyan tag (`#1192e8`)
  - `REQUEST_CONTEXT` → Carbon orange tag (`#ff832b`)
  - `ANSWER` → Carbon green tag (`#24a148`)
- While streaming (steps are still arriving), show a pulsing loading indicator

**Todo List**:
1. Create `frontend/src/components/AssistancePanel/ThinkingTrace.jsx`
2. Props: `steps: Array<{step_number, action, description, confidence?, result?}>`, `isStreaming: bool`
3. Wrap in Carbon `Accordion` with one `AccordionItem`:
   - Title: `View reasoning (${steps.length} steps)` with a small `ChevronDown` or `ChevronRight` icon
   - Body: ordered list of steps
4. Each step rendered as:
   ```
   [step badge]  [action colored tag]  [description text]
                 [confidence bar if confidence present]
   ```
5. Use Carbon `Tag` component with explicit type mapping:
   - `CHECK_STATE` → `type="teal"` 
   - `SEARCH_QDRANT` → `type="cyan"`
   - `REQUEST_CONTEXT` → `type="warm-gray"`
   - `ANSWER` → `type="green"`
6. Confidence: render as a mini `ProgressBar` (Carbon) if `step.confidence` is defined
7. If `isStreaming && steps.length > 0`: show `InlineLoading` text "Reasoning..." after last step
8. SCSS: `.thinking-trace` — `background: #f4f4f4`, `border-left: 3px solid #0f62fe`, `font-size: 0.875rem`, `font-family: monospace` for descriptions

**Relevant Context**:
- `frontend/src/components/ReviewFlagsDisplay.jsx` — follow Carbon `Tag` usage pattern
- `frontend/src/components/ValidationResultsViewer.jsx` — follow Carbon `ProgressBar` usage pattern
- Carbon `Accordion` / `AccordionItem` — already used in `IntakeDraftViewer.jsx`

**Status**: `[ ] pending`

---

## Sub-Task 4: `CommandBlock.jsx` Component

**Intent**: When the assistant determines it needs more context and generates a diagnostic command, this component renders a terminal-style command block with a Carbon `CopyButton`, followed by a textarea where the user pastes the output, and a Submit button to ingest it. Pure component — no API calls, just fires `onSubmitOutput(text, contextType)` callback.

**Expected Outcomes**:
- `frontend/src/components/AssistancePanel/CommandBlock.jsx` exists
- Dark terminal style: `#161616` background, `#42be65` green text for the command
- Carbon `CopyButton` copies command to clipboard
- Descriptive text explains what to do: "Run this command in your project root, then paste the output below"
- `<TextArea>` for pasting output (placeholder: "Paste command output here...")
- Submit button (disabled until textarea is non-empty)
- Context type label shown above: "Maven Dependency Tree" / "Project Structure" / etc.
- After submit: shows inline success notification "Context added successfully"

**Todo List**:
1. Create `frontend/src/components/AssistancePanel/CommandBlock.jsx`
2. Props: `command: {command, shell, description, context_type}`, `onSubmitOutput: (output, contextType) => void`, `isSubmitting: bool`
3. Structure:
   ```
   [Carbon Tile, dark background]
     [Tag: context_type label]
     [description text — normal weight]
     [code block: command text] [CopyButton]
     [TextArea: paste output here]
     [Button: "Submit Context" — primary, disabled if empty]
   ```
4. Use Carbon `CopyButton` with `feedback="Copied!"` prop
5. `TextArea` rows=6, `light` variant
6. On submit: calls `onSubmitOutput(text, command.context_type)`, clears textarea
7. Context type label mapping:
   - `dependency_tree` → "Maven Dependency Tree"
   - `project_structure` → "Project Structure"
   - `java_class` → "Java Source File"
   - `config_file` → "Configuration File"
   - `other` → "Custom Output"
8. SCSS: `.command-block` — dark tile, monospace font for command, left border `4px solid #42be65`

**Relevant Context**:
- `frontend/src/components/ReviewFlagsDisplay.jsx` — Carbon `Tile` usage pattern
- `frontend/src/pages/WorkflowExecution.jsx` — Carbon `CodeSnippet` is imported and used there; could use `CodeSnippet` instead of raw `code` element for the command display

**Status**: `[ ] pending`

---

## Sub-Task 5: `ChatMessage.jsx` Component

**Intent**: Render a single message in the chat — either a user message (right-aligned, blue bubble) or an assistant message (left-aligned, white tile with thinking trace below). System messages (context added confirmations) render as centered info banners. Pure component.

**Expected Outcomes**:
- `frontend/src/components/AssistancePanel/ChatMessage.jsx` exists
- User messages: right-aligned, `background: #0f62fe`, `color: #ffffff`, rounded pill style
- Assistant messages: left-aligned, Carbon `Tile` with `background: #ffffff`, `color: #161616`
- Below assistant message: `<ThinkingTrace>` (collapsed) if `thinkingTrace.length > 0`
- Below thinking trace: `<CommandBlock>` if `needsMoreContext && diagnosticCommand`
- Source citations: small gray tags at bottom of assistant message — `"extracted_facts.tech_stack"`, `"project_docs/pom.xml"`
- System messages: full-width `InlineNotification` kind="success" or "info"
- Timestamp: small gray text below each message (`HH:mm` format)

**Todo List**:
1. Create `frontend/src/components/AssistancePanel/ChatMessage.jsx`
2. Props: `message: {id, role, content, thinkingTrace, sourcesUsed, needsMoreContext, diagnosticCommand, timestamp}`, `onSubmitOutput: fn`, `isSubmitting: bool`, `isStreaming: bool`
3. Render logic:
   - `role === "user"` → right-aligned pill bubble
   - `role === "assistant"` → Carbon `Tile` (left-aligned) + optional `ThinkingTrace` + optional `CommandBlock` + source tags
   - `role === "system"` → Carbon `InlineNotification` full width
4. Streaming state: if `isStreaming && role === "assistant"` and `content` is empty — show `InlineLoading` text "Thinking..."
5. Source citations: map `sourcesUsed` to small Carbon `Tag` components with `type="gray"`, `size="sm"`
6. Timestamp: use `new Date(message.timestamp).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})`
7. SCSS: `.chat-message-user` (right), `.chat-message-assistant` (left), `.chat-message-system` (center), `.message-sources` (tags row), `.message-timestamp` (small gray)

**Relevant Context**:
- `frontend/src/components/PhaseStatusCard.jsx` — Carbon `Tile` pattern
- `frontend/src/components/ReviewFlagsDisplay.jsx` — Carbon `Tag` pattern
- ThinkingTrace component from Sub-Task 3
- CommandBlock component from Sub-Task 4

**Status**: `[ ] pending`

---

## Sub-Task 6: `ContextUploadZone.jsx` Component

**Intent**: A compact zone at the bottom of the context sidebar that allows the user to upload a file (Java, XML, properties, txt, pom.xml etc.) and have it ingested into the project's Qdrant collection. Uses Carbon `FileUploader`. Shows a list of already-ingested context documents. Pure component — fires callbacks up to the hook.

**Expected Outcomes**:
- `frontend/src/components/AssistancePanel/ContextUploadZone.jsx` exists
- Carbon `FileUploader` accepting `.java`, `.xml`, `.properties`, `.txt`, `.json`, `.yaml`, `.yml`, `.md`, `.log`
- On file selected: calls `onUploadFile(file, contextType)` callback — shows progress
- Context type dropdown (Carbon `Select`): "Project Structure", "Maven POM", "Java Source", "Config File", "Other"
- List of already-ingested docs: file icon, description, date added, chunk count
- Empty state: "No additional context added yet. Upload files or paste command output in the chat."

**Todo List**:
1. Create `frontend/src/components/AssistancePanel/ContextUploadZone.jsx`
2. Props: `contextDocuments: Array<{description, source_type, added_at, chunks_added}>`, `onUploadFile: (file, contextType) => void`, `isUploading: bool`
3. Carbon `FileUploader`:
   - `labelTitle="Add Context Files"`
   - `labelDescription="Supported: .java, .xml, .properties, .txt, .json, .yaml, .md"`
   - `accept` array of above extensions
   - `onChange` handler calls `onUploadFile`
4. Carbon `Select` for context type above the uploader
5. Documents list: map `contextDocuments` to Carbon `StructuredListRow` or simple tile rows:
   - Document icon + description + `"${chunks_added} chunks"` + relative date
6. Show `InlineLoading` when `isUploading`
7. SCSS: compact styling, border-top separator, smaller font for document list

**Relevant Context**:
- `frontend/src/pages/DocumentUpload.jsx` — Carbon `FileUploader` usage pattern already in the project
- `frontend/src/components/IntakeDraftViewer.jsx` — Carbon `StructuredList` usage pattern

**Status**: `[ ] pending`

---

## Sub-Task 7: `AssistancePanel/index.jsx` — Main Panel Layout

**Intent**: Compose all sub-components into the full assistance panel. Two-column layout: left wide column is the chat (messages + input bar), right narrow column is the context sidebar (context docs + upload zone). Handles the input bar (Carbon `TextInput` + Send button + Clear history button). Injects project context summary as the first assistant message (welcome message) using mock intake draft data.

**Expected Outcomes**:
- `frontend/src/components/AssistancePanel/index.jsx` exists
- Two-column layout: chat (75%) | context sidebar (25%)
- Welcome message pre-loaded: "I have reviewed the intake draft for this project. I can answer questions about the extracted facts, validation findings, or help identify gaps. What would you like to know?"
- Input bar at bottom: `TextInput` + `Button` (Send) + `IconButton` (Clear history, Trash icon)
- Chat panel scrolls to bottom on new message (`useRef` + `scrollIntoView`)
- Pressing Enter in the input field sends the message
- Send button disabled while `isStreaming`
- Suggested starter questions shown when `messages.length === 1` (only welcome message):
  - "What is the primary tech stack of this application?"
  - "Are there any critical validation issues I should review?"
  - "What dependencies might cause migration issues?"
  - "Run a command to get the full dependency tree"
- Clicking a suggested question populates and sends it automatically

**Todo List**:
1. Create `frontend/src/components/AssistancePanel/index.jsx`
2. Import and use `useAssistance(projectId)` hook
3. Layout using Carbon `Grid` + `Column` (lg=12 / lg=4 split):
   ```
   [Grid]
     [Column lg=12]
       [chat-panel — scrollable]
         [welcome message — pre-loaded]
         [messages.map → ChatMessage]
         [isStreaming → live ChatMessage with currentThinkingSteps]
       [suggested-questions — shown only if messages.length === 1]
       [input-bar]
         [TextInput onKeyDown Enter]
         [Button Send — disabled if isStreaming || !inputText]
         [IconButton Trash — clear history]
     [Column lg=4]
       [context-sidebar]
         [heading "Project Context"]
         [context-summary — small tile with project name, phase, extracted facts count]
         [ContextUploadZone]
   ```
4. Chat scroll: `const bottomRef = useRef(null)` + `useEffect(() => bottomRef.current?.scrollIntoView({behavior:'smooth'}), [messages, currentThinkingSteps])`
5. Suggested questions: render as Carbon `ClickableTile` components in a 2-column grid, hidden once there are >1 messages
6. Context summary tile: shows `project_id`, `"Phase: Human Review"`, `"${extracted_facts_count} facts extracted"` — read from hook state (passed as prop from HumanReview)
7. Input: `inputText` local state, send on Enter keydown (`e.key === 'Enter' && !e.shiftKey`)

**Relevant Context**:
- `frontend/src/pages/HumanReview.jsx` — `projectId` from `useParams()` — pass as prop to AssistancePanel
- `frontend/src/pages/WorkflowExecution.jsx` — Carbon `Grid`/`Column` layout pattern
- `frontend/src/pages/Dashboard.jsx` — Carbon `ClickableTile` pattern

**Status**: `[ ] pending`

---

## Sub-Task 8: `AssistancePanel.scss` — All Styles

**Intent**: Write all SCSS for the AssistancePanel component tree in one file. Follow the exact color conventions and Carbon override patterns used in `ValidationResultsViewer.scss` and `ReviewFlagsDisplay.scss`. No inline styles — everything in this SCSS file.

**Expected Outcomes**:
- `frontend/src/components/AssistancePanel/AssistancePanel.scss` exists
- Imports Carbon tokens for consistency (`@use '@carbon/react/scss/theme'` or direct hex values)
- All selectors are prefixed with `.assistance-panel` to avoid leaking into other components
- Dark/light contrast maintained: white content on `#f4f4f4` background

**Key Style Blocks**:

```scss
// Panel layout
.assistance-panel {
  height: 600px;
  display: flex;
  flex-direction: column;
}

// Chat container
.assistance-chat-panel {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  background: #f4f4f4;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

// User message bubble
.chat-message-user {
  align-self: flex-end;
  max-width: 75%;
  background: #0f62fe;
  color: #ffffff;
  border-radius: 18px 18px 4px 18px;
  padding: 0.75rem 1rem;
  font-size: 0.875rem;
}

// Assistant message tile
.chat-message-assistant {
  align-self: flex-start;
  max-width: 85%;
  background: #ffffff;
  color: #161616;
  border-radius: 4px 18px 18px 18px;
  padding: 0.75rem 1rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.12);
}

// System confirmation
.chat-message-system {
  align-self: center;
  width: 100%;
}

// Thinking trace
.thinking-trace {
  margin-top: 0.5rem;
  border-left: 3px solid #0f62fe;
  background: #f4f4f4;
  font-size: 0.8125rem;
}
.thinking-step {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.375rem 0.75rem;
  border-bottom: 1px solid #e0e0e0;
  font-family: 'IBM Plex Mono', monospace;
  color: #525252;
}

// Command block
.command-block {
  margin-top: 0.75rem;
  background: #161616;
  border-left: 4px solid #42be65;
  border-radius: 4px;
  padding: 1rem;
  .command-text {
    font-family: 'IBM Plex Mono', monospace;
    color: #42be65;
    font-size: 0.875rem;
  }
  .command-output-area {
    margin-top: 0.75rem;
  }
}

// Source citations
.message-sources {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  margin-top: 0.5rem;
}

// Message timestamp
.message-timestamp {
  font-size: 0.75rem;
  color: #8d8d8d;
  margin-top: 0.25rem;
  text-align: right;
}

// Input bar
.assistance-input-bar {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: #ffffff;
  border-top: 1px solid #e0e0e0;
  align-items: flex-end;
}

// Suggested questions
.suggested-questions {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  .cds--tile {
    font-size: 0.8125rem;
    color: #0f62fe;
    cursor: pointer;
    background: #edf5ff;
    &:hover { background: #d0e2ff; }
  }
}

// Context sidebar
.assistance-context-sidebar {
  background: #f4f4f4;
  padding: 1rem;
  border-left: 1px solid #e0e0e0;
  overflow-y: auto;
}

// Context summary tile
.context-summary-tile {
  background: #ffffff;
  padding: 0.75rem;
  border-left: 3px solid #0f62fe;
  margin-bottom: 1rem;
  .context-summary-label {
    font-size: 0.75rem;
    color: #525252;
  }
  .context-summary-value {
    font-size: 0.875rem;
    color: #161616;
    font-weight: 600;
  }
}

// Context doc list
.context-doc-item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid #e0e0e0;
  font-size: 0.8125rem;
  color: #525252;
  .doc-name { color: #161616; font-weight: 500; }
  .doc-chunks { color: #0f62fe; }
}
```

**Todo List**:
1. Create `frontend/src/components/AssistancePanel/AssistancePanel.scss`
2. Write all the style blocks above — this is the single SCSS source for the entire component tree
3. Import in `AssistancePanel/index.jsx` as `import './AssistancePanel.scss'`
4. Verify no styles leak outside `.assistance-panel` root class
5. Add `@media (max-width: 768px)` breakpoint: stack columns vertically, hide context sidebar

**Relevant Context**:
- `frontend/src/components/ValidationResultsViewer.scss` — Carbon override patterns to follow
- `frontend/src/components/ReviewFlagsDisplay.scss` — gradient and tile hover patterns
- `.agents/CODING_STANDARDS.md` — explicit IBM Carbon colors rule: `#161616`, `#0f62fe`, `#ffffff`

**Status**: `[ ] pending`

---

## Sub-Task 9: Wire Into `HumanReview.jsx` — 4th Tab

**Intent**: Add the "Advanced Assistance" tab to `HumanReview.jsx` with the absolute minimum changes. Import `AssistancePanel`, add one `Tab`, add one `TabPanel`. Nothing else changes. The existing 3 tabs are untouched.

**Expected Outcomes**:
- `HumanReview.jsx` has exactly 2 additions: one import line, one `Tab` + `TabPanel` block
- Existing `selectedTab` state and tab logic works unchanged (Carbon `Tabs` accepts 4 tabs identically to 3)
- AssistancePanel receives `projectId` and a `workflowStateSummary` prop (derived from existing `workflowState`)
- No regressions in Review Flags / Intake Draft / Validation Results tabs

**Todo List**:
1. Open `frontend/src/pages/HumanReview.jsx`
2. Add one import: `import AssistancePanel from '../components/AssistancePanel'`
3. Derive a summary prop from existing `workflowState`:
   ```jsx
   const stateSummary = {
     projectId,
     phase: workflowState?.phase,
     factsCount: Object.values(workflowState?.extracted_facts || {})
       .reduce((acc, arr) => acc + (Array.isArray(arr) ? arr.length : 0), 0),
   }
   ```
4. In the `<Tabs>` block, add after the 3rd `<Tab>`:
   ```jsx
   <Tab>Advanced Assistance</Tab>
   ```
5. In the `<TabPanels>` block, add after the 3rd `<TabPanel>`:
   ```jsx
   <TabPanel>
     <AssistancePanel projectId={projectId} stateSummary={stateSummary} />
   </TabPanel>
   ```
6. That is ALL — no other changes to `HumanReview.jsx`

**Relevant Context**:
- `frontend/src/pages/HumanReview.jsx` — Tab structure is at lines ~220-280; Carbon `Tabs` component
- `useParams()` already extracts `projectId` at line ~15 — pass directly
- `workflowState` is already loaded in `useEffect` at line ~25 — derive `stateSummary` from it

**Status**: `[ ] pending`

---

## Implementation Order

```
Sub-Task 1: assistanceApi.js        ← Foundation (mock data shapes)
     ↓
Sub-Task 2: useAssistance.js        ← Hook (state + stream handling)
     ↓
Sub-Task 3: ThinkingTrace.jsx       ← UI atom (CoT steps)
Sub-Task 4: CommandBlock.jsx        ← UI atom (command + paste)
Sub-Task 5: ChatMessage.jsx         ← UI molecule (user of 3+4)
Sub-Task 6: ContextUploadZone.jsx   ← UI molecule (sidebar)
     ↓ (all atoms done)
Sub-Task 7: AssistancePanel/index.jsx  ← UI organism (composes all)
Sub-Task 8: AssistancePanel.scss    ← Can be done alongside 3-7
     ↓
Sub-Task 9: HumanReview.jsx patch   ← Wire in (2 additions only)
```

---

## Files Created / Changed

```
CREATED (all new, isolated):
frontend/src/services/assistanceApi.js
frontend/src/hooks/useAssistance.js
frontend/src/components/AssistancePanel/
    index.jsx
    ChatMessage.jsx
    ThinkingTrace.jsx
    CommandBlock.jsx
    ContextUploadZone.jsx
    AssistancePanel.scss

MODIFIED (surgical additions only):
frontend/src/pages/HumanReview.jsx    ← +1 import, +1 Tab, +1 TabPanel
```

---

## Switching From Mock to Real API

When the real `/api/assistance` backend is ready, these are the only changes needed in `assistanceApi.js`:

```js
// Line 1: Change this one constant
const MOCK_MODE = false;   // was: true

// That's it. All 5 functions automatically call real endpoints.
```

Each function already has the real endpoint documented as a comment above the mock branch.

---

**Plan Written By**: Bob (AI Planning Agent)
**Based On**: Full read of HumanReview.jsx (305 lines), all 5 components, api.js, both hooks, all scss files
**Status**: Ready for review — no implementation until approved
