import argparse
import logging
import os
from config.settings import Settings
from modules.version_resolver import VersionResolver
from modules.jira_client import JiraClient
from modules.notes_extractor import NotesExtractor
from modules.llm_consolidator import LLMConsolidator, _version_sort_key
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
        "--version", nargs="+", default=["latest"],
        help=(
            "Versão-alvo (um ou mais): 'latest', 'unreleased' ou ex: "
            "'POS-2.24.0' — para combinar versões: --version POS-2.24.0 POS-2.24.1"
        ),
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Reprocessa mesmo sem alterações detectadas"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Gera o documento localmente sem publicar no Outline"
    )
    args = parser.parse_args()

    cfg = Settings()
    jira = JiraClient(cfg)
    resolver = VersionResolver(jira, cfg)
    extractor = NotesExtractor(jira, cfg)
    consolidator = LLMConsolidator(cfg)
    publisher = OutlinePublisher(cfg)
    state = StateManager(cfg)

    versions_notes: list[tuple[str, list[dict]]] = []
    all_tickets: dict[str, list[dict]] = {}
    any_changed = False

    for v_arg in args.version:
        version_name = resolver.resolve(v_arg)
        log.info(f"Versão-alvo: {version_name}")

        tickets = extractor.get_done_tickets(version_name)
        log.info(f"{len(tickets)} tickets DONE encontrados para {version_name}")

        changed = state.get_changed_tickets(version_name, tickets)
        if changed:
            any_changed = True

        all_tickets[version_name] = tickets
        notes = extractor.extract_release_notes(tickets)
        versions_notes.append((version_name, notes))

    if not any_changed and not args.force:
        log.info("Nenhuma alteração detectada. Encerrando.")
        return

    document = consolidator.consolidate_multi(versions_notes)

    # Output file named after the primary (semantically lowest) version
    primary = min((vn for vn, _ in versions_notes), key=_version_sort_key)
    os.makedirs(cfg.output_dir, exist_ok=True)
    output_path = f"{cfg.output_dir}/{primary.replace('/', '_')}.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(document)
    log.info(f"Backup local salvo em {output_path}")

    if args.dry_run:
        log.info(f"Dry-run: documento salvo em {output_path}, publicação ignorada.")
        return

    publisher.publish(primary, document)
    for version_name, tickets in all_tickets.items():
        state.save(version_name, tickets)
    log.info(f"Publicado no Outline: {primary}")


if __name__ == "__main__":
    main()
