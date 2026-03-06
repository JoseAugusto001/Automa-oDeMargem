from __future__ import annotations

import json
import os
import re
import time
from typing import TYPE_CHECKING, List, Tuple

import config
# #region agent log
def _log_dbg(loc: str, msg: str, data: dict, hyp: str) -> None:
    try:
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "debug-b0ec0f.log")
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"b0ec0f","location":loc,"message":msg,"data":data,"timestamp":int(time.time()*1000),"hypothesisId":hyp}) + "\n")
    except Exception:
        pass
# #endregion
from robo.passivos.csv_io import log_critico
from robo.passivos.modelos import Cliente

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page


def buscar_linha_historico(
    pagina_consulta: "Page",
    cpf_site: str,
    banco_atual: str,
    cliente: Cliente,
    timeout_por_tentativa: int,
    max_tentativas: int = 2,
    usar_recarregar: bool = False,
) -> Tuple["Locator | None", List["Locator"]]:
    cpf_digitos = cliente.cpf
    if banco_atual:
        locadores_linha = [
            pagina_consulta.locator(f"tr:has-text('{cpf_digitos}'):has-text('{banco_atual}')").first,
            pagina_consulta.locator(f"[role='row']:has-text('{cpf_digitos}'):has-text('{banco_atual}')").first,
            pagina_consulta.locator(f"tr:has-text('{cpf_site}'):has-text('{banco_atual}')").first,
            pagina_consulta.locator(f"[role='row']:has-text('{cpf_site}'):has-text('{banco_atual}')").first,
            pagina_consulta.locator(f"div:has-text('{cpf_site}'):has-text('{banco_atual}')").first,
            pagina_consulta.locator(f"[class*='row']:has-text('{cpf_site}'):has-text('{banco_atual}')").first,
            pagina_consulta.locator(f"[data-testid*='row']:has-text('{cpf_site}')").first,
        ]
    else:
        locadores_linha = [
            pagina_consulta.locator(f"tr:has-text('{cliente.cpf}')").first,
            pagina_consulta.locator(f"tr:has-text('{cpf_site}')").first,
            pagina_consulta.locator(f"[role='row']:has-text('{cpf_site}')").first,
            pagina_consulta.locator(f"li:has-text('{cpf_site}')").first,
            pagina_consulta.locator(f"div:has-text('{cpf_site}')").first,
            pagina_consulta.locator("tr, [role='row'], li, div").filter(has=pagina_consulta.get_by_text(cpf_site, exact=False)).filter(has=pagina_consulta.get_by_role("button", name=config.UI_BOTAO_VER_RESULTADO)).first,
        ]
    linha_cpf = None
    for tentativa in range(max_tentativas):
        for loc in locadores_linha:
            try:
                loc.wait_for(state="visible", timeout=timeout_por_tentativa)
                linha_cpf = loc
                break
            except Exception:
                pass
        if linha_cpf is not None:
            break
        if tentativa < max_tentativas - 1:
            pagina_consulta.wait_for_timeout(500)
    if linha_cpf is None and usar_recarregar:
        try:
            pagina_consulta.get_by_role("button", name=config.UI_BOTAO_RECARREGAR).first.click(timeout=5000)
            pagina_consulta.wait_for_load_state("domcontentloaded", timeout=10000)
            pagina_consulta.wait_for_timeout(config.PAUSA_APOS_RECARREGAR_MS)
            for tentativa2 in range(max_tentativas):
                for loc in locadores_linha:
                    try:
                        loc.wait_for(state="visible", timeout=timeout_por_tentativa)
                        linha_cpf = loc
                        break
                    except Exception:
                        pass
                if linha_cpf is not None:
                    break
                if tentativa2 < max_tentativas - 1:
                    pagina_consulta.wait_for_timeout(500)
        except Exception:
            pass
    return (linha_cpf, locadores_linha)


