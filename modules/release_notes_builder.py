import logging
import re

log = logging.getLogger(__name__)

BUG_TYPES = {"bug", "defect", "issue"}


def _version_sort_key(version: str) -> tuple:
    """Return a tuple of ints extracted from a version string for semantic sorting."""
    return tuple(int(n) for n in re.findall(r"\d+", version))


class LLMConsolidator:
    def __init__(self, cfg):
        pass

    def consolidate(self, version: str, notes: list[dict]) -> str:
        """Build a release-notes document for a single version."""
        if not notes:
            log.warning("Nenhuma nota de release encontrada para consolidar")
            return f"# Release Notes — {version}\n\nNo release notes found for this version.\n"

        lines = [f"# Release Notes — {version}", ""]
        lines += self._build_sections(version, notes)
        return "\n".join(lines)

    def consolidate_multi(self, versions_notes: list[tuple[str, list[dict]]]) -> str:
        """Build a combined document for one or more versions.

        The semantically lowest version becomes the main title
        (# Release Notes — X); each additional version is rendered as a
        hot-fix section (# Hot Fix X) in ascending version order.
        """
        if len(versions_notes) == 1:
            return self.consolidate(*versions_notes[0])

        sorted_pairs = sorted(versions_notes, key=lambda p: _version_sort_key(p[0]))
        primary_version, primary_notes = sorted_pairs[0]

        lines = [f"# Release Notes — {primary_version}", ""]
        if primary_notes:
            lines += self._build_sections(primary_version, primary_notes)
        else:
            lines += ["No release notes found for this version.", ""]

        for version, notes in sorted_pairs[1:]:
            lines += ["", f"# Hot Fix {version}", ""]
            if notes:
                lines += self._build_sections(version, notes)
            else:
                lines += ["No release notes found for this version.", ""]

        return "\n".join(lines)

    def _build_sections(self, version: str, notes: list[dict]) -> list[str]:
        """Return the ## Enhancements / ## Bug Fixes block for one version."""
        enhancements: dict[str, list[dict]] = {}
        bug_fixes: dict[str, list[dict]] = {}

        seen_types: set[str] = set()
        for n in notes:
            seen_types.add(n.get("issuetype", "unknown"))
            parent = (
                n["parent_summary"] or n["parent_key"]
                if n.get("parent_key")
                else "Other"
            )
            bucket = bug_fixes if n.get("issuetype", "").lower() in BUG_TYPES else enhancements
            bucket.setdefault(parent, []).append(n)
        log.info(f"[{version}] Tipos de issue encontrados: {seen_types}")

        lines: list[str] = []

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
            f"[{version}] {len(enhancements)} grupo(s) de enhancements, "
            f"{len(bug_fixes)} grupo(s) de bug fixes"
        )
        return lines
