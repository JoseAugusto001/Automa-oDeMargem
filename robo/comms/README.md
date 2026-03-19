# `robo.comms` — comunicação com a UI

Abstrai **login**, **formulário de consulta**, **histórico**, **resultado**, **simulação por tabela de meses** e **termo de autorização**, usando textos e seletores definidos em `robo.config`.

## `navegacao.py`

- Login no admin (`ADMIN_EMAIL` / `ADMIN_SENHA`).  
- Navegação até **Consulta Margem** e fluxo **CLT** / consultar saldo.  
- Utilitários: página principal de consulta, voltar para consulta “limpa”, fechar popup/aba de resultado.

Funções úteis: `login_e_ir_para_consulta`, `obter_pagina_consulta_principal`, `voltar_para_consulta_limpa`, `fechar_pagina_se_aberta`.

## `fluxo_consulta.py`

- Garantir CPF no campo correto.  
- Selecionar **QiTech** ou **Celcoin** (incl. variações de nome na UI).  
- Detectar mensagens de erro ou estado da página: CPF inválido, não encontrado, restrição de emissão, erro na consulta, registro não encontrado, etc.  
- `historico_tem_linha_sucesso_cpf` — verifica se já existe linha de sucesso para o CPF/banco.

## `historico.py`

- Localizar linha do histórico por CPF e banco (`buscar_linha_historico`).  
- Abrir resultado (popup ou inline) (`abrir_resultado_historico`).  
- Extrair **valor máximo da parcela** do resultado.  
- Tratar recusa de política ou requisição mal formatada antes de simular.  
- **`simular_tabelas`** — para cada prazo, seleciona opção na **Tabela** (select nativo e/ou dropdown Vue), preenche valor esperado, clica **Simular**, lê valores liberados/parcelas/total na página (ou bloco expandido) e acrescenta dicionários em `lista_saida` (`tipo`: `parcela` ou `limite_meses`).  
- **`processar_resultado_existente_no_historico`** — atalho quando o sucesso já está no histórico antes de nova consulta.

## `termo.py`

- Extrair link do termo a partir do modal ou da página.  
- Abrir termo em nova aba e interagir com o fluxo de assinatura (conforme implementação atual).

## `__init__.py`

Reexporta as funções públicas usadas pelo `processador` e por testes, para import centralizado (`from robo.comms import ...`).

---

- Orquestração: [../ativos/README.md](../ativos/README.md)  
- Config (textos UI): [../config.py](../config.py)  
- Pacote: [../README.md](../README.md)
