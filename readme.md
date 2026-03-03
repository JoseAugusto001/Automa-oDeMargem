# RoboPrata – Consulta Margem CLT

Robô de automação que consulta margem CLT no painel admin do Banco Prata: lê clientes de um CSV, faz login, consulta por CPF (QiTech), trata modal de autorização do termo quando necessário, obtém valor máximo da parcela e simula por tabelas, gravando resultado em CSV.

---

## Requisitos

- Python 3.x
- Dependências: `pip install -r requirements.txt`
- Chromium do Playwright: `playwright install chromium`
- Credenciais do admin no **.env**: crie um arquivo `.env` na raiz com `ADMIN_EMAIL` e `ADMIN_SENHA` (e-mail e senha do painel admin Banco Prata). O `.env` não é versionado (.gitignore). O módulo `credenciais.py` carrega essas variáveis do `.env` via python-dotenv; pode usar `.env.example` como modelo (copie para `.env` e preencha).

---

## Estrutura do projeto

| Arquivo / Pasta | Descrição |
|-----------------|-----------|
| **config.py** | Configuração central: URLs (admin, hub, CLT), viewport, timeouts, paths de entrada/saída, delimitador/encoding/colunas do CSV, textos de UI usados pelos seletores do Playwright. |
| **main.py** | Ponto de entrada CLI: parse de `--entrada`, `--saida`, `--headless`; chama `executar_robo()`. Suporta variável de ambiente `ROBO_HEADLESS`. |
| **robo_consulta_margem.py** | Lógica do robô: leitura do CSV, login no admin Banco Prata, navegação até Consulta Margem CLT, por cliente: preenchimento de CPF, seleção QiTech, consulta, tratamento do modal de autorização (extração da URL do termo, abertura em nova aba, preenchimento e envio), leitura do valor máximo da parcela, simulação por tabela e escrita no CSV de saída. Depende de `config` e `credenciais`. |
| **requirements.txt** | Dependências: `playwright>=1.48.0`, `python-dotenv>=1.0.0`. |
| **.env** | Não versionado (.gitignore). Contém `ADMIN_EMAIL` e `ADMIN_SENHA`; o `credenciais.py` carrega essas variáveis daqui. |
| **.env.example** | Modelo do .env (chaves sem valor). Copie para `.env` e preencha. |
| **credenciais.py.example** | Template do módulo que lê o .env. Copie para `credenciais.py` (necessário para o robô importar as credenciais). |
| **credenciais.py** | Não versionado (.gitignore). Carrega `ADMIN_EMAIL` e `ADMIN_SENHA` do `.env` e expõe para o robô. |
| **entrada/** | Pasta do CSV de clientes (por padrão `clientes.csv`). |
| **entrada/clientes.csv** | CSV de entrada: colunas obrigatórias `nome` e `cpf`; opcionais `contato`, `email`. Delimitador detectado (vírgula ou ponto-e-vírgula). Linhas sem nome/cpf válido são ignoradas. |
| **saida/** | Pasta de saída (no .gitignore). CSVs com prefixo `resultado_` + data/hora. |
| **saida/resultado_*.csv** | CSV de saída: `nome;cpf;contato;email;valor_maximo_parcela;qtd_parcelas;valor_liberado;valor_parcela;valor_total;status;erro`. Delimitador `;`, encoding UTF-8. |
| **.gitignore** | Ignora `.env`, `credenciais.py`, `__pycache__`, `*.pyc`, `saida/`, ambientes virtuais. |

---

## Uso

```text
python main.py [--entrada caminho] [--saida pasta] [--headless]
```

- **--entrada**: caminho do CSV de clientes (padrão: `entrada/clientes.csv`)
- **--saida**: pasta onde gravar os CSVs de resultado (padrão: `saida`)
- **--headless**: executa o browser sem janela (também ativado por `ROBO_HEADLESS=1` ou `true`/`yes`)
- **ROBO_DEBUG**: se definido (ex.: `set ROBO_DEBUG=1` no Windows), o robô imprime no console o passo atual do fluxo do termo de autorização (aguardando formulário, preenchendo, clicando ENVIAR, aguardando confirmação) para facilitar diagnóstico.

---

## Entrada (CSV)

- Colunas obrigatórias: **nome**, **cpf**
- Colunas opcionais: **contato**, **email**
- Delimitador: detectado automaticamente (`,` ou `;`)
- Linhas sem nome ou CPF válido (11 dígitos) são ignoradas

---

## Saída (CSV)

- Pasta: **saida/**
- Nome do arquivo: `resultado_AAAAMMDD_HHMMSS.csv`
- Colunas: `nome`, `cpf`, `contato`, `email`, `valor_maximo_parcela`, `qtd_parcelas`, `valor_liberado`, `valor_parcela`, `valor_total`, `status`, `erro`
- Delimitador: `;`  
- Encoding: UTF-8

Status típicos: `sucesso`, `cpf_invalido`, `restricao_emissao`, `sem_vinculo`, `falha_modal_autorizacao`, `falha_termo_autorizacao`, `falha_historico`, `falha_simulacao`, entre outros.

---

## Como funciona (fluxo)

1. Ler CSV de entrada e validar colunas (`nome`, `cpf`).
2. Criar CSV de saída com timestamp na pasta configurada.
3. Abrir Chromium (Playwright) e fazer login no admin Banco Prata.
4. Navegar até CLT / Consulta Margem.
5. Para cada cliente: validar CPF (11 dígitos), preencher formulário, selecionar banco QiTech e consultar.
6. Se aparecer o modal "Solicite a autorização do cliente": extrair URL do termo, abrir em nova aba, preencher dados (CPF, nome, e-mail, telefone), marcar checkboxes e enviar; depois voltar e consultar novamente.
7. Obter valor máximo da parcela no resultado e simular por tabelas (valor da parcela / valor total).
8. Escrever uma linha no CSV de saída com todos os campos e status (e mensagem de erro se houver).
9. Voltar à tela de consulta e repetir para o próximo cliente.

---

## Erros conhecidos / Observações

- **Credenciais:** as variáveis `ADMIN_EMAIL` e `ADMIN_SENHA` devem estar no `.env` (copie `.env.example` para `.env` e preencha). Sem elas o login no admin falha.
- O bug que causava `falha_modal_autorizacao` ("Não consegui extrair a URL do termo") foi corrigido: a extração do link do `<a href>` no modal de autorização passa a ser tentada sempre que o dialog está visível. O link do termo pode ser de vários domínios (assina.bancoprata.com.br, pratadigital.com.br, link.bancoapri.com.br), configurável em `config.URL_TERMO_DOMAINS`. Se o preenchimento/envio do formulário do termo falhar, o status gravado é `falha_termo_autorizacao`.
