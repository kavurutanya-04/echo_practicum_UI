# Echo practicum prototype

Echo combines five agents: Original (coordination/synthesis), Cherry (Text-to-SQL), Vanilla (textual RAG and systematic survey sentiment), Lime (indicator charts), and ZeroSugar (answer/evidence/chart-plan review). Sentiment uses source-linked provisional model labels and code-computed percentages; human quality validation remains pending. All employee data is synthetic. The prototype supports human review; it does not make personnel decisions. It currently runs in a terminal and exports local files.

Agent responsibilities and examples are in [Agent_Echo/AGENT_ROLES.md](Agent_Echo/AGENT_ROLES.md). [Agent_Echo/TESTING_AND_RAG.md](Agent_Echo/TESTING_AND_RAG.md) distinguishes offline engineering checks from real model evaluation, explains secure API setup and shows how to inspect retrieval traces. No API configuration means no real LLM evaluation; demo responses and judge scores are explicitly scripted.

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

Each collaborator supplies authorized credentials locally. Create `Agent_Echo/.env` by copying `Agent_Echo/.env.example` if a private `.env` does not already exist. Fill in the GW values: `GW_AZURE_OPENAI_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, and `AZURE_OPENAI_API_VERSION`. The application reads named keys and connection settings from this private file at live setup. Existing terminal/system environment variables take precedence, so `.env` is optional when those settings already exist. Agent/profile selection belongs in `connections.json` or terminal environment variables. Only group members may use the group's GW key, which must not be shared outside that group. Optional NVIDIA models share `NVIDIA_API_KEY`; OpenCode uses `OPENCODE_API_KEY`.

GitHub contains the code and empty-key template; `.env` is excluded from Git and must not be shared. A collaborator only needs keys for the profiles they use. Without credentials they can run offline demos and local tests; live calls require their selected provider's key. Repository access and university email do not supply API credentials. Provider quotas and free-endpoint availability can change; a prepared profile is not proof of live access or model quality.

## Publish from VS Code

Open this `Final_Project` folder itself. Check `git --version` and `git lfs version` in the VS Code terminal. Initialize a repository in this folder, run `git lfs install`, review and stage the included files, and commit. The committed `.gitattributes` configures the large CSV before it is added.

If no hosted repository exists, use `Publish to GitHub` and choose a private repository. If an empty hosted repository already exists, configure its URL as the remote instead of creating another repository. Invite teammates through GitHub repository settings.

For a first commit, Git may ask for `user.name` and `user.email`; configure these with your own chosen commit identity. These values identify commits and do not authenticate to GitHub.

Nothing is published by creating these setup files. Publication happens only when you push from Git or VS Code.
