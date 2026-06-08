import httpx
import logging

log = logging.getLogger(__name__)

CREATE_PAGE_MUTATION = """
mutation CreatePage(
  $content: String!
  $path: String!
  $title: String!
  $locale: String!
) {
  pages {
    create(
      content: $content
      description: ""
      editor: "markdown"
      isPrivate: false
      isPublished: true
      locale: $locale
      path: $path
      tags: ["release-notes"]
      title: $title
    ) {
      responseResult {
        succeeded
        errorCode
        message
      }
      page {
        id
        path
      }
    }
  }
}
"""

UPDATE_PAGE_MUTATION = """
mutation UpdatePage(
  $id: Int!
  $content: String!
  $title: String!
) {
  pages {
    update(
      id: $id
      content: $content
      title: $title
      isPublished: true
      tags: ["release-notes"]
    ) {
      responseResult {
        succeeded
        errorCode
        message
      }
    }
  }
}
"""

GET_PAGE_QUERY = """
query GetPage($path: String!, $locale: String!) {
  pages {
    singleByPath(path: $path, locale: $locale) {
      id
      path
      title
    }
  }
}
"""


class WikiJSPublisher:
    def __init__(self, cfg):
        self.graphql_url = f"{cfg.wikijs_url}/graphql"
        self.headers = {
            "Authorization": f"Bearer {cfg.wikijs_api_token}",
            "Content-Type": "application/json",
        }
        self.locale = cfg.wikijs_locale

    def _graphql(self, query: str, variables: dict) -> dict:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                self.graphql_url,
                json={"query": query, "variables": variables},
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    def _get_page_id(self, path: str) -> int | None:
        data = self._graphql(GET_PAGE_QUERY, {"path": path, "locale": self.locale})
        page = data.get("data", {}).get("pages", {}).get("singleByPath")
        return page["id"] if page else None

    def publish(self, path: str, version: str, content: str):
        title = f"Release Notes — {version}"
        existing_id = self._get_page_id(path)

        if existing_id:
            log.info(f"Página existente encontrada (id={existing_id}), atualizando...")
            result = self._graphql(
                UPDATE_PAGE_MUTATION,
                {"id": existing_id, "content": content, "title": title},
            )
            response_result = result["data"]["pages"]["update"]["responseResult"]
            if not response_result["succeeded"]:
                raise RuntimeError(
                    f"Erro ao atualizar página no Wiki.js: {response_result['message']}"
                )
            log.info(f"Página '{title}' atualizada com sucesso")
        else:
            log.info(f"Criando nova página em /{path}...")
            result = self._graphql(
                CREATE_PAGE_MUTATION,
                {
                    "content": content,
                    "path": path,
                    "title": title,
                    "locale": self.locale,
                },
            )
            response_result = result["data"]["pages"]["create"]["responseResult"]
            if not response_result["succeeded"]:
                raise RuntimeError(
                    f"Erro ao criar página no Wiki.js: {response_result['message']}"
                )
            page_id = result["data"]["pages"]["create"]["page"]["id"]
            log.info(f"Página '{title}' criada com sucesso (id={page_id})")

    def test_connection(self) -> bool:
        """Testa a conexão com o Wiki.js. Útil para validação inicial."""
        try:
            query = "{ pages { list(limit: 1) { id path } } }"
            self._graphql(query, {})
            log.info("Conexão com Wiki.js: OK")
            return True
        except Exception as e:
            log.error(f"Conexão com Wiki.js falhou: {e}")
            return False
