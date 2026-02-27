from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List

from playwright.sync_api import Page, sync_playwright  # type: ignore[import-untyped]

import config
import credenciais


@dataclass
class Cliente:
    nome: str
    cpf: str
    contato: str
    email: str


def normalizar_cpf(cpf: str) -> str:
    digitos = "".join(ch for ch in cpf if ch.isdigit())
    return digitos


def ler_clientes(caminho_csv: str) -> List[Cliente]:
    clientes: List[Cliente] = []
    with open(caminho_csv, newline="", encoding=config.CSV_ENCODING) as f:
        amostra = f.read(2048)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(amostra, delimiters=",;")
        except csv.Error:
            dialect = csv.excel
            dialect.delimiter = ","
        reader = csv.DictReader(f, dialect=dialect)
        if not reader.fieldnames or "nome" not in reader.fieldnames or "cpf" not in reader.fieldnames:
            raise ValueError("CSV deve conter colunas 'nome' e 'cpf'")
        for row in reader:
            nome = row.get("nome", "").strip()
            cpf = normalizar_cpf(row.get("cpf", ""))
            contato = row.get("contato", "").strip()
            email = row.get("email", "").strip()

            if not cpf or not nome:
                continue

            clientes.append(Cliente(nome=nome, cpf=cpf, contato=contato, email=email))

    return clientes


def garantir_pasta_saida(caminho_saida: str) -> str:
    os.makedirs(caminho_saida, exist_ok=True)
    return caminho_saida


def criar_caminho_csv_saida(base_dir: str | None = None) -> str:
    if base_dir is None:
        base_dir = config.DIR_SAIDA_PADRAO
    garantir_pasta_saida(base_dir)
    agora = datetime.now().strftime(config.FORMATO_DATA_CSV)
    return os.path.join(base_dir, f"{config.PREFIXO_CSV_SAIDA}{agora}.csv")


def escrever_cabecalho_saida(caminho_saida: str) -> None:
    existe = os.path.exists(caminho_saida)
    with open(caminho_saida, "a", newline="", encoding=config.CSV_ENCODING) as f:
        writer = csv.writer(f, delimiter=config.CSV_DELIMITER)
        if not existe:
            writer.writerow(config.CSV_COLUNAS_SAIDA)


def escrever_linha_saida(caminho_saida: str, valores: List[str]) -> None:
    with open(caminho_saida, "a", newline="", encoding=config.CSV_ENCODING) as f:
        csv.writer(f, delimiter=config.CSV_DELIMITER).writerow(valores)


def cpf_com_mascara(cpf: str) -> str:
    
    cpf = re.sub(r'\D', '', cpf)

    if len(cpf) != 11:
        return cpf


    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"


def login_e_ir_para_consulta(page: Page) -> None:
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

def cpf_digits(cpf: str) -> str:
    return re.sub(r"\D", "", cpf or "")

def cpf_valido_11(cpf: str) -> bool:
    return len(cpf_digits(cpf)) == 11



def voltar_para_consulta_limpa(page: Page):
    page.goto(config.URL_ADMIN_BASE + "clt/consultar", wait_until="domcontentloaded")
    campo = page.get_by_label(config.UI_LABEL_CPF)\
        .or_(page.get_by_placeholder(config.UI_PLACEHOLDER_CPF))\
        .or_(page.locator('input[name="cpf"], input[id*="cpf"]').first)
    campo.wait_for(state="visible", timeout=10000)
    try:
        campo.fill("")
    except Exception:
        pass