def _resultado_aberto_inline(pagina: "Page") -> bool:
    checks = [
        lambda: pagina.get_by_text(config.UI_TEXTO_VALOR_MAXIMO_PARCELA, exact=False).first.is_visible(),
        lambda: pagina.get_by_text(config.UI_LABEL_TABELA, exact=False).first.is_visible(),
        lambda: pagina.get_by_role("button", name=config.UI_BOTAO_SIMULAR).first.is_visible(),
        lambda: pagina.get_by_text(getattr(config, "UI_PLACEHOLDER_TABELA", "Selecione uma opção"), exact=False).first.is_visible(),
        lambda: pagina.get_by_text("Valor esperado", exact=False).first.is_visible(),
    ]
    for fn in checks:
        try:
            if fn():
                return True
        except Exception:
            pass
    return False


def abrir_resultado_historico(ctx, btn_ver_resultado, pagina_consulta=None) -> Tuple["Page | None", bool]:
    try:
        with ctx.expect_page(timeout=1500) as popup_info:
            btn_ver_resultado.click()
        pagina_resultado = popup_info.value
        pagina_resultado.wait_for_load_state("domcontentloaded", timeout=8000)
        return (pagina_resultado, True)
    except BaseException:
        pass
    if pagina_consulta and not pagina_consulta.is_closed():
        ph = getattr(config, "UI_PLACEHOLDER_TABELA", "Selecione uma opção")
        try:
            pagina_consulta.get_by_text(ph, exact=False).first.wait_for(state="visible", timeout=6000)
            return (pagina_consulta, True)
        except Exception:
            pass
        try:
            pagina_consulta.get_by_text(config.UI_TEXTO_VALOR_MAXIMO_PARCELA, exact=False).first.wait_for(state="visible", timeout=4000)
            return (pagina_consulta, True)
        except Exception:
            pass
    return (None, False)


def extrair_valor_maximo_parcela(pagina: "Page", timeout_ms: int | None = None) -> str:
    if timeout_ms is None:
        timeout_ms = config.TIMEOUT_VALOR_MAX_MS
    try:
        bloco_valor = pagina.get_by_text(config.UI_TEXTO_VALOR_MAXIMO_PARCELA, exact=False).first
        bloco_valor.wait_for(state="visible", timeout=timeout_ms)
        texto = bloco_valor.evaluate("el => el.closest('div')?.innerText || el.parentElement?.innerText || ''")
        match = re.search(r"[\d.,]+", texto.replace("R$", "").strip())
        return match.group(0).replace(".", "").replace(",", ".") if match else ""
    except BaseException:
        return ""


def tratar_recusa_ou_requisicao_mal_formatada(
    pagina_resultado: "Page",
    page: "Page",
    cliente: Cliente,
    banco_atual: str,
    lista_saida: list,
) -> Tuple[bool, str]:
    from robo.comms.navegacao import voltar_para_consulta_limpa
    texto_recusa = getattr(config, "UI_TEXTO_RECUSA_POLITICA_BANCO", "")
    msg_recusa_csv = getattr(config, "UI_TEXTO_RECUSA_POLITICA_BANCO_MSG", texto_recusa)
    if texto_recusa:
        try:
            if pagina_resultado.get_by_text(texto_recusa, exact=False).first.is_visible():
                log_critico(lista_saida, cliente, banco_atual, "recusa_politica_banco", msg_recusa_csv)
                voltar_para_consulta_limpa(page)
                return (True, "")
        except Exception:
            pass
    texto_req_mal = getattr(config, "UI_TEXTO_REQUISICAO_MAL_FORMATADA", "")
    texto_req_mal_alt = getattr(config, "UI_TEXTO_REQUISICAO_MAL_FORMATADA_ALT", "")
    req_mal_resultado = False
    if texto_req_mal:
        try:
            if pagina_resultado.get_by_text(texto_req_mal, exact=False).first.is_visible():
                req_mal_resultado = True
        except Exception:
            pass
    if not req_mal_resultado and texto_req_mal_alt:
        try:
            if pagina_resultado.get_by_text(texto_req_mal_alt, exact=False).first.is_visible():
                req_mal_resultado = True
        except Exception:
            pass
    if req_mal_resultado:
        msg_req_mal = getattr(config, "UI_TEXTO_REQUISICAO_MAL_FORMATADA_MSG", "Requisição mal formatada")
        log_critico(lista_saida, cliente, banco_atual, "requisicao_mal_formatada", msg_req_mal)
        voltar_para_consulta_limpa(page)
        return (True, "")
    valor = extrair_valor_maximo_parcela(pagina_resultado)
    return (False, valor)


