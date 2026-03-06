from robo.comms.navegacao import login_e_ir_para_consulta, voltar_para_consulta_limpa
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
    "login_e_ir_para_consulta",
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
