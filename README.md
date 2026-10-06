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

See `Agent_Echo/README.md` and `.env.example` for provider profile and environment variable names. Configure credentials locally; never commit them. The application does not automatically load `.env` files. Repository access and university email do not supply model API credentials.

## Publish from VS Code

Open this `Final_Project` folder itself. Check `git --version` and `git lfs version` in the VS Code terminal. Initialize a repository in this folder, run `git lfs install`, review and stage the included files, and commit. The committed `.gitattributes` configures the large CSV before it is added.

If no hosted repository exists, use `Publish to GitHub` and choose a private repository. If an empty hosted repository already exists, configure its URL as the remote instead of creating another repository. Invite teammates through GitHub repository settings.

For a first commit, Git may ask for `user.name` and `user.email`; configure these with your own chosen commit identity. These values identify commits and do not authenticate to GitHub.

Nothing is published by creating these setup files. Publication happens only when you push from Git or VS Code.
