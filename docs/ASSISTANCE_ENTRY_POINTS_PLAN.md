# Assistance Entry Points — Minimal UI Plan

**Scope**: Two additions to the Human Review page only.
1. An **"Ask Assistant"** button in the header action row — sits beside the existing Reject button
2. A **floating chat FAB** (Floating Action Button) fixed at the bottom-right corner of the viewport

No new pages. No new tabs. No new routes. No changes to the 3 existing tabs.
Both open a **slide-in chat drawer** — the same component, triggered from two entry points.

---

## Top-Level Overview

The current header action row at lines 173–190 of [`frontend/src/pages/HumanReview.jsx`](frontend/src/pages/HumanReview.jsx) looks like:

```
[ Reject ]  [ Approve ]
```

After this plan it will look like:

```
[ Ask Assistant ]  [ Reject ]  [ Approve ]
```

Additionally, a floating circular button fixed at `bottom: 2rem; right: 2rem` is always visible on the page, regardless of scroll position.

Both buttons open a **`ChatDrawer`** — a slide-in panel from the right side (not a modal, not a new page). The drawer contains a minimal mock chat UI with a text input, message history, and a simple "thinking…" loading state.

The `ChatDrawer` component is entirely self-contained. It is isolated from the existing workflow state management. It uses `MOCK_MODE = true` internally so the backend endpoint is a single-line swap later.

---

## What Gets Built

```
frontend/src/
├── components/
│   └── ChatDrawer/
│       ├── index.jsx          ← Slide-in drawer with chat UI
│       └── ChatDrawer.scss    ← All styles for the drawer
└── pages/
    ├── HumanReview.jsx        ← +3 lines: import + button + FAB
    └── HumanReview.scss       ← +15 lines: FAB styles only
```

Total new lines across all files: ~180.

---

## Sub-Task 1: `ChatDrawer` Component

**Intent**: Build the slide-in chat drawer as a single, self-contained component. It renders over the existing page without disrupting the layout. It has its own mock data, its own state, and fires no side effects outside itself. The open/close state is controlled by the parent (`HumanReview.jsx`) via an `isOpen` prop.

**Expected Outcomes**:
- `frontend/src/components/ChatDrawer/index.jsx` exists
- Opens as a fixed right-side panel: `width: 420px`, slides in with a CSS transition
- Has a header: "Ask the Assistant" + a close `IconButton` (Carbon `Close` icon)
- Has a scrollable message history area
- Has a text input bar at the bottom: Carbon `TextInput` + "Send" `Button`
- On Send: appends the user message, then after 800ms appends a mock assistant reply
- Mock assistant reply cycles through 3 realistic responses (see Todo)
- `MOCK_MODE = true` constant at top — switching to real API is one line
- Pressing `Enter` in the input sends the message
- `isOpen=false` → drawer is off-screen to the right (`transform: translateX(100%)`)
- `isOpen=true` → drawer slides in (`transform: translateX(0)`)
- A semi-transparent backdrop covers the page when the drawer is open (click backdrop → closes drawer)
- Accessible: `role="dialog"`, `aria-modal="true"`, `aria-label="Assistant chat"`

**Todo List**:
1. Create `frontend/src/components/ChatDrawer/index.jsx`
2. Import from `@carbon/react`: `Button`, `TextInput`, `IconButton`, `InlineLoading`
3. Import from `@carbon/icons-react`: `Close`, `Send`, `Chat`
4. Local state inside the component:
   - `messages` — array of `{id, role: 'user'|'assistant', text, timestamp}`
   - `inputText` — string
   - `isThinking` — bool (shows `InlineLoading` while "waiting for response")
5. `handleSend()` function:
   - Guards: if `!inputText.trim() || isThinking` → return
   - Appends user message to `messages`
   - Clears `inputText`
   - Sets `isThinking = true`
   - After 800ms setTimeout: appends mock assistant reply, sets `isThinking = false`
