import logging

log = logging.getLogger(__name__)

# ID do campo customizado "Release Notes" no seu Jira.
# Execute o script de descoberta (seção 7.4 do documento) para confirmar.
# Exemplo: customfield_10058
RELEASE_NOTES_FIELD = "customfield_release_notes"


class NotesExtractor:
    def __init__(self, jira_client, cfg):
        self.jira = jira_client
        self.cfg = cfg

    def get_done_tickets(self, version_name: str) -> list[dict]:
        if version_name == "unreleased":
            return self.jira.get_all_done_tickets()
        return self.jira.get_done_tickets_by_version(version_name)

    def extract_release_notes(self, tickets: list[dict]) -> list[dict]:
        results = []
        skipped = 0
        for ticket in tickets:
            fields = ticket.get("fields", {})
            raw_notes = fields.get(RELEASE_NOTES_FIELD)

            if not raw_notes:
                skipped += 1
                log.debug(f"Ticket {ticket['key']}: campo Release Notes vazio, ignorado")
                continue

            note_text = (
                self._parse_adf(raw_notes)
                if isinstance(raw_notes, dict)
                else str(raw_notes).strip()
            )

            if not note_text:
                skipped += 1
                continue

            results.append({
                "key": ticket["key"],
                "summary": fields.get("summary", ""),
                "notes": note_text,
                "updated": fields.get("updated", "")
            })

        log.info(
            f"Extração concluída: {len(results)} com notas, "
            f"{skipped} ignorados (campo vazio)"
        )
        return results

    def _parse_adf(self, adf_doc: dict) -> str:
        """
        Converte Atlassian Document Format (ADF) para texto plano.
        O campo Release Notes pode retornar ADF quando o editor é rich text.
        """
        texts = []
        self._walk_adf(adf_doc, texts)
        return " ".join(texts).strip()

    def _walk_adf(self, node: dict, texts: list):
        """Percorre recursivamente o ADF e coleta os nós de texto."""
        if not isinstance(node, dict):
            return
        if node.get("type") == "text":
            texts.append(node.get("text", ""))
        for child in node.get("content", []):
            self._walk_adf(child, texts)
