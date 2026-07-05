import logging
import re
from urllib.parse import urlparse

log = logging.getLogger(__name__)

IMAGE_MD_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")


class ImageRelocator:
    """Re-hosts Jira-linked images in release-notes markdown onto Outline.

    Jira attachment/media URLs require an authenticated Jira session to
    load, so they render as broken images once embedded in an Outline
    document. This downloads each referenced image through the Jira client
    and re-uploads it to Outline, rewriting the markdown to point at the
    new Outline-hosted URL.
    """

    def __init__(self, jira_client, outline_publisher):
        self.jira = jira_client
        self.outline = outline_publisher

    def relocate(self, markdown: str) -> str:
        cache: dict[str, str | None] = {}

        def replace(match: re.Match) -> str:
            alt, url = match.group(1), match.group(2)
            if not self._is_jira_hosted(url):
                return match.group(0)

            if url not in cache:
                cache[url] = self._rehost(url, alt)

            new_url = cache[url]
            return match.group(0) if new_url is None else f"![{alt}]({new_url})"

        return IMAGE_MD_RE.sub(replace, markdown)

    def _is_jira_hosted(self, url: str) -> bool:
        host = urlparse(url).netloc
        jira_host = urlparse(self.jira.client.url).netloc
        return host == jira_host or host.endswith("api.media.atlassian.com")

    def _rehost(self, url: str, alt: str) -> str | None:
        downloaded = self.jira.download_attachment(url)
        if downloaded is None:
            return None
        content, content_type = downloaded
        filename = alt or url.rsplit("/", 1)[-1]
        return self.outline.upload_image(filename, content, content_type)
