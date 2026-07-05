"""
Script auxiliar: valida a conexão com o Jira e lista as versões disponíveis.
Execute:

    python scripts/test_jira.py
"""

import os
import sys

# Ensure Python 3.11+ for consistent syntax and typing features
if sys.version_info < (3, 11):
    sys.stderr.write(
        f"This script requires Python 3.11+.\n"
        f"Current interpreter: {sys.version.split()[0]}\n"
        "Please recreate the virtual environment with Python 3.11 or newer.\n"
    )
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from config.settings import Settings
from modules.jira_client import JiraClient


def main():
    cfg = Settings()
    jira = JiraClient(cfg)

    print(f"Conectando ao Jira: {cfg.jira_url}")
    print(f"Projeto: {cfg.jira_project_key}\n")

    try:
        versions = jira.get_all_versions()
        print(f"✓ Conexão OK — {len(versions)} versão(ões) encontradas:\n")
        for v in versions:
            status = "Released" if v.get("released") else "Unreleased"
            date = v.get("releaseDate", "sem data")
            print(f"  [{status:<10}] {v['name']:<20} {date}")

        latest = jira.get_latest_released_version()
        print(f"\n→ Última versão released: {latest}")

    except Exception as e:
        print(f"✗ Erro ao conectar: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