def _clicar_por_texto(pagina: "Page", texto: str, exato: bool = False) -> bool:
    try:
        if exato:
            ok = pagina.evaluate("""(txt) => {
                const walk = (el) => {
                    if (el.nodeType !== 1) return false;
                    if ((el.textContent || '').trim() === txt && el.offsetParent !== null) {
                        el.click();
                        return true;
                    }
                    for (const c of el.children) { if (walk(c)) return true; }
                    return false;
                };
                return walk(document.body);
            }""", texto)
        else:
            ok = pagina.evaluate("""(txt) => {
                const t = (txt || '').toLowerCase();
                const walk = (el) => {
                    if (el.nodeType !== 1) return false;
                    const content = (el.textContent || '').trim();
                    if (content && content.toLowerCase().includes(t) && el.offsetParent !== null && content.length < 80) {
                        el.click();
                        return true;
                    }
                    for (const c of el.children) { if (walk(c)) return true; }
                    return false;
                };
                return walk(document.body);
            }""", texto)
        return bool(ok)
    except Exception:
        return False


def _obter_opcoes_tabela_combobox(escopo: "Page | Locator", pagina_resultado: "Page", banco_atual: str) -> List[tuple]:
    placeholder_tabela = re.compile(r"selecione\s*(uma\s*)?op[çc][aã]o", re.IGNORECASE)
    opcoes_com_meses: List[tuple] = []
    ph_tabela = getattr(config, "UI_PLACEHOLDER_TABELA", "Selecione uma opção")
    triggers = [
        escopo.get_by_text(ph_tabela, exact=False).first,
        escopo.locator('[role="combobox"]').nth(1),
        escopo.locator('[role="combobox"]').nth(0),
        escopo.get_by_label(config.UI_LABEL_TABELA).first,
        escopo.locator('select[name*="tabela"], select[id*="tabela"]').first,
    ]
    trigger_tabela = None
    for t in triggers:
        try:
            if t.count() > 0 and t.is_visible():
                trigger_tabela = t
                break
        except Exception:
            pass
    if trigger_tabela is None:
        return opcoes_com_meses
    try:
        trigger_tabela.click()
        pagina_resultado.wait_for_timeout(550)
    except Exception:
        return opcoes_com_meses
    for scope in [escopo, pagina_resultado]:
        for lb_get in [
            lambda s: s.get_by_role("listbox").filter(has_text=re.compile(r"\d+\s*meses", re.IGNORECASE)).first,
            lambda s: s.locator('[class*="v-list"]').filter(has_text=re.compile(r"\d+\s*meses", re.IGNORECASE)).first,
            lambda s: s.locator('[class*="v-menu"]').filter(has_text=re.compile(r"\d+\s*meses", re.IGNORECASE)).first,
            lambda s: s.locator('[class*="menu"]').filter(has_text=re.compile(r"\d+\s*meses", re.IGNORECASE)).first,
        ]:
            try:
                lb = lb_get(scope)
                if lb.count() > 0 and lb.is_visible():
                    for opt_sel in ["[role='option']", ".v-list-item", "[class*='list-item']", "li"]:
                        try:
                            opts = lb.locator(opt_sel).all_inner_texts()
                            for txt in opts:
                                txt = (txt or "").strip()
                                if not txt or placeholder_tabela.search(txt):
                                    continue
                                m = re.search(r"(\d+)\s*(?:meses|mes|parcelas?|x)?", txt, re.IGNORECASE)
                                if m:
                                    opcoes_com_meses.append((int(m.group(1)), txt))
                            if opcoes_com_meses:
                                return opcoes_com_meses
                        except Exception:
                            pass
            except Exception:
                pass
    labels_celcoin = ["6 meses (C)", "12 meses (C)", "18 meses (C)", "24 meses (C)"]
    labels_qitech = ["6 meses", "12 meses", "18 meses", "24 meses"]
    for label in (labels_celcoin if banco_atual and "celcoin" in banco_atual.lower() else labels_qitech):
        try:
            loc = escopo.get_by_text(label, exact=False).or_(pagina_resultado.get_by_text(label, exact=False)).first
            if loc.count() > 0 and loc.is_visible():
                mm = re.match(r"(\d+)", label)
                if mm:
                    opcoes_com_meses.append((int(mm.group(0)), label))
        except Exception:
            pass
    if not opcoes_com_meses:
        for label in labels_qitech if (banco_atual and "celcoin" in banco_atual.lower()) else labels_celcoin:
            try:
                loc = escopo.get_by_text(label, exact=False).or_(pagina_resultado.get_by_text(label, exact=False)).first
                if loc.count() > 0 and loc.is_visible():
                    mm = re.match(r"(\d+)", label)
                    if mm:
                        opcoes_com_meses.append((int(mm.group(0)), label))
            except Exception:
                pass
    return opcoes_com_meses


