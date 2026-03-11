import os

_ROBO_DIR = os.path.dirname(os.path.abspath(__file__))

# URLs e rotas
URL_ADMIN_BASE = "https://admin.bancoprata.com.br/"
URL_HUB_PATTERN = "**/hub"
URL_CLT_CONSULTAR_PATTERN = "**/clt/consultar"
URL_TERMO_CONTAIN = "assina.bancoprata.com.br/credito-trabalhador/termo-autorizacao"
URL_TERMO_CONTAIN_ALT = "credito-trabalhador/autorizar"
# Domínios
URL_TERMO_DOMAINS = ["assina.bancoprata.com.br", "pratadigital.com.br", "link.bancoapri.com.br"]

# Viewport 
VIEWPORT_LARGURA = 1920
VIEWPORT_ALTURA = 1080

# Timeouts (ms)
TIMEOUT_LOGIN_MS = 45000
TIMEOUT_LOGIN_FORM_MS = 10000
TIMEOUT_FORM_CONSULTA_MS = 6000
TIMEOUT_PROCESSAR_MS = 18000
TIMEOUT_VALOR_MAX_MS = 12000
PAUSA_ENTRE_CLIENTES_MS = 50
PAUSA_APOS_CONSULTAR_MS = 50
PAUSA_ESPERA_MODAL_CELCOIN_MS = 800
PAUSA_APOS_RECARREGAR_MS = 800
TIMEOUT_NAVEGACAO_VER_RESULTADO_MS = 8000
TIMEOUT_ESPERA_BLOCO_INLINE_MS = 5000
PAUSA_APOS_SIMULAR_MS = 100
PAUSA_APOS_ABRIR_DROPDOWN_TABELA_MS = 450
TIMEOUT_OPCAO_TABELA_MS = 2500
VALOR_MINIMO_PARCELA_SIMULAR = 180
SLOW_MO_HEADED_MS = 40

# Paths 
DIR_ENTRADA_PADRAO = os.path.join(_ROBO_DIR, "entrada")
ARQUIVO_ENTRADA_PADRAO = "clientes.csv"
DIR_SAIDA_PADRAO = os.path.join(_ROBO_DIR, "saida")
PREFIXO_CSV_SAIDA = "resultado_"
FORMATO_DATA_CSV = "%Y%m%d_%H%M%S"

# CSV
CSV_DELIMITER = ";"
CSV_ENCODING = "utf-8"
CSV_COLUNAS_SAIDA = [
    "nome",
    "cpf",
    "contato",
    "email",
    "banco",
    "valor_maximo_parcela",
    "qtd_parcelas",
    "valor_liberado",
    "valor_parcela",
    "valor_total",
    "status",
    "erro",
]
CSV_COLUNAS_SAIDA_AGREGADO = [
    "nome", "cpf", "contato", "email", "banco", "valor_maximo_parcela",
    "valor_parcela_6m", "valor_parcela_12m", "valor_parcela_18m", "valor_parcela_24m",
    "valor_liberado_6m", "valor_liberado_12m", "valor_liberado_18m", "valor_liberado_24m",
    "valor_total_6m", "valor_total_12m", "valor_total_18m", "valor_total_24m",
    "status_6m", "status_12m", "status_18m", "status_24m",
    "status", "erro",
]

