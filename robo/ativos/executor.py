from __future__ import annotations

import os
from typing import cast

from playwright.sync_api import sync_playwright, ViewportSize  # type: ignore[import-untyped]

import config
from robo.passivos import csv_io
from robo.comms import navegacao
from robo.ativos.processador import processar_clientes


def executar_robo(caminho_entrada: str | None = None, dir_saida: str | None = None, headless: bool = False) -> None:
    if caminho_entrada is None:
        caminho_entrada = os.path.join(config.DIR_ENTRADA_PADRAO, config.ARQUIVO_ENTRADA_PADRAO)
    if dir_saida is None:
        dir_saida = config.DIR_SAIDA_PADRAO
    if not os.path.exists(caminho_entrada):
        raise FileNotFoundError(f"Arquivo de entrada não encontrado: {caminho_entrada}")
    clientes = csv_io.ler_clientes(caminho_entrada)
    if not clientes:
        print("Nenhum cliente válido encontrado no CSV.")
        return
    caminho_saida = csv_io.criar_caminho_csv_saida(dir_saida)
    print(f"CSV de saída: {caminho_saida}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=config.SLOW_MO_HEADED_MS if not headless else 0)
        viewport = cast(ViewportSize, {"width": config.VIEWPORT_LARGURA, "height": config.VIEWPORT_ALTURA})
        context = browser.new_context(viewport=viewport)
        context.grant_permissions(["geolocation"])
        context.set_geolocation({"latitude": -23.5505, "longitude": -46.6333})
        page = context.new_page()
        page.set_default_timeout(15000)
        page.set_default_navigation_timeout(30000)
        try:
            navegacao.login_e_ir_para_consulta(page)
            processar_clientes(page, clientes, caminho_saida)
        except Exception as e:
            if "TargetClosedError" in type(e).__name__:
                print("O navegador foi fechado durante a execução. Não feche a janela manualmente; confira o .env (ADMIN_EMAIL e ADMIN_SENHA) e tente de novo.")
            raise
        finally:
            try:
                for pg in context.pages:
                    if not pg.is_closed():
                        pg.close()
            except Exception:
                pass
            browser.close()
