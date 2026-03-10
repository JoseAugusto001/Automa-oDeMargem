from __future__ import annotations

import re
from typing import TYPE_CHECKING, List, Tuple

import config
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
            pagina_consulta.locator("tr, [role='row'], div").filter(has_text=re.compile(re.escape(cpf_site))).filter(has_text=re.compile(re.escape(banco_atual), re.I)).first,
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
    from robo.comms import navegacao
    texto_recusa = getattr(config, "UI_TEXTO_RECUSA_POLITICA_BANCO", "")
    msg_recusa_csv = getattr(config, "UI_TEXTO_RECUSA_POLITICA_BANCO_MSG", texto_recusa)
    if texto_recusa:
        try:
            if pagina_resultado.get_by_text(texto_recusa, exact=False).first.is_visible():
                log_critico(lista_saida, cliente, banco_atual, "recusa_politica_banco", msg_recusa_csv)
                navegacao.voltar_para_consulta_limpa(page)
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
        navegacao.voltar_para_consulta_limpa(page)
        return (True, "")
    valor = extrair_valor_maximo_parcela(pagina_resultado)
    return (False, valor)


def _clicar_por_texto(pagina: "Page | Locator", texto: str, exato: bool = False) -> bool:
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


def _abrir_tabela_por_teclado(pagina_ui: "Page | Locator", escopo: "Page | Locator") -> bool:
    """Tenta abrir o dropdown Tabela via foco + Enter/Espaço (funciona em muitos custom components)."""
    try:
        ok = escopo.evaluate("""(root) => {
            const findAndOpen = (el, depth) => {
                if (!el || depth > 20) return false;
                const txt = (el.textContent || '').trim();
                if (txt === 'Selecione uma opção' && el.offsetParent) {
                    const parent = el.closest('div, span, button, [role="combobox"]');
                    const target = parent || el;
                    target.focus();
                    target.dispatchEvent(new KeyboardEvent('keydown', { key: ' ', code: 'Space', keyCode: 32, bubbles: true }));
                    target.dispatchEvent(new KeyboardEvent('keyup', { key: ' ', code: 'Space', keyCode: 32, bubbles: true }));
                    return true;
                }
                if (txt === 'Tabela') {
                    let p = el.parentElement;
                    for (let i = 0; i < 8 && p; i++) {
                        const trigger = p.querySelector('[role="combobox"], [aria-haspopup], select, div[tabindex="0"]');
                        if (trigger && trigger.offsetParent) {
                            trigger.focus();
                            trigger.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
                            trigger.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
                            return true;
                        }
                        p = p.parentElement;
                    }
                    return false;
                }
                for (const c of el.children || []) { if (findAndOpen(c, depth + 1)) return true; }
                return false;
            };
            return findAndOpen(root, 0);
        }""")
        return bool(ok)
    except Exception:
        return False


def _clicar_tabela_via_js(escopo: "Page | Locator") -> bool:
    """Usa evaluate para encontrar e clicar no dropdown Tabela (contorna componentes customizados)."""
    script = """(root) => {
        const walk = (el, depth) => {
            if (!el || depth > 20) return null;
            const txt = (el.textContent || '').trim();
            if (txt === 'Tabela' && (el.tagName === 'LABEL' || el.tagName === 'SPAN' || el.tagName === 'DIV')) {
                let p = el.parentElement;
                for (let i = 0; i < 10 && p; i++) {
                    const cb = p.querySelector('[role="combobox"], [aria-haspopup="listbox"], .MuiSelect-select, .MuiAutocomplete-input');
                    if (cb && cb.offsetParent) { cb.click(); return true; }
                    const sel = p.querySelector('select');
                    if (sel && sel.offsetParent) { sel.click(); return true; }
                    const ph = p.querySelector('[class*="placeholder"], [class*="Placeholder"], [class*="select"]');
                    if (ph && (ph.textContent || '').includes('Selecione') && ph.offsetParent) { ph.click(); return true; }
                    const divs = p.querySelectorAll('div[role="button"], div[tabindex="0"], span[role="button"], button');
                    for (const d of divs) {
                        if ((d.textContent || '').includes('Selecione uma opção') && d.offsetParent) { d.click(); return true; }
                    }
                    const anyWithPlaceholder = p.querySelectorAll('div, span');
                    for (const el of anyWithPlaceholder) {
                        if ((el.textContent || '').trim() === 'Selecione uma opção' && el.offsetParent && !el.querySelector('[role="combobox"]')) {
                            el.click(); return true;
                        }
                    }
                    p = p.parentElement;
                }
                return null;
            }
            for (const c of el.children || []) {
                const r = walk(c, depth + 1);
                if (r !== null) return r;
            }
            return null;
        };
        return walk(root, 0) === true;
    }"""
    try:
        ok = escopo.evaluate(script)
        return bool(ok)
    except Exception:
        return False


