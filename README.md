<img width="1916" height="1440" alt="RN_Arch" src="https://github.com/user-attachments/assets/b09e2ce6-026f-45ae-9408-106850f04d9b" />

Release Notes Agent — how it works

The agent is a command-line tool (agent.py) that, for a given Jira fix version (or several combined), pulls every "Done" ticket, extracts its Release Notes field, rehosts any embedded images so they don't break, assembles everything into one document, and publishes it to Outline. Each step is owned by a small, single-purpose module:

JiraClient — the only module that talks to Jira. Runs the JQL queries that fetch "Done" tickets for a version (or with no fix version, for the unreleased mode), looks up released versions, and downloads image bytes from Jira attachment/media URLs using the authenticated session.

VersionResolver — turns the --version argument into a concrete Jira version name: latest resolves to the most recently released version, unreleased is passed through as-is, and any explicit version string (e.g. POS-2.24.0) is used directly.

NotesExtractor — reads each ticket's custom "Release Notes" field and converts it to clean markdown, whether it arrives as a Jira wiki-markup string or as an ADF (rich text) document. This is also where image references — both !file.png! wiki syntax and ADF media nodes — get resolved against the ticket's real attachment list into proper ![alt](url) markdown links.

ReleaseNotesBuilder — takes the extracted notes and assembles the final document: groups tickets under their parent feature, splits them into Enhancements vs. Bug Fixes, and — when more than one version is requested — combines them into a single document with the lowest version as the main release and the rest as hot-fix sections. Purely deterministic formatting logic; no LLM involved despite the module's history.

ImageRelocator — the piece that fixes broken images in Outline. Scans the assembled document for any image link pointing at Jira, downloads it through JiraClient, re-uploads it via OutlinePublisher, and rewrites the link to the new Outline-hosted URL. Anything not hosted on Jira is left untouched.

OutlinePublisher — the only module that talks to Outline. Finds an existing document by title and updates it, or creates a new one; also handles the low-level attachment upload flow (attachments.create + the resulting signed upload) used by ImageRelocator.

StateManager — keeps a per-version JSON snapshot of each ticket's updated timestamp under state/, so the agent can detect whether anything actually changed since the last run and skip unnecessary republishing (unless --force is passed).

agent.py — the orchestrator. Wires all of the above together for a single run: resolve version(s) → fetch tickets → extract notes → build the document → relocate images → publish → save state.



# Release Notes Agent

A local agent that collects DONE tickets from Jira, extracts the "Release Notes" field, and publishes a consolidated document — with images rehosted from Jira — to Outline.

## Prerequisites

- Python 3.11+
- Jira Cloud access (API Token)
- Outline instance with the API enabled

## Quick Setup

```bash
# 1. Create a virtual environment
# If you don't have Python 3.11 installed, install it (Homebrew):
#
# ```bash
# brew install python@3.11
# ```

python3.11 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure credentials
cp .env.example .env
nano .env   # fill in your credentials

# 4. Initial validation
python scripts/test_jira.py
python scripts/discover_field.py   # note the field ID and update modules/notes_extractor.py
```

## Usage

```bash
source venv/bin/activate

# Specific version
python agent.py --version POS-2.24.0

# Latest Released version in Jira
python agent.py --version latest

# DONE tickets with no fixVersion
python agent.py --version unreleased

# Combine multiple versions (e.g. a base release plus hotfixes) into one document
python agent.py --version POS-2.24.0 POS-2.24.1

# Force reprocessing even without detected changes
python agent.py --version POS-2.24.0 --force

# Post the generated RN in a .md file to validate locally before sending to the Doc Portal
python agent.py --version POS-2.24.0 --dry-run --force

```

## Scheduling (cron)

```bash
crontab -e
```

Add an entry (example: every Monday at 9am):

```
0 9 * * 1 /path/to/venv/bin/python /path/to/agent.py --version latest >> /path/to/logs/cron.log 2>&1
```

## Project Structure

```
release-notes-agent/
├── agent.py                  # Main entrypoint
├── .env                      # Credentials (do not commit)
├── .env.example              # Template
├── requirements.txt
├── config/
│   └── settings.py
├── modules/
│   ├── jira_client.py
│   ├── version_resolver.py
│   ├── notes_extractor.py
│   ├── release_notes_builder.py
│   ├── image_relocator.py
│   ├── outline_publisher.py
│   └── state_manager.py
├── scripts/
│   ├── discover_field.py     # Discovers the Release Notes field ID
│   └── test_jira.py          # Validates Jira connection
├── state/                    # Per-version state (gitignored)
├── output/                   # Local document backups (gitignored)
└── logs/                     # Execution logs (gitignored)
```

## First Run: Discovering the Release Notes Field

The custom field ID for "Release Notes" varies per Jira instance. Run:

```bash
python scripts/discover_field.py
```

Note the returned ID (e.g. `customfield_10058`) and update the `RELEASE_NOTES_FIELD`
constant in `modules/notes_extractor.py`.
