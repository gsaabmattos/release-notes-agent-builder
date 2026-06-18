import logging

log = logging.getLogger(__name__)

BUG_TYPES = {"bug", "defect", "issue"}


class LLMConsolidator:
    def __init__(self, cfg):
        pass

    def consolidate(self, version: str, notes: list[dict]) -> str:
        if not notes:
            log.warning("Nenhuma nota de release encontrada para consolidar")
            return (
                f"# Release Notes — {version}\n\n"
                f"No release notes found for this version.\n"
            )

        enhancements: dict[str, list[dict]] = {}
        bug_fixes: dict[str, list[dict]] = {}

        seen_types: set[str] = set()
        for n in notes:
            seen_types.add(n.get("issuetype", "unknown"))
            parent = (
                f"{n['parent_key']} — {n['parent_summary']}"
                if n.get("parent_key")
                else "Other"
            )
            bucket = bug_fixes if n.get("issuetype", "").lower() in BUG_TYPES else enhancements
            bucket.setdefault(parent, []).append(n)
        log.info(f"Tipos de issue encontrados: {seen_types}")

        lines = [f"# Release Notes — {version}", ""]

        if enhancements:
            lines.append("## Enhancements")
            for parent, tickets in enhancements.items():
                lines.append(f"### {parent}")
                for t in tickets:
                    lines.append(f"#### {t['summary']}")
                    lines.append(t["notes"])
                    lines.append("")

        if bug_fixes:
            lines.append("## Bug Fixes")
            for parent, tickets in bug_fixes.items():
                lines.append(f"### {parent}")
                for t in tickets:
                    lines.append(f"#### {t['summary']}")
                    lines.append(t["notes"])
                    lines.append("")

        log.info(
            f"Documento gerado: {len(enhancements)} grupo(s) de enhancements, "
            f"{len(bug_fixes)} grupo(s) de bug fixes"
        )
        return "\n".join(lines)