def _clicar_tabela_via_js_pagina(pagina: "Page | Locator") -> bool:
    """Busca o bloco de simulação pela página (Valor máximo da parcela) e clica no dropdown Tabela."""
    try:
        ok = pagina.evaluate("""() => {
            const findBlock = (el, depth) => {
                if (!el || depth > 25) return null;
                if ((el.textContent || '').includes('Valor máximo da parcela') && (el.textContent || '').includes('Tabela')) {
                    const walk = (n, d) => {
                        if (!n || d > 15) return null;
                        if ((n.textContent || '').trim() === 'Tabela' && (n.tagName === 'LABEL' || n.tagName === 'SPAN' || n.tagName === 'DIV')) {
                            let p = n.parentElement;
                            for (let i = 0; i < 10 && p; i++) {
                                const cb = p.querySelector('[role="combobox"], [aria-haspopup="listbox"], .MuiSelect-select, select');
                                if (cb && cb.offsetParent) { cb.click(); return true; }
                                const any = p.querySelectorAll('div, span, button');
                                for (const a of any) {
                                    if ((a.textContent || '').trim() === 'Selecione uma opção' && a.offsetParent) { a.click(); return true; }
                                }
                                p = p.parentElement;
                            }
                            return null;
                        }
                        for (const c of n.children || []) { const r = walk(c, d + 1); if (r !== null) return r; }
                        return null;
                    };
                    return walk(el, 0) === true;
                }
                for (const c of el.children || []) { const r = findBlock(c, depth + 1); if (r !== null) return r; }
                return null;
            };
            return findBlock(document.body, 0) === true;
        }""")
        return bool(ok)
    except Exception:
        return False


def _obter_escopo_simulacao(escopo: "Page | Locator") -> "Page | Locator":
    """Prioriza bloco Vue (tr.expanded-row > .simulation/.simulation-table); fallback por texto."""
    try:
        bloco = escopo.locator("tr.expanded-row").locator(".simulation, .simulation-table").first
        if bloco.count() > 0 and bloco.is_visible():
            return bloco
    except Exception:
        pass
    try:
        bloco = escopo.locator("section.expanded_row").locator(".simulation, .simulation-table").first
        if bloco.count() > 0 and bloco.is_visible():
            return bloco
    except Exception:
        pass
    texto_valor = getattr(config, "UI_TEXTO_VALOR_MAXIMO_PARCELA", "Valor máximo da parcela")
    label_tabela = getattr(config, "UI_LABEL_TABELA", "Tabela")
    try:
        bloco = escopo.locator("div, section").filter(
            has=escopo.get_by_text(texto_valor, exact=False)
        ).filter(
            has=escopo.get_by_text(label_tabela, exact=True)
        ).first
        if bloco.count() > 0 and bloco.is_visible():
            return bloco
    except Exception:
        pass
    try:
        bloco = escopo.locator("div, section").filter(
            has=escopo.get_by_text(texto_valor, exact=False)
        ).filter(
            has=escopo.locator(f'label:has-text("{label_tabela}")')
        ).first
        if bloco.count() > 0 and bloco.is_visible():
            return bloco
    except Exception:
        pass
    return escopo


