import logging

import httpx

log = logging.getLogger(__name__)


class OutlinePublisher:
    def __init__(self, cfg):
        self.base_url = cfg.outline_url.rstrip("/")
        self.api_url = self.base_url + "/api"
        self.headers = {
            "Authorization": f"Bearer {cfg.outline_api_token}",
            "Content-Type": "application/json",
        }
        self.collection_id = cfg.outline_collection_id

    def _post(self, endpoint: str, body: dict) -> dict:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                f"{self.api_url}/{endpoint}",
                json=body,
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    def _find_document_id(self, title: str) -> str | None:
        """Search for an existing document by exact title. Returns its ID or None."""
        try:
            result = self._post("documents.search", {
                "query": title,
                "collectionId": self.collection_id,
            })
            for item in result.get("data", []):
                doc = item.get("document", {})
                if doc.get("title") == title:
                    return doc["id"]
        except Exception as exc:
            log.warning(f"Busca no Outline falhou: {exc}")
        return None

    def upload_image(self, filename: str, content: bytes, content_type: str) -> str | None:
        """Upload raw image bytes as an Outline attachment, returning its hosted URL."""
        try:
            created = self._post("attachments.create", {
                "name": filename,
                "contentType": content_type,
                "size": len(content),
            })
            data = created.get("data", {})
            attachment_url = data.get("attachment", {}).get("url")

            with httpx.Client(timeout=60) as client:
                if data.get("mode") == "put":
                    response = client.put(
                        data["url"], content=content, headers=data.get("headers", {})
                    )
                else:
                    response = client.post(
                        data["uploadUrl"],
                        data=data.get("form", {}),
                        files={"file": (filename, content, content_type)},
                    )
                response.raise_for_status()

            if attachment_url and attachment_url.startswith("/"):
                attachment_url = self.base_url + attachment_url
            return attachment_url
        except Exception as exc:
            log.warning(f"Falha ao enviar imagem '{filename}' para o Outline: {exc}")
            return None

    def publish(self, version: str, content: str):
        title = f"Release Notes — {version}"
        existing_id = self._find_document_id(title)

        if existing_id:
            log.info(f"Documento existente encontrado (id={existing_id}), atualizando...")
            self._post("documents.update", {
                "id": existing_id,
                "title": title,
                "text": content,
                "publish": True,
            })
            log.info(f"Documento '{title}' atualizado com sucesso")
        else:
            log.info(f"Criando novo documento '{title}'...")
            result = self._post("documents.create", {
                "title": title,
                "text": content,
                "collectionId": self.collection_id,
                "publish": True,
            })
            doc_id = result.get("data", {}).get("id")
            log.info(f"Documento '{title}' criado com sucesso (id={doc_id})")

    def test_connection(self) -> bool:
        try:
            self._post("collections.list", {})
            log.info("Conexão com Outline: OK")
            return True
        except Exception as exc:
            log.error(f"Conexão com Outline falhou: {exc}")
            return False