6. Mock replies — rotate via `messages.length % 3`:
   - Reply 0: `"Based on the extracted facts, the application uses Spring Boot 2.7 with a PostgreSQL 13 database. The confidence score for the tech stack section is 0.92."`
   - Reply 1: `"The validation found 2 medium-priority flags related to missing deployment configuration. You can see the details in the Review Flags tab."`
   - Reply 2: `"I don't have enough context to answer that with high confidence. Try running: mvn dependency:tree -Doutput=dep-tree.txt in your project root and paste the output here."`
7. JSX structure:
   ```jsx
   <>
     {/* Backdrop */}
     {isOpen && <div className="chat-drawer__backdrop" onClick={onClose} />}

     {/* Drawer panel */}
     <div
       className={`chat-drawer ${isOpen ? 'chat-drawer--open' : ''}`}
       role="dialog"
       aria-modal="true"
       aria-label="Assistant chat"
     >
       {/* Header */}
       <div className="chat-drawer__header">
         <span className="chat-drawer__title">Ask the Assistant</span>
         <IconButton label="Close" onClick={onClose} kind="ghost" size="sm">
           <Close />
         </IconButton>
       </div>

       {/* Messages */}
       <div className="chat-drawer__messages" ref={messagesEndRef_parent}>
         {messages.map(msg => (
           <div key={msg.id} className={`chat-drawer__message chat-drawer__message--${msg.role}`}>
             <span className="chat-drawer__message-text">{msg.text}</span>
             <span className="chat-drawer__message-time">
               {new Date(msg.timestamp).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}
             </span>
           </div>
         ))}
         {isThinking && (
           <div className="chat-drawer__message chat-drawer__message--assistant">
             <InlineLoading description="Thinking..." />
           </div>
         )}
         <div ref={messagesEndRef} />
       </div>

       {/* Input bar */}
       <div className="chat-drawer__input-bar">
         <TextInput
           id="chat-input"
           labelText=""
           hideLabel
           placeholder="Ask about this project..."
           value={inputText}
           onChange={e => setInputText(e.target.value)}
           onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
           disabled={isThinking}
         />
         <Button
           kind="primary"
           size="md"
           renderIcon={Send}
           iconDescription="Send"
           onClick={handleSend}
           disabled={isThinking || !inputText.trim()}
         >
           Send
         </Button>
       </div>
     </div>
   </>
   ```
8. Auto-scroll: `useRef` on a bottom sentinel div + `useEffect(() => messagesEndRef.current?.scrollIntoView({behavior:'smooth'}), [messages, isThinking])`
9. Props: `isOpen: bool`, `onClose: () => void`, `projectId: string` (for future real API use)

**Relevant Context**:
- [`frontend/src/pages/HumanReview.jsx`](frontend/src/pages/HumanReview.jsx) line 15 — existing Carbon icon imports (`Checkmark`, `Close`) — `Close` is already imported; use the same import in ChatDrawer
- [`frontend/src/pages/HumanReview.jsx`](frontend/src/pages/HumanReview.jsx) line 4 — Carbon component import pattern to follow exactly
- [`frontend/src/components/IntakeDraftViewer.jsx`](frontend/src/components/IntakeDraftViewer.jsx) — Carbon component usage pattern

**Status**: `[ ] pending`

---

## Sub-Task 2: `ChatDrawer.scss`

**Intent**: Write all styles for the drawer. The drawer must NOT fight with existing Carbon styles. All selectors are scoped under `.chat-drawer`. The slide-in transition uses CSS `transform` (no JS animation). Backdrop is a semi-transparent overlay.

**Expected Outcomes**:
- `frontend/src/components/ChatDrawer/ChatDrawer.scss` exists
- Drawer is fixed, right-side, full-height, `z-index: 9000` (above Carbon modals at 9999 — use 8000 to stay below Carbon modals)
- Smooth 250ms ease-out transition on open/close
- Message bubbles: user = right-aligned blue, assistant = left-aligned white
- Input bar is pinned to drawer bottom with border-top separator
- Responsive: on screens < 480px, drawer is 100% width

