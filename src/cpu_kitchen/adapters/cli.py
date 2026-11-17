"""Adaptador de linha de comando (CLI) para demonstração no terminal."""

from cpu_kitchen.application import carregar_cenarios
from cpu_kitchen.domain import (
    CenarioTurno,
    CozinhaEngine,
    ResultadoTurno,
    avaliar_turno,
    criar_escalonador,
)


def _selecionar_cenario(cenarios: list[CenarioTurno]) -> CenarioTurno:
    """Exibe o menu de etapas da fase única e retorna o cenário escolhido."""
    print("\n=== CPU KITCHEN — ESCALONAMENTO DE CPU (CONSOLE) ===")
    for idx, cenario in enumerate(cenarios, start=1):
        algo_info = cenario.algoritmo_fixo or "Livre (FCFS ou Round Robin)"
        print(f"  [{idx}] {cenario.titulo} | Algoritmo: {algo_info}")

    while True:
        escolha = input("\nEscolha o número da etapa: ").strip()
        if escolha.isdigit() and 1 <= int(escolha) <= len(cenarios):
            return cenarios[int(escolha) - 1]
        print("Opção inválida. Digite o número correspondente à etapa.")


def _configurar_escalonador(cenario: CenarioTurno) -> tuple[str, int]:
    """Define o algoritmo e o quantum com base nas travas do cenário."""
    if cenario.algoritmo_fixo:
        algoritmo = cenario.algoritmo_fixo
        print(f"\nAlgoritmo fixo desta etapa: {algoritmo}")
    else:
        print("\nEscolha o algoritmo para o Desafio Final:")
        print("  [1] FCFS (First-Come, First-Served)")
        print("  [2] Round Robin (Preemptivo por Quantum)")
        while True:
            opcao = input("Opção [1/2]: ").strip()
            if opcao == "1":
                algoritmo = "FCFS"
                break
            if opcao == "2":
                algoritmo = "Round Robin"
                break
            print("Digite 1 para FCFS ou 2 para Round Robin.")

    quantum = 0
    if algoritmo == "Round Robin":
        entrada_q = input(
            f"Informe o Quantum (Enter para padrão = {cenario.quantum_padrao}): "
        ).strip()
        if entrada_q.isdigit() and int(entrada_q) >= 1:
            quantum = int(entrada_q)
        else:
            quantum = cenario.quantum_padrao

    return algoritmo, quantum


def _renderizar_estado_cozinha(engine: CozinhaEngine) -> None:
    """Desenha no terminal o estado atual das estações da cozinha."""
    aguardando = [
        f"{p.id}(t={p.chegada})" for p in engine.pedidos if p.status == "AGUARDANDO"
    ]
    bancada = [
        f"{p.id}[rest:{p.restante}u | esp:{p.espera}/{p.limite_paciencia}u]"
        for p in engine.fila_prontos
    ]
    concluidos = [p.id for p in engine.pedidos if p.status == "CONCLUIDO"]
    abandonados = [p.id for p in engine.pedidos if p.status == "ABANDONADO"]

    if engine.pedido_atual and engine.estado_chef == "TROCANDO":
        status_fogao = f"TROCANDO PANELA -> {engine.pedido_atual.id} (Bloco Cinza)"
    elif engine.pedido_atual:
        status_fogao = (
            f"COZINHANDO {engine.pedido_atual.id} - {engine.pedido_atual.nome} "
            f"(restante: {engine.pedido_atual.restante}u)"
        )
    else:
        status_fogao = "OCIOSO (Aguardando pedidos)"

    print("-" * 72)
    print(f"RELÓGIO: t = {engine.tempo}u | ALGORITMO: {engine.escalonador.nome}")
    print(f"  1. Balcão (A chegar)   : {', '.join(aguardando) or 'Nenhum'}")
    print(f"  2. Bancada (Fila)      : {' -> '.join(bancada) or 'Vazia'}")
    print(f"  3. Chef / Fogão (CPU)  : {status_fogao}")
    print(f"  4. Entregues           : {', '.join(concluidos) or 'Nenhum'}")
    if abandonados:
        print(f"  !  Abandonos (-1 ★)    : {', '.join(abandonados)}")

    eventos_recentes = [e for e in engine.eventos if e.tempo == engine.tempo - 1]
    for ev in eventos_recentes:
        print(f"     -> [{ev.tipo}] {ev.mensagem}")


def _exibir_relatorio_final(
    cenario: CenarioTurno,
    resultado: ResultadoTurno,
) -> None:
    """Imprime o Gráfico de Gantt textual, métricas, estrelas e dicas."""
    avaliacao = avaliar_turno(
        resultado=resultado,
        melhor_espera_media=cenario.melhor_espera_media,
        selo_turno=cenario.selo,
    )

    print("\n" + "=" * 72)
    print(f"QUADRO DE RESULTADOS — {cenario.titulo}")
    print("=" * 72)

    linha_gantt = " ".join(f"[{slot.label}]" for slot in resultado.gantt)
    print(f"\nGráfico de Gantt ({resultado.tempo_total}u totais):")
    print(f"  {linha_gantt}")

    estrelas_str = "★" * avaliacao.estrelas + "☆" * (3 - avaliacao.estrelas)
    print(f"\nDesempenho:")
    print(f"  Estrelas         : {estrelas_str} ({avaliacao.estrelas}/3)")
    print(f"  Eficiência       : {avaliacao.eficiencia_percentual:.1f}%")
    print(
        f"  Espera Média     : {avaliacao.espera_media:.2f}u "
        f"(Ideal: {avaliacao.melhor_espera_media:.2f}u)"
    )
    print(f"  Trocas de Panela : {resultado.trocas_panela}u")
    print(f"  Abandonos        : {resultado.abandonos}")

    if avaliacao.selo_conquistado:
        print(f"\n  [SELO DESBLOQUEADO]: {avaliacao.selo_conquistado}")

    print("\nDetalhamento por Pedido:")
    for p in resultado.pedidos:
        print(
            f"  - {p.id} ({p.nome}): Status={p.status} | "
            f"Espera={p.espera}u / Paciência={p.limite_paciencia}u"
        )

    if resultado.dicas:
        print("\nDicas do Chef:")
        for dica in resultado.dicas:
            print(f"  * {dica}")
    print("=" * 72 + "\n")


def executar_cli() -> None:
    """Ponto de entrada principal da interface de terminal."""
    cenarios = carregar_cenarios()
    cenario = _selecionar_cenario(cenarios)
    print(f"\nObjetivo: {cenario.descricao}")

    algoritmo, quantum = _configurar_escalonador(cenario)
    escalonador = criar_escalonador(algoritmo=algoritmo, quantum=quantum)
    engine = CozinhaEngine(pedidos=cenario.pedidos, escalonador=escalonador)

    modo = input("\nModo: [1] Completo instantâneo | [2] Passo a passo (tick): ").strip()
    if modo == "2":
        print("\nPressione ENTER para avançar 1 unidade de tempo (ou 'q' para concluir direto).")
        while engine.tem_trabalho_pendente():
            _renderizar_estado_cozinha(engine)
            comando = input("Avançar tick > ").strip().lower()
            if comando == "q":
                engine.executar_completo()
                break
            engine.tick()
        _renderizar_estado_cozinha(engine)
        resultado = engine.gerar_resultado()
    else:
        resultado = engine.executar_completo()

    _exibir_relatorio_final(cenario=cenario, resultado=resultado)


if __name__ == "__main__":
    executar_cli()