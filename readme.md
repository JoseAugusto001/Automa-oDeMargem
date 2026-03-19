# RoboPrata — Consulta Margem CLT

Automação para consulta de margem e simulações (QiTech / Celcoin) no fluxo CLT do Banco Prata.

Requer Python 3.10+.

## Documentação completa

Consulte **[DOCUMENTACAO.md](DOCUMENTACAO.md)** para:

- como executar (`python main.py`, flags e variáveis de ambiente);
- credenciais (`.env`);
- fluxo geral e links para READMEs por pasta (`robo/ativos`, `robo/comms`, `robo/passivos`).

## Início rápido

1. Instale dependências e o Chromium do Playwright:

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

2. Configure `ADMIN_EMAIL` e `ADMIN_SENHA` no `.env` (use `.env.example` como base).  
3. Coloque clientes em `robo/entrada/clientes.csv`.  
4. Execute: `python main.py`

## Segurança e dados sensíveis

- Não versione `robo/entrada/` e `robo/saida/`: podem conter dados pessoais.  
- Não versione `.env` e `credenciais.py`.
