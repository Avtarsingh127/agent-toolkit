---
name: handoff
description: Write a compact handoff note for the current task so a fresh session (or the other agent) can continue without the long context.
claude:
  disable-model-invocation: true
---

Write a handoff note so this work can continue in a brand-new session, in Claude Code or Antigravity, with no access to this conversation.

Save it to `.agents/handoff/<YYYY-MM-DD>-<short-task-slug>.md` in the project root (create the directory; add `.agents/handoff/` to `.gitignore` if missing). Keep it under 60 lines:

```
# Handoff: <task>
## Goal
<one or two sentences, including the definition of done>
## State
- Done: ...
- In progress: ...
- Not started: ...
## Files touched
- path — what changed and why
## Decisions made (and rejected alternatives)
- ...
## How to verify
- exact commands and what passing looks like
## Next steps
1. ...
## Gotchas
- environment/project/context notes, flaky steps, things that wasted time
```

Then reply with only: the file path, and the line to start the next session with:
`Continue the task in @<path>. Read it first, then confirm the next step before editing.`
<!-- only:claude -->
Remind me to run `/clear` (free) rather than `/compact`.
<!-- end -->
<!-- only:antigravity -->
Remind me to start a new conversation for the next step.
<!-- end -->
