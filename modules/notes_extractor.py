import logging

log = logging.getLogger(__name__)

# ID do campo customizado "Release Notes" no seu Jira.
# Execute o script de descoberta (seção 7.4 do documento) para confirmar.
# Exemplo: customfield_10058
RELEASE_NOTES_FIELD = "customfield_10066"


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

            parent = fields.get("parent", {})
            parent_key = parent.get("key", "")
            parent_summary = parent.get("fields", {}).get("summary", "")

            results.append({
                "key": ticket["key"],
                "summary": fields.get("summary", ""),
                "issuetype": fields.get("issuetype", {}).get("name", "Task"),
                "parent_key": parent_key,
                "parent_summary": parent_summary,
                "notes": note_text,
                "updated": fields.get("updated", "")
            })

        log.info(
            f"Extração concluída: {len(results)} com notas, "
            f"{skipped} ignorados (campo vazio)"
        )
        return results

    def _parse_adf(self, adf_doc: dict) -> str:
        return self._adf_to_md(adf_doc).strip()

    def _adf_to_md(self, node: dict) -> str:
        if not isinstance(node, dict):
            return ""

        t = node.get("type", "")
        content = node.get("content", [])
        attrs = node.get("attrs", {})

        if t in ("doc",):
            return "".join(self._adf_to_md(c) for c in content)

        if t == "paragraph":
            inner = "".join(self._adf_to_md(c) for c in content)
            return inner + "\n\n"

        if t == "hardBreak":
            return "\n"

        if t == "heading":
            level = attrs.get("level", 1)
            inner = "".join(self._adf_to_md(c) for c in content)
            return "#" * level + " " + inner.strip() + "\n\n"

        if t == "blockquote":
            inner = "".join(self._adf_to_md(c) for c in content).strip()
            return "\n".join(f"> {line}" for line in inner.splitlines()) + "\n\n"

        if t == "codeBlock":
            lang = attrs.get("language", "")
            inner = "".join(self._adf_to_md(c) for c in content)
            return f"```{lang}\n{inner}\n```\n\n"

        if t == "bulletList":
            return "".join(
                self._adf_list_item(item, depth=0, ordered=False)
                for item in content
            ) + "\n"

        if t == "orderedList":
            return "".join(
                self._adf_list_item(item, depth=0, ordered=True, index=i)
                for i, item in enumerate(content, 1)
            ) + "\n"

        if t == "text":
            text = node.get("text", "")
            for mark in node.get("marks", []):
                mt = mark.get("type", "")
                if mt == "strong":
                    text = f"**{text}**"
                elif mt == "em":
                    text = f"*{text}*"
                elif mt == "code":
                    text = f"`{text}`"
                elif mt == "strike":
                    text = f"~~{text}~~"
                elif mt == "link":
                    href = mark.get("attrs", {}).get("href", "")
                    text = f"[{text}]({href})"
            return text

        return "".join(self._adf_to_md(c) for c in content)

    def _adf_list_item(self, node: dict, depth: int, ordered: bool, index: int = 1) -> str:
        indent = "  " * depth
        prefix = f"{index}." if ordered else "-"
        parts = []
        for child in node.get("content", []):
            ct = child.get("type", "")
            if ct == "paragraph":
                text = "".join(self._adf_to_md(c) for c in child.get("content", [])).strip()
                parts.append(f"{indent}{prefix} {text}")
            elif ct == "bulletList":
                nested = "".join(
                    self._adf_list_item(item, depth + 1, ordered=False)
                    for item in child.get("content", [])
                )
                parts.append(nested.rstrip())
            elif ct == "orderedList":
                nested = "".join(
                    self._adf_list_item(item, depth + 1, ordered=True, index=i)
                    for i, item in enumerate(child.get("content", []), 1)
                )
                parts.append(nested.rstrip())
            else:
                parts.append(self._adf_to_md(child).strip())
        return "\n".join(parts) + "\n"
