# Echo project guidance

## Start with a small amount of context

Read this guidance and [Agent_Echo/PROJECT_CONTEXT.md](Agent_Echo/PROJECT_CONTEXT.md) once per chat when Echo work first becomes relevant, unless their contents are already available in the chat context. Reuse that orientation rather than repeating the reading chain for every question. Reread only relevant sections if the documents change or verification is needed, and follow only the links needed for the current request. This applies when opening `Final_Project` directly as well as when working from the parent Practicum workspace.

- Verify current code/configuration before changing behavior. Do not reread the entire repository for each question.
- Keep implemented behavior, observed results, proposals, and unresolved decisions distinct.
- When changing synthesis or presentation, preserve facts and provenance without freezing wording. Keep the role instructions, answer/replay contract and review schema aligned; distinguish mandatory corrections from optional suggestions, and retain compatibility for saved answer versions.
- Keep objective integrity checks separate from model judgment. Narrative digits, quantifiers and repairable presentation are not proof of false meaning. Current source-facts-v3 sends those signals to ZeroSugar without making them deterministic failures; preserve v1/v2 replay. Retain source/scope, quote-literalness, coverage and structured arithmetic checks. Do not add language-pattern rejection rules as substitutes for semantic review.
- Preserve the existing five roles unless the user requests a role change. Echo is the overall system, not an additional agent.
- Preserve manager/date scoping, read-only data tools, citations, independent finding review, and withholding of unsupported output.
- Do not invent numbers, missing coverage, causal effects, benchmark results, or successful provider access. Demo and connection tests do not establish analytical quality.
- Use English for application code, prompts, project documentation, and manager-facing outputs. Explain work in the user's requested language.
- Credentials belong in the ignored local `.env` or approved process environment. Never read or print keys for orientation. Current non-secret model/endpoint settings and role assignments belong in `Agent_Echo/connections.json`.
- For code changes, use the checks documented in `Agent_Echo/TESTING_AND_RAG.md` as appropriate. Report what was actually run. Documentation-only changes need link/content review, not live API calls.
- Respect a user instruction to skip tests or live calls. The 2026-10-21 v3 update was authorized for code/documentation and GitHub publication without local tests or API calls; earlier test counts do not validate it. A future successful-answer claim requires inspecting the actual new run and completed review.

## Maintain continuity

After a user-authorized change materially affects architecture, configuration, verified results, priorities, or pending decisions, update the relevant section of `Agent_Echo/PROJECT_CONTEXT.md` in the same task. Keep it compact and point to detailed sources rather than copying them.

Use [Agent_Echo/DOCUMENTATION_MAP.md](Agent_Echo/DOCUMENTATION_MAP.md) to find all operating guides, source contracts, dataset documentation and local historical notes. Update affected references together, checking links and obsolete commands. Preserve historical evidence and license notices rather than rewriting every file after each change.

This `AGENTS.md` guides the coding assistant; it is not an Echo runtime prompt. Echo's six shared model rules live in `Agent_Echo/agents/policies.py`, role-specific instructions in the five agent modules, and CLI behavior in `Agent_Echo/run_agent.py`. Keep responsibilities and deterministic controls in their existing modules; do not introduce a new policy agent or move role-specific logic into this guidance.

Record dates and evidence for observations. Do not turn a suggestion from a conversation into an approved implementation or replace detailed source documentation with an unsupported summary. Explain unresolved contradictions instead of silently choosing an older note.

This guidance and the context file support future chats; they do not automatically import every previous conversation or start background synchronization. Do not edit Codex's generated memory store as part of ordinary project documentation maintenance.
