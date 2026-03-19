from __future__ import annotations

from playwright.sync_api import Page  # type: ignore[import-untyped]

import config
import credenciais


def login_e_ir_para_consulta(page: Page) -> None:
    credenciais.exigir_credenciais()
    page.goto(config.URL_ADMIN_BASE, wait_until="domcontentloaded")
    campo_email = page.get_by_label(config.UI_LABEL_EMAIL).or_(page.locator("input[type='email']").first)
    campo_email.wait_for(state="visible", timeout=config.TIMEOUT_LOGIN_FORM_MS)
    campo_email.fill(credenciais.ADMIN_EMAIL)
    campo_senha = page.get_by_label(config.UI_LABEL_SENHA).or_(page.locator("input[type='password']").first)
    campo_senha.fill(credenciais.ADMIN_SENHA)
    btn_login = page.get_by_role("button", name=config.UI_BOTAO_FAZER_LOGIN).or_(page.get_by_role("button", name="Entrar")).or_(page.get_by_role("button", name="Login"))
    btn_login.click()
    page.wait_for_url(config.URL_HUB_PATTERN, timeout=config.TIMEOUT_LOGIN_MS)
    link_clt = (
        page.get_by_role("link", name=config.UI_LINK_CONSULTA_MARGEM)
        .or_(page.get_by_role("link", name=config.UI_MENU_CLT))
        .or_(page.locator('a[href*="clt/consultar"], a[href*="/clt"]').first)
    )
    link_clt.wait_for(state="visible", timeout=config.TIMEOUT_LOGIN_FORM_MS)
    link_clt.click()
    page.wait_for_url(config.URL_CLT_CONSULTAR_PATTERN, timeout=config.TIMEOUT_LOGIN_MS)


def obter_pagina_consulta_principal(page: Page) -> Page | None:
    for p in page.context.pages:
        try:
            if "clt/consultar" in p.url:
                return p
        except Exception:
            pass
    return page.context.pages[0] if page.context.pages else None


def fechar_pagina_se_aberta(pg: Page | None, pagina_base: Page | None = None) -> None:
    try:
        if pg and not pg.is_closed() and pg != pagina_base:
            pg.close()
    except Exception:
        pass


def voltar_para_consulta_limpa(page: Page) -> None:
    page.goto(config.URL_ADMIN_BASE + "clt/consultar", wait_until="domcontentloaded")
    campo = page.get_by_label(config.UI_LABEL_CPF)\
        .or_(page.get_by_placeholder(config.UI_PLACEHOLDER_CPF))\
        .or_(page.locator('input[name="cpf"], input[id*="cpf"]').first)
    campo.wait_for(state="visible", timeout=10000)
    try:
        campo.fill("")
    except Exception:
        pass
