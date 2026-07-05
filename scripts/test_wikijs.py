"""
Script auxiliar: valida a conexão com o Wiki.js antes de usar o agente.
Execute:

    python scripts/test_wikijs.py
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
from modules.wikijs_publisher import WikiJSPublisher


def main():
    cfg = Settings()
    publisher = WikiJSPublisher(cfg)

    print(f"Testando conexão com Wiki.js em {cfg.wikijs_url}...")
    ok = publisher.test_connection()

    if ok:
        print("✓ Conexão OK — Wiki.js respondeu corretamente")
        print(f"  Base path configurado: {cfg.wikijs_base_path}")
        print(f"  Locale configurado:    {cfg.wikijs_locale}")
    else:
        print("✗ Falha na conexão — verifique WIKIJS_URL e WIKIJS_API_TOKEN no .env")
        sys.exit(1)


if __name__ == "__main__":
    main()
