from __future__ import annotations

import os
import re
from typing import Any, Iterable, Literal
from urllib.parse import urlparse

from playwright.sync_api import Page  # type: ignore[import-untyped]

import config
from robo.passivos import cpf_utils
from robo.passivos import csv_io
from robo.comms import fluxo_consulta
from robo.comms import historico
from robo.comms import navegacao
from robo.comms import termo
from robo.passivos.modelos import Cliente, TermoRequisicaoMalFormatada


def _preencher_e_submeter_termo(
    aba_termo: Page, page: Page, cpf_site: str, cliente: Cliente
) -> Literal["ok", "termo_em_processamento", "falha_btn_enviar", "termo_em_processamento_apos_envio"]:
    if os.environ.get("ROBO_DEBUG"):
        print("Termo: aguardando formulário...")
    aba_termo.get_by_text("Termo de Autorização", exact=False).first.wait_for(state="visible", timeout=10000)
    aba_termo.locator("input").first.wait_for(state="visible", timeout=8000)
    aba_termo.wait_for_timeout(400)
    texto_req_mal = getattr(config, "UI_TEXTO_REQUISICAO_MAL_FORMATADA", "")
    texto_req_mal_alt = getattr(config, "UI_TEXTO_REQUISICAO_MAL_FORMATADA_ALT", "")
    req_mal_visivel = False
    if texto_req_mal:
        try:
            if aba_termo.get_by_text(texto_req_mal, exact=False).first.is_visible():
                req_mal_visivel = True
        except Exception:
            pass
    if not req_mal_visivel and texto_req_mal_alt:
        try:
            if aba_termo.get_by_text(texto_req_mal_alt, exact=False).first.is_visible():
                req_mal_visivel = True
        except Exception:
            pass
    if req_mal_visivel:
        raise TermoRequisicaoMalFormatada()
    texto_proc = getattr(config, "UI_TEXTO_TERMO_EM_PROCESSAMENTO", "em processamento")
    try:
        bpv = aba_termo.get_by_text(texto_proc, exact=False).first.is_visible()
    except Exception:
        bpv = False
    if bpv:
        timeout_proc = getattr(config, "TIMEOUT_TERMO_PROCESSAMENTO_MS", 30000)
        processamento_resolvido = False
        for _ in range(max(1, timeout_proc // 2000)):
            aba_termo.wait_for_timeout(2000)
            try:
                if not aba_termo.get_by_text(texto_proc, exact=False).first.is_visible():
                    processamento_resolvido = True
                    break
                for txt in [config.UI_TEXTO_OBRIGADO] + getattr(config, "UI_TEXTO_OBRIGADO_ALT", []):
                    if aba_termo.get_by_text(txt, exact=False).first.is_visible():
                        processamento_resolvido = True
                        break
                if processamento_resolvido:
                    break
            except Exception:
                processamento_resolvido = True
                break
        if not processamento_resolvido:
            return "termo_em_processamento"
    if os.environ.get("ROBO_DEBUG"):
        print("Termo: preenchendo campos...")
    container_termo = aba_termo.get_by_text("Termo de Autorização", exact=False).first.locator("..").locator("..").locator("..")
    inputs_vis = container_termo.locator("input:not([type='hidden']):not([type='submit']):not([type='button'])").all()
    if len(inputs_vis) < 4:
        try:
            alt = aba_termo.locator("#validation-login").locator("input:not([type='hidden']):not([type='submit']):not([type='button'])").all()
            if len(alt) >= 4:
                inputs_vis = alt
        except Exception:
            pass
    preencheu = False
    if len(inputs_vis) >= 4:
        inputs_vis[0].fill(cpf_site)
        inputs_vis[1].fill(cliente.nome)
        inputs_vis[2].fill(cliente.email)
        inputs_vis[3].fill(cliente.contato)
        preencheu = True
    if not preencheu:
        campo_cpf_termo = aba_termo.get_by_label(re.compile(r"CPF\s*\*?", re.IGNORECASE)).or_(aba_termo.locator('input[name="cpf"], input[placeholder*="CPF"], input[id*="cpf"]').first)
        campo_cpf_termo.wait_for(state="visible", timeout=10000)
        try:
            campo_cpf_termo.first.fill(cpf_site)
            try:
                campo_cpf_termo.first.evaluate("(el, val) => { el.value = val; el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); }", cpf_site)
            except Exception:
                pass
            campo_nome_termo = aba_termo.get_by_label(re.compile(r"Nome\s*\*?", re.IGNORECASE)).or_(aba_termo.locator('input[placeholder*="Nome"], input[name="nome"], input[id*="nome"]').first)
            campo_nome_termo.first.fill(cliente.nome)
            try:
                campo_nome_termo.first.evaluate("(el, val) => { el.value = val; el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); }", cliente.nome)
            except Exception:
                pass
            campo_email_termo = aba_termo.get_by_label(re.compile(r"E-mail\s*\*?", re.IGNORECASE)).or_(aba_termo.locator('input[type="email"], input[name*="email"], input[placeholder*="mail"]').first)
            campo_email_termo.first.fill(cliente.email)
            try:
                campo_email_termo.first.evaluate("(el, val) => { el.value = val; el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); }", cliente.email)
            except Exception:
                pass
            campo_tel_termo = aba_termo.get_by_label(re.compile(r"Número de telefone|telefone\s*\*?", re.IGNORECASE)).or_(aba_termo.locator('input[name*="telefone"], input[placeholder*="telefone"], input[placeholder*="Número"], input[id*="telefone"]').first)
            campo_tel_termo.first.fill(cliente.contato)
            try:
                campo_tel_termo.first.evaluate("(el, val) => { el.value = val; el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); }", cliente.contato)
            except Exception:
                pass
        except Exception:
            raise
    checkboxes = aba_termo.get_by_role("checkbox").all()
    for chk in checkboxes:
        try:
            if not chk.is_checked():
                chk.check()
        except Exception:
            pass
    if len(checkboxes) == 0:
        try:
            for texto in [getattr(config, "UI_TEXTO_CHECKBOX_ACEITO", "Eu aceito os termos"), "Declaro que não estou em aviso"]:
                loc = aba_termo.get_by_text(re.compile(re.escape(texto), re.IGNORECASE)).first
                if loc.count() > 0 and loc.is_visible():
                    loc.click()
        except Exception:
            pass
    aba_termo.wait_for_timeout(300)
    req_mal_antes_enviar = False
    if texto_req_mal:
        try:
            if aba_termo.get_by_text(texto_req_mal, exact=False).first.is_visible():
                req_mal_antes_enviar = True
        except Exception:
            pass
    if not req_mal_antes_enviar and texto_req_mal_alt:
        try:
            if aba_termo.get_by_text(texto_req_mal_alt, exact=False).first.is_visible():
                req_mal_antes_enviar = True
        except Exception:
            pass
    if req_mal_antes_enviar:
        raise TermoRequisicaoMalFormatada()
    btn_enviar = (
        aba_termo.get_by_role("button", name=re.compile(r"ENVIAR", re.IGNORECASE))
        .or_(aba_termo.locator('button:has-text("ENVIAR")').first)
        .or_(aba_termo.locator("button").filter(has_text=re.compile(r"ENVIAR", re.IGNORECASE)).first)
        .or_(aba_termo.get_by_text(re.compile(r"^ENVIAR$", re.IGNORECASE)))
    )
    timeout_btn = getattr(config, "TIMEOUT_BOTAO_ENVIAR_MS", 10000)
    try:
        btn_enviar.first.wait_for(state="visible", timeout=timeout_btn)
    except Exception:
        return "falha_btn_enviar"
    try:
        aba_termo.wait_for_function("() => { const all = document.querySelectorAll('button'); for (const x of all) { if ((x.textContent || '').trim().toUpperCase().includes('ENVIAR') && !x.disabled) return true; } return false; }", timeout=min(6000, timeout_btn))
    except Exception:
        pass
    btn_enviar.first.scroll_into_view_if_needed(timeout=5000)
    aba_termo.wait_for_timeout(300)
    if os.environ.get("ROBO_DEBUG"):
        print("Termo: clicando ENVIAR...")
    try:
        btn_enviar.first.click(timeout=10000)
    except Exception:
        try:
            btn_enviar.first.click(force=True, timeout=10000)
        except Exception:
            raise
    aba_termo.wait_for_timeout(2000)
    textos_obrigado_early = [config.UI_TEXTO_OBRIGADO] + getattr(config, "UI_TEXTO_OBRIGADO_ALT", [])
    obrigado_ja_visivel = False
    for txt in textos_obrigado_early:
        try:
            if aba_termo.get_by_text(txt, exact=False).first.is_visible():
                obrigado_ja_visivel = True
                break
        except Exception:
            pass
    if not obrigado_ja_visivel:
        try:
            btn_enviar.first.click(force=True, timeout=10000)
        except Exception:
            pass
    if os.environ.get("ROBO_DEBUG"):
        print("Termo: aguardando confirmação...")
    timeout_obrigado = getattr(config, "TIMEOUT_TERMO_OBRIGADO_MS", 25000)
    textos_obrigado = [config.UI_TEXTO_OBRIGADO] + getattr(config, "UI_TEXTO_OBRIGADO_ALT", [])
    obrigado_ok = False
    timeout_proc_apos = getattr(config, "TIMEOUT_TERMO_PROCESSAMENTO_MS", 30000)
    texto_proc_apos = getattr(config, "UI_TEXTO_TERMO_EM_PROCESSAMENTO", "em processamento")
    for _ in range(max(1, timeout_proc_apos // 2000)):
        try:
            for txt in textos_obrigado:
                if aba_termo.get_by_text(txt, exact=False).first.is_visible():
                    obrigado_ok = True
                    break
            if obrigado_ok:
                break
        except Exception:
            pass
        aba_termo.wait_for_timeout(2000)
    if not obrigado_ok:
        try:
            if aba_termo.get_by_text(texto_proc_apos, exact=False).first.is_visible():
                return "termo_em_processamento_apos_envio"
        except Exception:
            pass
    if not obrigado_ok:
        for txt in textos_obrigado:
            try:
                aba_termo.wait_for_selector(f"text={txt}", timeout=timeout_obrigado // len(textos_obrigado))
                obrigado_ok = True
                break
            except Exception:
                pass
        if not obrigado_ok:
            aba_termo.wait_for_selector(f"text={config.UI_TEXTO_OBRIGADO}", timeout=timeout_obrigado)
    return "ok"


def _aguardar_status_linha_historico(
    pagina_consulta: Page,
    page: Page,
    linha_cpf: Any,
    locadores_linha: list,
    timeout_por_tentativa: int,
    check_historico_apos_erro: bool,
    lista_saida: list,
    cliente: Cliente,
    banco_atual: str,
) -> tuple[str, Any]:
    status_historico: str = "processando"
    texto_processando = getattr(config, "UI_TEXTO_PROCESSANDO", "Processando")
    max_recarregar = getattr(config, "MAX_RECARREGAR_PROCESSANDO", 15)
    for _tentativa_hist in range(max_recarregar + 1):
        st = None
        try:
            if linha_cpf.get_by_text(config.UI_TEXTO_ERRO_NA_CONSULTA, exact=False).first.is_visible():
                st = "erro"
        except Exception:
            pass
        if st is None:
            try:
                if linha_cpf.get_by_text(texto_processando, exact=False).first.is_visible():
                    st = "processando"
            except Exception:
                pass
        if st is None:
            try:
                texto_proc_alt = getattr(config, "UI_TEXTO_PROCESSANDO_ALT", "")
                if texto_proc_alt and linha_cpf.get_by_text(texto_proc_alt, exact=False).first.is_visible():
                    st = "processando"
            except Exception:
                pass
        if st is None:
            try:
                if linha_cpf.get_by_text(config.UI_TEXTO_SUCESSO, exact=False).first.is_visible():
                    st = "sucesso"
            except Exception:
                pass
        if st is None:
            st = "processando"
        if st == "erro":
            if check_historico_apos_erro:
                msg_req_mal = getattr(config, "UI_TEXTO_REQUISICAO_MAL_FORMATADA_MSG", "Requisição mal formatada no termo")
                csv_io.log_critico(lista_saida, cliente, banco_atual, "requisicao_mal_formatada", msg_req_mal)
                navegacao.voltar_para_consulta_limpa(page)
                return ("requisicao_mal_formatada", linha_cpf)
            csv_io.log_critico(lista_saida, cliente, banco_atual, "erro_na_consulta", config.UI_TEXTO_ERRO_NA_CONSULTA)
            navegacao.voltar_para_consulta_limpa(page)
            return ("erro", linha_cpf)
        if st == "processando":
            if _tentativa_hist >= max_recarregar:
                if check_historico_apos_erro:
                    msg_req_mal = getattr(config, "UI_TEXTO_REQUISICAO_MAL_FORMATADA_MSG", "Requisição mal formatada no termo")
                    csv_io.log_critico(lista_saida, cliente, banco_atual, "requisicao_mal_formatada", msg_req_mal)
                    navegacao.voltar_para_consulta_limpa(page)
                    return ("requisicao_mal_formatada", linha_cpf)
                csv_io.log_critico(lista_saida, cliente, banco_atual, "processando_timeout", "Status permaneceu Processando após recarregar")
                navegacao.voltar_para_consulta_limpa(page)
                return ("processando_timeout", linha_cpf)
            try:
                pagina_consulta.get_by_role("button", name=config.UI_BOTAO_RECARREGAR).first.click(timeout=5000)
            except Exception:
                pass
            try:
                pagina_consulta.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception:
                pass
            pagina_consulta.wait_for_timeout(config.PAUSA_APOS_RECARREGAR_MS)
            linha_cpf = None
            for loc in locadores_linha:
                try:
                    loc.wait_for(state="visible", timeout=timeout_por_tentativa)
                    linha_cpf = loc
                    break
                except Exception:
                    pass
            if linha_cpf is None:
                if check_historico_apos_erro:
                    msg_req_mal = getattr(config, "UI_TEXTO_REQUISICAO_MAL_FORMATADA_MSG", "Requisição mal formatada no termo")
                    csv_io.log_critico(lista_saida, cliente, banco_atual, "requisicao_mal_formatada", msg_req_mal)
                    navegacao.voltar_para_consulta_limpa(page)
                    return ("requisicao_mal_formatada", None)
                csv_io.log_critico(lista_saida, cliente, banco_atual, "processando_timeout", "Linha não encontrada após recarregar")
                navegacao.voltar_para_consulta_limpa(page)
                return ("processando_timeout", None)
        if st == "sucesso":
            return ("sucesso", linha_cpf)
    return ("processando_timeout", linha_cpf)


def processar_clientes(page: Page, clientes: Iterable[Cliente], caminho_saida: str) -> None:
    """Fluxo: por cliente -> por banco (QiTech, Celcoin) -> consulta ou resultado no histórico;
    se modal termo: abre aba termo, preenche, envia, volta e reconsulta;
    quando linha com Sucesso: abre resultado, extrai valor máximo, simula 6/12/18/24 meses, grava em lista_saida;
    no final chama salvar_dataframe_final."""
    timeout_ms = config.TIMEOUT_PROCESSAR_MS
    cpfs_ja_processados: set[str] = set()
    lista_saida: list = []
    for idx, cliente in enumerate(clientes):
        pular_cliente = False
        status = "nao_processado"
        mensagem_erro = ""
        valor_maximo_parcela = ""
        pular = False
        cpf_raw = cliente.cpf
        if not cpf_utils.cpf_valido_11(cpf_raw):
            csv_io.log_critico(lista_saida, cliente, "", "cpf_invalido", "CPF com tamanho diferente de 11 dígitos (provável perda no CSV)")
            pular = True
        cpf_site = cpf_utils.cpf_com_mascara(cpf_raw)
        try:
            if idx > 0:
                page.wait_for_timeout(config.PAUSA_ENTRE_CLIENTES_MS)

            if not pular:
                if cliente.cpf in cpfs_ja_processados:
                    print(f"CPF {cliente.cpf} já processado, pulando.")
                    pular = True
                else:
                    cpfs_ja_processados.add(cliente.cpf)
            if pular:
                navegacao.voltar_para_consulta_limpa(page)
                continue
            print(f"Processando CPF {cliente.cpf} - {cliente.nome}")
            try:
                banner_nova_versao = page.get_by_text(config.UI_TEXTO_NOVA_VERSAO_RECARREGANDO, exact=False).or_(page.get_by_text("Recarregando", exact=False)).first
                if banner_nova_versao.is_visible():
                    try:
                        with page.expect_navigation(timeout=12000):
                            page.wait_for_timeout(300)
                    except Exception:
                        pass
                    try:
                        page.wait_for_load_state("domcontentloaded", timeout=10000)
                    except Exception:
                        pass
                    page.wait_for_timeout(300)
            except Exception:
                    pass
            page.wait_for_timeout(200)
            try:
                page.wait_for_load_state("domcontentloaded", timeout=8000)
            except Exception:
                pass
            if fluxo_consulta.pagina_tem_restricao_emissao(page):
                try:
                    msg_restricao = page.get_by_text(config.UI_TEXTO_RESTRICAO_EMISSAO, exact=False).first.inner_text()[:500] if page.get_by_text(config.UI_TEXTO_RESTRICAO_EMISSAO, exact=False).first.is_visible() else config.UI_TEXTO_RESTRICAO_EMISSAO
                except Exception:
                    msg_restricao = config.UI_TEXTO_RESTRICAO_EMISSAO
                csv_io.log_critico(lista_saida, cliente, "", "restricao_emissao", msg_restricao.replace("\n", " ").replace("\r", ""))
                navegacao.voltar_para_consulta_limpa(page)
                continue
            campo_cpf = (
                page.get_by_label(config.UI_LABEL_CPF)
                .or_(page.get_by_placeholder(config.UI_PLACEHOLDER_CPF))
                .or_(page.locator('input[name="cpf"], input[id*="cpf"]').first)
            )
            campo_cpf.wait_for(state="visible", timeout=config.TIMEOUT_FORM_CONSULTA_MS)
            page.wait_for_timeout(200)

            for banco_atual in ["QiTech", "Celcoin"]:
                check_historico_apos_erro = False
                status = "nao_processado"
                mensagem_erro = ""
                valor_maximo_parcela = ""
                pagina_resultado = None
                linha_cpf = None
                aba_termo = None
                if pular_cliente:
                    break
                pagina_consulta_principal = navegacao.obter_pagina_consulta_principal(page)
                if pagina_consulta_principal and not pagina_consulta_principal.is_closed():
                    pagina_consulta_principal.bring_to_front()
                page.wait_for_timeout(150)
                print(f"Selecionando banco {banco_atual}...")
                if not fluxo_consulta.selecionar_banco(page, banco_atual):
                    csv_io.log_critico(lista_saida, cliente, banco_atual, "erro_selecao_banco", "Não foi possível selecionar o banco no formulário")
                    pular_cliente = True
                    break
                campo_cpf = page.get_by_label(config.UI_LABEL_CPF).or_(page.get_by_placeholder(config.UI_PLACEHOLDER_CPF)).or_(page.locator('input[name="cpf"], input[id*="cpf"]').first)
                try:
                    campo_cpf.fill(cpf_site)
                    try:
                        campo_cpf.first.evaluate("el => el.dispatchEvent(new Event('blur', { bubbles: true }))")
                    except Exception:
                        pass
                except Exception:
                    campo_cpf.evaluate("(el, val) => { el.value = val; el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); el.dispatchEvent(new Event('blur', { bubbles: true })); }", cpf_site)
                page.wait_for_timeout(150)
                fluxo_consulta.garantir_cpf_preenchido(page, cpf_site)
                page.wait_for_timeout(150)
                try:
                    if not campo_cpf.input_value().strip():
                        campo_cpf.fill(cpf_site)
                        page.wait_for_timeout(100)
                except Exception:
                    pass
                if historico.processar_resultado_existente_no_historico(page, cpf_site, banco_atual, cliente, lista_saida, timeout_ms):
                    continue
                fluxo_consulta.garantir_cpf_preenchido(page, cpf_site)
                pg_consulta = pagina_consulta_principal or page
                btn_consultar = pg_consulta.locator(f"#{config.UI_ID_BOTAO_CONSULTAR_SALDO}").or_(pg_consulta.get_by_role("button", name=config.UI_BOTAO_CONSULTAR_SALDO)).or_(pg_consulta.get_by_role("button", name=re.compile(r"consultar\s*saldo", re.IGNORECASE)))
                try:
                    btn_consultar.first.scroll_into_view_if_needed(timeout=2000)
                except Exception:
                    pass
                nav_ocorreu = False
                try:
                    btn_consultar.first.click(force=True)
                    page.wait_for_timeout(100)
                    def resultado_apareceu() -> bool:
                        p = pg_consulta
                        if fluxo_consulta.pagina_tem_restricao_emissao(p): return True
                        if fluxo_consulta.pagina_tem_cpf_invalido(p): return True
                        if fluxo_consulta.pagina_tem_cpf_nao_encontrado(p): return True
                        if fluxo_consulta.pagina_tem_registro_nao_encontrado(p): return True
                        if fluxo_consulta.pagina_tem_erro_na_consulta(p): return True
                        try:
                            if p.get_by_text(config.UI_TEXTO_MODAL_AUTORIZACAO, exact=False).first.is_visible(): return True
                        except Exception:
                            pass
                        try:
                            if p.get_by_text(config.UI_TEXTO_SEM_VINCULO, exact=False).first.is_visible(): return True
                        except Exception:
                            pass
                        try:
                            if p.locator(f"tr:has-text('{cpf_site}')").first.is_visible():
                                return True
                            if p.locator(f"tr:has-text('{cliente.cpf}')").first.is_visible():
                                return True
                        except Exception:
                            pass
                        return False
                    for _ in range(20):
                        if resultado_apareceu():
                            nav_ocorreu = True
                            break
                        page.wait_for_timeout(100)
                except Exception as e:
                    csv_io.log_critico(lista_saida, cliente, banco_atual, "falha_historico", str(e)[:300])
                    continue
                if not nav_ocorreu:
                    try:
                        page.wait_for_load_state("domcontentloaded", timeout=8000)
                    except Exception:
                        pass
                page.wait_for_timeout(config.PAUSA_APOS_CONSULTAR_MS)
                if fluxo_consulta.pagina_tem_registro_nao_encontrado(page):
                    msg_reg = getattr(config, "UI_TEXTO_REGISTRO_NAO_ENCONTRADO_MSG", "Infelizmente não foi possível encontrar este registro.")
                    csv_io.log_critico(lista_saida, cliente, banco_atual, "registro_nao_encontrado", msg_reg)
                    navegacao.voltar_para_consulta_limpa(page)
                    continue
                if banco_atual and "celcoin" in banco_atual.lower():
                    pausa_celcoin = getattr(config, "PAUSA_ESPERA_MODAL_CELCOIN_MS", 6000)
                    textos_modal = getattr(config, "UI_TEXTO_MODAL_AUTORIZACAO_CELCOIN", [config.UI_TEXTO_MODAL_AUTORIZACAO])
                    if isinstance(textos_modal, str):
                        textos_modal = [textos_modal]
                    for _ in range(max(1, pausa_celcoin // 300)):
                        try:
                            if any(page.get_by_text(t, exact=False).first.is_visible() for t in textos_modal):
                                break
                            if termo.extrair_link_termo_pagina(page):
                                break
                        except Exception:
                            pass
                        page.wait_for_timeout(300)
                if fluxo_consulta.pagina_tem_restricao_emissao(page):
                    try:
                        msg_restricao = page.get_by_text(config.UI_TEXTO_RESTRICAO_EMISSAO, exact=False).first.inner_text()[:500] if page.get_by_text(config.UI_TEXTO_RESTRICAO_EMISSAO, exact=False).first.is_visible() else config.UI_TEXTO_RESTRICAO_EMISSAO
                    except Exception:
                        msg_restricao = config.UI_TEXTO_RESTRICAO_EMISSAO
                    csv_io.log_critico(lista_saida, cliente, banco_atual, "restricao_emissao", msg_restricao.replace("\n", " ").replace("\r", ""))
                    navegacao.voltar_para_consulta_limpa(page)
                    continue
                page.wait_for_timeout(200)
                if fluxo_consulta.pagina_tem_cpf_invalido(page) and not fluxo_consulta.historico_tem_linha_sucesso_cpf(page, cpf_site):
                    try:
                        err_loc = page.get_by_text(config.UI_TEXTO_CPF_INVALIDO, exact=False).or_(page.get_by_text(getattr(config, "UI_TEXTO_CPF_INVALIDO_ALT2", "CPF informado não é válido"), exact=False)).first
                        msg_cpf = err_loc.inner_text()[:300].replace("\n", " ").replace("\r", "") if err_loc.is_visible() else "CPF inválido"
                    except Exception:
                        msg_cpf = "CPF inválido"
                    csv_io.log_critico(lista_saida, cliente, banco_atual, "cpf_invalido", msg_cpf)
                    pular_cliente = True
                    navegacao.voltar_para_consulta_limpa(page)
                    break
                if fluxo_consulta.pagina_tem_cpf_nao_encontrado(page):
                    try:
                        loc_cpf = page.get_by_text(config.UI_TEXTO_CPF_NAO_ENCONTRADO, exact=False).or_(page.get_by_text(getattr(config, "UI_TEXTO_CPF_NAO_ENCONTRADO_ALT", ""), exact=False)).first
                        msg_nao_enc = loc_cpf.inner_text()[:300].replace("\n", " ").replace("\r", "") if loc_cpf.is_visible() else config.UI_TEXTO_CPF_NAO_ENCONTRADO
                    except Exception:
                        msg_nao_enc = config.UI_TEXTO_CPF_NAO_ENCONTRADO
                    csv_io.log_critico(lista_saida, cliente, banco_atual, "cpf_nao_encontrado", msg_nao_enc)
                    navegacao.voltar_para_consulta_limpa(page)
                    break
                url_termo = None
                textos_modal_banco = getattr(config, "UI_TEXTO_MODAL_AUTORIZACAO_CELCOIN", [config.UI_TEXTO_MODAL_AUTORIZACAO]) if (banco_atual and "celcoin" in banco_atual.lower()) else [config.UI_TEXTO_MODAL_AUTORIZACAO]
                if isinstance(textos_modal_banco, str):
                    textos_modal_banco = [textos_modal_banco]
                modal_visivel = False
                for txt in textos_modal_banco:
                    try:
                        if page.get_by_text(txt, exact=False).first.is_visible():
                            modal_visivel = True
                            break
                    except Exception:
                        pass
                if modal_visivel:
                    page.get_by_text(textos_modal_banco[0], exact=False).first.wait_for(state="visible", timeout=8000)
                    url_termo = termo.extrair_link_termo_do_modal(page)
                    if not url_termo:
                        page.wait_for_timeout(200)
                        doms = getattr(config, "URL_TERMO_DOMAINS", ["assina.bancoprata.com.br"])
                        try:
                            for el in page.locator("input[readonly], input:not([type='hidden']), textarea").all():
                                try:
                                    v = (el.input_value() or "").strip().split("\n")[0].strip()
                                    if v.startswith("http") and any(d in v for d in doms):
                                        url_termo = v
                                        break
                                except Exception:
                                    pass
                        except Exception:
                            pass
                    if not url_termo and banco_atual and "celcoin" in banco_atual.lower():
                        url_termo = termo.extrair_link_termo_pagina(page)
                    if not url_termo:
                        status = "falha_modal_autorizacao"
                        mensagem_erro = "Não consegui extrair a URL do termo."
                        csv_io.log_critico(lista_saida, cliente, banco_atual, "falha_modal_autorizacao", mensagem_erro)
                        navegacao.voltar_para_consulta_limpa(page)
                        continue
                if not modal_visivel and not url_termo and banco_atual and "celcoin" in banco_atual.lower():
                    url_termo = termo.extrair_link_termo_pagina(page)
                if not modal_visivel and not url_termo and fluxo_consulta.pagina_tem_erro_na_consulta(page):
                    msg_erro = config.UI_TEXTO_ERRO_NA_CONSULTA
                    try:
                        loc_alt = page.get_by_text(getattr(config, "UI_TEXTO_SEM_VINCULO_ALT", config.UI_TEXTO_SEM_VINCULO), exact=False).first
                        if loc_alt.is_visible():
                            msg_erro = loc_alt.inner_text()[:300].replace("\n", " ").replace("\r", "")
                        else:
                            loc_vinculo = page.get_by_text(config.UI_TEXTO_SEM_VINCULO, exact=False).first
                            if loc_vinculo.is_visible():
                                msg_erro = loc_vinculo.inner_text()[:300].replace("\n", " ").replace("\r", "")
                    except Exception:
                        try:
                            loc_vinculo = page.get_by_text(config.UI_TEXTO_SEM_VINCULO, exact=False).first
                            if loc_vinculo.is_visible():
                                msg_erro = loc_vinculo.inner_text()[:300].replace("\n", " ").replace("\r", "")
                        except Exception:
                            pass
                    csv_io.log_critico(lista_saida, cliente, banco_atual, "erro_na_consulta", msg_erro)
                    navegacao.voltar_para_consulta_limpa(page)
                    continue
                if url_termo:
                    print("URL termo:", url_termo)
                    passo_termo = "inicio"
                    try:
                        parsed = urlparse(url_termo)
                        origin_termo = f"{parsed.scheme}://{parsed.netloc}"
                        page.context.grant_permissions(["geolocation"], origin=origin_termo)
                    except Exception:
                        try:
                            page.context.grant_permissions(["geolocation"], origin="https://assina.bancoprata.com.br")
                        except Exception:
                            pass
                    aba_termo = termo.abrir_termo_em_nova_aba(page, url_termo)
                    aba_termo.on("dialog", lambda d: d.accept())
                    aba_termo.wait_for_load_state("domcontentloaded")
                    try:
                        parsed_aba = urlparse(aba_termo.url)
                        page.context.grant_permissions(["geolocation"], origin=f"{parsed_aba.scheme}://{parsed_aba.netloc}")
                    except Exception:
                        pass
                    try:
                        resultado_termo = _preencher_e_submeter_termo(aba_termo, page, cpf_site, cliente)
                        if resultado_termo == "termo_em_processamento":
                            csv_io.log_critico(lista_saida, cliente, banco_atual, "aguardar_formulario_autorizacao", "Aguardar formulário de autorização")
                            navegacao.fechar_pagina_se_aberta(aba_termo)
                            page.bring_to_front()
                            navegacao.voltar_para_consulta_limpa(page)
                            continue
                        if resultado_termo == "falha_btn_enviar":
                            csv_io.log_critico(lista_saida, cliente, banco_atual, "aguardar_formulario_autorizacao", "Aguardar formulário de autorização")
                            navegacao.fechar_pagina_se_aberta(aba_termo)
                            page.bring_to_front()
                            navegacao.voltar_para_consulta_limpa(page)
                            continue
                        if resultado_termo == "termo_em_processamento_apos_envio":
                            csv_io.log_critico(lista_saida, cliente, banco_atual, "aguardar_formulario_autorizacao", "Aguardar formulário de autorização")
                            navegacao.fechar_pagina_se_aberta(aba_termo)
                            page.bring_to_front()
                            navegacao.voltar_para_consulta_limpa(page)
                            continue
                        navegacao.fechar_pagina_se_aberta(aba_termo)
                        page.bring_to_front()
                        page.get_by_role("button", name=config.UI_BOTAO_VOLTAR).first.wait_for(state="visible", timeout=8000)
                        page.get_by_role("button", name=config.UI_BOTAO_VOLTAR).first.click()
                        page.wait_for_timeout(400)
                        fluxo_consulta.garantir_cpf_preenchido(page, cpf_site)
                        if not fluxo_consulta.selecionar_banco(page, banco_atual):
                            csv_io.log_critico(lista_saida, cliente, banco_atual, "erro_selecao_banco", "Não foi possível selecionar o banco no formulário")
                            pular_cliente = True
                            break
                        btn_consultar.first.click()
                        page.wait_for_timeout(config.PAUSA_APOS_CONSULTAR_MS)
                        try:
                            page.wait_for_load_state("domcontentloaded", timeout=10000)
                        except Exception:
                            pass
                        page.wait_for_timeout(config.PAUSA_APOS_CONSULTAR_MS)
                        page.wait_for_timeout(500)
                        textos_modal_retry = getattr(config, "UI_TEXTO_MODAL_AUTORIZACAO_CELCOIN", [config.UI_TEXTO_MODAL_AUTORIZACAO]) if (banco_atual and "celcoin" in banco_atual.lower()) else [config.UI_TEXTO_MODAL_AUTORIZACAO]
                        if isinstance(textos_modal_retry, str):
                            textos_modal_retry = [textos_modal_retry]
                        aguardando_autorizacao = False
                        for txt in textos_modal_retry:
                            try:
                                if page.get_by_text(txt, exact=False).first.is_visible():
                                    aguardando_autorizacao = True
                                    break
                            except Exception:
                                pass
                        if not aguardando_autorizacao:
                            try:
                                if termo.extrair_link_termo_pagina(page):
                                    aguardando_autorizacao = True
                            except Exception:
                                pass
                        if aguardando_autorizacao:
                            csv_io.log_critico(lista_saida, cliente, banco_atual, "aguardar_formulario_autorizacao", "Aguardar formulário de autorização")
                            navegacao.voltar_para_consulta_limpa(page)
                            continue
                    except TermoRequisicaoMalFormatada:
                        check_historico_apos_erro = True
                    except Exception as e_termo:
                        msg_termo = str(e_termo).replace("\n", " ").replace("\r", "")[:450]
                        tipo_termo = type(e_termo).__name__
                        is_timeout = isinstance(e_termo, Exception) and ("Timeout" in tipo_termo or "Timeout" in msg_termo or "exceeded" in msg_termo.lower())
                        termo_processamento_visivel = False
                        if is_timeout and aba_termo:
                            try:
                                if not aba_termo.is_closed() and aba_termo.get_by_text(getattr(config, "UI_TEXTO_TERMO_EM_PROCESSAMENTO", "em processamento"), exact=False).first.is_visible():
                                    termo_processamento_visivel = True
                            except Exception:
                                pass
                        if termo_processamento_visivel:
                            csv_io.log_critico(lista_saida, cliente, banco_atual, "aguardar_formulario_autorizacao", "Aguardar formulário de autorização")
                        elif is_timeout:
                            csv_io.log_critico(lista_saida, cliente, banco_atual, "aguardar_formulario_autorizacao", "Aguardar formulário de autorização")
                        else:
                            csv_io.log_critico(lista_saida, cliente, banco_atual, "falha_termo_autorizacao", f"Termo ({passo_termo}): {tipo_termo}: {msg_termo}")
                        navegacao.fechar_pagina_se_aberta(aba_termo)
                        page.bring_to_front()
                        navegacao.voltar_para_consulta_limpa(page)
                        continue
                msg_vinculo = page.get_by_text(config.UI_TEXTO_SEM_VINCULO, exact=False).first
                try:
                    vinculo_visivel = msg_vinculo.is_visible()
                except Exception:
                    vinculo_visivel = False
                if vinculo_visivel:
                    msg_sem_vinculo = getattr(config, "UI_TEXTO_SEM_VINCULO", "Sem vínculo") if not mensagem_erro else mensagem_erro
                    csv_io.log_critico(lista_saida, cliente, banco_atual, "sem_vinculo", msg_sem_vinculo)
                    navegacao.voltar_para_consulta_limpa(page)
                    continue
                if status == "falha_modal_autorizacao":
                    csv_io.log_critico(lista_saida, cliente, banco_atual, status, mensagem_erro)
                    navegacao.voltar_para_consulta_limpa(page)
                    continue
                if check_historico_apos_erro:
                    try:
                        page.get_by_role("button", name=config.UI_BOTAO_RECARREGAR).first.click(timeout=5000)
                        page.wait_for_load_state("domcontentloaded", timeout=10000)
                        page.wait_for_timeout(config.PAUSA_APOS_RECARREGAR_MS)
                    except Exception as e:
                        csv_io.log_critico(lista_saida, cliente, banco_atual, "falha_historico", str(e)[:300])
                        continue
                try:
                    max_tentativas_tabela = getattr(config, "MAX_TENTATIVAS_TABELA_VISIVEL", 3)
                    linha_cpf = None
                    locadores_linha = []
                    status_historico = None
                    pagina_consulta = navegacao.obter_pagina_consulta_principal(page) or (page.context.pages[0] if page.context.pages else page)
                    for tentativa in range(max_tentativas_tabela):
                        try:
                            page.wait_for_load_state("domcontentloaded", timeout=10000)
                        except Exception:
                            pass
                        page.wait_for_timeout(200)
                        pagina_consulta = navegacao.obter_pagina_consulta_principal(page) or (page.context.pages[0] if page.context.pages else page)
                        try:
                            pagina_consulta.bring_to_front()
                        except Exception as e:
                            csv_io.log_critico(lista_saida, cliente, banco_atual, "falha_historico", str(e)[:300])
                            break
                        page.wait_for_timeout(200)
                        for _ in range(5):
                            try:
                                if pagina_consulta.get_by_text(cpf_site, exact=False).first.is_visible():
                                    break
                            except Exception:
                                pass
                            page.wait_for_timeout(200)
                        timeout_por_tentativa = min(5000, timeout_ms // 3)
                        linha_cpf, locadores_linha = historico.buscar_linha_historico(pagina_consulta, cpf_site, banco_atual, cliente, timeout_por_tentativa, max_tentativas=2, usar_recarregar=getattr(config, "USE_RECARREGAR_HISTORICO", False))
                        if linha_cpf is None:
                            if check_historico_apos_erro:
                                msg_req_mal = getattr(config, "UI_TEXTO_REQUISICAO_MAL_FORMATADA_MSG", "Requisição mal formatada no termo")
                                csv_io.log_critico(lista_saida, cliente, banco_atual, "requisicao_mal_formatada", msg_req_mal)
                                navegacao.voltar_para_consulta_limpa(page)
                                break
                            page.wait_for_timeout(300)
                            continue
                        status_historico, linha_cpf = _aguardar_status_linha_historico(
                            pagina_consulta, page, linha_cpf, locadores_linha, timeout_por_tentativa,
                            check_historico_apos_erro, lista_saida, cliente, banco_atual
                        )
                        if status_historico in ("erro", "requisicao_mal_formatada", "processando_timeout"):
                            break
                        if linha_cpf is None:
                            page.wait_for_timeout(300)
                            continue
                        break
                    if linha_cpf is None and not check_historico_apos_erro:
                        csv_io.log_critico(lista_saida, cliente, banco_atual, "falha_historico", f"Tabela não ficou visível após {max_tentativas_tabela} tentativas")
                        navegacao.voltar_para_consulta_limpa(page)
                        continue
                    if status_historico in ("erro", "requisicao_mal_formatada", "processando_timeout"):
                        continue
                    if linha_cpf is None:
                        continue
                    if banco_atual:
                        try:
                            texto_linha = linha_cpf.inner_text()
                            if banco_atual.lower() not in (texto_linha or "").lower():
                                csv_io.log_critico(lista_saida, cliente, banco_atual, "falha_historico", "Linha do histórico não corresponde ao banco atual")
                                navegacao.voltar_para_consulta_limpa(page)
                                continue
                        except Exception:
                            pass
                    btn_ver_resultado = (
                        linha_cpf.get_by_role("button", name=re.compile(r"ver\s*resultado", re.IGNORECASE))
                        .or_(linha_cpf.get_by_role("link", name=re.compile(r"ver\s*resultado", re.IGNORECASE)))
                        .or_(linha_cpf.locator("button, a, [role='button']").filter(has_text=re.compile(r"ver\s*resultado", re.IGNORECASE)))
                        .or_(linha_cpf.get_by_text(config.UI_BOTAO_VER_RESULTADO, exact=False))
                        .first
                    )
                    btn_ver_resultado.wait_for(state="visible", timeout=10000)
                    btn_ver_resultado.scroll_into_view_if_needed(timeout=5000)
                    if linha_cpf.get_by_text(config.UI_TEXTO_SUCESSO, exact=False).first.is_visible():
                        try:
                            pagina_resultado, ok = historico.abrir_resultado_historico(page.context, btn_ver_resultado, pagina_consulta)
                            if not ok or pagina_resultado is None:
                                raise RuntimeError("Falha ao abrir resultado")
                            pagina_resultado.bring_to_front()
                            deve_continuar, valor_extraido = historico.tratar_recusa_ou_requisicao_mal_formatada(pagina_resultado, page, cliente, banco_atual, lista_saida)
                            if deve_continuar:
                                continue
                            valor_maximo_parcela = valor_extraido
                            if valor_maximo_parcela:
                                status = "sucesso"
                        except BaseException as ex_abrir:
                            if not valor_maximo_parcela:
                                valor_maximo_parcela = ""
                            if status != "sucesso":
                                status = "falha_historico"
                                mensagem_erro = str(ex_abrir).replace("\n", " ").replace("\r", "")[:300]
                    else:
                        status = "status_nao_sucesso"
                        try:
                            pagina_resultado = pagina_consulta
                        except BaseException:
                            pagina_resultado = page.context.pages[0] if page.context.pages else page
                except BaseException as e:
                    if isinstance(e, (KeyboardInterrupt, SystemExit)):
                        raise
                    str_e = str(e)
                    if "Timeout" in type(e).__name__ or "Timeout" in str_e or "exceeded" in str_e.lower():
                        erro_msg = "Tela de resultado não carregou no tempo esperado"
                    else:
                        erro_msg = str_e.replace("\n", " ").replace("\r", "")[:500]
                    csv_io.log_critico(lista_saida, cliente, banco_atual, "falha_historico", erro_msg)
                    navegacao.voltar_para_consulta_limpa(page)
                    pagina_resultado = page.context.pages[0] if page.context.pages else page
                if not valor_maximo_parcela and status == "nao_processado":
                    status = "falha_historico"
                try:
                    if pagina_resultado and not pagina_resultado.is_closed():
                        pagina_resultado.locator(".simulation, .simulation-table, tr.expanded-row").or_(pagina_resultado.get_by_text(getattr(config, "UI_PLACEHOLDER_TABELA", "Selecione uma opção"), exact=False)).first.wait_for(state="visible", timeout=4000)
                except Exception:
                    pass
                if not valor_maximo_parcela and pagina_resultado and not pagina_resultado.is_closed():
                    try:
                        v = historico.extrair_valor_maximo_parcela(pagina_resultado)
                        if v:
                            valor_maximo_parcela = v
                            status = "sucesso"
                    except Exception:
                        pass
                if not valor_maximo_parcela or status != "sucesso":
                    if fluxo_consulta.pagina_tem_cpf_invalido(page):
                        status = "cpf_invalido"
                        try:
                            err_loc = page.get_by_text(config.UI_TEXTO_CPF_INVALIDO, exact=False).or_(page.get_by_text(getattr(config, "UI_TEXTO_CPF_INVALIDO_ALT2", "CPF informado não é válido"), exact=False)).first
                            mensagem_erro = err_loc.inner_text()[:300].replace("\n", " ").replace("\r", "") if err_loc.is_visible() else config.UI_TEXTO_CPF_INVALIDO
                        except Exception:
                            mensagem_erro = config.UI_TEXTO_CPF_INVALIDO
                    csv_io.log_critico(lista_saida, cliente, banco_atual, status, mensagem_erro or "Erro não especificado")
                    navegacao.voltar_para_consulta_limpa(page)
                    continue
                gravou_alguma_linha_simulacao = False
                simulacao_foi_tentada = False
                if pagina_resultado is not None and linha_cpf is not None:
                    try:
                        if not pagina_resultado.is_closed():
                            try:
                                pagina_resultado.bring_to_front()
                            except Exception:
                                pass
                        timeout_bloco = getattr(config, "TIMEOUT_ESPERA_BLOCO_SIMULACAO_MS", 6000)
                        try:
                            pagina_resultado.locator("tr.expanded-row, .simulation, .simulation-table").first.wait_for(state="visible", timeout=timeout_bloco)
                        except Exception:
                            try:
                                pagina_resultado.get_by_text(config.UI_TEXTO_VALOR_MAXIMO_PARCELA, exact=False).first.wait_for(state="visible", timeout=timeout_bloco)
                            except Exception:
                                pass
                        escopo_simulacao: Any = pagina_resultado
                        try:
                            bloco_vue = pagina_resultado.locator("tr.expanded-row").locator(".simulation, .simulation-table").first
                            if bloco_vue.count() > 0 and bloco_vue.is_visible():
                                escopo_simulacao = bloco_vue
                        except Exception:
                            pass
                        if escopo_simulacao == pagina_resultado:
                            try:
                                bloco = pagina_resultado.locator("div, section").filter(has=pagina_resultado.get_by_text(config.UI_TEXTO_VALOR_MAXIMO_PARCELA, exact=False)).filter(has=pagina_resultado.get_by_text(config.UI_LABEL_TABELA, exact=False)).first
                                if bloco.count() > 0 and bloco.is_visible():
                                    escopo_simulacao = bloco
                            except Exception:
                                pass
                        if escopo_simulacao == pagina_resultado and "clt/consultar" in pagina_resultado.url:
                            try:
                                bloco_expandido = linha_cpf.locator("xpath=following-sibling::*[1]").or_(linha_cpf.locator("xpath=ancestor::*[.//*[contains(translate(text(), 'VALOR', 'valor'), 'valor máximo')]][1]")).first
                                if bloco_expandido.count() > 0 and bloco_expandido.get_by_text(config.UI_TEXTO_VALOR_MAXIMO_PARCELA, exact=False).first.is_visible():
                                    escopo_simulacao = bloco_expandido
                            except Exception:
                                pass
                        try:
                            escopo_simulacao.get_by_text(config.UI_TEXTO_VALOR_MAXIMO_PARCELA, exact=False).first.wait_for(state="visible", timeout=3000)
                        except Exception:
                            pass
                        try:
                            escopo_simulacao.get_by_label(config.UI_LABEL_TIPO).select_option(label=config.UI_OPCAO_VALOR_PARCELA)
                        except Exception:
                            pass
                        def _cb_tabela(aberto: bool, metodo: str) -> None:
                            print(f"[Tabela] aberta={aberto} metodo={metodo}")
                        res = historico.simular_tabelas(escopo_simulacao, valor_maximo_parcela, cliente, banco_atual, lista_saida, pagina_resultado, on_abrir_tabela=_cb_tabela)
                        gravou_alguma_linha_simulacao = res[0] if isinstance(res, tuple) else res
                        simulacao_foi_tentada = res[1] if isinstance(res, tuple) and len(res) > 1 else gravou_alguma_linha_simulacao
                    except Exception:
                        try:
                            v_fallback = valor_maximo_parcela
                            if not v_fallback:
                                v_fallback = historico.extrair_valor_maximo_parcela(pagina_resultado)
                            def _cb_tabela_fb(aberto: bool, metodo: str) -> None:
                                print(f"[Tabela fallback] aberta={aberto} metodo={metodo}")
                            res = historico.simular_tabelas(pagina_resultado, v_fallback, cliente, banco_atual, lista_saida, pagina_resultado, on_abrir_tabela=_cb_tabela_fb)
                            gravou_alguma_linha_simulacao = res[0] if isinstance(res, tuple) else res
                            simulacao_foi_tentada = res[1] if isinstance(res, tuple) and len(res) > 1 else gravou_alguma_linha_simulacao
                        except Exception:
                            simulacao_foi_tentada = False
                if valor_maximo_parcela and not simulacao_foi_tentada:
                    status_sem_sim = getattr(config, "STATUS_CONSULTA_SEM_SIMULACAO", "consulta_ok_sem_simulacao")
                    erro_sem_sim = getattr(config, "ERRO_SIMULACAO_NAO_REALIZADA", "Simulação não realizada (Tabela não preenchida ou sem opções).")
                    csv_io.log_critico(lista_saida, cliente, banco_atual, status_sem_sim, erro_sem_sim)
                navegacao.fechar_pagina_se_aberta(pagina_resultado, page)
                pagina_consulta_principal = navegacao.obter_pagina_consulta_principal(page)
                voltou_consulta = bool(pagina_consulta_principal)
                if pagina_consulta_principal:
                    try:
                        pagina_consulta_principal.bring_to_front()
                    except Exception:
                        pass
                precisa_voltar = not voltou_consulta
                if not precisa_voltar and pagina_resultado and not pagina_resultado.is_closed():
                    try:
                        if "clt/consultar" not in pagina_resultado.url:
                            precisa_voltar = True
                    except Exception:
                        precisa_voltar = True
                if precisa_voltar:
                    try:
                        pg = page.context.pages[0] if page.context.pages else page
                        pg.bring_to_front()
                        pg.goto(config.URL_ADMIN_BASE + "clt/consultar", wait_until="domcontentloaded")
                    except Exception:
                        pass
                continue
            if pular_cliente:
                navegacao.voltar_para_consulta_limpa(page)
                continue
        except BaseException as e:
            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                raise
            print(f"Erro ao processar cliente {cliente.cpf}: {e}")
            try:
                erro_msg = str(e).replace("\n", " ").replace("\r", "")[:500]
                csv_io.log_critico(lista_saida, cliente, "", "falha_historico", erro_msg)
            except Exception:
                pass
        navegacao.voltar_para_consulta_limpa(page)
    csv_io.salvar_dataframe_final(caminho_saida, lista_saida)
