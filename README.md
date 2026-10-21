# Echo practicum prototype

Echo combines five agents: Original (coordination/synthesis), Cherry (Text-to-SQL), Vanilla (textual RAG and systematic survey sentiment), Lime (indicator charts), and ZeroSugar (answer/evidence/chart-plan review). Sentiment uses source-linked provisional model labels and code-computed percentages; human quality validation remains pending. All employee data is synthetic. The prototype supports human review; it does not make personnel decisions. It currently runs in a terminal and exports local files.

Agent responsibilities and examples are in [Agent_Echo/AGENT_ROLES.md](Agent_Echo/AGENT_ROLES.md). [Agent_Echo/TESTING_AND_RAG.md](Agent_Echo/TESTING_AND_RAG.md) distinguishes offline engineering checks from real model evaluation, explains secure API setup and shows how to inspect retrieval traces. No API configuration means no real LLM evaluation; demo responses and judge scores are explicitly scripted.

Documentation reviewed 2026-10-21. Start with [project context](Agent_Echo/PROJECT_CONTEXT.md)
and the [complete reference map](Agent_Echo/DOCUMENTATION_MAP.md). The latest implementation
passed 207 offline tests. Luna's fourth run completed the numeric comparison; the fifth
comment-classification run failed before ZeroSugar. Routing, retained classification
progress, individual comment sources and safe diagnostics were then repaired. The sixth
live run is the next pending test, not a completed result.

## Repository contents

- `Agent_Echo/`: application code, tests, provider configuration templates, and documentation.
- `files_update/`: eleven application CSVs, the schema dictionary, the import manifest, and dataset documentation.

The root `.gitignore` excludes earlier drafts, classroom references, private QA files, generated databases, reports, caches, virtual environments, and credentials. `QA_manifest.csv` and `QA_data_dictionary.csv` are required import metadata and remain included. Exclusions apply to untracked files; they do not remove anything already committed.

`OP_work_requests.csv` uses Git LFS. Install Git with Git LFS support and run `git lfs install` before the first commit or clone. Each collaborator can download all included synthetic datasets; agent access restrictions apply inside the application, not to repository collaborators.

## Reproduce on Windows

Install Python 3.11 or newer, Git, and Git LFS. Clone the repository using VS Code's `Git: Clone` command or Git. In a terminal at the repository root:

```powershell
git lfs pull
cd Agent_Echo
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe import_data.py
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe run_agent.py original --manager M14 --demo
```

The importer creates `Agent_Echo/data/echo.db` locally and validates all eleven tables. Run it once after cloning; rebuilding an existing database requires the explicit `--replace` option. The demo uses scripted model responses with real local tools, requires no credentials, and does not evaluate live model reasoning.

On macOS or Linux, use `python3` where needed and `.venv/bin/python` instead of `.venv\Scripts\python.exe`.

## Live model configuration

**The primary/final connection is the professor's group-assigned GW Azure resource (`gw_azure`), used by all five agents by default.** See [Agent_Echo/README.md](Agent_Echo/README.md#primary-final-connection-gw-azure-ai-foundry) and [Agent_Echo/.env.example](Agent_Echo/.env.example) for setup. Other profiles, including NVIDIA Nemotron/GLM and OpenCode DeepSeek, are optional tests with no automatic fallback. Select `--profile gw_azure` for a final GW-only run, regardless of temporary per-role test overrides.

Each collaborator supplies authorized credentials locally. Create `Agent_Echo/.env` from
`Agent_Echo/.env.example` only if a private `.env` does not already exist. Store API keys
only there: `GW_AZURE_OPENAI_KEY` for the assigned university resource, or the selected
optional provider's key. Endpoint, model/deployment, API version, limits and role
assignments belong exclusively in `Agent_Echo/connections.json`. Selection is CLI
`--profile`, then the role's JSON assignment, then JSON `default_profile`. Old model,
endpoint and `ECHO_*_PROFILE` environment overrides are not used. Process API-key values
take precedence over the private `.env`. Group credentials must stay within the group.

The user's current optional experiment selects `--profile apinex_test`, using
`free/gpt-6-luna` for every role with `APINEX_API_KEY`, 6000 maximum output tokens and
shared 20-second request spacing within one process. HTTP 429 retries respect the shared
cooldown. Run one terminal process per key; separate processes are not coordinated.
This explicit trial does not change the JSON default from `gw_azure`. See the
[APInex setup and limits](Agent_Echo/TESTING_AND_RAG.md#apinex-sdk-trial).

GitHub contains the code and empty-key template; `.env` is excluded from Git and must not be shared. A collaborator only needs keys for the profiles they use. Without credentials they can run offline demos and local tests; live calls require their selected provider's key. Repository access and university email do not supply API credentials. Provider quotas and free-endpoint availability can change; a prepared profile is not proof of live access or model quality.

Trial access checks on 2026-10-16 did not confirm a working connection: OpenCode's free tier rejected external Python requests with HTTP 403 `FreeTierError`; NVIDIA model checks returned HTTP 404 or timed out. [Agent_Echo/README.md](Agent_Echo/README.md#test-nvidia-and-opencode-with-private-local-keys) records the scope and limitations. Connection failures now report safe HTTP/timeout categories without exposing credentials. The primary/final provider remains GW Azure.

## Publish from VS Code

The existing repository is [echo-practicum](https://github.com/percyroggwu/echo-practicum).
Open the cloned `Final_Project` root in VS Code; do not initialize another repository
inside `Agent_Echo`. From the root terminal, enter `cd Agent_Echo` before running
`python run_agent.py`. Opening `Agent_Echo` alone is also valid; VS Code may offer to
recognize its parent Git repository. Recognizing it does not overwrite source files.

Check `git --version` and `git lfs version`, run `git lfs install` as needed, review only
the intended files, commit and push. The committed `.gitattributes` configures the large CSV.

For a separate new copy without a hosted repository, use `Publish to GitHub` and choose
the intended visibility; for an existing remote, push there. Do not create a duplicate
hosted repository for this checkout. Invite teammates through GitHub repository settings.

For a first commit, Git may ask for `user.name` and `user.email`; configure these with your own chosen commit identity. These values identify commits and do not authenticate to GitHub.

Nothing is published by creating these setup files. Publication happens only when you push from Git or VS Code.
