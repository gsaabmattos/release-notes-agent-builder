import logging
from urllib.parse import urlparse

import httpx
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

    def _fetch_all(self, jql: str) -> list[dict]:
        log.info(f"JQL: {jql}")
        issues = self.client.enhanced_jql_get_list_of_tickets(jql, fields="*all")
        log.info(f"{len(issues)} tickets encontrados")
        return issues

    def get_done_tickets_by_version(self, version_name: str) -> list[dict]:
        jql = (
            f'project = "{self.project}" '
            f'AND fixVersion = "{version_name}" '
            f'AND status = Done '
            f'ORDER BY updated DESC'
        )
        return self._fetch_all(jql)

    def get_all_done_tickets(self) -> list[dict]:
        jql = (
            f'project = "{self.project}" '
            f'AND status = Done '
            f'AND fixVersion is EMPTY '
            f'ORDER BY updated DESC'
        )
        return self._fetch_all(jql)

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

    def download_attachment(self, url: str) -> tuple[bytes, str] | None:
        """Download an image referenced from a release-notes field.

        Only sends Jira credentials to the Jira host itself — Atlassian's
        media API URLs already carry a signed token in the query string, and
        forwarding Basic auth to a third-party host would leak it.
        """
        same_host = urlparse(url).netloc == urlparse(self.client.url).netloc
        auth = (self.client.username, self.client.password) if same_host else None
        try:
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                response = client.get(url, auth=auth)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "application/octet-stream")
                return response.content, content_type
        except Exception as exc:
            log.warning(f"Falha ao baixar imagem do Jira ({url}): {exc}")
            return None

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
