from __future__ import annotations

import re


def normalizar_cpf(cpf: str) -> str:
    digitos = "".join(ch for ch in cpf if ch.isdigit())
    return digitos


def cpf_digits(cpf: str) -> str:
    return re.sub(r"\D", "", cpf or "")


def cpf_valido_11(cpf: str) -> bool:
    return len(cpf_digits(cpf)) == 11


def cpf_com_mascara(cpf: str) -> str:
    cpf = re.sub(r'\D', '', cpf)
    if len(cpf) != 11:
        return cpf
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
