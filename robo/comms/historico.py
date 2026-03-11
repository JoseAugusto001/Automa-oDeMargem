from __future__ import annotations

import re
from typing import TYPE_CHECKING, Callable, List, Optional, Tuple, cast

import config
from robo.passivos.csv_io import log_critico
from robo.passivos.modelos import Cliente

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page


def _get_page(loc_or_page: "Page | Locator") -> "Page | None":
    """Obtém a Page a partir de um Locator ou Page. Page tem .keyboard; Locator tem .page."""
    if hasattr(loc_or_page, "keyboard"):
        return cast("Page", loc_or_page)
    if hasattr(loc_or_page, "page"):
        return getattr(loc_or_page, "page", None)
    return None


def _opcoes_dropdown_visiveis(pagina_ui: "Page | Locator", label_tabela: str, timeout_ms: int = 800) -> bool:
    """Verifica se as opções do dropdown (portal ou role=option) estão visíveis."""
    try:
        pagina_ui.locator(".vue-portal-target").get_by_text(label_tabela, exact=False).first.wait_for(state="visible", timeout=timeout_ms)
        return True
    except Exception:
        pass
    try:
        pagina_ui.get_by_role("option").first.wait_for(state="visible", timeout=timeout_ms)
        return True
    except Exception:
        pass
    return False


def _selecionar_tabela_select_nativo(escopo: "Page | Locator", meses: int, label_opcao: str, timeout_ms: int = 2500, banco_atual: str = "") -> bool:
    """Se o bloco Tabela for um <select> nativo (ex.: span com label Tabela > div.select > select), seleciona por value ou label.
    Usa select_option + dispatch input/change; fallback com clique no select + teclado (ArrowDown + Enter) para Vue reconhecer."""
    label_tabela = getattr(config, "UI_LABEL_TABELA", "Tabela")
    try:
        sel = escopo.locator("span").filter(has=escopo.get_by_text(label_tabela, exact=False)).locator("select").first
        if sel.count() == 0:
            sel = escopo.locator("div.control").filter(has=escopo.locator("label").filter(has_text=label_tabela)).locator("select").first
        if sel.count() == 0:
            sel = escopo.locator("div.control").filter(has_text=label_tabela).locator("select").first
        if sel.count() == 0:
            sel = escopo.locator("select").filter(has=escopo.locator("option[value='68']")).first
        if sel.count() == 0:
            try:
                selects = escopo.locator("select").all()
                for s in selects:
                    if s.count() > 0 and s.is_visible():
                        opt = s.locator("option[value='65'], option[value='66'], option[value='67'], option[value='68']").first
                        if opt.count() > 0:
                            sel = s
                            break
            except Exception:
                pass
        if sel.count() == 0:
            sel = escopo.locator("select").nth(1)
        if sel.count() == 0:
            return False
        is_celcoin = "celcoin" in (banco_atual or "").lower()
        if is_celcoin:
            return False
        page = _get_page(escopo)
        value_map = {6: "65", 12: "66", 18: "67", 24: "68"}
        val = value_map.get(meses)
        try:
            sel.evaluate("""(el, val) => {
                if (!val) return;
                el.value = val;
                el.selectedIndex = Array.from(el.options).findIndex(o => o.value === val);
                if (el.selectedIndex < 0) return;
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                el.dispatchEvent(new Event('blur', { bubbles: true }));
            }""", val)
        except Exception:
            pass
        if val:
            try:
                sel.select_option(value=val, timeout=timeout_ms)
            except Exception:
                pass
        else:
            try:
                sel.select_option(label=label_opcao, timeout=timeout_ms)
            except Exception:
                pass
        try:
            sel.evaluate("el => { el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); }")
        except Exception:
            pass
        if page is not None:
            try:
                try:
                    wrapper = sel.locator("xpath=..")
                    if wrapper.count() > 0 and wrapper.is_visible():
                        wrapper.click(timeout=timeout_ms)
                    else:
                        sel.click(timeout=timeout_ms)
                except Exception:
                    sel.click(timeout=timeout_ms)
                page.wait_for_timeout(80)
                arrow_count = {24: 1, 18: 2, 12: 3, 6: 4}.get(meses, 0)
                for _ in range(arrow_count):
                    page.keyboard.press("ArrowDown")
                    page.wait_for_timeout(30)
                page.keyboard.press("Enter")
                page.wait_for_timeout(50)
            except Exception:
                pass
        return True
    except Exception:
        return False


