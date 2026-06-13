# Release Notes Agent

A local agent that collects DONE tickets from Jira, extracts the "Release Notes" field, and publishes a consolidated document to Wiki.js using a local LLM (Ollama).

## Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) installed and running
- Jira Cloud access (API Token)
- Wiki.js running with the API enabled

## Quick Setup

```bash
# 1. Install Ollama and the model
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:7b

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure credentials
cp .env.example .env
nano .env   # fill in your credentials

# 5. Initial validation
python scripts/test_jira.py
python scripts/discover_field.py   # note the field ID and update modules/notes_extractor.py
python scripts/test_wikijs.py
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

# Force reprocessing even without detected changes
python agent.py --version POS-2.24.0 --force

# Post the generated RN in a .md file to validate locally before sending to the Doc POrtal
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
│   ├── llm_consolidator.py
│   ├── wikijs_publisher.py
│   └── state_manager.py
├── prompts/
│   └── consolidation.txt     # Customizable LLM prompt
├── scripts/
│   ├── discover_field.py     # Discovers the Release Notes field ID
│   ├── test_jira.py          # Validates Jira connection
│   └── test_wikijs.py        # Validates Wiki.js connection
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
