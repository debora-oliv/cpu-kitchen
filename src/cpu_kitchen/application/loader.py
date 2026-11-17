"""Carregador e validador declarativo de cenários da cozinha."""

import json
from pathlib import Path
from typing import Any

from cpu_kitchen.domain.models import CenarioTurno, Pedido

CAMINHO_PADRAO_CENARIOS = Path(__file__).resolve().parents[3] / "data" / "cenarios.json"


class CenarioLoadError(Exception):
    """Exceção lançada quando o arquivo de cenários está ausente ou inválido."""


def carregar_cenarios(caminho: Path | str = CAMINHO_PADRAO_CENARIOS) -> list[CenarioTurno]:
    """Lê e valida a lista de cenários a partir de um arquivo JSON.

    Args:
        caminho: Caminho para o arquivo JSON de cenários.

    Returns:
        Lista ordenada de objetos CenarioTurno prontos para o motor.

    Raises:
        CenarioLoadError: Se o arquivo não existir, estiver corrompido ou violar regras.
    """
    arquivo = Path(caminho)
    if not arquivo.exists():
        raise CenarioLoadError(f"Arquivo de cenários não encontrado: {arquivo}")

    try:
        conteudo = json.loads(arquivo.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CenarioLoadError(f"JSON inválido em '{arquivo}': {exc}") from exc

    cenarios_brutos = conteudo.get("cenarios")
    if not isinstance(cenarios_brutos, list) or not cenarios_brutos:
        raise CenarioLoadError("O arquivo JSON deve conter uma lista não vazia em 'cenarios'.")

    ids_vistos: set[str] = set()
    cenarios_validados: list[CenarioTurno] = []

    for item in cenarios_brutos:
        cenario = _parse_cenario(item)
        if cenario.id in ids_vistos:
            raise CenarioLoadError(f"ID de cenário duplicado encontrado: '{cenario.id}'.")
        ids_vistos.add(cenario.id)
        cenarios_validados.append(cenario)

    return cenarios_validados


def _parse_cenario(dados: dict[str, Any]) -> CenarioTurno:
    """Converte e valida um dicionário bruto em uma instância de CenarioTurno.

    Args:
        dados: Dicionário extraído do array 'cenarios' no JSON.

    Returns:
        Instância validada de CenarioTurno.

    Raises:
        CenarioLoadError: Se campos obrigatórios estiverem ausentes ou incoerentes.
    """
    campos_obrigatorios = (
        "id",
        "titulo",
        "descricao",
        "quantum_padrao",
        "melhor_espera_media",
        "selo",
        "pedidos",
    )
    for campo in campos_obrigatorios:
        if campo not in dados:
            raise CenarioLoadError(f"Campo obrigatório '{campo}' ausente no cenário.")

    algoritmo_fixo = dados.get("algoritmo_fixo")
    if algoritmo_fixo is not None and algoritmo_fixo not in ("FCFS", "Round Robin"):
        raise CenarioLoadError(
            f"Algoritmo inválido '{algoritmo_fixo}' no cenário '{dados['id']}'."
        )

    quantum_padrao = int(dados["quantum_padrao"])
    if quantum_padrao < 1:
        raise CenarioLoadError(
            f"O 'quantum_padrao' deve ser >= 1 no cenário '{dados['id']}'."
        )

    melhor_espera = float(dados["melhor_espera_media"])
    if melhor_espera < 0:
        raise CenarioLoadError(
            f"A 'melhor_espera_media' não pode ser negativa no cenário '{dados['id']}'."
        )

    pedidos_brutos = dados["pedidos"]
    if not isinstance(pedidos_brutos, list) or not pedidos_brutos:
        raise CenarioLoadError(
            f"O cenário '{dados['id']}' deve possuir ao menos um pedido."
        )

    pedidos = [_parse_pedido(p, dados["id"]) for p in pedidos_brutos]

    return CenarioTurno(
        id=str(dados["id"]),
        titulo=str(dados["titulo"]),
        descricao=str(dados["descricao"]),
        algoritmo_fixo=algoritmo_fixo,
        quantum_padrao=quantum_padrao,
        melhor_espera_media=melhor_espera,
        selo=str(dados["selo"]),
        pedidos=pedidos,
    )


def _parse_pedido(dados: dict[str, Any], cenario_id: str) -> Pedido:
    """Converte e valida um item de pedido em um objeto Pedido do domínio.

    Args:
        dados: Dicionário com os atributos do pedido no JSON.
        cenario_id: Identificador do cenário pai para mensagens de erro claras.

    Returns:
        Instância de Pedido com tempo restante inicializado.

    Raises:
        CenarioLoadError: Se chegada < 0 ou burst <= 0.
    """
    for campo in ("id", "nome", "chegada", "burst", "cor"):
        if campo not in dados:
            raise CenarioLoadError(
                f"Campo '{campo}' ausente em pedido do cenário '{cenario_id}'."
            )

    chegada = int(dados["chegada"])
    burst = int(dados["burst"])

    if chegada < 0:
        raise CenarioLoadError(
            f"Pedido '{dados['id']}' no cenário '{cenario_id}' tem chegada negativa."
        )
    if burst < 1:
        raise CenarioLoadError(
            f"Pedido '{dados['id']}' no cenário '{cenario_id}' deve ter burst >= 1."
        )

    return Pedido(
        id=str(dados["id"]),
        nome=str(dados["nome"]),
        chegada=chegada,
        burst=burst,
        cor=str(dados["cor"]),
    )