def _abrir_tabela_clique_e_enter(escopo: "Page | Locator", pagina_ui: "Page | Locator") -> bool:
    """Abre o dropdown Tabela com clique real do Playwright no trigger + Enter."""
    page = _get_page(pagina_ui)
    if page is None:
        return False
    ph = getattr(config, "UI_PLACEHOLDER_TABELA", "Selecione uma opção")
    label_tabela = getattr(config, "UI_LABEL_TABELA", "Tabela")
    try:
        bloco_tabela = escopo.locator("div, span, section").filter(has=escopo.get_by_text(label_tabela, exact=False)).first
        if bloco_tabela.count() > 0 and bloco_tabela.is_visible():
            el = bloco_tabela.get_by_text(ph, exact=True).first
            if el.count() > 0 and el.is_visible():
                el.click(timeout=2000)
                page.wait_for_timeout(200)
                page.keyboard.press("Enter")
                return True
    except Exception:
        pass
    try:
        el = escopo.get_by_text(ph, exact=True).first
        if el.count() > 0 and el.is_visible():
            el.click(timeout=2000)
            page.wait_for_timeout(200)
            page.keyboard.press("Enter")
            return True
    except Exception:
        pass
    locator_custom = getattr(config, "LOCATOR_TABELA_DROPDOWN", None)
    if locator_custom and isinstance(locator_custom, str):
        try:
            el = escopo.locator(locator_custom).first
            if el.count() > 0 and el.is_visible():
                el.click(timeout=2000)
                page.wait_for_timeout(200)
                page.keyboard.press("Enter")
                return True
        except Exception:
            pass
    return False


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
        with ctx.expect_page(timeout=3000) as popup_info:
            btn_ver_resultado.click()
        pagina_resultado = popup_info.value
        pagina_resultado.wait_for_load_state("domcontentloaded", timeout=4000)
        try:
            pagina_resultado.locator(".simulation, .simulation-table, tr.expanded-row").or_(pagina_resultado.get_by_text(getattr(config, "UI_PLACEHOLDER_TABELA", "Selecione uma opção"), exact=False)).first.wait_for(state="visible", timeout=4000)
        except Exception:
            try:
                pagina_resultado.get_by_text(config.UI_TEXTO_VALOR_MAXIMO_PARCELA, exact=False).first.wait_for(state="visible", timeout=3000)
            except Exception:
                pass
        return (pagina_resultado, True)
    except BaseException:
        pass
    if pagina_consulta and not pagina_consulta.is_closed():
        ph = getattr(config, "UI_PLACEHOLDER_TABELA", "Selecione uma opção")
        try:
            pagina_consulta.locator(".simulation, .simulation-table, tr.expanded-row").or_(pagina_consulta.get_by_text(ph, exact=False)).first.wait_for(state="visible", timeout=5000)
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


def _disparar_clique_real_tabela(escopo: "Page | Locator") -> bool:
    """Abre o dropdown Tabela com sequência de eventos (mousedown/mouseup/click) para Vue/Bootstrap."""
    script = """(root) => {
        const fire = (el) => {
            if (!el || !el.offsetParent) return false;
            el.focus();
            const opts = { bubbles: true, cancelable: true, view: window };
            el.dispatchEvent(new MouseEvent('mousedown', opts));
            el.dispatchEvent(new MouseEvent('mouseup', opts));
            el.dispatchEvent(new MouseEvent('click', opts));
            return true;
        };
        const walk = (el, depth) => {
            if (!el || depth > 25) return false;
            const txt = (el.textContent || '').trim();
            if (txt === 'Selecione uma opção' && (el.tagName === 'DIV' || el.tagName === 'SPAN' || el.tagName === 'LABEL')) {
                if (fire(el)) return true;
                let p = el.parentElement;
                for (let i = 0; i < 6 && p; i++) {
                    if (fire(p)) return true;
                    const cb = p.querySelector('[role="combobox"], [aria-haspopup], [tabindex="0"]');
                    if (cb && fire(cb)) return true;
                    p = p.parentElement;
                }
            }
            if ((el.textContent || '').includes('Valor máximo da parcela') && (el.textContent || '').includes('Tabela')) {
                const ph = el.querySelector('[class*="select"], [class*="dropdown"], [role="combobox"], [aria-haspopup]');
                if (ph && fire(ph)) return true;
                const all = el.querySelectorAll('div, span');
                for (const n of all) {
                    if ((n.textContent || '').trim() === 'Selecione uma opção' && fire(n)) return true;
                }
            }
            for (const c of el.children || []) { if (walk(c, depth + 1)) return true; }
            return false;
        };
        return walk(root, 0);
    }"""
    try:
        return bool(escopo.evaluate(script))
    except Exception:
        return False


