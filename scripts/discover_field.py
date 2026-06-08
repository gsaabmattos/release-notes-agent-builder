"""
Script auxiliar: descobre o ID do campo "Release Notes" no seu Jira.
Execute antes de usar o agente pela primeira vez:

    python scripts/discover_field.py

Depois atualize a constante RELEASE_NOTES_FIELD em modules/notes_extractor.py
com o ID retornado (ex: customfield_10058).
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from config.settings import Settings
from modules.jira_client import JiraClient


def main():
    cfg = Settings()
    jira = JiraClient(cfg)

    print("Buscando todos os campos customizados no Jira...\n")
    fields = jira.client.get_all_fields()

    print("Campos que contêm 'release' ou 'note' no nome:")
    print("-" * 50)
    found = False
    for f in fields:
        name = f.get("name", "")
        if "release" in name.lower() or "note" in name.lower():
            print(f"  ID: {f['id']:<30} Nome: {name}")
            found = True

    if not found:
        print("  Nenhum campo encontrado com 'release' ou 'note'.")
        print("\nTodos os campos customizados disponíveis:")
        print("-" * 50)
        for f in fields:
            if f["id"].startswith("customfield_"):
                print(f"  ID: {f['id']:<30} Nome: {f.get('name', '')}")

    print("\nAtualize RELEASE_NOTES_FIELD em modules/notes_extractor.py com o ID correto.")


if __name__ == "__main__":
    main()
