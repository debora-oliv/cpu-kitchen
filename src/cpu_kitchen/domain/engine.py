"""Motor de simulação determinístico tick-a-tick da cozinha."""

import copy
from typing import Literal

from cpu_kitchen.domain.models import (
    EventoTurno,
    Pedido,
    ResultadoTurno,
    SlotGantt,
)
from cpu_kitchen.domain.strategies import EscalonadorStrategy

EstadoChef = Literal["OCIOSO", "TROCANDO", "COZINHANDO"]

COR_TROCA_PANELA = "#9E9E9E"
COR_OCIOSO = "#E5E7EB"


class CozinhaEngine:
    """Simula a execução de pedidos na CPU/chef unidade por unidade de tempo."""

    def __init__(self, pedidos: list[Pedido], escalonador: EscalonadorStrategy) -> None:
        """Inicializa o motor com uma cópia isolada dos pedidos do cenário.

        Args:
            pedidos: Lista de pedidos configurados para o turno.
            escalonador: Estratégia que dita a preempção do chef.
        """
        self.pedidos: list[Pedido] = copy.deepcopy(pedidos)
        self.escalonador: EscalonadorStrategy = escalonador

        self.tempo: int = 0
        self.fila_prontos: list[Pedido] = []
        self.pedido_atual: Pedido | None = None
        self.ultimo_id_cozinhado: str | None = None
        self.estado_chef: EstadoChef = "OCIOSO"
        self.quantum_usado: int = 0

        self.gantt: list[SlotGantt] = []
        self.eventos: list[EventoTurno] = []
        self.trocas_panela: int = 0
        self.abandonos: int = 0
        self._dicas: list[str] = []

    def tem_trabalho_pendente(self) -> bool:
        """Verifica se ainda há pedidos aguardando chegada, na fila ou no fogão."""
        return any(
            p.status in ("AGUARDANDO", "NA_FILA", "COZINHANDO") for p in self.pedidos
        )

    def tick(self) -> bool:
        """Avança a simulação em exatamente 1 unidade de tempo.

        Returns:
            True se ainda restar trabalho pendente após este tick; False se encerrou.
        """
        if not self.tem_trabalho_pendente():
            return False

        self._processar_chegadas()

        if self.estado_chef == "OCIOSO":
            if not self._alocar_proximo_pedido():
                self.gantt.append(
                    SlotGantt(
                        tempo=self.tempo,
                        tipo="OCIOSO",
                        label="Livre",
                        cor=COR_OCIOSO,
                    )
                )
                self.tempo += 1
                return self.tem_trabalho_pendente()

        if self.estado_chef == "TROCANDO":
            self._executar_troca_panela()
            self._verificar_paciencia_fila()
        elif self.estado_chef == "COZINHANDO":
            self._executar_cozimento()
            self._verificar_paciencia_fila()
            self._avaliar_fim_do_tick_cozimento()

        self.tempo += 1

        if not self.tem_trabalho_pendente():
            self._avaliar_dicas_gerais()
            return False

        return True

    def executar_completo(self, limite_ticks: int = 500) -> ResultadoTurno:
        """Executa todos os ticks até a conclusão do turno.

        Args:
            limite_ticks: Trava de segurança contra loops infinitos.

        Returns:
            Objeto ResultadoTurno com métricas, Gantt, eventos e dicas.
        """
        while self.tem_trabalho_pendente() and self.tempo < limite_ticks:
            self.tick()
        return self.gerar_resultado()

    def gerar_resultado(self) -> ResultadoTurno:
        """Consolida o estado atual da simulação em um ResultadoTurno."""
        dicas_unicas = list(dict.fromkeys(self._dicas))
        return ResultadoTurno(
            algoritmo=self.escalonador.nome,
            quantum=self.escalonador.quantum,
            pedidos=copy.deepcopy(self.pedidos),
            gantt=list(self.gantt),
            eventos=list(self.eventos),
            tempo_total=self.tempo,
            trocas_panela=self.trocas_panela,
            abandonos=self.abandonos,
            dicas=dicas_unicas,
        )

    def _processar_chegadas(self) -> None:
        """Move pedidos cujo tempo de chegada bate com o relógio para a bancada."""
        for pedido in self.pedidos:
            if pedido.chegada == self.tempo and pedido.status == "AGUARDANDO":
                pedido.status = "NA_FILA"
                self.fila_prontos.append(pedido)
                self.eventos.append(
                    EventoTurno(
                        tempo=self.tempo,
                        tipo="CHEGADA",
                        mensagem=f"{pedido.id} ({pedido.nome}) chegou na bancada.",
                        pedido_id=pedido.id,
                    )
                )

    def _alocar_proximo_pedido(self) -> bool:
        """Retira o próximo pedido da fila e define se haverá troca de panela."""
        if not self.fila_prontos:
            return False

        proximo = self.fila_prontos.pop(0)
        proximo.status = "COZINHANDO"
        self.pedido_atual = proximo
        self.quantum_usado = 0

        trocou_pedido = (
            self.ultimo_id_cozinhado is not None
            and self.ultimo_id_cozinhado != proximo.id
        )
        if trocou_pedido:
            self.estado_chef = "TROCANDO"
            self.eventos.append(
                EventoTurno(
                    tempo=self.tempo,
                    tipo="TROCA_PANELA",
                    mensagem=f"Chef trocando panela para preparar {proximo.id} (-1u).",
                    pedido_id=proximo.id,
                )
            )
        else:
            self.estado_chef = "COZINHANDO"

        return True

    def _executar_troca_panela(self) -> None:
        """Consome 1 unidade de tempo preparando o fogão para um novo pedido."""
        self.trocas_panela += 1
        self.gantt.append(
            SlotGantt(
                tempo=self.tempo,
                tipo="TROCA_PANELA",
                label="Troca",
                cor=COR_TROCA_PANELA,
            )
        )
        for pedido in self.fila_prontos:
            pedido.espera += 1

        if self.pedido_atual is not None:
            self.pedido_atual.espera += 1

        self.estado_chef = "COZINHANDO"

    def _executar_cozimento(self) -> None:
        """Processa 1 unidade de tempo do pedido ativo na CPU."""
        if self.pedido_atual is None:
            return

        self.gantt.append(
            SlotGantt(
                tempo=self.tempo,
                tipo="PEDIDO",
                label=self.pedido_atual.id,
                cor=self.pedido_atual.cor,
                pedido_id=self.pedido_atual.id,
            )
        )
        self.pedido_atual.restante -= 1
        self.quantum_usado += 1
        self.ultimo_id_cozinhado = self.pedido_atual.id

        for pedido in self.fila_prontos:
            pedido.espera += 1

    def _verificar_paciencia_fila(self) -> None:
        """Remove da bancada clientes cuja espera ultrapassou o limite."""
        for pedido in list(self.fila_prontos):
            if pedido.espera > pedido.limite_paciencia:
                pedido.status = "ABANDONADO"
                self.fila_prontos.remove(pedido)
                self.abandonos += 1
                self.eventos.append(
                    EventoTurno(
                        tempo=self.tempo,
                        tipo="ABANDONO",
                        mensagem=(
                            f"{pedido.id} ({pedido.nome}) foi embora após esperar "
                            f"{pedido.espera}u (limite: {pedido.limite_paciencia}u)."
                        ),
                        pedido_id=pedido.id,
                    )
                )
                self._registrar_dica_abandono(pedido)

    def _avaliar_fim_do_tick_cozimento(self) -> None:
        """Verifica conclusão do pedido ou preempção ao término do tick."""
        if self.pedido_atual is None:
            return

        if self.pedido_atual.restante == 0:
            self.pedido_atual.status = "CONCLUIDO"
            self.pedido_atual.tempo_conclusao = self.tempo + 1
            self.eventos.append(
                EventoTurno(
                    tempo=self.tempo,
                    tipo="CONCLUSAO",
                    mensagem=f"{self.pedido_atual.id} ({self.pedido_atual.nome}) concluído!",
                    pedido_id=self.pedido_atual.id,
                )
            )
            self.pedido_atual = None
            self.estado_chef = "OCIOSO"
        elif self.escalonador.deve_preemptar(self.quantum_usado, self.fila_prontos):
            self.pedido_atual.status = "NA_FILA"
            self.fila_prontos.append(self.pedido_atual)
            self.eventos.append(
                EventoTurno(
                    tempo=self.tempo,
                    tipo="PREEMPCAO",
                    mensagem=(
                        f"Quantum ({self.escalonador.quantum}u) esgotado: "
                        f"{self.pedido_atual.id} voltou para o fim da bancada."
                    ),
                    pedido_id=self.pedido_atual.id,
                )
            )
            self.pedido_atual = None
            self.estado_chef = "OCIOSO"

    def _registrar_dica_abandono(self, pedido: Pedido) -> None:
        """Adiciona explicação pedagógica sobre o motivo do abandono."""
        if self.escalonador.nome == "FCFS":
            self._dicas.append(
                f"{pedido.id} ({pedido.nome}) desistiu da fila! No FCFS, pedidos longos "
                f"chegando primeiro bloqueiam pedidos curtos (Efeito Comboio), "
                f"estourando a paciência ({pedido.limite_paciencia}u)."
            )
        else:
            self._dicas.append(
                f"{pedido.id} ({pedido.nome}) desistiu da fila! Com quantum = "
                f"{self.escalonador.quantum}u, o tempo gasto em trocas de panela ou "
                f"a espera entre rodadas excedeu a paciência ({pedido.limite_paciencia}u)."
            )

    def _avaliar_dicas_gerais(self) -> None:
        """Gera dicas sobre sobrecarga de troca de contexto ao fim do turno."""
        if (
            self.escalonador.nome == "Round Robin"
            and self.trocas_panela >= len(self.pedidos)
            and self.escalonador.quantum == 1
        ):
            self._dicas.append(
                f"Quantum muito pequeno (1u) gerou {self.trocas_panela}u paradas em "
                f"troca de panela. Aumentar o quantum reduz o desperdício de troca de contexto."
            )