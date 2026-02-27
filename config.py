# URLs e rotas
URL_ADMIN_BASE = "https://admin.bancoprata.com.br/"
URL_HUB_PATTERN = "**/hub"
URL_CLT_CONSULTAR_PATTERN = "**/clt/consultar"
URL_TERMO_CONTAIN = "assina.bancoprata.com.br/credito-trabalhador/termo-autorizacao"
URL_TERMO_CONTAIN_ALT = "credito-trabalhador/autorizar"

# Viewport 
VIEWPORT_LARGURA = 1920
VIEWPORT_ALTURA = 1080

# Timeouts (ms)
TIMEOUT_LOGIN_MS = 45000
TIMEOUT_LOGIN_FORM_MS = 10000
TIMEOUT_FORM_CONSULTA_MS = 6000
TIMEOUT_PROCESSAR_MS = 18000
TIMEOUT_VALOR_MAX_MS = 12000
PAUSA_ENTRE_CLIENTES_MS = 150
PAUSA_APOS_CONSULTAR_MS = 400
PAUSA_APOS_RECARREGAR_MS = 2500
PAUSA_APOS_VER_RESULTADO_MS = 400
PAUSA_APOS_SIMULAR_MS = 350
SLOW_MO_HEADED_MS = 80

# Paths
DIR_ENTRADA_PADRAO = "entrada"
ARQUIVO_ENTRADA_PADRAO = "clientes.csv"
DIR_SAIDA_PADRAO = "saida"
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
    "valor_maximo_parcela",
    "qtd_parcelas",
    "valor_liberado",
    "valor_parcela",
    "valor_total",
    "status",
    "erro",
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
UI_BOTAO_CONSULTAR_SALDO = "Consultar saldo"
UI_ID_BOTAO_CONSULTAR_SALDO = "btnConsultar"
UI_TEXTO_MODAL_AUTORIZACAO = "Solicite a autorização do cliente"
UI_LABEL_NOME = "Nome"
UI_LABEL_TELEFONE = "Telefone"
UI_BOTAO_ENVIAR = "ENVIAR"
UI_TEXTO_OBRIGADO = "Obrigado"
UI_BOTAO_VOLTAR = "Voltar"
UI_TEXTO_SEM_VINCULO = "não possui vínculos empregatícios ativos"
UI_TEXTO_CPF_INVALIDO = "CPF inválido"
UI_TEXTO_RESTRICAO_EMISSAO = "Não é permitida a emissão de propostas"
UI_BOTAO_RECARREGAR = "Recarregar"
UI_TEXTO_NOVA_VERSAO_RECARREGANDO = "Nova versão detectada"
USE_RECARREGAR_HISTORICO = False
UI_BOTAO_VER_RESULTADO = "Ver resultado"
UI_TEXTO_SUCESSO = "Sucesso"
UI_TEXTO_VALOR_MAXIMO_PARCELA = "Valor máximo da parcela"
UI_LABEL_TABELA = "Tabela"
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
