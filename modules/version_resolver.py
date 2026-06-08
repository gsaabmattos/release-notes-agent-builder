import logging

log = logging.getLogger(__name__)


class VersionResolver:
    def __init__(self, jira_client, cfg):
        self.jira = jira_client
        self.cfg = cfg

    def resolve(self, version_arg: str) -> str:
        """
        Resolve a versão-alvo com base no argumento fornecido.
        - 'latest'     -> busca a última versão Released no Jira
        - 'unreleased' -> retorna a string 'unreleased' (modo sem fixVersion)
        - qualquer outra string -> usa diretamente como nome da versão
        """
        if version_arg == "latest":
            version = self.jira.get_latest_released_version()
            log.info(f"Modo 'latest': versão resolvida para '{version}'")
            return version

        if version_arg == "unreleased":
            log.info("Modo 'unreleased': buscando tickets sem fixVersion")
            return "unreleased"

        log.info(f"Versão informada diretamente: '{version_arg}'")
        return version_arg
