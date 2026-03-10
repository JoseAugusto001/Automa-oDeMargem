from robo.comms.historico import abrir_resultado_historico, buscar_linha_historico, extrair_valor_maximo_parcela, processar_resultado_existente_no_historico, simular_tabelas, tratar_recusa_ou_requisicao_mal_formatada
from robo.comms.navegacao import fechar_pagina_se_aberta, login_e_ir_para_consulta, obter_pagina_consulta_principal, voltar_para_consulta_limpa
from robo.comms.termo import abrir_termo_em_nova_aba, extrair_link_termo_do_modal, extrair_link_termo_pagina
from robo.comms.fluxo_consulta import (
    garantir_cpf_preenchido,
    historico_tem_linha_sucesso_cpf,
    pagina_tem_cpf_invalido,
    pagina_tem_cpf_nao_encontrado,
    pagina_tem_erro_na_consulta,
    pagina_tem_registro_nao_encontrado,
    pagina_tem_restricao_emissao,
    selecionar_banco,
)

__all__ = [
    "abrir_resultado_historico",
    "buscar_linha_historico",
    "extrair_valor_maximo_parcela",
    "processar_resultado_existente_no_historico",
    "simular_tabelas",
    "tratar_recusa_ou_requisicao_mal_formatada",
    "fechar_pagina_se_aberta",
    "login_e_ir_para_consulta",
    "obter_pagina_consulta_principal",
    "voltar_para_consulta_limpa",
    "abrir_termo_em_nova_aba",
    "extrair_link_termo_do_modal",
    "extrair_link_termo_pagina",
    "garantir_cpf_preenchido",
    "historico_tem_linha_sucesso_cpf",
    "pagina_tem_cpf_invalido",
    "pagina_tem_cpf_nao_encontrado",
    "pagina_tem_erro_na_consulta",
    "pagina_tem_registro_nao_encontrado",
    "pagina_tem_restricao_emissao",
    "selecionar_banco",
]
