from __future__ import annotations

from dataclasses import dataclass


class TermoRequisicaoMalFormatada(Exception):
    pass


@dataclass
class Cliente:
    nome: str
    cpf: str
    contato: str
    email: str