def _clicar_tabela_via_js(escopo: "Page | Locator") -> bool:
    """Usa evaluate para encontrar e clicar no dropdown Tabela (contorna componentes customizados)."""
    script = """(root) => {
        const fire = (el) => { if (!el || !el.offsetParent) return false; el.focus(); el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true })); el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true })); el.dispatchEvent(new MouseEvent('click', { bubbles: true })); return true; };
        const walk = (el, depth) => {
            if (!el || depth > 20) return null;
            const txt = (el.textContent || '').trim();
            if (txt === 'Tabela' && (el.tagName === 'LABEL' || el.tagName === 'SPAN' || el.tagName === 'DIV')) {
                let p = el.parentElement;
                for (let i = 0; i < 10 && p; i++) {
                    const cb = p.querySelector('[role="combobox"], [aria-haspopup="listbox"], .MuiSelect-select, .MuiAutocomplete-input');
                    if (cb && cb.offsetParent) { if (fire(cb)) return true; cb.click(); return true; }
                    const sel = p.querySelector('select');
                    if (sel && sel.offsetParent) { sel.click(); return true; }
                    const ph = p.querySelector('[class*="placeholder"], [class*="Placeholder"], [class*="select"]');
                    if (ph && (ph.textContent || '').includes('Selecione') && ph.offsetParent) { if (fire(ph)) return true; ph.click(); return true; }
                    const divs = p.querySelectorAll('div[role="button"], div[tabindex="0"], span[role="button"], button');
                    for (const d of divs) {
                        if ((d.textContent || '').includes('Selecione uma opção') && d.offsetParent) { if (fire(d)) return true; d.click(); return true; }
                    }
                    const anyWithPlaceholder = p.querySelectorAll('div, span');
                    for (const node of anyWithPlaceholder) {
                        if ((node.textContent || '').trim() === 'Selecione uma opção' && node.offsetParent && !node.querySelector('[role="combobox"]')) {
                            if (fire(node)) return true; node.click(); return true;
                        }
                    }
                    p = p.parentElement;
                }
                return null;
            }
            for (const c of el.children || []) { const r = walk(c, depth + 1); if (r !== null) return r; }
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
            const fire = (el) => { if (!el || !el.offsetParent) return false; el.focus(); el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true })); el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true })); el.dispatchEvent(new MouseEvent('click', { bubbles: true })); return true; };
            const findBlock = (el, depth) => {
                if (!el || depth > 25) return null;
                if ((el.textContent || '').includes('Valor máximo da parcela') && (el.textContent || '').includes('Tabela')) {
                    const walk = (n, d) => {
                        if (!n || d > 15) return null;
                        if ((n.textContent || '').trim() === 'Tabela' && (n.tagName === 'LABEL' || n.tagName === 'SPAN' || n.tagName === 'DIV')) {
                            let p = n.parentElement;
                            for (let i = 0; i < 10 && p; i++) {
                                const cb = p.querySelector('[role="combobox"], [aria-haspopup="listbox"], .MuiSelect-select, select');
                                if (cb && cb.offsetParent) { if (fire(cb)) return true; cb.click(); return true; }
                                const any = p.querySelectorAll('div, span, button');
                                for (const a of any) {
                                    if ((a.textContent || '').trim() === 'Selecione uma opção' && a.offsetParent) { if (fire(a)) return true; a.click(); return true; }
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
    on_abrir_tabela: Optional[Callable[[bool, str], None]] = None,
) -> tuple[bool, bool]:
    """
    Para cada mês (6, 12, 18, 24) de baixo para cima: abre o dropdown Tabela, escolhe o mês, clica Simular e grava; ao final grava "Limite de opções de meses alcançado".
    Ordem: _abrir_tabela_clique_e_enter, _disparar_clique_real_tabela, LOCATOR_TABELA_DROPDOWN, _abrir_tabela_por_teclado,
    _clicar_tabela_via_js, _clicar_tabela_via_js_pagina. Só considera aberto se opções ficarem visíveis (timeout 800 ms).
    """
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
    meses_array = [6, 12, 18, 24]
    labels_celcoin = ["6 meses (C)", "12 meses (C)", "18 meses (C)", "24 meses (C)"]
    labels_qitech = ["6 meses", "12 meses", "18 meses", "24 meses"]
    is_celcoin = "celcoin" in (banco_atual or "").lower()
    opcoes_com_meses = [
        (meses_array[i], labels_celcoin[i] if is_celcoin else labels_qitech[i])
        for i in range(len(meses_array))
    ]
    variantes_por_mes = getattr(config, "UI_TABELA_VARIANTES_MESES", None)
    if variantes_por_mes is None:
        variantes_por_mes = {6: ["6 meses (C)", "6 meses"], 12: ["12 meses (C)", "12 meses"], 18: ["18 meses (C)", "18 meses"], 24: ["24 meses (C)", "24 meses"]}
    pausa_dropdown = getattr(config, "PAUSA_APOS_ABRIR_DROPDOWN_TABELA_MS", 600)
    timeout_opcao = getattr(config, "TIMEOUT_OPCAO_TABELA_MS", 2500)
    timeout_validacao_ms = getattr(config, "TIMEOUT_VALIDACAO_OPCOES_TABELA_MS", 800)
    timeout_opcoes_visiveis = min(1500, timeout_opcao)
    gravou_alguma = False
    alguma_vez_opcao_clicada = False
    for _meses, label_tabela in opcoes_com_meses:
        linha_status = "falha_simulacao"
        valor_liberado = ""
        valor_parcela = ""
        valor_total = ""
        qtd_parcelas = str(_meses)
        erro_linha = ""
        trigger_aberto = False
        opcao_clicada = False
        try:
            wait_fn = getattr(pagina_ui, "wait_for_timeout", None)
            if _selecionar_tabela_select_nativo(escopo, _meses, label_tabela, timeout_opcao, banco_atual):
                opcao_clicada = True
            if not opcao_clicada:
                if _abrir_tabela_clique_e_enter(escopo, pagina_ui):
                    if wait_fn:
                        wait_fn(250)
                    if _opcoes_dropdown_visiveis(pagina_ui, label_tabela, timeout_validacao_ms):
                        trigger_aberto = True
                        if on_abrir_tabela:
                            on_abrir_tabela(True, "clique_e_enter")
                        if getattr(config, "DEBUG_TABELA", False):
                            print("[DEBUG_TABELA] aberta=True metodo=clique_e_enter")
                if not trigger_aberto and _disparar_clique_real_tabela(escopo):
                    if wait_fn:
                        wait_fn(250)
                    if _opcoes_dropdown_visiveis(pagina_ui, label_tabela, timeout_validacao_ms):
                        trigger_aberto = True
                        if on_abrir_tabela:
                            on_abrir_tabela(True, "disparar_clique_real_escopo")
                        if getattr(config, "DEBUG_TABELA", False):
                            print("[DEBUG_TABELA] aberta=True metodo=disparar_clique_real_escopo")
                if not trigger_aberto and pagina_resultado is not None and _disparar_clique_real_tabela(pagina_resultado):
                    if wait_fn:
                        wait_fn(250)
                    if _opcoes_dropdown_visiveis(pagina_ui, label_tabela, timeout_validacao_ms):
                        trigger_aberto = True
                        if on_abrir_tabela:
                            on_abrir_tabela(True, "disparar_clique_real_pagina")
                        if getattr(config, "DEBUG_TABELA", False):
                            print("[DEBUG_TABELA] aberta=True metodo=disparar_clique_real_pagina")
                locator_tabela_custom = getattr(config, "LOCATOR_TABELA_DROPDOWN", None)
                if not trigger_aberto and locator_tabela_custom and isinstance(locator_tabela_custom, str):
                    try:
                        el = escopo.locator(locator_tabela_custom).first
                        if el.count() > 0:
                            el.scroll_into_view_if_needed(timeout=2000)
                            el.click(force=True, timeout=2000)
                            if wait_fn:
                                wait_fn(250)
                            if _opcoes_dropdown_visiveis(pagina_ui, label_tabela, timeout_validacao_ms):
                                trigger_aberto = True
                                if on_abrir_tabela:
                                    on_abrir_tabela(True, "locator_custom")
                                if getattr(config, "DEBUG_TABELA", False):
                                    print("[DEBUG_TABELA] aberta=True metodo=locator_custom")
                    except Exception:
                        try:
                            pagina_ui.locator(locator_tabela_custom).first.click(force=True, timeout=2000)
                            if wait_fn:
                                wait_fn(250)
                            if _opcoes_dropdown_visiveis(pagina_ui, label_tabela, timeout_validacao_ms):
                                trigger_aberto = True
                                if on_abrir_tabela:
                                    on_abrir_tabela(True, "locator_custom_pagina")
                                if getattr(config, "DEBUG_TABELA", False):
                                    print("[DEBUG_TABELA] aberta=True metodo=locator_custom_pagina")
                        except Exception:
                            pass
                if not trigger_aberto and _abrir_tabela_por_teclado(pagina_ui, escopo):
                    if wait_fn:
                        wait_fn(250)
                    if _opcoes_dropdown_visiveis(pagina_ui, label_tabela, timeout_validacao_ms):
                        trigger_aberto = True
                        if on_abrir_tabela:
                            on_abrir_tabela(True, "teclado")
                        if getattr(config, "DEBUG_TABELA", False):
                            print("[DEBUG_TABELA] aberta=True metodo=teclado")
                if not trigger_aberto and _clicar_tabela_via_js(escopo):
                    if wait_fn:
                        wait_fn(250)
                    if _opcoes_dropdown_visiveis(pagina_ui, label_tabela, timeout_validacao_ms):
                        trigger_aberto = True
                        if on_abrir_tabela:
                            on_abrir_tabela(True, "clicar_js_escopo")
                        if getattr(config, "DEBUG_TABELA", False):
                            print("[DEBUG_TABELA] aberta=True metodo=clicar_js_escopo")
                if not trigger_aberto and pagina_resultado is not None and _clicar_tabela_via_js_pagina(pagina_resultado):
                    if wait_fn:
                        wait_fn(250)
                    if _opcoes_dropdown_visiveis(pagina_ui, label_tabela, timeout_validacao_ms):
                        trigger_aberto = True
                        if on_abrir_tabela:
                            on_abrir_tabela(True, "clicar_js_pagina")
                        if getattr(config, "DEBUG_TABELA", False):
                            print("[DEBUG_TABELA] aberta=True metodo=clicar_js_pagina")
                if not trigger_aberto:
                    if on_abrir_tabela:
                        on_abrir_tabela(False, "nenhum_metodo_abriu")
                    if getattr(config, "DEBUG_TABELA", False):
                        print("[DEBUG_TABELA] aberta=False metodo=nenhum_metodo_abriu")
                    continue
                if wait_fn:
                    wait_fn(pausa_dropdown)
                opcoes_visiveis = False
                try:
                    pagina_ui.locator(".vue-portal-target").get_by_text(label_tabela, exact=False).first.wait_for(state="visible", timeout=timeout_opcoes_visiveis)
                    opcoes_visiveis = True
                except Exception:
                    try:
                        pagina_ui.get_by_role("option").first.wait_for(state="visible", timeout=timeout_opcoes_visiveis)
                        opcoes_visiveis = True
                    except Exception:
                        pass
                if not opcoes_visiveis:
                    if on_abrir_tabela:
                        on_abrir_tabela(False, "opcoes_nao_apareceram")
                    if getattr(config, "DEBUG_TABELA", False):
                        print("[DEBUG_TABELA] opcoes_nao_apareceram timeout=" + str(timeout_opcoes_visiveis))
                    continue
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
                            loc_portal = pagina_ui.locator(".vue-portal-target").get_by_text(lbl_opcao, exact=True).first
                            if loc_portal.count() > 0 and loc_portal.is_visible():
                                loc_portal.click(timeout=timeout_opcao)
                                opcao_clicada = True
                        except Exception:
                            pass
            if not opcao_clicada:
                continue
            alguma_vez_opcao_clicada = True
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
                    try:
                        escopo.get_by_text(config.UI_TEXTO_VALOR_MAIOR_DISPONIVEL, exact=False).first.wait_for(state="visible", timeout=3000)
                    except Exception:
                        try:
                            escopo.get_by_text(getattr(config, "UI_TEXTO_ERRO_MARGEM_SIMULACAO", ""), exact=False).first.wait_for(state="visible", timeout=2000)
                        except Exception:
                            pass
            msg_erro_margem = escopo.get_by_text(getattr(config, "UI_TEXTO_ERRO_MARGEM_SIMULACAO", ""), exact=False).first
            try:
                if msg_erro_margem.is_visible():
                    linha_status = "erro_margem_simulacao"
                    erro_linha = getattr(config, "UI_TEXTO_ERRO_MARGEM_SIMULACAO", "Não foi possível encontrar a margem total para simulação, por favor, refaça a obtenção de saldo")
            except Exception:
                pass
            msg_maior = escopo.get_by_text(config.UI_TEXTO_VALOR_MAIOR_DISPONIVEL, exact=False).first
            tentou_valor_total = False
            try:
                if msg_maior.is_visible():
                    linha_status = "valor_maior_que_disponivel"
                    tentou_valor_total = True
                    try:
                        escopo.get_by_label(config.UI_LABEL_TIPO).click(timeout=2000)
                        if wait_fn:
                            wait_fn(250)
                    except Exception:
                        pass
                    tipo_sel = escopo.get_by_label(config.UI_LABEL_TIPO)
                    for lbl in [config.UI_OPCAO_VALOR_TOTAL, getattr(config, "UI_OPCAO_VALOR_TOTAL_ALT", "Valor Total")]:
                        try:
                            tipo_sel.select_option(label=lbl, timeout=2000)
                            break
                        except Exception:
                            try:
                                _clicar_por_texto(pagina_ui, lbl)
                                break
                            except Exception:
                                pass
                    if wait_fn:
                        wait_fn(150)
                    try:
                        escopo.get_by_role("button", name=config.UI_BOTAO_SIMULAR).first.click(timeout=2000)
                    except Exception:
                        _clicar_por_texto(pagina_ui, config.UI_BOTAO_SIMULAR)
                    if wait_fn:
                        wait_fn(900)
                    try:
                        escopo.get_by_text(config.UI_TEXTO_VALOR_LIBERADO, exact=False).first.wait_for(state="visible", timeout=6000)
                    except Exception:
                        try:
                            escopo.get_by_text(getattr(config, "UI_TEXTO_VALOR_LIBERADO_ALT", "Liberado"), exact=False).first.wait_for(state="visible", timeout=3000)
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
            if sucesso or tentou_valor_total:
                try:
                    bloco_liberado = escopo.get_by_text(config.UI_TEXTO_VALOR_LIBERADO, exact=False).first
                    txt_liberado = bloco_liberado.evaluate("el => el.closest('div')?.innerText || el.parentElement?.innerText || ''")
                    if not (txt_liberado and re.search(r"[\d.,]+", txt_liberado)):
                        bloco_liberado = escopo.get_by_text(getattr(config, "UI_TEXTO_VALOR_LIBERADO_ALT", "Liberado"), exact=False).first
                        txt_liberado = bloco_liberado.evaluate("el => el.closest('div')?.innerText || el.parentElement?.innerText || ''")
                    m_li = re.search(r"R?\$?\s*([\d.,]+)", (txt_liberado or "").replace(" ", ""))
                    if m_li:
                        valor_liberado = m_li.group(1).replace(".", "").replace(",", ".")
                except Exception:
                    pass
                try:
                    parcelas_el = escopo.get_by_text(config.UI_TEXTO_PARCELAS_X_RS, exact=False).first
                    txt_parc = parcelas_el.evaluate("el => el.closest('div')?.innerText || el.parentElement?.innerText || ''")
                    m_parc = re.search(r"(\d+)\s*x\s*R?\$?\s*([\d.,]+)", (txt_parc or ""), re.IGNORECASE)
                    if m_parc:
                        valor_parcela = f"{m_parc.group(1)}x {m_parc.group(2).replace(',', '.')}"
                        if not tentou_valor_total:
                            qtd_parcelas = str(m_parc.group(1))
                except Exception:
                    pass
                try:
                    total_el = escopo.get_by_text(config.UI_TEXTO_TOTAL, exact=False).first
                    txt_tot = total_el.evaluate("el => el.closest('div')?.innerText || el.parentElement?.innerText || ''")
                    m_tot = re.search(r"R?\$?\s*([\d.,]+)", (txt_tot or "").replace(" ", ""))
                    if m_tot:
                        valor_total = m_tot.group(1).replace(".", "").replace(",", ".")
                except Exception:
                    pass
                if not valor_liberado or not valor_parcela or not valor_total:
                    for fonte in [escopo, pagina_ui if pagina_ui is not escopo else None]:
                        if fonte is None:
                            continue
                        try:
                            txt_bloco = fonte.evaluate("el => el.innerText || ''")
                            if not valor_liberado and txt_bloco:
                                m = re.search(r"[Ll]iberado\s*[:\s]*R?\$?\s*([\d.,]+)", txt_bloco)
                                if m:
                                    valor_liberado = m.group(1).replace(".", "").replace(",", ".")
                            if not valor_parcela and txt_bloco:
                                m = re.search(r"(\d+)\s*x\s*R?\$?\s*([\d.,]+)", txt_bloco, re.IGNORECASE)
                                if m:
                                    valor_parcela = f"{m.group(1)}x {m.group(2).replace(',', '.')}"
                                    if not tentou_valor_total:
                                        qtd_parcelas = str(m.group(1))
                            if not valor_total and txt_bloco:
                                m = re.search(r"[Tt]otal\s*[:\s]*R?\$?\s*([\d.,]+)", txt_bloco)
                                if m:
                                    valor_total = m.group(1).replace(".", "").replace(",", ".")
                            if valor_liberado and valor_parcela and valor_total:
                                break
                        except Exception:
                            pass
                if not tentou_valor_total:
                    linha_status = "sucesso"
        except Exception as e:
            erro_linha = str(e).replace("\n", " ").replace("\r", "")[:500]
        skip_parcela = linha_status == "falha_simulacao" and not valor_liberado and not valor_parcela and not valor_total and not erro_linha
        if not skip_parcela:
            valor_esperado_str = str(valor_maximo_parcela if valor_maximo_parcela is not None else "")
            lista_saida.append({
                "nome": cliente.nome, "cpf": cliente.cpf, "contato": cliente.contato, "email": cliente.email,
                "banco": banco_atual, "valor_maximo_parcela": valor_maximo_parcela, "valor_esperado": valor_esperado_str,
                "qtd_parcelas": qtd_parcelas, "valor_liberado": valor_liberado, "valor_parcela": valor_parcela, "valor_total": valor_total,
                "status": linha_status, "erro": erro_linha, "tipo": "parcela",
            })
            gravou_alguma = True
    limite_msg = getattr(config, "UI_TEXTO_LIMITE_OPCOES_MESES", "Limite de opções de meses alcançado")
    lista_saida.append({
        "nome": cliente.nome, "cpf": cliente.cpf, "contato": cliente.contato, "email": cliente.email,
        "banco": banco_atual, "valor_esperado": "", "valor_liberado": "", "valor_parcela": "", "qtd_parcelas": "", "valor_maximo_parcela": "", "valor_total": "",
        "status": limite_msg, "erro": "", "tipo": "limite_meses",
    })
    return (gravou_alguma, alguma_vez_opcao_clicada)


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
