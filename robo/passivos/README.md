# `robo.passivos` — dados e I/O

Camada **sem Playwright**: modelos de domínio, normalização de CPF e leitura/gravação dos CSVs de entrada e saída.

## `modelos.py`

- **`Cliente`** — `dataclass` com `nome`, `cpf`, `contato`, `email`.  
- **`TermoRequisicaoMalFormatada`** — exceção sinalizando página de termo com mensagem de requisição mal formatada (tratada no `processador`).

## `cpf_utils.py`

Funções para normalizar/validar CPF em texto (dígitos apenas, tamanho 11, etc.), usadas na leitura do CSV de entrada.

## `csv_io.py`

| Função / papel | Descrição |
|----------------|-----------|
| `garantir_pasta_saida` | Cria diretório de saída se não existir |
| `criar_caminho_csv_saida` | Gera nome `resultado_YYYYMMDD_HHMMSS.csv` em `DIR_SAIDA_PADRAO` |
| `escrever_cabecalho_saida` / `escrever_linha_saida` | Escrita incremental legada (se usada) |
| `ler_clientes` | Lê CSV de entrada; exige colunas `nome` e `cpf`; delimitador detectado por `csv.Sniffer` (`,` ou `;`) |
| `log_critico` | Acrescenta linha de erro em `lista_saida` (`tipo`: `erro`) |
| `salvar_dataframe_final` | Filtra registros com `tipo` em `parcela`, `limite_meses`, `erro`; monta DataFrame com `config.CSV_COLUNAS_SAIDA` e grava o CSV final; imprime contagem de linhas e parcelas |

## CSV de entrada

Arquivo padrão: `robo/entrada/clientes.csv`.

Colunas obrigatórias: **`nome`**, **`cpf`**.  
Opcionais: **`contato`**, **`email`**.

## CSV de saída

- Colunas definidas em `config.CSV_COLUNAS_SAIDA` (separador `;`, UTF-8).  
- Inclui linhas por simulação (`tipo` = `parcela`), linha final por banco com texto de limite de meses (`tipo` = `limite_meses`) e possíveis linhas de erro (`tipo` = `erro`).  
- Existe também `CSV_COLUNAS_SAIDA_AGREGADO` no config para um layout agregado (se o fluxo passar a usá-lo).

## `__init__.py`

Expõe submódulos conforme necessário para imports do pacote.

---

- Orquestração que consome este módulo: [../ativos/README.md](../ativos/README.md)  
- Índice geral: [DOCUMENTACAO.md](../../DOCUMENTACAO.md)