def processar_clientes(page: Page, clientes: Iterable[Cliente], caminho_saida: str) -> None:
    timeout_ms = config.TIMEOUT_PROCESSAR_MS
    cpfs_ja_processados: set[str] = set()
    for idx, cliente in enumerate(clientes):
        pular = False
        cpf_raw = cliente.cpf
        if not cpf_valido_11(cpf_raw):
            escrever_linha_saida(
                caminho_saida,
                [cliente.nome, cpf_raw, cliente.contato, cliente.email, "", "", "", "", "", "cpf_invalido", "CPF com tamanho diferente de 11 dígitos (provável perda no CSV)"]
            )
            pular = True
        cpf_site = cpf_com_mascara(cpf_raw)
        pagina_resultado = page
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
              voltar_para_consulta_limpa(page)
              continue
            if not pular:
              print(f"Processando CPF {cliente.cpf} - {cliente.nome}")
              valor_maximo_parcela = ""
              status = "nao_processado"
              mensagem_erro = ""
            if pular:
              voltar_para_consulta_limpa(page)
              continue
            try:
                banner_nova_versao = page.get_by_text(config.UI_TEXTO_NOVA_VERSAO_RECARREGANDO, exact=False).or_(page.get_by_text("Recarregando", exact=False)).first
                if banner_nova_versao.is_visible():
                    try:
                        with page.expect_navigation(timeout=12000):
                            page.wait_for_timeout(10000)
                    except Exception:
                        pass
                    try:
                        page.wait_for_load_state("domcontentloaded", timeout=10000)
                    except Exception:
                        pass
                    page.wait_for_timeout(1500)
            except Exception:
                    pass
            page.wait_for_timeout(500)
            try:
                page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception:
                pass
            

            def pagina_tem_restricao_emissao():
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
            def pagina_tem_cpf_invalido():
                try:
                    loc = page.get_by_text(config.UI_TEXTO_CPF_INVALIDO, exact=False)\
                    .or_(page.get_by_text(getattr(config, "UI_TEXTO_CPF_INVALIDO_ALT", "CPF informado não é válido"), exact=False))\
                    .or_(page.get_by_text(re.compile(r"cpf.*inv[aá]lido|cpf.*n[aã]o.*v[aá]lido|o\s*cpf\s*informado\s*n[aã]o\s*[eé]\s*v[aá]lido", re.IGNORECASE)))

                    return loc.first.is_visible()

                except Exception:
                    return False


            if pagina_tem_restricao_emissao():
                try:
                    msg_restricao = page.get_by_text(config.UI_TEXTO_RESTRICAO_EMISSAO, exact=False).first.inner_text()[:500] if page.get_by_text(config.UI_TEXTO_RESTRICAO_EMISSAO, exact=False).first.is_visible() else config.UI_TEXTO_RESTRICAO_EMISSAO
                except Exception:
                    msg_restricao = config.UI_TEXTO_RESTRICAO_EMISSAO
                escrever_linha_saida(caminho_saida, [cliente.nome, cliente.cpf, cliente.contato, cliente.email, "", "", "", "", "", "restricao_emissao", msg_restricao.replace("\n", " ").replace("\r", "")])
                pular = True
            campo_cpf = (
                page.get_by_label(config.UI_LABEL_CPF)
                .or_(page.get_by_placeholder(config.UI_PLACEHOLDER_CPF))
                .or_(page.locator('input[name="cpf"], input[id*="cpf"]').first)
            )
            campo_cpf.wait_for(state="visible", timeout=config.TIMEOUT_FORM_CONSULTA_MS)
            page.wait_for_timeout(300)

            def garantir_cpf_preenchido():
                campo = page.get_by_label(config.UI_LABEL_CPF).or_(page.get_by_placeholder(config.UI_PLACEHOLDER_CPF)).or_(page.locator('input[name="cpf"], input[id*="cpf"]').first)
                try:
                    if not campo.input_value().strip():
                        campo.fill("")
                        campo.fill(cpf_site)
                        page.wait_for_timeout(100)
                except Exception:
                    try:
                        campo.evaluate("(el, val) => { el.value = val; el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); }", cpf_site)
                        page.wait_for_timeout(100)
                    except Exception:
                        pass

            def selecionar_banco_qitech():
                try:
                    ok = page.evaluate("""() => {
                        const sel = document.querySelector('form select[name*="banco"], form select[id*="banco"], form select');
                        if (sel) {
                            for (const opt of sel.options) { if (/qitech/i.test(opt.text || opt.label)) { opt.selected = true; sel.dispatchEvent(new Event('change', { bubbles: true })); return true; } }
                        }
                        return false;
                    }""")
                    if ok:
                        return True
                except Exception:
                    pass
                try:
                    sel = page.locator("form select").first
                    sel.wait_for(state="visible", timeout=1200)
                    try:
                        sel.select_option(label=config.UI_OPCAO_QITECH_ALT)
                    except Exception:
                        sel.select_option(label="QITECH")
                    return True
                except Exception:
                    pass
                form = page.locator("form").first
                trigger = form.get_by_text("Celcoin", exact=True).first
                try:
                    trigger.wait_for(state="visible", timeout=1800)
                    trigger.click(no_wait_after=True)
                    page.wait_for_timeout(120)
                    listbox = page.get_by_role("listbox").first
                    listbox.wait_for(state="visible", timeout=600)
                    listbox.get_by_text(re.compile(r"qitech", re.IGNORECASE)).first.click(no_wait_after=True, timeout=1000)
                    return True
                except Exception:
                    pass
                try:
                    opcao = page.get_by_role("option", name=re.compile(r"qitech", re.IGNORECASE)).first
                    opcao.wait_for(state="visible", timeout=600)
                    opcao.click(no_wait_after=True)
                    return True
                except Exception:
                    pass
                try:
                    menu = page.get_by_role("menu").first
                    menu.wait_for(state="visible", timeout=500)
                    menu.get_by_text(re.compile(r"qitech", re.IGNORECASE)).first.click(no_wait_after=True, timeout=800)
                    return True
                except Exception:
                    pass
                try:
                    form.get_by_text(re.compile(r"qitech", re.IGNORECASE)).first.click(no_wait_after=True, timeout=800)
                    return True
                except Exception:
                    pass
                return False

            print("Selecionando banco QiTech...")
            selecionar_banco_qitech()
            try:
                page.wait_for_load_state("domcontentloaded", timeout=6000)
            except Exception:
                pass
            page.wait_for_timeout(600)
            campo_cpf = page.get_by_label(config.UI_LABEL_CPF).or_(page.get_by_placeholder(config.UI_PLACEHOLDER_CPF)).or_(page.locator('input[name="cpf"], input[id*="cpf"]').first)
            try:
                campo_cpf.fill(cpf_site)
            except Exception:
                campo_cpf.evaluate("(el, val) => { el.value = val; el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); }", cpf_site)
            page.wait_for_timeout(300)
            garantir_cpf_preenchido()
            page.wait_for_timeout(350)
            try:
                if not campo_cpf.input_value().strip():
                    campo_cpf.fill(cpf_site)
                    page.wait_for_timeout(200)
            except Exception:
                pass
            btn_consultar = page.locator(f"#{config.UI_ID_BOTAO_CONSULTAR_SALDO}").or_(page.get_by_role("button", name=config.UI_BOTAO_CONSULTAR_SALDO)).or_(page.get_by_role("button", name=re.compile(r"consultar\s*saldo", re.IGNORECASE)))
            btn_consultar.first.wait_for(state="visible", timeout=15000)
            btn_consultar.first.scroll_into_view_if_needed(timeout=5000)
            page.wait_for_timeout(250)
            nav_ocorreu = False
            try:
               btn_consultar.first.click(force=True)
               page.wait_for_timeout(150)
               def resultado_apareceu() -> bool:
                    if pagina_tem_restricao_emissao(): return True  
                    if pagina_tem_cpf_invalido(): return True  
                    try:
                        if page.get_by_text(config.UI_TEXTO_MODAL_AUTORIZACAO, exact=False).first.is_visible(): return True
                    except Exception:
                        pass
                    try:
                        if page.get_by_text(config.UI_TEXTO_SEM_VINCULO, exact=False).first.is_visible(): return True
                    except Exception:       
                        pass
                    try:
                        return page.locator(f"tr:has-text('{cpf_site}')").first.is_visible()
                    except Exception:
                        return False
               page.wait_for_function("() => true", timeout=200)
               for _ in range(20):
                   if resultado_apareceu():
                       nav_ocorreu = True
                       break
                   page.wait_for_timeout(500)
            except Exception:
                pass
            if not nav_ocorreu:
                try:
                    btn_consultar.first.click(force=True)
                    page.wait_for_timeout(2000)
                except Exception:
                    pass
            try:
                page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception:
                pass
            page.wait_for_timeout(config.PAUSA_APOS_CONSULTAR_MS)
            if pagina_tem_restricao_emissao():
                try:
                    msg_restricao = page.get_by_text(config.UI_TEXTO_RESTRICAO_EMISSAO, exact=False).first.inner_text()[:500] if page.get_by_text(config.UI_TEXTO_RESTRICAO_EMISSAO, exact=False).first.is_visible() else config.UI_TEXTO_RESTRICAO_EMISSAO
                except Exception:
                    msg_restricao = config.UI_TEXTO_RESTRICAO_EMISSAO
                escrever_linha_saida(caminho_saida, [cliente.nome, cliente.cpf, cliente.contato, cliente.email, "", "", "", "", "", "restricao_emissao", msg_restricao.replace("\n", " ").replace("\r", "")])
                
                pular = True
            
            if pagina_tem_cpf_invalido():
                escrever_linha_saida(caminho_saida, [cliente.nome, cliente.cpf, cliente.contato, cliente.email, "", "", "", "", "", "cpf_invalido", mensagem_erro])
                
                pular = True
            page.wait_for_timeout(400)
            if pagina_tem_cpf_invalido():
                escrever_linha_saida(caminho_saida, [cliente.nome, cliente.cpf, cliente.contato, cliente.email, "", "", "", "", "", "cpf_invalido", mensagem_erro])
                
                pular = True
            modal_autorizacao = page.get_by_text(config.UI_TEXTO_MODAL_AUTORIZACAO, exact=False).first
            try:
                modal_visivel = modal_autorizacao.is_visible()
            except Exception:
                modal_visivel = False
            if modal_visivel:
                try:
                    url_termo_alt = getattr(config, "URL_TERMO_CONTAIN_ALT", "credito-trabalhador/autorizar")
                    link_termo = None
                    for selector in [f'a[href*="{config.URL_TERMO_CONTAIN}"]', f'a[href*="{url_termo_alt}"]']:
                        try:
                            link_termo = page.locator(selector).first.get_attribute("href")
                            if link_termo:
                                break
                        except Exception:
                            pass
                    if link_termo:
                        with page.context.expect_page(timeout=timeout_ms) as nova_aba_info:
                            page.locator(f'a[href*="{config.URL_TERMO_CONTAIN}"]').or_(page.locator(f'a[href*="{url_termo_alt}"]')).first.click()
                        aba_termo = nova_aba_info.value
                        aba_termo.on("dialog", lambda d: d.accept())
                        aba_termo.wait_for_load_state("domcontentloaded")
                        aba_termo.get_by_label(config.UI_LABEL_CPF).or_(aba_termo.locator('input[placeholder*="CPF"], input[name="cpf"]').first).fill(cpf_site)
                        aba_termo.get_by_label(config.UI_LABEL_NOME).or_(aba_termo.locator('input[placeholder*="Nome"], input[name="nome"]').first).fill(cliente.nome)
                        aba_termo.get_by_label(config.UI_LABEL_EMAIL).or_(aba_termo.locator('input[type="email"]').first).fill(cliente.email)
                        aba_termo.get_by_label("telefone").or_(aba_termo.get_by_label(config.UI_LABEL_TELEFONE)).or_(aba_termo.locator('input[name*="telefone"], input[placeholder*="telefone"]').first).fill(cliente.contato)
                        for chk in aba_termo.get_by_role("checkbox").all():
                            if not chk.is_checked():
                                chk.check()
                        aba_termo.get_by_role("button", name=config.UI_BOTAO_ENVIAR).click()
                        aba_termo.wait_for_selector(f"text={config.UI_TEXTO_OBRIGADO}", timeout=timeout_ms)
                        aba_termo.close()
                        page.bring_to_front()
                        page.get_by_role("button", name=config.UI_BOTAO_VOLTAR).first.wait_for(state="visible", timeout=5000)
                        page.get_by_role("button", name=config.UI_BOTAO_VOLTAR).first.click()
                        page.wait_for_timeout(800)
                        page.get_by_label(config.UI_LABEL_CPF).or_(page.locator('input[name="cpf"], input[id*="cpf"]').first).wait_for(state="visible", timeout=5000)
                        page.wait_for_timeout(400)
                        page.get_by_label(config.UI_LABEL_CPF).or_(page.locator('input[name="cpf"], input[id*="cpf"]').first).fill(cpf_site)
                        page.wait_for_timeout(400)
                        page.locator(f"#{config.UI_ID_BOTAO_CONSULTAR_SALDO}").or_(page.get_by_role("button", name=config.UI_BOTAO_CONSULTAR_SALDO)).first.click()
                        try:
                            page.wait_for_load_state("domcontentloaded", timeout=config.TIMEOUT_PROCESSAR_MS)
                        except Exception:
                            pass
                        page.wait_for_timeout(config.PAUSA_APOS_CONSULTAR_MS)
                    else:
                        status = "falha_modal_autorizacao"
                except Exception as e:
                    print(f"Erro no fluxo do termo: {e}")
                    status = "falha_modal_autorizacao"

            msg_vinculo = page.get_by_text(config.UI_TEXTO_SEM_VINCULO, exact=False).first
            try:
                vinculo_visivel = msg_vinculo.is_visible()
            except Exception:
                vinculo_visivel = False
            if vinculo_visivel:
                escrever_linha_saida(caminho_saida, [cliente.nome, cliente.cpf, cliente.contato, cliente.email, "", "", "", "", "", "sem_vinculo", mensagem_erro])
                
                pular = True
            if status == "falha_modal_autorizacao":
                escrever_linha_saida(caminho_saida, [cliente.nome, cliente.cpf, cliente.contato, cliente.email, "", "", "", "", "", status, mensagem_erro])
                
                pular = True
            try:
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=10000)
                except Exception:
                    pass
                page.wait_for_timeout(1500)
                pagina_consulta = page.context.pages[0]
                for p in page.context.pages:
                    try:
                        if "clt/consultar" in p.url:
                            pagina_consulta = p
                            break
                    except Exception:
                        pass
                try:
                    pagina_consulta.bring_to_front()
                except Exception:
                    pass
                page.wait_for_timeout(1200)
                for _ in range(10):
                    try:
                        if pagina_consulta.get_by_text(cpf_site, exact=False).first.is_visible():
                            break
                    except Exception:
                        pass
                    page.wait_for_timeout(2000)
                linha_cpf = None
                timeout_por_tentativa = min(6000, timeout_ms // 3)
                locadores_linha = [
                    pagina_consulta.locator(f"tr:has-text('{cliente.cpf}')").first,
                    pagina_consulta.locator(f"tr:has-text('{cpf_site}')").first,
                    pagina_consulta.locator(f"[role='row']:has-text('{cpf_site}')").first,
                    pagina_consulta.locator(f"li:has-text('{cpf_site}')").first,
                    pagina_consulta.locator("tr, [role='row'], li").filter(has=pagina_consulta.get_by_text(cpf_site, exact=False)).filter(has=pagina_consulta.get_by_role("button", name=config.UI_BOTAO_VER_RESULTADO)).first,
                ]
                for tentativa in range(3):
                    for loc in locadores_linha:
                        try:
                            loc.wait_for(state="visible", timeout=timeout_por_tentativa)
                            linha_cpf = loc
                            break
                        except Exception:
                            pass
                    if linha_cpf is not None:
                        break
                    if tentativa < 2:
                        page.wait_for_timeout(2000)
                if linha_cpf is None and getattr(config, "USE_RECARREGAR_HISTORICO", False):
                    try:
                        page.get_by_role("button", name=config.UI_BOTAO_RECARREGAR).first.click(timeout=5000)
                        page.wait_for_load_state("domcontentloaded", timeout=10000)
                        page.wait_for_timeout(config.PAUSA_APOS_RECARREGAR_MS)
                        for tentativa2 in range(3):
                            for loc in locadores_linha:
                                try:
                                    loc.wait_for(state="visible", timeout=timeout_por_tentativa)
                                    linha_cpf = loc
                                    break
                                except Exception:
                                    pass
                            if linha_cpf is not None:
                                break
                            if tentativa2 < 2:
                                page.wait_for_timeout(2000)
                    except Exception:
                        pass
                if linha_cpf is None:
                    raise Exception("Linha do CPF não encontrada no histórico")
                btn_ver_resultado = linha_cpf.get_by_role("button", name=config.UI_BOTAO_VER_RESULTADO).or_(linha_cpf.get_by_text(config.UI_BOTAO_VER_RESULTADO)).first
                btn_ver_resultado.wait_for(state="visible", timeout=8000)
                btn_ver_resultado.scroll_into_view_if_needed(timeout=3000)
                pagina_consulta.wait_for_timeout(300)
                if linha_cpf.get_by_text(config.UI_TEXTO_SUCESSO, exact=False).first.is_visible():
                    click_ver_resultado_ok = False
                    try:
                        ctx = page.context
                        num_abas_antes = len(ctx.pages)
                        try:
                            btn_ver_resultado.click(timeout=10000)
                            click_ver_resultado_ok = True
                        except BaseException:
                            valor_maximo_parcela = ""
                            status = "falha_historico"
                        if not click_ver_resultado_ok:
                            raise BaseException("clique Ver resultado falhou")
                        esperou = False
                        for p in ctx.pages:
                            try:
                                if not p.is_closed():
                                    p.wait_for_timeout(config.PAUSA_APOS_VER_RESULTADO_MS)
                                    esperou = True
                                    break
                            except BaseException:
                                pass
                        if not esperou and ctx.pages:
                            try:
                                ctx.pages[0].wait_for_timeout(config.PAUSA_APOS_VER_RESULTADO_MS)
                            except BaseException:
                                pass
                        try:
                            if len(ctx.pages) > num_abas_antes:
                                pagina_resultado = ctx.pages[-1]
                                try:
                                    pagina_resultado.bring_to_front()
                                except BaseException:
                                    pass
                            else:
                                pagina_resultado = None
                                for p in ctx.pages:
                                    try:
                                        if not p.is_closed():
                                            pagina_resultado = p
                                            break
                                    except BaseException:
                                        pass
                                if pagina_resultado is None:
                                    pagina_resultado = ctx.pages[0] if ctx.pages else page
                        except BaseException:
                            pagina_resultado = ctx.pages[0] if ctx.pages else page
                        try:
                            bloco_valor = pagina_resultado.get_by_text(config.UI_TEXTO_VALOR_MAXIMO_PARCELA, exact=False).first
                            bloco_valor.wait_for(state="visible", timeout=config.TIMEOUT_VALOR_MAX_MS)
                            texto = bloco_valor.evaluate("el => el.closest('div')?.innerText || el.parentElement?.innerText || ''")
                            match = re.search(r"[\d.,]+", texto.replace("R$", "").strip())
                            if match:
                                valor_maximo_parcela = match.group(0).replace(".", "").replace(",", ".")
                                status = "sucesso"
                            else:
                                valor_maximo_parcela = ""
                        except BaseException:
                            valor_maximo_parcela = ""
                    except BaseException:
                        if not valor_maximo_parcela:
                            valor_maximo_parcela = ""
                        if status != "sucesso":
                            status = "falha_historico"
                else:
                    status = "status_nao_sucesso"
                    try:
                        pagina_resultado = pagina_consulta
                    except BaseException:
                        pagina_resultado = page.context.pages[0] if page.context.pages else page
            except BaseException as e:
                if isinstance(e, (KeyboardInterrupt, SystemExit)):
                    raise
                erro_msg = str(e).replace("\n", " ").replace("\r", "")[:500]
                escrever_linha_saida(
                        caminho_saida,
                        [cliente.nome, cliente.cpf, cliente.contato, cliente.email, "", "", "", "", "", "falha_historico", erro_msg]
                    )
                
                voltar_para_consulta_limpa(page)
            
                pagina_resultado = page.context.pages[0] if page.context.pages else page
            if not valor_maximo_parcela and status == "nao_processado":
                status = "falha_historico"
            if not valor_maximo_parcela or status != "sucesso":
                if pagina_tem_cpf_invalido():
                    status = "cpf_invalido"
                escrever_linha_saida(caminho_saida, [cliente.nome, cliente.cpf, cliente.contato, cliente.email, valor_maximo_parcela, "", "", "", "", status, mensagem_erro])
                
                pular = True
            try:
                dropdown_tabela = pagina_resultado.get_by_label(config.UI_LABEL_TABELA).or_(pagina_resultado.locator('select[name*="tabela"], select[id*="tabela"]').first)
                opcoes_texto = dropdown_tabela.locator("option").evaluate_all("opts => opts.map(o => o.textContent.trim()).filter(Boolean)")
            except Exception:
                opcoes_texto = []
            opcoes_com_meses: List[tuple] = []
            for txt in opcoes_texto:
                m = re.search(r"(\d+)\s*(?:meses|mes)?", txt, re.IGNORECASE)
                if m:
                    opcoes_com_meses.append((int(m.group(1)), txt))
            opcoes_com_meses.sort(key=lambda x: x[0])
            for _meses, label_tabela in opcoes_com_meses:
                linha_status = "falha_simulacao"
                valor_liberado = ""
                valor_parcela = ""
                valor_total = ""
                qtd_parcelas = str(_meses)
                erro_linha = ""
                try:
                    try:
                        pagina_resultado.get_by_label(config.UI_LABEL_TIPO).select_option(label=config.UI_OPCAO_VALOR_PARCELA)
                    except Exception:
                        pagina_resultado.locator('select[name*="tipo"], [role="combobox"]').first.select_option(label=config.UI_OPCAO_VALOR_PARCELA)
                    try:
                        dropdown_tabela.select_option(label=label_tabela)
                    except Exception:
                        pagina_resultado.locator('select[name*="tabela"], select[id*="tabela"]').first.select_option(label=label_tabela)
                    pagina_resultado.get_by_role("button", name=config.UI_BOTAO_SIMULAR).click()
                    pagina_resultado.wait_for_timeout(config.PAUSA_APOS_SIMULAR_MS)
                    msg_maior = pagina_resultado.get_by_text(config.UI_TEXTO_VALOR_MAIOR_DISPONIVEL, exact=False).first
                    tentou_valor_total = False
                    try:
                        if msg_maior.is_visible():
                            tentou_valor_total = True
                            try:
                                pagina_resultado.get_by_label(config.UI_LABEL_TIPO).select_option(label=config.UI_OPCAO_VALOR_TOTAL)
                            except Exception:
                                pagina_resultado.locator('select[name*="tipo"], [role="combobox"]').first.select_option(label=config.UI_OPCAO_VALOR_TOTAL)
                            pagina_resultado.get_by_role("button", name=config.UI_BOTAO_SIMULAR).click()
                            pagina_resultado.wait_for_timeout(config.PAUSA_APOS_SIMULAR_MS)
                    except Exception:
                        pass
                    sucesso = pagina_resultado.get_by_text(config.UI_TEXTO_VALOR_LIBERADO, exact=False).first.is_visible() and pagina_resultado.get_by_text(config.UI_TEXTO_ENTENDA_ENCARGOS, exact=False).first.is_visible()
                    if tentou_valor_total and not sucesso:
                        linha_status = "valor_maior_que_disponivel"
                    if sucesso:
                        try:
                            bloco_liberado = pagina_resultado.get_by_text(config.UI_TEXTO_VALOR_LIBERADO, exact=False).first
                            txt_liberado = bloco_liberado.evaluate("el => el.closest('div')?.innerText || el.parentElement?.innerText || ''")
                            m_li = re.search(r"R?\$?\s*([\d.,]+)", txt_liberado.replace(" ", ""))
                            if m_li:
                                valor_liberado = m_li.group(1).replace(".", "").replace(",", ".")
                        except Exception:
                            pass
                        try:
                            parcelas_el = pagina_resultado.get_by_text(config.UI_TEXTO_PARCELAS_X_RS, exact=False).first
                            txt_parc = parcelas_el.evaluate("el => el.closest('div')?.innerText || el.parentElement?.innerText || ''")
                            m_parc = re.search(r"(\d+)\s*x\s*R?\$?\s*([\d.,]+)", txt_parc, re.IGNORECASE)
                            if m_parc:
                                valor_parcela = m_parc.group(2).replace(".", "").replace(",", ".")
                        except Exception:
                            pass
                        try:
                            total_el = pagina_resultado.get_by_text(config.UI_TEXTO_TOTAL, exact=False).first
                            txt_tot = total_el.evaluate("el => el.closest('div')?.innerText || el.parentElement?.innerText || ''")
                            m_tot = re.search(r"R?\$?\s*([\d.,]+)", txt_tot.replace(" ", ""))
                            if m_tot:
                                valor_total = m_tot.group(1).replace(".", "").replace(",", ".")
                        except Exception:
                            pass
                        linha_status = "sucesso"
                except Exception as e:
                    print(f"Erro simulação {label_tabela}: {e}")
                    erro_linha = str(e).replace("\n", " ").replace("\r", "")[:500]
                escrever_linha_saida(caminho_saida, [cliente.nome, cliente.cpf, cliente.contato, cliente.email, valor_maximo_parcela, qtd_parcelas, valor_liberado, valor_parcela, valor_total, linha_status, erro_linha])
            voltou_consulta = False
            for p in page.context.pages:
                try:
                    if "clt/consultar" in p.url:
                        p.bring_to_front()
                        voltou_consulta = True
                        break
                except Exception:
                    pass
            if not voltou_consulta:
                try:
                    page.context.pages[0].bring_to_front()
                    page.context.pages[0].goto(config.URL_ADMIN_BASE + "clt/consultar", wait_until="domcontentloaded")
                except Exception:
                    pass
        except BaseException as e:
            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                raise
            print(f"Erro ao processar cliente {cliente.cpf}: {e}")
            try:
                erro_msg = str(e).replace("\n", " ").replace("\r", "")[:500]
                escrever_linha_saida(caminho_saida, [cliente.nome, cliente.cpf, cliente.contato, cliente.email, "", "", "", "", "", "falha_historico", erro_msg])
            except Exception:
                pass
        voltar_para_consulta_limpa(page)



def executar_robo(caminho_entrada: str | None = None, dir_saida: str | None = None, headless: bool = False) -> None:
    if caminho_entrada is None:
        caminho_entrada = os.path.join(config.DIR_ENTRADA_PADRAO, config.ARQUIVO_ENTRADA_PADRAO)
    if dir_saida is None:
        dir_saida = config.DIR_SAIDA_PADRAO
    if not os.path.exists(caminho_entrada):
        raise FileNotFoundError(f"Arquivo de entrada não encontrado: {caminho_entrada}")

    clientes = ler_clientes(caminho_entrada)
    if not clientes:
        print("Nenhum cliente válido encontrado no CSV.")
        return

    caminho_saida = criar_caminho_csv_saida(dir_saida)
    escrever_cabecalho_saida(caminho_saida)
    print(f"CSV de saída: {caminho_saida}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=config.SLOW_MO_HEADED_MS if not headless else 0)
        context_opts = {"viewport": {"width": config.VIEWPORT_LARGURA, "height": config.VIEWPORT_ALTURA}}
        context = browser.new_context(**context_opts)
        context.grant_permissions(["geolocation"])
        page = context.new_page()

        page.set_default_timeout(15000)
        page.set_default_navigation_timeout(30000)


        try:
            login_e_ir_para_consulta(page)
            processar_clientes(page, clientes, caminho_saida)
        except Exception as e:
            if "TargetClosedError" in type(e).__name__:
                print("O navegador foi fechado durante a execução. Não feche a janela manualmente; confira o .env (ADMIN_EMAIL e ADMIN_SENHA) e tente de novo.")
            raise
        finally:
            browser.close()