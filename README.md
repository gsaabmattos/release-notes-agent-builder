# Release Notes Agent

Agente local que coleta tickets DONE do Jira, extrai o campo "Release Notes" e publica um documento consolidado no Wiki.js via LLM local (Ollama).

## Pré-requisitos

- Python 3.11+
- [Ollama](https://ollama.com) instalado e rodando
- Acesso ao Jira Cloud (API Token)
- Wiki.js rodando localmente com API habilitada

## Instalação rápida

```bash
# 1. Instalar Ollama e o modelo
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:7b

# 2. Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Configurar credenciais
cp .env.example .env
nano .env   # preencher com suas credenciais

# 5. Validações iniciais
python scripts/test_jira.py
python scripts/discover_field.py   # anote o ID e atualize modules/notes_extractor.py
python scripts/test_wikijs.py
```

## Uso

```bash
source venv/bin/activate

# Versão específica
python agent.py --version "1.4.2"

# Última versão Released no Jira
python agent.py --version latest

# Tickets DONE sem fixVersion
python agent.py --version unreleased

# Forçar reprocessamento
python agent.py --version "1.4.2" --force
```

## Agendamento (cron)

```bash
crontab -e
```

Adicionar (exemplo: toda segunda-feira às 09h):

```
0 9 * * 1 /caminho/para/venv/bin/python /caminho/para/agent.py --version latest >> /caminho/para/logs/cron.log 2>&1
```

## Estrutura

```
release-notes-agent/
├── agent.py                  # Entrypoint principal
├── .env                      # Credenciais (não versionar)
├── .env.example              # Template
├── requirements.txt
├── config/
│   └── settings.py
├── modules/
│   ├── jira_client.py
│   ├── version_resolver.py
│   ├── notes_extractor.py
│   ├── llm_consolidator.py
│   ├── wikijs_publisher.py
│   └── state_manager.py
├── prompts/
│   └── consolidation.txt     # Prompt customizável para o LLM
├── scripts/
│   ├── discover_field.py     # Descobre ID do campo Release Notes
│   ├── test_jira.py          # Valida conexão Jira
│   └── test_wikijs.py        # Valida conexão Wiki.js
├── state/                    # Estado por versão (gitignored)
├── output/                   # Backup local dos documentos (gitignored)
└── logs/                     # Logs de execução (gitignored)
```

## Primeiro uso: descobrir o campo Release Notes

O ID do campo customizado "Release Notes" varia por instância Jira. Execute:

```bash
python scripts/discover_field.py
```

Anote o ID retornado (ex: `customfield_10058`) e atualize a constante
`RELEASE_NOTES_FIELD` no arquivo `modules/notes_extractor.py`.
