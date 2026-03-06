from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import List

import pandas as pd

import config
from robo.passivos.cpf_utils import normalizar_cpf
from robo.passivos.modelos import Cliente


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


def log_critico(lista_saida: list, cliente: Cliente, banco: str, status: str, erro: str) -> None:
    print(f"[{status}] CPF={cliente.cpf} BANCO={banco} ERRO={erro}")
    lista_saida.append({
        "nome": cliente.nome, "cpf": cliente.cpf, "contato": cliente.contato, "email": cliente.email,
        "banco": banco, "valor_maximo_parcela": "", "qtd_parcelas": "", "valor_liberado": "", "valor_parcela": "",
        "valor_total": "", "status": status, "erro": erro[:500], "tipo": "erro",
    })


def salvar_dataframe_final(caminho_saida: str, lista_saida: list) -> None:
    dir_saida = os.path.dirname(caminho_saida)
    if dir_saida:
        garantir_pasta_saida(dir_saida)
    parcelas = [r for r in lista_saida if r.get("tipo") != "erro" and str(r.get("qtd_parcelas", "")).strip() in ("6", "12", "18", "24")]
    erros = [r for r in lista_saida if r.get("tipo") == "erro"]
    linhas_agregadas: list[dict] = []
    contagem = {"6": 0, "12": 0, "18": 0, "24": 0}
    if parcelas:
        df_parc = pd.DataFrame(parcelas)
        for (nome, cpf, contato, email, banco, valor_max), grp in df_parc.groupby(["nome", "cpf", "contato", "email", "banco", "valor_maximo_parcela"]):
            row: dict = {"nome": nome, "cpf": cpf, "contato": contato, "email": email, "banco": banco, "valor_maximo_parcela": valor_max}
            for m in ("6", "12", "18", "24"):
                sub = grp[grp["qtd_parcelas"] == m]
                if not sub.empty:
                    s = sub.iloc[0]
                    row[f"valor_parcela_{m}m"] = s.get("valor_parcela", "")
                    row[f"valor_liberado_{m}m"] = s.get("valor_liberado", "")
                    row[f"valor_total_{m}m"] = s.get("valor_total", "")
                    row[f"status_{m}m"] = s.get("status", "")
                    contagem[m] += 1
                else:
                    row[f"valor_parcela_{m}m"] = row[f"valor_liberado_{m}m"] = row[f"valor_total_{m}m"] = row[f"status_{m}m"] = ""
            row["status"] = ""
            row["erro"] = ""
            linhas_agregadas.append(row)
    for r in erros:
        linhas_agregadas.append({
            "nome": r["nome"], "cpf": r["cpf"], "contato": r["contato"], "email": r["email"], "banco": r["banco"],
            "valor_maximo_parcela": "", "valor_parcela_6m": "", "valor_parcela_12m": "", "valor_parcela_18m": "", "valor_parcela_24m": "",
            "valor_liberado_6m": "", "valor_liberado_12m": "", "valor_liberado_18m": "", "valor_liberado_24m": "",
            "valor_total_6m": "", "valor_total_12m": "", "valor_total_18m": "", "valor_total_24m": "",
            "status_6m": "", "status_12m": "", "status_18m": "", "status_24m": "",
            "status": r["status"], "erro": r["erro"],
        })
    df_final = pd.DataFrame(linhas_agregadas, columns=config.CSV_COLUNAS_SAIDA_AGREGADO)
    df_final.to_csv(caminho_saida, sep=config.CSV_DELIMITER, index=False, encoding=config.CSV_ENCODING)
    print(f"Parcelas contabilizadas: 6m={contagem['6']} | 12m={contagem['12']} | 18m={contagem['18']} | 24m={contagem['24']}")


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
