from __future__ import annotations

import re

from playwright.sync_api import Page  # type: ignore[import-untyped]

import config


def pagina_tem_restricao_emissao(page: Page) -> bool:
    try:
        loc = page.get_by_text(config.UI_TEXTO_RESTRICAO_EMISSAO, exact=False).or_(page.get_by_text(re.compile(r"n[aã]o\s*[eé]\s*permitida.*emiss[aã]o.*proposta|empresa\s*consultada\s*em\s*menos\s*de\s*2\s*anos", re.IGNORECASE)))
        if loc.first.is_visible():
            return True
    except Exception:
        pass
    try:
        texto = page.evaluate("() => document.body?.innerText || ''")
        if re.search(r"n[aã]o\s*[eé]\s*permitida\s*a\s*emiss[aã]o\s*de\s*proposta|empresa\s*consultada\s*em\s*menos\s*de\s*2\s*anos", texto, re.IGNORECASE):
            return True
    except Exception:
        pass
    return False


def pagina_tem_cpf_invalido(page: Page) -> bool:
    try:
        loc = page.get_by_text(config.UI_TEXTO_CPF_INVALIDO, exact=False)\
            .or_(page.get_by_text(getattr(config, "UI_TEXTO_CPF_INVALIDO_ALT", "O CPF informado não é válido"), exact=False))\
            .or_(page.get_by_text(getattr(config, "UI_TEXTO_CPF_INVALIDO_ALT2", "CPF informado não é válido"), exact=False))\
            .or_(page.get_by_text(re.compile(r"cpf.*inv[aá]lido|cpf.*n[aã]o.*v[aá]lido|o?\s*cpf\s*informado\s*n[aã]o\s*[eé]?\s*v[aá]lido", re.IGNORECASE)))
        return loc.first.is_visible()
    except Exception:
        return False


def pagina_tem_cpf_nao_encontrado(page: Page) -> bool:
    try:
        loc = page.get_by_text(config.UI_TEXTO_CPF_NAO_ENCONTRADO, exact=False).or_(page.get_by_text(getattr(config, "UI_TEXTO_CPF_NAO_ENCONTRADO_ALT", ""), exact=False)).or_(page.get_by_text(re.compile(r"cpf\s*n[aã]o\s*encontrado\s*na\s*base|trabalhador\s*ineleg[ií]vel", re.IGNORECASE)))
        if loc.first.is_visible():
            return True
    except Exception:
        pass
    try:
        texto = page.evaluate("() => document.body?.innerText || ''")
        if re.search(r"cpf\s*n[aã]o\s*encontrado\s*na\s*base|trabalhador\s*ineleg[ií]vel", texto, re.IGNORECASE):
            return True
    except Exception:
        pass
    return False


def pagina_tem_erro_na_consulta(page: Page) -> bool:
    try:
        if page.get_by_text(config.UI_TEXTO_ERRO_NA_CONSULTA, exact=False).first.is_visible():
            return True
    except Exception:
        pass
    return False


def pagina_tem_registro_nao_encontrado(page: Page) -> bool:
    try:
        texto_reg = getattr(config, "UI_TEXTO_REGISTRO_NAO_ENCONTRADO", "")
        if texto_reg and page.get_by_text(texto_reg, exact=False).first.is_visible():
            return True
    except Exception:
        pass
    return False


def garantir_cpf_preenchido(page: Page, cpf_site: str) -> None:
    campo = (
        page.get_by_label(config.UI_LABEL_CPF)
        .or_(page.get_by_placeholder(config.UI_PLACEHOLDER_CPF))
        .or_(page.locator('input[name="cpf"], input[id*="cpf"]').first)
    )
    try:
        valor_atual = (campo.input_value() or "").strip()
    except Exception:
        valor_atual = ""
    if valor_atual != cpf_site:
        try:
            campo.fill("")
            campo.fill(cpf_site)
            try:
                campo.first.evaluate("""
                    (el) => {
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        el.dispatchEvent(new Event('blur', { bubbles: true }));
                    }
                """)
            except Exception:
                pass
            page.wait_for_timeout(300)
        except Exception:
            try:
                campo.evaluate("""
                    (el, val) => {
                        el.value = val;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        el.dispatchEvent(new Event('blur', { bubbles: true }));
                    }
                """, cpf_site)
                page.wait_for_timeout(300)
            except Exception:
                pass