**Full SCSS content**:

```scss
@use '@carbon/react/scss/spacing' as *;
@use '@carbon/react/scss/theme' as *;
@use '@carbon/react/scss/type' as *;

// Backdrop
.chat-drawer__backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 7999;
}

// Drawer panel
.chat-drawer {
  position: fixed;
  top: 0;
  right: 0;
  height: 100vh;
  width: 420px;
  background: #ffffff;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.18);
  z-index: 8000;
  display: flex;
  flex-direction: column;
  transform: translateX(100%);
  transition: transform 250ms ease-out;

  &--open {
    transform: translateX(0);
  }

  @media (max-width: 480px) {
    width: 100%;
  }
}

// Header
.chat-drawer__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-05 $spacing-06;
  background: linear-gradient(135deg, #0f62fe 0%, #0043ce 100%);
  color: #ffffff;
  flex-shrink: 0;
}

.chat-drawer__title {
  @include type-style('heading-03');
  color: #ffffff;
}

// Messages area
.chat-drawer__messages {
  flex: 1;
  overflow-y: auto;
  padding: $spacing-05 $spacing-05;
  background: #f4f4f4;
  display: flex;
  flex-direction: column;
  gap: $spacing-04;
}

// Individual message
.chat-drawer__message {
  display: flex;
  flex-direction: column;
  max-width: 85%;

  &--user {
    align-self: flex-end;
    align-items: flex-end;

    .chat-drawer__message-text {
      background: #0f62fe;
      color: #ffffff;
      border-radius: 16px 16px 4px 16px;
      padding: $spacing-03 $spacing-04;
      @include type-style('body-01');
    }
  }

  &--assistant {
    align-self: flex-start;
    align-items: flex-start;

    .chat-drawer__message-text {
      background: #ffffff;
      color: #161616;
      border-radius: 4px 16px 16px 16px;
      padding: $spacing-03 $spacing-04;
      @include type-style('body-01');
      box-shadow: 0 1px 4px rgba(0, 0, 0, 0.10);
    }
  }
}

.chat-drawer__message-time {
  @include type-style('helper-01');
  color: #8d8d8d;
  margin-top: $spacing-02;
  padding: 0 $spacing-03;
}

// Input bar
.chat-drawer__input-bar {
  display: flex;
  gap: $spacing-03;
  padding: $spacing-04 $spacing-05;
  background: #ffffff;
  border-top: 1px solid #e0e0e0;
  flex-shrink: 0;
  align-items: flex-end;

  // Make TextInput fill remaining space
  .cds--text-input-wrapper {
    flex: 1;
  }
}

// Floating Action Button
.chat-fab {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: #0f62fe;
  color: #ffffff;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.24);
  z-index: 7000;
  transition: background 150ms ease, transform 150ms ease, box-shadow 150ms ease;

  &:hover {
    background: #0043ce;
    transform: scale(1.08);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.30);
  }

  &:active {
    transform: scale(0.96);
  }

  // Badge dot — shown when there are unread messages (future use)
  &__badge {
    position: absolute;
    top: 4px;
    right: 4px;
    width: 10px;
    height: 10px;
    background: #da1e28;
    border-radius: 50%;
    border: 2px solid #ffffff;
  }

  svg {
    width: 24px;
    height: 24px;
    fill: #ffffff;
  }
}
```

**Todo List**:
1. Create `frontend/src/components/ChatDrawer/ChatDrawer.scss`
2. Write the full SCSS block above
3. Import it in `ChatDrawer/index.jsx` as `import './ChatDrawer.scss'`

