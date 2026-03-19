# `robo.ativos` — orquestração

Módulos que **disparam e coordenam** a automação: browser, login, loop por cliente e por banco, integração com histórico, modal de autorização, termo e simulação.

## `executor.py`

- Inicia **Playwright** (Chromium), contexto com geolocalização e página padrão.  
- Chama `navegacao.login_e_ir_para_consulta(page)`.  
- Chama `processar_clientes(page, clientes, caminho_saida)`.  
- Trata fechamento do browser e mensagem amigável se o alvo fechar durante a execução.

Função principal: `executar_robo(caminho_entrada=None, dir_saida=None, headless=False)`.

## `processador.py`

Coração do fluxo de negócio:

- Recebe a lista de `Cliente` e o caminho do CSV de saída.  
- Para cada cliente, para cada banco (**QiTech** e **Celcoin**):  
  - Preenche CPF e seleciona o banco (`fluxo_consulta`).  
  - Pode reutilizar resultado já existente no histórico (`historico.processar_resultado_existente_no_historico`).  
  - Aguarda status da linha no histórico, abre **Ver resultado** quando há sucesso.  
  - Trata **modal de autorização**, preenchimento de nome/telefone e fluxo do **termo** em nova aba (`termo`).  
  - Extrai valor máximo da parcela e chama `historico.simular_tabelas` para cada combinação de prazos (6/12/18/24).  
- Registra erros com `csv_io.log_critico` e, ao final, `csv_io.salvar_dataframe_final`.

Função principal: `processar_clientes(page, clientes, caminho_saida)`.

## Dependências

- `playwright.sync_api.Page`  
- `config`, `robo.passivos.csv_io`, `robo.passivos.modelos`, `robo.comms.*`

---

- Pacote: [../README.md](../README.md)  
- UI e simulação: [../comms/README.md](../comms/README.md)  
- CSV: [../passivos/README.md](../passivos/README.md)