def simular_tabelas(
    escopo: "Page | Locator",
    valor_maximo_parcela: str,
    cliente: Cliente,
    banco_atual: str,
    lista_saida: list,
    pagina_resultado: "Page | None" = None,
) -> bool:
    if pagina_resultado is None:
        pagina_resultado = escopo
    labels_celcoin = ["6 meses (C)", "12 meses (C)", "18 meses (C)", "24 meses (C)"]
    labels_qitech = ["6 meses", "12 meses", "18 meses", "24 meses"]
    opcoes_com_meses = [(6, labels_celcoin[0] if "celcoin" in (banco_atual or "").lower() else labels_qitech[0]),
                        (12, labels_celcoin[1] if "celcoin" in (banco_atual or "").lower() else labels_qitech[1]),
                        (18, labels_celcoin[2] if "celcoin" in (banco_atual or "").lower() else labels_qitech[2]),
                        (24, labels_celcoin[3] if "celcoin" in (banco_atual or "").lower() else labels_qitech[3])]
    pausa_dropdown = getattr(config, "PAUSA_APOS_ABRIR_DROPDOWN_TABELA_MS", 450)
    timeout_opcao = getattr(config, "TIMEOUT_OPCAO_TABELA_MS", 2500)
    gravou_alguma = False
    cb_count = -1
    try:
        cb_count = escopo.locator('[role="combobox"]').count()
    except Exception:
        pass
    # #region agent log
    _log_dbg("historico.py:simular_tabelas", "inicio_loop", {"combobox_count": cb_count, "banco": banco_atual}, "H3")
    # #endregion
    for _meses, label_tabela in opcoes_com_meses:
        linha_status = "falha_simulacao"
        valor_liberado = ""
        valor_parcela = ""
        valor_total = ""
        qtd_parcelas = str(_meses)
        erro_linha = ""
        try:
            trigger_aberto = False
            try:
                cb = escopo.locator('[role="combobox"]').nth(1)
                if cb.count() > 0:
                    cb.scroll_into_view_if_needed(timeout=1000)
                    cb.click(force=True, timeout=1500)
                    trigger_aberto = True
            except Exception:
                pass
            if not trigger_aberto:
                try:
                    lbl = escopo.get_by_label(config.UI_LABEL_TABELA).first
                    if lbl.count() > 0:
                        lbl.scroll_into_view_if_needed(timeout=1000)
                        lbl.click(force=True, timeout=1500)
                        trigger_aberto = True
                except Exception:
                    pass
            if not trigger_aberto:
                try:
                    el_valor = escopo.get_by_text(re.compile(r"\d+\s*meses", re.IGNORECASE)).first
                    if el_valor.count() > 0 and el_valor.is_visible():
                        el_valor.scroll_into_view_if_needed(timeout=1000)
                        el_valor.click(force=True, timeout=1500)
                        trigger_aberto = True
                except Exception:
                    pass
            if not trigger_aberto:
                _clicar_por_texto(pagina_resultado, "Tabela")
            # #region agent log
            _log_dbg("historico.py:trigger", "apos_abrir_dropdown", {"trigger_aberto": trigger_aberto, "label": label_tabela}, "H1")
            # #endregion
            pagina_resultado.wait_for_timeout(pausa_dropdown)
            opcao_clicada = False
            try:
                opt = pagina_resultado.get_by_role("option", name=label_tabela).first
                if opt.count() > 0:
                    opt.wait_for(state="visible", timeout=min(1500, timeout_opcao))
                    opt.click(timeout=timeout_opcao)
                    opcao_clicada = True
            except Exception:
                pass
            if not opcao_clicada:
                try:
                    loc = pagina_resultado.get_by_text(label_tabela, exact=True).first
                    if loc.count() > 0:
                        loc.wait_for(state="visible", timeout=min(1500, timeout_opcao))
                        loc.click(timeout=timeout_opcao)
                        opcao_clicada = True
                except Exception:
                    pass
            if not opcao_clicada:
                if not _clicar_por_texto(pagina_resultado, label_tabela, exato=True):
                    _clicar_por_texto(pagina_resultado, label_tabela)
            # #region agent log
            _log_dbg("historico.py:opcao", "antes_simular", {"opcao_clicada": opcao_clicada, "trigger_aberto": trigger_aberto, "label": label_tabela}, "H2")
            # #endregion
            pagina_resultado.wait_for_timeout(250)
            try:
                escopo.get_by_role("button", name=config.UI_BOTAO_SIMULAR).first.click(timeout=2000)
            except Exception:
                _clicar_por_texto(pagina_resultado, config.UI_BOTAO_SIMULAR)
            try:
                escopo.get_by_text(config.UI_TEXTO_VALOR_LIBERADO, exact=False).first.wait_for(state="visible", timeout=4000)
            except Exception:
                try:
                    escopo.get_by_text(config.UI_TEXTO_ENTENDA_ENCARGOS, exact=False).first.wait_for(state="visible", timeout=3000)
                except Exception:
                    pass
            msg_maior = escopo.get_by_text(config.UI_TEXTO_VALOR_MAIOR_DISPONIVEL, exact=False).first
            tentou_valor_total = False
            try:
                if msg_maior.is_visible():
                    tentou_valor_total = True
                    try:
                        escopo.get_by_label(config.UI_LABEL_TIPO).select_option(label=config.UI_OPCAO_VALOR_TOTAL)
                    except Exception:
                        _clicar_por_texto(pagina_resultado, config.UI_LABEL_TIPO)
                        _clicar_por_texto(pagina_resultado, config.UI_OPCAO_VALOR_TOTAL)
                    try:
                        escopo.get_by_role("button", name=config.UI_BOTAO_SIMULAR).first.click(timeout=2000)
                    except Exception:
                        _clicar_por_texto(pagina_resultado, config.UI_BOTAO_SIMULAR)
                    try:
                        escopo.get_by_text(config.UI_TEXTO_VALOR_LIBERADO, exact=False).first.wait_for(state="visible", timeout=4000)
                    except Exception:
                        pass
            except Exception:
                pass
            sucesso = False
            try:
                lib = escopo.get_by_text(config.UI_TEXTO_VALOR_LIBERADO, exact=False).first.is_visible()
                enc = escopo.get_by_text(config.UI_TEXTO_ENTENDA_ENCARGOS, exact=False).first.is_visible()
                sucesso = lib and enc
            except Exception:
                pass
            if tentou_valor_total and not sucesso:
                linha_status = "valor_maior_que_disponivel"
            if sucesso:
                try:
                    bloco_liberado = escopo.get_by_text(config.UI_TEXTO_VALOR_LIBERADO, exact=False).first
                    txt_liberado = bloco_liberado.evaluate("el => el.closest('div')?.innerText || el.parentElement?.innerText || ''")
                    m_li = re.search(r"R?\$?\s*([\d.,]+)", txt_liberado.replace(" ", ""))
                    if m_li:
                        valor_liberado = m_li.group(1).replace(".", "").replace(",", ".")
                except Exception:
                    pass
                try:
                    parcelas_el = escopo.get_by_text(config.UI_TEXTO_PARCELAS_X_RS, exact=False).first
                    txt_parc = parcelas_el.evaluate("el => el.closest('div')?.innerText || el.parentElement?.innerText || ''")
                    m_parc = re.search(r"(\d+)\s*x\s*R?\$?\s*([\d.,]+)", txt_parc, re.IGNORECASE)
                    if m_parc:
                        valor_parcela = m_parc.group(2).replace(".", "").replace(",", ".")
                except Exception:
                    pass
                try:
                    total_el = escopo.get_by_text(config.UI_TEXTO_TOTAL, exact=False).first
                    txt_tot = total_el.evaluate("el => el.closest('div')?.innerText || el.parentElement?.innerText || ''")
                    m_tot = re.search(r"R?\$?\s*([\d.,]+)", txt_tot.replace(" ", ""))
                    if m_tot:
                        valor_total = m_tot.group(1).replace(".", "").replace(",", ".")
                except Exception:
                    pass
                linha_status = "sucesso"
        except Exception as e:
            erro_linha = str(e).replace("\n", " ").replace("\r", "")[:500]
        valor_min = getattr(config, "VALOR_MINIMO_PARCELA_SIMULAR", None)
        gravar_linha = True
        if valor_min is not None and valor_min > 0:
            try:
                vp = float(valor_parcela) if valor_parcela else 0.0
                vl = float(valor_liberado) if valor_liberado else 0.0
                gravar_linha = vp >= valor_min or vl >= valor_min
            except Exception:
                pass
        if gravar_linha:
            lista_saida.append({
                "nome": cliente.nome, "cpf": cliente.cpf, "contato": cliente.contato, "email": cliente.email,
                "banco": banco_atual, "valor_maximo_parcela": valor_maximo_parcela, "qtd_parcelas": qtd_parcelas,
                "valor_liberado": valor_liberado, "valor_parcela": valor_parcela, "valor_total": valor_total,
                "status": linha_status, "erro": erro_linha, "tipo": "parcela",
            })
            gravou_alguma = True
    return gravou_alguma


