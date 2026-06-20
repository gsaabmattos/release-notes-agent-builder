import logging
import re

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
                else self._wiki_to_md(str(raw_notes))
            )
            # Remove the space after any '#' at the start of a line so Outline
            # does not render inline '#' characters as markdown headings.
            note_text = re.sub(r"^(#+) ", r"\1", note_text, flags=re.MULTILINE)

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

    def _beautify_xml(self, raw: str) -> str:
        """Indent an XML fragment using a simple tag-depth tracker.

        Works on deliberately incomplete XML (unclosed tags, bare '...' omission
        markers) — does not require or attempt full XML parsing.
        """
        if not raw.strip():
            return raw

        MARKER = "\x00DOTS\x00"
        text = raw.replace("...", MARKER)
        # Collapse all whitespace (tabs, newlines) to single spaces so
        # tab-separated single-line Jira fragments are handled the same as
        # already-wrapped multi-line content.
        text = re.sub(r"[ \t\r\n]+", " ", text).strip()

        # Tokenize: split on XML tags while keeping the tags themselves
        tokens = re.split(r"(<[^>]*>)", text)
        tokens = [t.strip() for t in tokens if t.strip()]

        indent = "  "
        depth = 0
        lines: list[str] = []

        for tok in tokens:
            if tok == MARKER:
                if lines and lines[-1] != "":
                    lines.append("")
                lines.append(indent * depth + "...")
                lines.append("")
            elif re.match(r"</", tok):
                depth = max(0, depth - 1)
                lines.append(indent * depth + tok)
            elif tok.endswith("/>") or re.match(r"<[?!]", tok):
                lines.append(indent * depth + tok)
            elif re.match(r"<", tok):
                lines.append(indent * depth + tok)
                depth += 1
            else:
                lines.append(indent * depth + tok)

        # Collapse consecutive blank lines and strip leading/trailing blanks
        deduped: list[str] = []
        for line in lines:
            if line == "" and deduped and deduped[-1] == "":
                continue
            deduped.append(line)
        while deduped and deduped[0] == "":
            deduped.pop(0)
        while deduped and deduped[-1] == "":
            deduped.pop()

        # Collapse simple leaf elements spanning three lines:
        #   <tag>        →   <tag>text</tag>
        #     text
        #   </tag>
        result: list[str] = []
        i = 0
        while i < len(deduped):
            line = deduped[i]
            stripped = line.strip()
            if (stripped.startswith("<")
                    and not stripped.startswith("</")
                    and not stripped.endswith("/>")
                    and not re.match(r"<[?!]", stripped)
                    and i + 2 < len(deduped)):
                text_stripped = deduped[i + 1].strip()
                close_stripped = deduped[i + 2].strip()
                tag_name = re.match(r"<([^\s>/]+)", stripped)
                close_match = re.match(r"</([^\s>]+)>$", close_stripped)
                if (tag_name and close_match
                        and tag_name.group(1) == close_match.group(1)
                        and text_stripped
                        and not text_stripped.startswith("<")
                        and text_stripped != "..."):
                    result.append(line.rstrip() + text_stripped + close_stripped)
                    i += 3
                    continue
            result.append(line)
            i += 1

        return "\n".join(result)

    def _wiki_to_md(self, text: str) -> str:
        """Convert Jira wiki markup to standard CommonMark markdown."""

        # 1. Fenced code blocks — must run first to protect their content
        def replace_code(m):
            lang = (m.group(1) or "").strip()
            content = m.group(2).strip()
            if lang == "xml":
                content = self._beautify_xml(content)
            return f"\n```{lang}\n{content}\n```\n"
        text = re.sub(r"\{code(?::([^}]*))?\}(.*?)\{code\}", replace_code, text, flags=re.DOTALL)

        # 2. No-format blocks
        text = re.sub(
            r"\{noformat[^}]*\}(.*?)\{noformat\}",
            lambda m: f"\n```\n{m.group(1).strip()}\n```\n",
            text, flags=re.DOTALL,
        )

        # 3. Panels → blockquote (NOTE / WARNING / INFO boxes)
        def replace_panel(m):
            lines = m.group(1).strip().splitlines()
            return "\n" + "\n".join(f"> {l}" for l in lines) + "\n"
        text = re.sub(r"\{panel[^}]*\}(.*?)\{panel\}", replace_panel, text, flags=re.DOTALL)

        # 4. Inline monospace: {{text}} → `text`
        text = re.sub(r"\{\{([^}]+)\}\}", r"`\1`", text)

        # 5. Images — remove entirely (binary assets don't transfer to Outline)
        text = re.sub(r"!(?:[^!\n|]+)(?:\|[^!]*)?\!", "", text)

        # 6. Headings: h1. → # … h6. → ######
        for lvl in range(6, 0, -1):
            text = re.sub(rf"^h{lvl}\. ", "#" * lvl + " ", text, flags=re.MULTILINE)

        # 7. Bullet lists — MUST come before bold so "* item" isn't treated as bold
        text = re.sub(r"^\*{3} ", "    - ", text, flags=re.MULTILINE)
        text = re.sub(r"^\*{2} ", "  - ", text, flags=re.MULTILINE)
        text = re.sub(r"^\* ", "- ", text, flags=re.MULTILINE)

        # 8. Bold: *text* → **text** (non-whitespace content only)
        text = re.sub(r"\*(\S(?:[^*\n]*\S)?)\*", r"**\1**", text)

        # 9. Italic: _text_ → *text*
        text = re.sub(r"(?<!\w)_(\S(?:[^_\n]*\S)?)_(?!\w)", r"*\1*", text)

        # 10. Links: [label|url] and smart-links [label|url|smart-link] → [label](url)
        text = re.sub(r"\[([^\]|]+)\|([^|\]]+)(?:\|[^\]]*)?\]", r"[\1](\2)", text)

        # 11. Horizontal rules
        text = re.sub(r"^----$", "---", text, flags=re.MULTILINE)

        return text.strip()

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