def simular_tabelas(
    escopo: "Page | Locator",
    valor_maximo_parcela: str,
    cliente: Cliente,
    banco_atual: str,
    lista_saida: list,
    pagina_resultado: "Page | None" = None,
) -> bool:
    pagina_ui: "Page | Locator" = pagina_resultado if pagina_resultado is not None else escopo
    timeout_bloco = getattr(config, "TIMEOUT_ESPERA_BLOCO_SIMULACAO_MS", 10000)
    try:
        escopo.locator(".simulation, .simulation-table, tr.expanded-row").first.wait_for(state="visible", timeout=timeout_bloco)
    except Exception:
        try:
            escopo.get_by_text(config.UI_TEXTO_VALOR_MAXIMO_PARCELA, exact=False).first.wait_for(state="visible", timeout=timeout_bloco)
        except Exception:
            pass
    escopo = _obter_escopo_simulacao(escopo)
    meses_array = [6, 12, 24]
    labels_celcoin = ["6 meses (C)", "12 meses (C)", "24 meses (C)"]
    labels_qitech = ["6 meses", "12 meses", "24 meses"]
    is_celcoin = "celcoin" in (banco_atual or "").lower()
    opcoes_com_meses = [
        (meses_array[i], labels_celcoin[i] if is_celcoin else labels_qitech[i])
        for i in range(len(meses_array))
    ]
    variantes_por_mes = getattr(config, "UI_TABELA_VARIANTES_MESES", None)
    if variantes_por_mes is None:
        variantes_por_mes = {6: ["6 meses (C)", "6 meses"], 12: ["12 meses (C)", "12 meses"], 24: ["24 meses (C)", "24 meses"]}
    pausa_dropdown = getattr(config, "PAUSA_APOS_ABRIR_DROPDOWN_TABELA_MS", 600)
    timeout_opcao = getattr(config, "TIMEOUT_OPCAO_TABELA_MS", 2500)
    gravou_alguma = False
    for _meses, label_tabela in opcoes_com_meses:
        linha_status = "falha_simulacao"
        valor_liberado = ""
        valor_parcela = ""
        valor_total = ""
        qtd_parcelas = str(_meses)
        erro_linha = ""
        try:
            trigger_aberto = False
            locator_tabela_custom = getattr(config, "LOCATOR_TABELA_DROPDOWN", None)
            if locator_tabela_custom and isinstance(locator_tabela_custom, str):
                try:
                    el = escopo.locator(locator_tabela_custom).first
                    if el.count() > 0:
                        el.scroll_into_view_if_needed(timeout=2000)
                        el.click(force=True, timeout=2000)
                        trigger_aberto = True
                except Exception:
                    try:
                        pagina_ui.locator(locator_tabela_custom).first.click(force=True, timeout=2000)
                        trigger_aberto = True
                    except Exception:
                        pass
            if not trigger_aberto and _abrir_tabela_por_teclado(pagina_ui, escopo):
                trigger_aberto = True
            if not trigger_aberto and _clicar_tabela_via_js(escopo):
                trigger_aberto = True
            if not trigger_aberto and pagina_resultado is not None and _clicar_tabela_via_js_pagina(pagina_resultado):
                trigger_aberto = True
            wait_fn = getattr(pagina_ui, "wait_for_timeout", None)
            if wait_fn is not None:
                wait_fn(pausa_dropdown)
            opcao_clicada = False
            labels_tentar = variantes_por_mes.get(_meses, [label_tabela])
            if label_tabela not in labels_tentar:
                labels_tentar = [label_tabela] + list(labels_tentar)
            for lbl_opcao in labels_tentar:
                if opcao_clicada:
                    break
                try:
                    opt_portal = pagina_ui.locator(".vue-portal-target").get_by_text(lbl_opcao, exact=False).first
                    if opt_portal.count() > 0 and opt_portal.is_visible():
                        opt_portal.click(timeout=timeout_opcao)
                        opcao_clicada = True
                except Exception:
                    pass
                if not opcao_clicada:
                    try:
                        opt = pagina_ui.get_by_role("option").filter(has_text=re.compile(re.escape(lbl_opcao), re.I)).first
                        if opt.count() > 0:
                            opt.wait_for(state="visible", timeout=min(1500, timeout_opcao))
                            opt.click(timeout=timeout_opcao)
                            opcao_clicada = True
                    except Exception:
                        pass
                if not opcao_clicada:
                    try:
                        sel = escopo.get_by_label(config.UI_LABEL_TABELA)
                        if sel.count() > 0:
                            sel.select_option(label=lbl_opcao, timeout=timeout_opcao)
                            opcao_clicada = True
                    except Exception:
                        pass
                if not opcao_clicada:
                    try:
                        loc = escopo.get_by_text(lbl_opcao, exact=True).first
                        if loc.count() > 0:
                            loc.wait_for(state="visible", timeout=min(1500, timeout_opcao))
                            loc.click(timeout=timeout_opcao)
                            opcao_clicada = True
                    except Exception:
                        pass
                if not opcao_clicada:
                    try:
                        loc = pagina_ui.locator(f'[role="option"]:has-text("{lbl_opcao}"), div:has-text("{lbl_opcao}"), li:has-text("{lbl_opcao}")').first
                        if loc.count() > 0 and loc.is_visible():
                            loc.click(timeout=timeout_opcao)
                            opcao_clicada = True
                    except Exception:
                        pass
            if not opcao_clicada:
                opcao_clicada = _clicar_por_texto(pagina_ui, label_tabela, exato=True) or _clicar_por_texto(pagina_ui, label_tabela)
            if not opcao_clicada:
                continue
            try:
                escopo.get_by_role("button", name=config.UI_BOTAO_SIMULAR).first.wait_for(state="visible", timeout=1500)
            except Exception:
                pass
            try:
                escopo.get_by_role("button", name=config.UI_BOTAO_SIMULAR).first.click(timeout=2000)
            except Exception:
                _clicar_por_texto(pagina_ui, config.UI_BOTAO_SIMULAR)
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
                    linha_status = "valor_maior_que_disponivel"
                    tentou_valor_total = True
                    try:
                        escopo.get_by_label(config.UI_LABEL_TIPO).select_option(label=config.UI_OPCAO_VALOR_TOTAL)
                    except Exception:
                        _clicar_por_texto(pagina_ui, config.UI_LABEL_TIPO)
                        _clicar_por_texto(pagina_ui, config.UI_OPCAO_VALOR_TOTAL)
                    try:
                        escopo.get_by_role("button", name=config.UI_BOTAO_SIMULAR).first.click(timeout=2000)
                    except Exception:
                        _clicar_por_texto(pagina_ui, config.UI_BOTAO_SIMULAR)
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
    from robo.comms import fluxo_consulta
    from robo.comms import navegacao
    try:
        pagina_consulta_antes = navegacao.obter_pagina_consulta_principal(page) or (page.context.pages[0] if page.context.pages else page)
        try:
            pagina_consulta_antes.bring_to_front()
        except Exception:
            pass
        try:
            page.locator(f"#{config.UI_ID_BOTAO_CONSULTAR_SALDO}").or_(page.get_by_role("button", name=config.UI_BOTAO_CONSULTAR_SALDO)).first.wait_for(state="visible", timeout=5000)
        except Exception:
            pass
        if fluxo_consulta.pagina_tem_registro_nao_encontrado(page):
            msg_reg = getattr(config, "UI_TEXTO_REGISTRO_NAO_ENCONTRADO_MSG", "Infelizmente não foi possível encontrar este registro.")
            log_critico(lista_saida, cliente, banco_atual, "registro_nao_encontrado", msg_reg)
            navegacao.voltar_para_consulta_limpa(page)
            return True
        timeout_por_tentativa_antes = min(3000, timeout_ms // 5)
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
                navegacao.voltar_para_consulta_limpa(page)
                status_historico_antes = "erro"
                break
            if st == "processando":
                if _tentativa_hist >= max_recarregar_antes:
                    log_critico(lista_saida, cliente, banco_atual, "processando_timeout", "Status permaneceu Processando após recarregar")
                    navegacao.voltar_para_consulta_limpa(page)
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
                    navegacao.voltar_para_consulta_limpa(page)
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
            try:
                btn_ver_resultado_antes.wait_for(state="visible", timeout=12000)
            except Exception:
                try:
                    linha_cpf_antes.click(timeout=2000)
                    pagina_consulta_antes.wait_for_timeout(500)
                    btn_ver_resultado_antes.wait_for(state="visible", timeout=8000)
                except Exception:
                    raise
            btn_ver_resultado_antes.scroll_into_view_if_needed(timeout=3000)
            try:
                btn_ver_resultado_antes.wait_for(state="visible", timeout=500)
            except Exception:
                pass
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
            navegacao.fechar_pagina_se_aberta(pagina_resultado_antes, page)
            pagina_consulta_principal = navegacao.obter_pagina_consulta_principal(page)
            if pagina_consulta_principal:
                try:
                    pagina_consulta_principal.bring_to_front()
                except Exception:
                    pass
            return True
    except Exception as e:
        log_critico(lista_saida, cliente, banco_atual, "falha_historico", str(e)[:300])
    return False
