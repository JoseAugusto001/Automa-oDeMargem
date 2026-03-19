# RoboPrata — Consulta Margem CLT

Automação para consulta de margem e simulações (QiTech / Celcoin) no fluxo CLT do Banco Prata.

## Documentação completa

Consulte **[DOCUMENTACAO.md](DOCUMENTACAO.md)** para:

- como executar (`python main.py`, flags e variáveis de ambiente);
- credenciais (`.env`);
- fluxo geral e links para READMEs por pasta (`robo/ativos`, `robo/comms`, `robo/passivos`).

## Início rápido

1. Configure `ADMIN_EMAIL` e `ADMIN_SENHA` no `.env`.  
2. Coloque clientes em `robo/entrada/clientes.csv`.  
3. Execute: `python main.py`
