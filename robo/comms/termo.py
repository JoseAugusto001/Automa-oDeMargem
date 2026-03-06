from __future__ import annotations

import re

from playwright.sync_api import Page  # type: ignore[import-untyped]

import config


def extrair_link_termo_do_modal(page: Page) -> str | None:
    dialog = (
        page.locator("[role='dialog'], .modal, [class*='modal'], [data-testid*='modal']")
        .filter(has_text=re.compile(re.escape(config.UI_TEXTO_MODAL_AUTORIZACAO), re.IGNORECASE))
        .first
    )
    try:
        dialog.wait_for(state="visible", timeout=8000)
    except Exception:
        try:
            dialog = page.get_by_text(config.UI_TEXTO_MODAL_AUTORIZACAO, exact=False).first.locator("..").locator("..")
            dialog.wait_for(state="visible", timeout=5000)
        except Exception:
            dialog = page.locator("body")
    doms = getattr(config, "URL_TERMO_DOMAINS", ["assina.bancoprata.com.br"])
    for dom in doms:
        try:
            a = dialog.locator(f"a[href*='{dom}']").first
            if a.count() > 0:
                href = (a.get_attribute("href") or "").strip()
                if href.startswith("http"):
                    return href
        except Exception:
            pass
    try:
        els = dialog.locator("input, textarea")
        for i in range(min(els.count(), 40)):
            el = els.nth(i)
            try:
                v = (el.input_value() or "").strip().split("\n")[0].strip()
                if v.startswith("http") and any(d in v for d in doms):
                    return v
            except Exception:
                pass
    except Exception:
        pass
    try:
        urls = dialog.evaluate(r"""
             (root, doms) => {
             if (!doms || !doms.length) return [];
             const out = [];
             const attrs = ["href","value","data-clipboard-text","data-url","data-link","data-href"];
             var reByDom = doms.map(function(d) { return new RegExp("https?:\\/\\/[^\\s'\"]*" + d.replace(/\./g, "\\.").replace(/\//g, "\\/") + "[^\\s'\"]*", "ig"); });
             root.querySelectorAll("*").forEach(function(el) {
               attrs.forEach(function(a) {
                var v = el.getAttribute && el.getAttribute(a);
                if (v && typeof v === "string" && v.indexOf("http") === 0 && doms.some(function(d) { return v.indexOf(d) !== -1; })) out.push(v.trim());
               });
               if ("value" in el && typeof el.value === "string" && el.value.indexOf("http") === 0 && doms.some(function(d) { return el.value.indexOf(d) !== -1; })) out.push(el.value.trim());
             });
             var txt = (root.innerText || "");
             reByDom.forEach(function(re) { (txt.match(re) || []).forEach(function(u) { out.push(u.trim()); }); });
             return out.filter(function(x, i, arr) { return arr.indexOf(x) === i; }).slice(0, 15);
             }
         """, doms)
        for u in (urls or []):
            u = (u or "").strip().split("\n")[0].strip()
            if u.startswith("http") and any(d in u for d in doms):
                return u
    except Exception:
        pass
    try:
        for el in page.locator("input, textarea").all():
            try:
                v = (el.input_value() or "").strip().split("\n")[0].strip()
                if v.startswith("http") and any(d in v for d in doms):
                    return v
            except Exception:
                pass
    except Exception:
        pass
    try:
        try:
            page.context.grant_permissions(["clipboard-read", "clipboard-write"])
        except Exception:
            pass
        btn = dialog.get_by_role("button", name=re.compile(r"copiar", re.IGNORECASE))\
            .or_(dialog.get_by_text(re.compile(r"copiar", re.IGNORECASE))).first
        if btn.count() > 0:
            btn.click()
            page.wait_for_timeout(250)
            clip = page.evaluate("() => navigator.clipboard.readText()")
            clip = (clip or "").strip()
            if clip.startswith("http") and any(d in clip for d in doms):
                return clip
    except Exception:
        pass
    return None


def extrair_link_termo_pagina(page: Page) -> str | None:
    doms = getattr(config, "URL_TERMO_DOMAINS", ["assina.bancoprata.com.br"])
    for dom in doms:
        try:
            a = page.locator(f"a[href*='{dom}']").first
            if a.count() > 0:
                href = (a.get_attribute("href") or "").strip()
                if href.startswith("http"):
                    return href
        except Exception:
            pass
    try:
        urls = page.evaluate(r"""
            (doms) => {
            if (!doms || !doms.length) return [];
            const out = [];
            const root = document.body;
            const attrs = ["href","value","data-clipboard-text","data-url","data-link","data-href"];
            root.querySelectorAll("a, input, textarea").forEach(function(el) {
                attrs.forEach(function(a) {
                    var v = el.getAttribute && el.getAttribute(a);
                    if (v && typeof v === "string" && v.indexOf("http") === 0 && doms.some(function(d) { return v.indexOf(d) !== -1; })) out.push(v.trim());
                });
                if ("value" in el && typeof el.value === "string" && el.value.indexOf("http") === 0 && doms.some(function(d) { return el.value.indexOf(d) !== -1; })) out.push(el.value.trim());
            });
            return out.filter(function(x, i, arr) { return arr.indexOf(x) === i; }).slice(0, 10);
            }
        """, doms)
        for u in (urls or []):
            u = (u or "").strip().split("\n")[0].strip()
            if u.startswith("http") and any(d in u for d in doms):
                return u
    except Exception:
        pass
    return None


def abrir_termo_em_nova_aba(page: Page, url_termo: str) -> Page:
    termo = page.context.new_page()
    termo.goto(url_termo, wait_until="domcontentloaded")
    return termo