**Relevant Context**:
- [`frontend/src/pages/HumanReview.scss`](frontend/src/pages/HumanReview.scss) lines 1–3 — uses same `@use '@carbon/react/scss/spacing'`, `theme`, `type` imports; follow exact same pattern
- [`frontend/src/pages/HumanReview.scss`](frontend/src/pages/HumanReview.scss) line 21 — existing gradient uses `$layer-02`/`$layer-03` tokens; the drawer header uses explicit `#0f62fe`/`#0043ce` (as per CODING_STANDARDS.md explicit color rule)
- z-index hierarchy: Carbon modals are at `z-index: 9999` → drawer at `8000` → backdrop at `7999` → FAB at `7000`

**Status**: `[ ] pending`

---

## Sub-Task 3: Wire Into `HumanReview.jsx`

**Intent**: Add the "Ask Assistant" button and the floating FAB to `HumanReview.jsx` with the minimum possible changes. The ChatDrawer component handles all its own state. `HumanReview.jsx` only needs to track `isChatOpen` (one new state variable) and render two new elements.

**Expected Outcomes**:
- `HumanReview.jsx` has exactly these additions — nothing else changes:
  - 1 new import line (`ChatDrawer`)
  - 1 new import icon (`Chat` from `@carbon/icons-react`)
  - 1 new state variable (`isChatOpen`)
  - 1 new `Button` in the header action row
  - 1 `<ChatDrawer>` element at the bottom of the JSX
  - 1 floating FAB `<button>` at the bottom of the JSX
- Existing Reject and Approve buttons are **untouched** — not moved, not renamed, not re-ordered
- The "Ask Assistant" button is `kind="ghost"` with a `Chat` icon — visually lighter than the Reject/Approve pair
- Button order in header: `[ Ask Assistant ]  [ Reject ]  [ Approve ]` — Ask Assistant is leftmost

**Exact diff to `HumanReview.jsx`**:

```
LINE 4 — add Chat to icon imports:
  BEFORE: import { Checkmark, Close } from '@carbon/icons-react';
  AFTER:  import { Checkmark, Close, Chat } from '@carbon/icons-react';

LINE 19 — add ChatDrawer import (after existing imports):
  ADD: import ChatDrawer from '../components/ChatDrawer';

LINE 39 — add isChatOpen state (after existing useState calls):
  ADD: const [isChatOpen, setIsChatOpen] = useState(false);

LINES 173–190 — inside the !alreadyReviewed block, add Ask Assistant button BEFORE Reject:
  ADD before <Button kind="secondary" ...Reject...>:
    <Button
      kind="ghost"
      renderIcon={Chat}
      onClick={() => setIsChatOpen(true)}
    >
      Ask Assistant
    </Button>

LINE 298 — before the closing </div> of the component, add:
  ADD:
    {/* Chat Drawer */}
    <ChatDrawer
      isOpen={isChatOpen}
      onClose={() => setIsChatOpen(false)}
      projectId={projectId}
    />

    {/* Floating chat button */}
    <button
      className="chat-fab"
      onClick={() => setIsChatOpen(true)}
      aria-label="Open assistant chat"
      title="Ask the Assistant"
    >
      <Chat />
    </button>
```

**Todo List**:
1. Open [`frontend/src/pages/HumanReview.jsx`](frontend/src/pages/HumanReview.jsx)
2. Add `Chat` to the `@carbon/icons-react` import on line 15
3. Add `import ChatDrawer from '../components/ChatDrawer';` after line 19
4. Add `const [isChatOpen, setIsChatOpen] = useState(false);` after line 44
5. Add the "Ask Assistant" `Button` at line 174 (inside `__header-actions`, BEFORE the Reject button)
6. Add `<ChatDrawer>` and the `.chat-fab` `<button>` before the closing `</div>` at line 298
7. Add the `.chat-fab` styles to [`frontend/src/pages/HumanReview.scss`](frontend/src/pages/HumanReview.scss) — import the `ChatDrawer.scss` already handles the `.chat-fab` class, so no duplication needed — BUT the FAB is rendered in `HumanReview.jsx` so the SCSS must be loaded. Since `ChatDrawer.scss` is imported via `ChatDrawer/index.jsx`, the `.chat-fab` styles are included automatically when `ChatDrawer` is imported. ✅ No SCSS change to `HumanReview.scss` needed.

