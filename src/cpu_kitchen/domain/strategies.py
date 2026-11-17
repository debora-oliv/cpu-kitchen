"""Estratégias de escalonamento de CPU (FCFS e Round Robin)."""

from abc import ABC, abstractmethod

from cpu_kitchen.domain.models import Pedido


class EscalonadorStrategy(ABC):
    """Contrato base para políticas de escalonamento do chef."""

    @property
    @abstractmethod
    def nome(self) -> str:
        """Retorna o nome legível do algoritmo."""

    @property
    def quantum(self) -> int:
        """Retorna o quantum configurado (0 quando não aplicável)."""
        return 0

    @abstractmethod
    def deve_preemptar(self, quantum_usado: int, fila_prontos: list[Pedido]) -> bool:
        """Decide se o pedido atual deve liberar o fogão ao fim do tick.

        Args:
            quantum_usado: Ticks consecutivos já executados pelo pedido atual.
            fila_prontos: Pedidos atualmente aguardando na bancada.

        Returns:
            True se o pedido deve voltar para o fim da fila; False caso contrário.
        """


class FCFSStrategy(EscalonadorStrategy):
    """Política First-Come, First-Served (não-preemptiva)."""

    @property
    def nome(self) -> str:
        """Retorna o identificador do algoritmo FCFS."""
        return "FCFS"

    def deve_preemptar(self, quantum_usado: int, fila_prontos: list[Pedido]) -> bool:
        """Nunca interrompe um pedido antes de sua conclusão."""
        return False


class RoundRobinStrategy(EscalonadorStrategy):
    """Política Round Robin (preemptiva por fatia de tempo)."""

    def __init__(self, quantum: int) -> None:
        """Inicializa a estratégia Round Robin com um quantum fixo.

        Args:
            quantum: Número máximo de ticks consecutivos por pedido na CPU.

        Raises:
            ValueError: Se o quantum informado for menor que 1.
        """
        if quantum < 1:
            raise ValueError("O quantum deve ser maior ou igual a 1.")
        self._quantum = quantum

    @property
    def nome(self) -> str:
        """Retorna o identificador do algoritmo Round Robin."""
        return "Round Robin"

    @property
    def quantum(self) -> int:
        """Retorna o valor do quantum configurado."""
        return self._quantum

    def deve_preemptar(self, quantum_usado: int, fila_prontos: list[Pedido]) -> bool:
        """Preempta quando o quantum se esgota e existe outro pedido na bancada."""
        return quantum_usado >= self._quantum and len(fila_prontos) > 0


def criar_escalonador(algoritmo: str, quantum: int = 2) -> EscalonadorStrategy:
    """Instancia a estratégia de escalonamento a partir de seu nome.

    Args:
        algoritmo: Nome do algoritmo ('FCFS' ou 'Round Robin').
        quantum: Valor do quantum caso o algoritmo seja Round Robin.

    Returns:
        Instância concreta de EscalonadorStrategy.

    Raises:
        ValueError: Se o nome do algoritmo não for suportado.
    """
    normalizado = algoritmo.strip().upper()
    if normalizado == "FCFS":
        return FCFSStrategy()
    if normalizado in ("ROUND ROBIN", "RR"):
        return RoundRobinStrategy(quantum=quantum)
    raise ValueError(f"Algoritmo de escalonamento desconhecido: '{algoritmo}'.")