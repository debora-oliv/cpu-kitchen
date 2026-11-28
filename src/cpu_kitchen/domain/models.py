"""Modelos de domínio para a simulação de escalonamento de CPU na cozinha."""

from dataclasses import dataclass, field
from typing import Literal

StatusPedido = Literal[
    "AGUARDANDO",
    "NA_FILA",
    "COZINHANDO",
    "CONCLUIDO",
    "ABANDONADO",
]

TipoSlotGantt = Literal["PEDIDO", "TROCA_PANELA", "OCIOSO"]


@dataclass
class Pedido:
    """Representa um processo (PCB) na bancada da cozinha.

    Attributes:
        id: Identificador curto do pedido (ex: 'P1').
        nome: Nome legível do prato para exibição.
        chegada: Instante (tick) em que o pedido chega ao balcão.
        burst: Tempo total de preparo necessário na CPU/chef.
        cor: Código hexadecimal da cor associada ao pedido.
        restante: Unidades de tempo de preparo que ainda faltam.
        espera: Tempo acumulado aguardando na fila de prontos.
        tempo_conclusao: Instante em que o pedido foi finalizado, se concluído.
        status: Estado atual do pedido no ciclo de vida da cozinha.
    """

    id: str
    nome: str
    chegada: int
    burst: int
    cor: str
    restante: int = field(init=False)
    espera: int = 0
    tempo_conclusao: int | None = None
    status: StatusPedido = "AGUARDANDO"

    def __post_init__(self) -> None:
        """Inicializa o tempo restante com o tempo total de burst."""
        self.restante = self.burst

    @property
    def limite_paciencia(self) -> int:
        """Calcula o limite determinístico de espera (2x o tempo de preparo)."""
        return 2 * self.burst

    @property
    def paciencia_restante(self) -> int:
        """Retorna quantas unidades de tempo restam antes do cliente desistir."""
        return max(0, self.limite_paciencia - self.espera)


@dataclass(frozen=True)
class SlotGantt:
    """Representa uma unidade de tempo na linha do tempo da CPU/chef.

    Attributes:
        tempo: Instante da simulação correspondente ao bloco.
        tipo: Categoria do slot ('PEDIDO', 'TROCA_PANELA' ou 'OCIOSO').
        label: Rótulo curto exibido dentro do bloco.
        cor: Cor de fundo do bloco no diagrama.
        pedido_id: ID do pedido em execução, quando aplicável.
    """

    tempo: int
    tipo: TipoSlotGantt
    label: str
    cor: str
    pedido_id: str | None = None


@dataclass(frozen=True)
class EventoTurno:
    """Registra um acontecimento relevante em um tick específico.

    Attributes:
        tempo: Instante em que o evento ocorreu.
        tipo: Código do evento (CHEGADA, TROCA_PANELA, PREEMPCAO, CONCLUSAO, ABANDONO).
        mensagem: Descrição legível do evento para logs ou narração.
        pedido_id: Identificador do pedido relacionado ao evento, se houver.
    """

    tempo: int
    tipo: str
    mensagem: str
    pedido_id: str | None = None


@dataclass(frozen=True)
class CenarioTurno:
    """Configuração determinística de uma etapa da fase única.

    Attributes:
        id: Identificador único da etapa.
        titulo: Nome da etapa exibido ao jogador.
        descricao: Objetivo pedagógico da etapa.
        algoritmo_fixo: Nome do algoritmo travado ('FCFS', 'Round Robin') ou None se livre.
        quantum_padrao: Valor inicial sugerido para o quantum.
        melhor_espera_media: Referência ótima de espera média para cálculo de eficiência.
        selo: Nome do selo único desbloqueado ao atingir 3 estrelas.
        pedidos: Lista base de pedidos da etapa.
    """

    id: str
    titulo: str
    descricao: str
    algoritmo_fixo: str | None
    quantum_padrao: int
    melhor_espera_media: float
    selo: str
    pedidos: list[Pedido]


@dataclass(frozen=True)
class ResultadoTurno:
    """Consolida os dados produzidos após a execução de um turno.

    Attributes:
        algoritmo: Nome da política de escalonamento utilizada.
        quantum: Valor de quantum configurado (0 para algoritmos não-preemptivos).
        pedidos: Estado final de todos os pedidos do turno.
        gantt: Sequência cronológica de blocos executados pela CPU.
        eventos: Histórico detalhado de eventos ocorridos tick a tick.
        tempo_total: Duração total da simulação em unidades de tempo.
        trocas_panela: Total de unidades de tempo gastas em troca de contexto.
        abandonos: Quantidade de clientes que foram embora por excesso de espera.
        dicas: Orientações pedagógicas geradas a partir dos erros do turno.
    """

    algoritmo: str
    quantum: int
    pedidos: list[Pedido]
    gantt: list[SlotGantt]
    eventos: list[EventoTurno]
    tempo_total: int
    trocas_panela: int
    abandonos: int
    dicas: list[str]


@dataclass(frozen=True)
class AvaliacaoTurno:
    """Resultado da avaliação de desempenho e recompensas do jogador.

    Attributes:
        estrelas: Pontuação final de 0 a 3 estrelas.
        eficiencia_percentual: Razão percentual entre a espera ideal e a obtida.
        espera_media: Tempo médio de espera dos pedidos no turno.
        melhor_espera_media: Tempo médio de espera de referência do cenário.
        selo_conquistado: Nome do selo se atingiu 3 estrelas, ou None.
    """

    estrelas: int
    eficiencia_percentual: float
    espera_media: float
    melhor_espera_media: float
    selo_conquistado: str | None

# Adicionar ao final de src/cpu_kitchen/domain/models.py

def montar_pedidos_por_ordem(
    pedidos_padrao: list[Pedido],
    indices_escolhidos: list[int],
) -> list[Pedido]:
    """Cria a lista de pedidos na ordem escolhida mantendo os tempos de chegada do cenário.

    Se nenhum prato for escolhido, retorna a ordem padrão do cenário.
    O 1º escolhido vira P1 com a chegada do 1º slot, o 2º vira P2, e assim por diante.
    """
    if not indices_escolhidos:
        return list(pedidos_padrao)

    tempos_chegada = [p.chegada for p in pedidos_padrao]
    pedidos_ordenados: list[Pedido] = []

    for pos, idx_original in enumerate(indices_escolhidos):
        prato_base = pedidos_padrao[idx_original]
        pedidos_ordenados.append(
            Pedido(
                id=f"P{pos + 1}",
                nome=prato_base.nome,
                chegada=tempos_chegada[pos],
                burst=prato_base.burst,
                cor=prato_base.cor,
            )
        )

    return pedidos_ordenados