**Relevant Context**:
- [`frontend/src/pages/HumanReview.jsx`](frontend/src/pages/HumanReview.jsx) line 15 — `Close` already imported from `@carbon/icons-react`; add `Chat` to same line
- [`frontend/src/pages/HumanReview.jsx`](frontend/src/pages/HumanReview.jsx) lines 173–190 — the `__header-actions` div; the new button goes first inside this div
- [`frontend/src/pages/HumanReview.jsx`](frontend/src/pages/HumanReview.jsx) line 298 — closing `</div>` of the root `.human-review` div; new elements go just before it
- `kind="ghost"` makes the Ask Assistant button visually lighter than `kind="secondary"` (Reject) and `kind="primary"` (Approve) — preserving the visual hierarchy of the action row

**Status**: `[ ] pending`

---

## Implementation Order

```
Sub-Task 1: ChatDrawer/index.jsx      ← Build the drawer component (standalone)
Sub-Task 2: ChatDrawer/ChatDrawer.scss ← Write all styles
Sub-Task 3: HumanReview.jsx patch     ← Wire in (6 surgical additions)
```

Sub-Tasks 1 and 2 can be done simultaneously.
Sub-Task 3 only starts after 1 and 2 are complete.

---

## Files Changed

```
CREATED:
frontend/src/components/ChatDrawer/index.jsx        (new)
frontend/src/components/ChatDrawer/ChatDrawer.scss  (new)

MODIFIED (surgical only):
frontend/src/pages/HumanReview.jsx
  Line 15  — add Chat to icon imports
  Line 19  — add ChatDrawer import
  Line 44  — add isChatOpen state
  Line 174 — add Ask Assistant button
  Line 298 — add <ChatDrawer> + .chat-fab button
```

**`HumanReview.scss` — zero changes needed.**

---

## What It Will Look Like

**Header action row** (only when not yet reviewed):
```
┌─────────────────────────────────────────────────────┐
│  Human Review                                       │
│  Review the intake draft...                         │
│                                    [Ask Assistant▾] [Reject✕] [Approve✓] │
└─────────────────────────────────────────────────────┘
```

**Floating button** (always visible, bottom-right):
```
                                    ┌───┐
                                    │ 💬│  ← fixed, always visible
                                    └───┘
```

**Drawer open state** (slides in from right):
```
┌─────────────────────────────────┐
│  Ask the Assistant           [✕]│  ← blue gradient header
├─────────────────────────────────┤
│                                 │
│  [user] What is the tech stack? │
│  [bot] Based on extracted facts │
│        the app uses Spring...   │
│                                 │
│  [bot] Thinking...              │
│                                 │
├─────────────────────────────────┤
│  [Ask about this project...] [→]│  ← input bar
└─────────────────────────────────┘
```

---

## Switching to Real API Later

In `ChatDrawer/index.jsx`, the mock section is:
```js
// MOCK_MODE: swap this flag when backend is ready
const MOCK_MODE = true;

// Replace this block with: const reply = await assistanceApi.sendMessage(projectId, text)
setTimeout(() => {
  const mockReplies = [...];
  setMessages(prev => [...prev, { role: 'assistant', text: mockReplies[...] }]);
  setIsThinking(false);
}, 800);
```

When the `/api/assistance` backend (from `ADVANCED_ASSISTANCE_PLAN.md`) is ready:
1. Change `MOCK_MODE = false`
2. Replace the `setTimeout` block with a real SSE stream call to `assistanceApi.sendMessage()`
3. That is the only change needed

---

**Plan Written By**: Bob (AI Planning Agent)
**Based On**: Full read of HumanReview.jsx (305 lines) + HumanReview.scss (134 lines)
**Status**: Ready for implementation — 3 sub-tasks, ~180 new lines total
