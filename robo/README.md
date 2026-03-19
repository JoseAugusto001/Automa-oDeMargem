# Pacote `robo`

Código da automação de consulta de margem CLT. A execução típica parte da raiz do repositório com `python main.py`, que importa `robo.ativos.executor`.

## Estrutura

| Subpasta | Papel |
|----------|--------|
| [`ativos/`](ativos/README.md) | Orquestração em tempo de execução (Playwright + fluxo por cliente/banco) |
| [`comms/`](comms/README.md) | Comunicação com páginas e componentes da UI |
| [`passivos/`](passivos/README.md) | Dados, modelos e leitura/gravação de CSV |
| `entrada/` | CSV de clientes (entrada) |
| `saida/` | CSV de resultados (saída) |

## `config.py`

Configuração central do robô:

- **URLs e padrões** — admin, hub, rota CLT consultar, domínios de termo de autorização.  
- **Viewport e timeouts** — login, formulários, histórico, simulação, modais (incl. Celcoin).  
- **Paths** — `DIR_ENTRADA_PADRAO`, `DIR_SAIDA_PADRAO`, nome do arquivo de entrada, prefixo e formato do CSV de saída.  
- **CSV** — delimitador (`;`), encoding, listas de colunas (`CSV_COLUNAS_SAIDA`, `CSV_COLUNAS_SAIDA_AGREGADO`).  
- **Textos de UI** — rótulos e trechos usados como âncoras para localizar botões, campos e mensagens (QiTech, Celcoin, simulação, termo, erros).  
- **Flags** — ex.: `USE_RECARREGAR_HISTORICO`, `DEBUG_TABELA` (via `ROBO_DEBUG_TABELA`).

Alterar textos da interface do Banco Prata costuma exigir ajustes aqui.

## `credenciais.py`

Carrega `ADMIN_EMAIL` e `ADMIN_SENHA` do ambiente (`.env` via `load_dotenv`). O login usa esses valores em `comms.navegacao`.

## `main.py` (dentro de `robo/`)

CLI semelhante ao `main.py` da raiz: argumentos `--entrada`, `--saida`, `--headless` e uso de `ROBO_HEADLESS`. Pode ser executado como módulo/script se o `PYTHONPATH` incluir o projeto.

## Variáveis de ambiente

| Variável | Impacto |
|----------|---------|
| `ROBO_HEADLESS` | Se `1`, `true` ou `yes`, equivale a `--headless` (executa sem janela). |
| `ROBO_DEBUG` | Habilita logs extras durante o fluxo (termo/simulações). |
| `ROBO_DEBUG_TABELA` | Detalha abertura/seleção da tabela de simulação. |

## `__init__.py`

Reexporta `Cliente`, `TermoRequisicaoMalFormatada` e `executar_robo` para importações curtas do pacote.

## Relação com a raiz do repositório

Na raiz, [`config.py`](../config.py) faz `from robo.config import *` para que `main.py` use a mesma configuração sem prefixo `robo.`.

---

- Índice geral: [DOCUMENTACAO.md](../DOCUMENTACAO.md)  
- Detalhes: [ativos/README.md](ativos/README.md) · [comms/README.md](comms/README.md) · [passivos/README.md](passivos/README.md)