def processar_resultado_existente_no_historico(page: "Page", cpf_site: str, banco_atual: str, cliente: Cliente, lista_saida: list, timeout_ms: int) -> bool:
    from robo.comms.fluxo_consulta import pagina_tem_registro_nao_encontrado
    from robo.comms.navegacao import fechar_pagina_se_aberta, obter_pagina_consulta_principal, voltar_para_consulta_limpa
    try:
        page.wait_for_timeout(200)
        pagina_consulta_antes = obter_pagina_consulta_principal(page) or (page.context.pages[0] if page.context.pages else page)
        try:
            pagina_consulta_antes.bring_to_front()
        except Exception:
            pass
        try:
            page.locator(f"#{config.UI_ID_BOTAO_CONSULTAR_SALDO}").or_(page.get_by_role("button", name=config.UI_BOTAO_CONSULTAR_SALDO)).first.wait_for(state="visible", timeout=5000)
        except Exception:
            pass
        page.wait_for_timeout(200)
        if pagina_tem_registro_nao_encontrado(page):
            msg_reg = getattr(config, "UI_TEXTO_REGISTRO_NAO_ENCONTRADO_MSG", "Infelizmente não foi possível encontrar este registro.")
            log_critico(lista_saida, cliente, banco_atual, "registro_nao_encontrado", msg_reg)
            voltar_para_consulta_limpa(page)
            return True
        timeout_por_tentativa_antes = min(800, timeout_ms // 10)
        linha_cpf_antes, locadores_linha_antes = buscar_linha_historico(pagina_consulta_antes, cpf_site, banco_atual, cliente, timeout_por_tentativa_antes, max_tentativas=1, usar_recarregar=False)
        if linha_cpf_antes is None:
            return False
        status_historico_antes = None
        texto_processando_antes = getattr(config, "UI_TEXTO_PROCESSANDO", "Processando")
        max_recarregar_antes = getattr(config, "MAX_RECARREGAR_PROCESSANDO", 15)
        for _tentativa_hist in range(max_recarregar_antes + 1):
            st = None
            try:
                if linha_cpf_antes.get_by_text(config.UI_TEXTO_ERRO_NA_CONSULTA, exact=False).first.is_visible():
                    st = "erro"
            except Exception:
                pass
            if st is None:
                try:
                    if linha_cpf_antes.get_by_text(texto_processando_antes, exact=False).first.is_visible():
                        st = "processando"
                except Exception:
                    pass
            if st is None:
                try:
                    _tp = getattr(config, "UI_TEXTO_PROCESSANDO_ALT", "")
                    if _tp and linha_cpf_antes.get_by_text(_tp, exact=False).first.is_visible():
                        st = "processando"
                except Exception:
                    pass
            if st is None:
                try:
                    if linha_cpf_antes.get_by_text(config.UI_TEXTO_SUCESSO, exact=False).first.is_visible():
                        st = "sucesso"
                except Exception:
                    pass
            if st is None:
                st = "processando"
            if st == "erro":
                log_critico(lista_saida, cliente, banco_atual, "erro_na_consulta", config.UI_TEXTO_ERRO_NA_CONSULTA)
                voltar_para_consulta_limpa(page)
                status_historico_antes = "erro"
                break
            if st == "processando":
                if _tentativa_hist >= max_recarregar_antes:
                    log_critico(lista_saida, cliente, banco_atual, "processando_timeout", "Status permaneceu Processando após recarregar")
                    voltar_para_consulta_limpa(page)
                    status_historico_antes = "processando_timeout"
                    break
                try:
                    pagina_consulta_antes.get_by_role("button", name=config.UI_BOTAO_RECARREGAR).first.click(timeout=5000)
                    pagina_consulta_antes.wait_for_load_state("domcontentloaded", timeout=10000)
                except Exception as e:
                    log_critico(lista_saida, cliente, banco_atual, "falha_historico", str(e)[:300])
                    status_historico_antes = "processando_timeout"
                    break
                pagina_consulta_antes.wait_for_timeout(config.PAUSA_APOS_RECARREGAR_MS)
                linha_cpf_antes = None
                for loc in locadores_linha_antes:
                    try:
                        loc.wait_for(state="visible", timeout=timeout_por_tentativa_antes)
                        linha_cpf_antes = loc
                        break
                    except Exception:
                        pass
                if linha_cpf_antes is None:
                    log_critico(lista_saida, cliente, banco_atual, "processando_timeout", "Linha não encontrada após recarregar")
                    voltar_para_consulta_limpa(page)
                    status_historico_antes = "processando_timeout"
                    break
            if st == "sucesso":
                status_historico_antes = "sucesso"
                break
        if status_historico_antes == "erro" or status_historico_antes == "processando_timeout":
            return True
        if status_historico_antes == "sucesso" and linha_cpf_antes is not None:
            btn_ver_resultado_antes = (
                linha_cpf_antes.get_by_role("button", name=re.compile(r"ver\s*resultado", re.IGNORECASE))
                .or_(linha_cpf_antes.get_by_role("link", name=re.compile(r"ver\s*resultado", re.IGNORECASE)))
                .or_(linha_cpf_antes.locator("button, a, [role='button']").filter(has_text=re.compile(r"ver\s*resultado", re.IGNORECASE)))
                .or_(linha_cpf_antes.get_by_text(config.UI_BOTAO_VER_RESULTADO, exact=False))
                .or_(linha_cpf_antes.get_by_text("Ver", exact=False))
                .first
            )
            btn_ver_resultado_antes.wait_for(state="visible", timeout=8000)
            btn_ver_resultado_antes.scroll_into_view_if_needed(timeout=3000)
            pagina_consulta_antes.wait_for_timeout(150)
            pagina_resultado_antes, ok = abrir_resultado_historico(page.context, btn_ver_resultado_antes, pagina_consulta_antes)
            if not ok or pagina_resultado_antes is None:
                raise RuntimeError("Falha ao abrir resultado")
            deve_continuar, valor_maximo_parcela_antes = tratar_recusa_ou_requisicao_mal_formatada(pagina_resultado_antes, page, cliente, banco_atual, lista_saida)
            if deve_continuar:
                return True
            if valor_maximo_parcela_antes:
                try:
                    simular_tabelas(pagina_resultado_antes, valor_maximo_parcela_antes, cliente, banco_atual, lista_saida)
                except BaseException:
                    pass
            fechar_pagina_se_aberta(pagina_resultado_antes, page)
            pagina_consulta_principal = obter_pagina_consulta_principal(page)
            if pagina_consulta_principal:
                try:
                    pagina_consulta_principal.bring_to_front()
                except Exception:
                    pass
            return True
    except Exception as e:
        log_critico(lista_saida, cliente, banco_atual, "falha_historico", str(e)[:300])
    return False
