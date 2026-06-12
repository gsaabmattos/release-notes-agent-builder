import logging
from pathlib import Path
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

log = logging.getLogger(__name__)

DEFAULT_PROMPT = """\
Você é um technical writer experiente. Abaixo estão as notas de release de tickets individuais \
do projeto, coletadas do campo Release Notes do Jira.

Sua tarefa é consolidar essas notas em um único documento de Release Notes para a versão {version}.

Regras obrigatórias:
- Agrupe as notas por categoria quando possível: New Features, Improvements, Bug Fixes, Breaking Changes
- Omita categorias que não tiverem entradas
- Remova duplicatas e redundâncias
- Use linguagem clara, objetiva e profissional
- Formato Markdown (use ## para categorias, - para itens)
- Inclua o cabeçalho: # Release Notes — {version}
- NÃO invente funcionalidades que não estejam nas notas fornecidas
- Se uma nota for muito genérica ou vaga, mantenha-a como está

Notas dos tickets:
{notes}

Documento consolidado:
"""


class LLMConsolidator:
    def __init__(self, cfg):
        self.llm = OllamaLLM(
            base_url=cfg.ollama_base_url,
            model=cfg.ollama_model,
            temperature=cfg.ollama_temperature,
            top_p=cfg.ollama_top_p,
            repeat_penalty=cfg.ollama_repeat_penalty,
        )
        self.prompt_template = self._load_prompt()
        self.chain = PromptTemplate.from_template(self.prompt_template) | self.llm

    def _load_prompt(self) -> str:
        prompt_path = Path("prompts/consolidation.txt")
        if prompt_path.exists():
            content = prompt_path.read_text(encoding="utf-8").strip()
            if content:
                log.info("Prompt customizado carregado de prompts/consolidation.txt")
                return content
        log.info("Usando prompt padrão embutido")
        return DEFAULT_PROMPT

    def consolidate(self, version: str, notes: list[dict]) -> str:
        if not notes:
            log.warning("Nenhuma nota de release encontrada para consolidar")
            return (
                f"# Release Notes — {version}\n\n"
                f"Nenhuma nota de release encontrada para esta versão.\n"
            )

        groups: dict[str, list[dict]] = {}
        for n in notes:
            group_label = (
                f"{n['parent_key']} — {n['parent_summary']}"
                if n.get("parent_key")
                else "Sem parent"
            )
            groups.setdefault(group_label, []).append(n)

        sections = []
        for group_label, group_notes in groups.items():
            items = "\n".join(
                f"  [{n['key']}] ({n['issuetype']}) {n['summary']}\n  {n['notes']}"
                for n in group_notes
            )
            sections.append(f"### {group_label}\n{items}")

        notes_text = "\n\n".join(sections)

        log.info(f"Enviando {len(notes)} nota(s) para consolidação via LLM ({self.llm.model})...")
        result = self.chain.invoke({"version": version, "notes": notes_text})
        log.info("Consolidação concluída")
        return result
