import logging
from atlassian import Jira

log = logging.getLogger(__name__)


class JiraClient:
    def __init__(self, cfg):
        self.client = Jira(
            url=cfg.jira_url,
            username=cfg.jira_email,
            password=cfg.jira_api_token,
            cloud=True
        )
        self.project = cfg.jira_project_key

    def get_done_tickets_by_version(self, version_name: str) -> list[dict]:
        jql = (
            f'project = "{self.project}" '
            f'AND fixVersion = "{version_name}" '
            f'AND status = Done '
            f'ORDER BY updated DESC'
        )
        fields = "summary,status,fixVersions,updated,customfield_release_notes"
        log.info(f"JQL: {jql}")
        issues = self.client.jql(jql, fields=fields, limit=500)
        return issues.get("issues", [])

    def get_all_done_tickets(self) -> list[dict]:
        """Busca todos os tickets DONE sem filtro de versão (modo 'unreleased')."""
        jql = (
            f'project = "{self.project}" '
            f'AND status = Done '
            f'AND fixVersion is EMPTY '
            f'ORDER BY updated DESC'
        )
        fields = "summary,status,fixVersions,updated,customfield_release_notes"
        issues = self.client.jql(jql, fields=fields, limit=500)
        return issues.get("issues", [])

    def get_latest_released_version(self) -> str:
        versions = self.client.get_project_versions(self.project)
        released = [v for v in versions if v.get("released")]
        if not released:
            raise ValueError("Nenhuma versão 'released' encontrada no projeto")
        latest = sorted(released, key=lambda v: v.get("releaseDate", ""))[-1]
        log.info(f"Versão mais recente encontrada: {latest['name']}")
        return latest["name"]

    def get_all_versions(self) -> list[dict]:
        return self.client.get_project_versions(self.project)

    def discover_release_notes_field(self) -> str | None:
        """Descobre o ID do campo customizado 'Release Notes'."""
        fields = self.client.get_all_fields()
        for f in fields:
            name = f.get("name", "").lower()
            if "release" in name and "note" in name:
                log.info(f"Campo encontrado: {f['id']} -> {f['name']}")
                return f["id"]
        log.warning("Campo 'Release Notes' não encontrado automaticamente.")
        return None
