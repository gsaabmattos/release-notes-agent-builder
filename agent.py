import argparse
import logging
import os
from config.settings import Settings
from modules.version_resolver import VersionResolver
from modules.jira_client import JiraClient
from modules.notes_extractor import NotesExtractor
from modules.llm_consolidator import LLMConsolidator
from modules.outline_publisher import OutlinePublisher
from modules.state_manager import StateManager

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/agent.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Release Notes Agent")
    parser.add_argument(
        "--version", default="latest",
        help="Versão-alvo: 'latest', 'unreleased' ou ex: '1.4.2'"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Reprocessa mesmo sem alterações detectadas"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Gera o documento localmente sem publicar no Wiki.js"
    )
    args = parser.parse_args()

    cfg = Settings()
    jira = JiraClient(cfg)
    resolver = VersionResolver(jira, cfg)
    extractor = NotesExtractor(jira, cfg)
    consolidator = LLMConsolidator(cfg)
    publisher = OutlinePublisher(cfg)
    state = StateManager(cfg)

    version_name = resolver.resolve(args.version)
    log.info(f"Versão-alvo: {version_name}")

    tickets = extractor.get_done_tickets(version_name)
    log.info(f"{len(tickets)} tickets DONE encontrados")

    changed = state.get_changed_tickets(version_name, tickets)
    if not changed and not args.force:
        log.info("Nenhuma alteração detectada. Encerrando.")
        return

    log.info(f"{len(changed)} ticket(s) com alterações detectadas")
    notes = extractor.extract_release_notes(tickets)
    document = consolidator.consolidate(version_name, notes)

    os.makedirs(cfg.output_dir, exist_ok=True)
    output_path = f"{cfg.output_dir}/{version_name.replace('/', '_')}.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(document)
    log.info(f"Backup local salvo em {output_path}")

    if args.dry_run:
        log.info(f"Dry-run: documento salvo em {output_path}, publicação ignorada.")
        return

    publisher.publish(version_name, document)
    state.save(version_name, tickets)
    log.info(f"Publicado no Outline: {version_name}")


if __name__ == "__main__":
    main()
