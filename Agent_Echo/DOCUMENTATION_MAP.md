# Echo documentation map

Reviewed: 2026-10-21 (America/New_York), against the current local implementation
and the saved live artifacts through run nine. Current answers use source-facts-v3;
historical test/replay counts below predate it. This is an index and maintenance guide, not an
additional runtime policy or a benchmark. No new provider request was made for this review.

## Current entry points and responsibilities

| Reference | Purpose and authority |
| --- | --- |
| [Workspace guidance](../../AGENTS.md) | Routes Practicum work to the Echo project; also covers unrelated coursework. Local parent file, outside the Echo Git repository. |
| [Project guidance](../AGENTS.md) | Instructions for the coding assistant maintaining Echo; read with the context file once per chat. Echo does not load this file as an agent prompt. |
| [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) | Compact current state, observed runs, approved decisions and next test. |
| [Repository README](../README.md) | Clone/setup, repository contents and collaboration. |
| [Application README](README.md) | Running Echo, configuration, artifacts, statuses and data access. |
| [AGENT_ROLES.md](AGENT_ROLES.md) | Responsibilities, tools, inputs/outputs and boundaries of all five roles. |
| [WORKFLOW_RELIABILITY.md](WORKFLOW_RELIABILITY.md) | Planning, bounded retries, declines, retained evidence, structured repair feedback, independent review, release gates and minimized diagnostics. |
| [SOURCE_GROUNDING.md](SOURCE_GROUNDING.md) | Source-bound numeric facts, cited synthesis, literal examples, v2 presentation and v1 replay compatibility. |
| [TESTING_AND_RAG.md](TESTING_AND_RAG.md) | Offline checks, provider probes, live evaluation, pacing and retrieval inspection. Latest suite result is dated there; a test count is not classifier accuracy. |
| [REFERENCE_VALIDATION.md](REFERENCE_VALIDATION.md) | Historical classroom comparison with current implementation corrections. Historical source-review dates are distinct from the current documentation review. |
| [Dataset README](../files_update/README.md) | Synthetic source definitions, periods, denominators and privacy assumptions; runtime behavior belongs to the code and application guides. |
| [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) | Attribution and reproduced license text. Preserve notices; do not rewrite them as project status. Reviewed without changing the license. |

## Executable configuration and instructions

| Source | Controls |
| --- | --- |
| [connections.json](connections.json) and [connections.py](agents/connections.py) | Non-secret model/endpoint/API settings, limits, role selection and key loading. Only key values come from process variables or ignored `.env`. |
| [.env.example](.env.example) | Empty key-name template; never actual credentials. |
| [policies.py](agents/policies.py) | Six common rules composed into analysis/model calls. This is the executable policy source, separate from coding-assistant guidance. |
| [Original](agents/original.py), [Cherry](agents/cherry.py), [Vanilla](agents/vanilla.py), [Lime](agents/lime.py), [ZeroSugar](agents/zero_sugar.py) | Role-specific prompts, tools and call paths. Shared rules do not transfer SQL, classification or verification ownership. |
| [run_agent.py](run_agent.py), [runtime.py](agents/runtime.py), [data_access.py](agents/data_access.py), [grounding.py](agents/grounding.py) | CLI scope/options, execution, source restrictions and deterministic checks. Code is authoritative when prose disagrees. |

## Local background and historical drafts

These four files are intentionally ignored by the repository and may be absent from a
clone. Their current-status notes were reviewed locally; inclusion here does not publish
them or approve their proposals.

| Local reference | How to use it |
| --- | --- |
| [technical_setup_agents.md](../technical_setup_agents.md) | Current local setup directions plus the distinction between installed SDKs and implemented adapters. |
| [echo_brainstorm_resumen_y_decisiones.md](../echo_brainstorm_resumen_y_decisiones.md) | Product/architecture proposals and unresolved decisions. Current reliability repairs preserve the five roles; proposed business execution is not implemented. |
| [brainstorm_employee_engagement.md](../brainstorm_employee_engagement.md) | September problem exploration, retained as history rather than current runtime specifications. |
| [alternativas_employee_engagement.md](../alternativas_employee_engagement.md) | September project/market comparison, not a refreshed market assessment or final selection. |

## Maintenance rules

1. Verify changed behavior in code/configuration and the relevant result/log before updating claims.
2. Update the context entry and affected operating guides together. Update this map when a
   reference is added, moved, retired or changes purpose; do not copy every implementation
   detail into each file.
3. Preserve historical dates, failed runs and unapproved proposals. Separate implemented,
   observed, locally tested and pending-live behavior. Keep source-bearing reports local.
4. Check relative links, commands and contradictory old instructions. Documentation-only
   updates need content/link review, not live model requests or a new reasoning benchmark.
5. Generated Codex memory, classroom sources, source datasets and license text are not
   automatically edited by project-document maintenance.

Current next local attempt: repeat the Recognition-comments question with the same M14/Q3
2026 scope and `--profile apinex_test --run-seconds 1000`, saving a fresh artifact such as
`reports/apinex_prueba_vanilla_10.json`. Runs six through nine have saved observations in
PROJECT_CONTEXT.md. Per user instruction, no tests or API calls were run for v3; a supplied
command is not proof of completion. Interactive chat, natural-language date resolution,
authentication and enterprise writes remain deferred.

Historical documentation review checks: 17 Markdown references and 147 relative file/heading links checked without
errors; documented CLI options checked against `--help`. License text was unchanged.
Only APInex's descriptive status label changed in `connections.json`; endpoints, keys,
model assignments, limits and pacing settings were unchanged. The 207-test result belongs
to the prior implementation verification, not a new run for this documentation update.
