# RoboPrata — Documentação

Automação de **consulta de margem CLT** no ecossistema Banco Prata (admin + fluxo CLT), com simulação por prazos (QiTech e Celcoin) e geração de CSV.

## Documentação por pasta

| Pasta | Descrição |
|-------|-----------|
| [robo/README.md](robo/README.md) | Pacote principal, configuração e visão geral |
| [robo/ativos/README.md](robo/ativos/README.md) | Orquestração: Playwright, loop de clientes e bancos |
| [robo/comms/README.md](robo/comms/README.md) | Interação com a UI (login, consulta, histórico, termo) |
| [robo/passivos/README.md](robo/passivos/README.md) | Modelos, CSV de entrada/saída e utilitários |

## Pré-requisitos

- Python 3.10+  
- Acesso ao admin do Banco Prata

## Instalação

Na raiz do repositório:

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

## Como executar

Na raiz do repositório (recomendado):

```bash
python main.py
```

Argumentos opcionais:

| Argumento | Descrição |
|-----------|-----------|
| `--entrada` | Caminho do CSV de clientes (padrão: `robo/entrada/clientes.csv`) |
| `--saida` | Pasta onde será gravado o CSV de resultado (padrão: `robo/saida/`) |
| `--headless` | Executa o Chromium sem janela visível |

## Variáveis de ambiente

| Variável | Impacto |
|----------|---------|
| `ROBO_HEADLESS` | Se `1`, `true` ou `yes`, equivale a `--headless` (executa sem janela). |
| `ROBO_DEBUG` | Habilita logs extras durante o fluxo (termo/simulações). |
| `ROBO_DEBUG_TABELA` | Detalha abertura/seleção da tabela de simulação. |

Execução alternativa (com o pacote no `PYTHONPATH`):

```bash
python -m robo.main
```

## Credenciais

Não commite senhas. Use arquivo `.env` na raiz (baseie-se em `.env.example`) com:

- `ADMIN_EMAIL` — e-mail do usuário admin  
- `ADMIN_SENHA` — senha  

O carregamento é feito por [`credenciais.py`](credenciais.py) / [`robo/credenciais.py`](robo/credenciais.py) via `python-dotenv`.

## Arquivos na raiz do projeto

| Arquivo | Função |
|---------|--------|
| `main.py` | Ponto de entrada CLI; chama `executar_robo` |
| `config.py` | Reexporta `robo.config` para imports a partir da raiz |
| `credenciais.py` | `ADMIN_EMAIL` / `ADMIN_SENHA` a partir do ambiente |
| `robo_consulta_margem.py` | Reexporta `executar_robo` (uso como módulo) |

## Fluxo de execução (alto nível)

```mermaid
flowchart LR
  main_py[main.py]
  exec[ativos.executor]
  proc[ativos.processador]
  nav[comms.navegacao]
  flux[comms.fluxo_consulta]
  hist[comms.historico]
  term[comms.termo]
  csv[passivos.csv_io]
  main_py --> exec
  exec --> nav
  exec --> proc
  proc --> flux
  proc --> hist
  proc --> term
  proc --> csv
  exec --> csv
```

1. Lê clientes do CSV ([`passivos/csv_io`](robo/passivos/README.md)).  
2. Abre o navegador, faz login e navega até a consulta CLT ([`comms/navegacao`](robo/comms/README.md)).  
3. Para cada cliente e cada banco (QiTech, Celcoin), preenche CPF, consulta, trata modal/termo quando necessário e, em caso de sucesso, abre o resultado e roda simulações por meses ([`ativos/processador`](robo/ativos/README.md) + [`comms/historico`](robo/comms/README.md)).  
4. Grava o CSV final em `robo/saida/` com prefixo `resultado_` e data/hora.

## Pastas de dados

- `robo/entrada/` — CSV de entrada (ex.: `clientes.csv` com colunas `nome`, `cpf`; opcionais `contato`, `email`).  
- `robo/saida/` — CSV gerados automaticamente; não versionar dados sensíveis (considere adicionar essas pastas ao `.gitignore`).

## Segurança e dados sensíveis

- Não versione `robo/entrada/` e `robo/saida/`: esses arquivos podem conter dados pessoais.  
- Não versione `.env` e `credenciais.py`.  
- Armazene resultados com acesso controlado e apague arquivos antigos quando possível.

## Saída (CSV)

- Arquivo `resultado_YYYYMMDD_HHMMSS.csv` dentro de `robo/saida/`.  
- Separador `;` e encoding UTF-8.  

---

*Para detalhes por módulo, abra os READMEs nas subpastas de `robo/` listados acima.*