# Textos de UI (seletores)
UI_LABEL_EMAIL = "E-mail"
UI_LABEL_SENHA = "Senha"
UI_BOTAO_FAZER_LOGIN = "Fazer login"
UI_LINK_CONSULTA_MARGEM = "Consulta Margem"
UI_MENU_CLT = "CLT"
UI_LABEL_CPF = "CPF"
UI_PLACEHOLDER_CPF = "000.000.000-00"
UI_LABEL_BANCO = "Banco"
UI_OPCAO_QITECH = "QITech"
UI_OPCAO_QITECH_ALT = "QiTech"
UI_OPCAO_CELCOIN = "Celcoin"
UI_BOTAO_CONSULTAR_SALDO = "Consultar saldo"
UI_ID_BOTAO_CONSULTAR_SALDO = "btnConsultar"
UI_TEXTO_MODAL_AUTORIZACAO = "Solicite a autorização do cliente"
UI_TEXTO_MODAL_AUTORIZACAO_CELCOIN = ["Solicite a autorização do cliente", "autorização do cliente", "autorizar"]
UI_LABEL_NOME = "Nome"
UI_LABEL_TELEFONE = "Telefone"
UI_BOTAO_ENVIAR = "ENVIAR"
UI_TEXTO_OBRIGADO = "Obrigado"
UI_TEXTO_OBRIGADO_ALT = ["Obrigado!", "Enviado com sucesso", "Sucesso"]
TIMEOUT_TERMO_OBRIGADO_MS = 15000
UI_TEXTO_TERMO_EM_PROCESSAMENTO = "em processamento"
TIMEOUT_TERMO_PROCESSAMENTO_MS = 15000
TIMEOUT_BOTAO_ENVIAR_MS = 10000
UI_BOTAO_VOLTAR = "Voltar"
UI_TEXTO_SEM_VINCULO = "não possui vínculos empregatícios ativos"
UI_TEXTO_SEM_VINCULO_ALT = "Este cliente não possui vinculos empregatícios ativos"
UI_TEXTO_CPF_INVALIDO = "CPF inválido"
UI_TEXTO_CPF_INVALIDO_ALT2 = "CPF informado não é válido"
UI_TEXTO_RESTRICAO_EMISSAO = "Não é permitida a emissão de propostas"
UI_BOTAO_RECARREGAR = "Recarregar"
UI_TEXTO_NOVA_VERSAO_RECARREGANDO = "Nova versão detectada"
USE_RECARREGAR_HISTORICO = False
MAX_TENTATIVAS_TABELA_VISIVEL = 3
UI_TEXTO_PROCESSANDO = "Processando"
UI_TEXTO_PROCESSANDO_ALT = "Em Processo"
TIMEOUT_ESPERA_HISTORICO_MS = 60000
MAX_RECARREGAR_PROCESSANDO = 15
UI_BOTAO_VER_RESULTADO = "Ver resultado"
UI_TEXTO_SUCESSO = "Sucesso"
UI_TEXTO_VALOR_MAXIMO_PARCELA = "Valor máximo da parcela"
UI_LABEL_TABELA = "Tabela"
UI_PLACEHOLDER_TABELA = "Selecione uma opção"
# Dropdown Tabela: estrutura Vue (tr.expanded-row > .simulation / .simulation-table)
LOCATOR_TABELA_DROPDOWN = ".simulation [role='combobox'], .simulation-table [role='combobox'], .simulation select, .simulation-table select"
UI_TABELA_VARIANTES_MESES = {6: ["6 meses (C)", "6 meses"], 12: ["12 meses (C)", "12 meses"], 24: ["24 meses (C)", "24 meses"]}
TIMEOUT_ESPERA_BLOCO_SIMULACAO_MS = 10000
UI_LABEL_TIPO = "Tipo"
UI_OPCAO_VALOR_PARCELA = "Valor da parcela"
UI_OPCAO_VALOR_TOTAL = "Valor total"
UI_BOTAO_SIMULAR = "Simular"
UI_TEXTO_VALOR_MAIOR_DISPONIVEL = "O valor desejado é maior que o disponível"
UI_TEXTO_VALOR_LIBERADO = "Valor Liberado"
UI_TEXTO_ENTENDA_ENCARGOS = "Entenda os encargos"
UI_TEXTO_TOTAL = "Total"
UI_TEXTO_PARCELAS_X_RS = "x R$"
UI_TEXTO_CPF_INVALIDO_ALT = "O CPF informado não é válido"
UI_TEXTO_CPF_NAO_ENCONTRADO = "CPF não encontrado na base ou CPF do trabalhador inelegível."
UI_TEXTO_CPF_NAO_ENCONTRADO_ALT = "CPF não encontrado na base ou CPF do trabalhador inelegível"
UI_TEXTO_ERRO_NA_CONSULTA = "Erro na consulta"
UI_LABEL_TELEFONE_TERMO = "Número de telefone"
UI_TEXTO_CHECKBOX_ACEITO = "Eu aceito os termos"
UI_TEXTO_RECUSA_POLITICA_BANCO = "Recusa por política interna do banco"
UI_TEXTO_RECUSA_POLITICA_BANCO_MSG = "Não será possível seguir com a digitação. Recusa por política interna do banco."
UI_TEXTO_REQUISICAO_MAL_FORMATADA = "sua requisição está mal formatada"
UI_TEXTO_REQUISICAO_MAL_FORMATADA_ALT = "mal formatada"
UI_TEXTO_REQUISICAO_MAL_FORMATADA_MSG = "Infelizmente sua requisição está mal formatada, corrija e tente novamente."
UI_TEXTO_REGISTRO_NAO_ENCONTRADO = "não foi possível encontrar este registro"
UI_TEXTO_REGISTRO_NAO_ENCONTRADO_MSG = "Infelizmente não foi possível encontrar este registro."
STATUS_CONSULTA_SEM_SIMULACAO = "consulta_ok_sem_simulacao"
ERRO_SIMULACAO_NAO_REALIZADA = "Simulação não realizada (Tabela não preenchida ou sem opções)."
DEBUG_TABELA = os.environ.get("ROBO_DEBUG_TABELA", "").strip().lower() in ("1", "true", "yes")
TIMEOUT_VALIDACAO_OPCOES_TABELA_MS = 800