def selecionar_banco(pg: Page, banco: str) -> bool:
    alvo = "celcoin" if "celcoin" in banco.lower() else "qitech"
    form = pg.locator("form").first
    sel = form.locator("select").first
    try:
        if sel.count() > 0 and sel.is_visible():
            options = sel.locator("option").all_inner_texts()
            for opt in options:
                if alvo in (opt or "").lower():
                    sel.select_option(label=opt)
                    return True
    except Exception:
        pass
    combobox = form.get_by_role("combobox").first
    try:
        if combobox.count() > 0 and combobox.is_visible():
            combobox.click()
            pg.wait_for_timeout(400)
            listbox = pg.get_by_role("listbox").first
            listbox.wait_for(state="visible", timeout=2000)
            option = listbox.get_by_role("option").filter(has_text=re.compile(alvo, re.IGNORECASE)).first
            option.click()
            return True
    except Exception:
        pass
    try:
        pg.get_by_text(re.compile(alvo, re.IGNORECASE)).first.click(timeout=1500)
        return True
    except Exception:
        pass
    is_qitech = banco and "qitech" in banco.lower()
    is_celcoin = banco and "celcoin" in banco.lower()
    try:
        ok = pg.evaluate("""(isQ) => {
            const sel = document.querySelector('form select[name*="banco"], form select[id*="banco"], form select');
            if (sel) {
                for (const opt of sel.options) {
                    const t = (opt.text || opt.label || '').toLowerCase();
                    if (isQ && t.indexOf('qitech') >= 0) { opt.selected = true; sel.dispatchEvent(new Event('change', { bubbles: true })); return true; }
                    if (!isQ && t.indexOf('celcoin') >= 0) { opt.selected = true; sel.dispatchEvent(new Event('change', { bubbles: true })); return true; }
                }
            }
            return false;
        }""", is_qitech)
        if ok:
            return True
    except Exception:
        pass
    try:
        sel = pg.locator("form select").first
        sel.wait_for(state="visible", timeout=1200)
        if is_qitech:
            try:
                sel.select_option(label=config.UI_OPCAO_QITECH_ALT)
            except Exception:
                sel.select_option(label="QITECH")
        else:
            sel.select_option(label=config.UI_OPCAO_CELCOIN)
        return True
    except Exception:
        pass
    try:
        campo_banco = pg.get_by_label(config.UI_LABEL_BANCO).or_(pg.locator("form").first.locator('[role="combobox"], select, [class*="select"], [class*="dropdown"]').first).first
        campo_banco.wait_for(state="visible", timeout=1500)
        campo_banco.click()
        pg.wait_for_timeout(400)
        if is_celcoin:
            pg.get_by_role("option").filter(has_text=re.compile(r"celcoin", re.IGNORECASE)).or_(pg.get_by_text(re.compile(r"celcoin", re.IGNORECASE))).first.click(timeout=3000)
        else:
            pg.get_by_role("option").filter(has_text=re.compile(r"qitech", re.IGNORECASE)).or_(pg.get_by_text(re.compile(r"qitech", re.IGNORECASE))).first.click(timeout=3000)
        pg.wait_for_timeout(200)
        return True
    except Exception:
        pass
    try:
        trigger = form.get_by_text("Celcoin", exact=True).first
        trigger.wait_for(state="visible", timeout=1800)
        trigger.click(no_wait_after=True)
        pg.wait_for_timeout(120)
        listbox = pg.get_by_role("listbox").first
        listbox.wait_for(state="visible", timeout=600)
        if is_celcoin:
            listbox.get_by_text(re.compile(r"celcoin", re.IGNORECASE)).first.click(no_wait_after=True, timeout=1000)
        else:
            listbox.get_by_text(re.compile(r"qitech", re.IGNORECASE)).first.click(no_wait_after=True, timeout=1000)
        return True
    except Exception:
        pass
    try:
        pattern = re.compile(r"celcoin", re.IGNORECASE) if is_celcoin else re.compile(r"qitech", re.IGNORECASE)
        opcao = pg.get_by_role("option", name=pattern).first
        opcao.wait_for(state="visible", timeout=600)
        opcao.click(no_wait_after=True)
        return True
    except Exception:
        pass
    try:
        menu = pg.get_by_role("menu").first
        menu.wait_for(state="visible", timeout=500)
        pattern = re.compile(r"celcoin", re.IGNORECASE) if is_celcoin else re.compile(r"qitech", re.IGNORECASE)
        menu.get_by_text(pattern).first.click(no_wait_after=True, timeout=800)
        return True
    except Exception:
        pass
    try:
        pattern = re.compile(r"celcoin", re.IGNORECASE) if is_celcoin else re.compile(r"qitech", re.IGNORECASE)
        form.get_by_text(pattern).first.click(no_wait_after=True, timeout=800)
        return True
    except Exception:
        pass
    return False


def historico_tem_linha_sucesso_cpf(page: Page, cpf_site: str) -> bool:
    try:
        row = page.locator(f"tr:has-text('{cpf_site}'):has-text('{config.UI_TEXTO_SUCESSO}')").or_(page.locator(f"[role='row']:has-text('{cpf_site}'):has-text('{config.UI_TEXTO_SUCESSO}')")).first
        return row.is_visible()
    except Exception:
        return False
