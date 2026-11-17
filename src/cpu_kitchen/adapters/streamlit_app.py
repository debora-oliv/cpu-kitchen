"""Adaptador web whitebox em Streamlit para o protótipo CPU Kitchen."""

import streamlit as st

from cpu_kitchen.application import carregar_cenarios
from cpu_kitchen.domain import (
    CenarioTurno,
    CozinhaEngine,
    Pedido,
    SlotGantt,
    avaliar_turno,
    criar_escalonador,
)

st.set_page_config(
    page_title="CPU Kitchen",
    page_icon="🍳",
    layout="wide",
)


def _inicializar_engine(
    cenario: CenarioTurno,
    algoritmo: str,
    quantum: int,
) -> CozinhaEngine:
    """Cria uma nova instância do motor e salva no estado da sessão."""
    escalonador = criar_escalonador(algoritmo=algoritmo, quantum=quantum)
    engine = CozinhaEngine(pedidos=cenario.pedidos, escalonador=escalonador)
    st.session_state["engine"] = engine
    st.session_state["assinatura_config"] = (cenario.id, algoritmo, quantum)
    return engine


def _retroceder_um_tick(
    cenario: CenarioTurno,
    algoritmo: str,
    quantum: int,
    tempo_atual: int,
) -> CozinhaEngine:
    """Reconstrói deterministicamente o estado da cozinha em (tempo_atual - 1)."""
    novo_engine = _inicializar_engine(cenario, algoritmo, quantum)
    tempo_alvo = max(0, tempo_atual - 1)
    for _ in range(tempo_alvo):
        if not novo_engine.tem_trabalho_pendente():
            break
        novo_engine.tick()
    return novo_engine


def _unificar_slots_gantt(gantt: list[SlotGantt]) -> list[dict]:
    """Unifica slots consecutivos de mesma cor, rótulo e tipo em blocos contínuos."""
    blocos_unificados: list[dict] = []
    for slot in gantt:
        if (
            blocos_unificados
            and blocos_unificados[-1]["cor"] == slot.cor
            and blocos_unificados[-1]["label"] == slot.label
            and blocos_unificados[-1]["tipo"] == slot.tipo
        ):
            blocos_unificados[-1]["fim"] = slot.tempo + 1
            blocos_unificados[-1]["duracao"] += 1
        else:
            blocos_unificados.append(
                {
                    "tipo": slot.tipo,
                    "label": slot.label,
                    "cor": slot.cor,
                    "inicio": slot.tempo,
                    "fim": slot.tempo + 1,
                    "duracao": 1,
                }
            )
    return blocos_unificados


def _renderizar_cartao_pedido(pedido: Pedido, detalhe_extra: str = "") -> str:
    """Gera o HTML de um card colorido preservando a identidade visual do processo."""
    return (
        f'<div style="border-left: 6px solid {pedido.cor}; '
        f"background-color: #F8FAFC; color: #0F172A; "
        f'padding: 8px 10px; border-radius: 6px; margin-bottom: 6px; '
        f'border: 1px solid #CBD5E1; border-left-width: 6px;">'
        f"<strong>{pedido.id} — {pedido.nome}</strong><br>"
        f'<span style="font-size: 12px;">'
        f"Chegada: <code>{pedido.chegada}u</code> | "
        f"Restante: <code>{pedido.restante}/{pedido.burst}u</code> | "
        f"Espera: <code>{pedido.espera}/{pedido.limite_paciencia}u</code>"
        f"{detalhe_extra}</span></div>"
    )


def _renderizar_estacoes_cozinha(engine: CozinhaEngine) -> None:
    """Exibe a planta conceitual da cozinha em 4 estações sincronizadas."""
    st.subheader("Estado Atual das Estações")
    col_chegada, col_bancada, col_chef, col_saida = st.columns(4)

    with col_chegada:
        st.markdown("**1. Balcão de Chegada**")
        aguardando = [p for p in engine.pedidos if p.status == "AGUARDANDO"]
        if not aguardando:
            st.markdown(
                '<div style="background-color: #634f46; color: #cccccc; '
                'padding: 14px; border-radius: 6px; text-align: center;">'
                "Nenhum pedido pendente</div>",
                unsafe_allow_html=True,
            )
        for p in aguardando:
            st.markdown(_renderizar_cartao_pedido(p), unsafe_allow_html=True)

    with col_bancada:
        st.markdown("**2. Bancada / Fila de Prontos**")
        if not engine.fila_prontos:
            st.markdown(
                '<div style="background-color: #695945; color: #cccccc; '
                'padding: 14px; border-radius: 6px; text-align: center;">'
                "Bancada vazia</div>",
                unsafe_allow_html=True,
            )
        for pos, p in enumerate(engine.fila_prontos, start=1):
            st.markdown(
                _renderizar_cartao_pedido(p, f" | Posição: <code>#{pos}</code>"),
                unsafe_allow_html=True,
            )

    with col_chef:
        st.markdown("**3. Chef / CPU**")
        if engine.pedido_atual and engine.estado_chef == "TROCANDO":
            st.markdown(
                '<div style="background-color: #9E9E9E; color: #cccccc; '
                'padding: 14px; border-radius: 6px; font-weight: bold; text-align: center;">'
                f"🔄 TROCANDO PANELA (-1u)<br>"
                f'<span style="font-size: 12px; font-weight: normal;">'
                f"Preparando fogão para {engine.pedido_atual.id}</span></div>",
                unsafe_allow_html=True,
            )
        elif engine.pedido_atual:
            st.markdown(
                _renderizar_cartao_pedido(
                    engine.pedido_atual,
                    f" | Quantum usado: <code>{engine.quantum_usado}u</code>",
                ),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="background-color: #52585E; color: #cccccc; '
                'padding: 14px; border-radius: 6px; text-align: center;">'
                "Chef Ocioso</div>",
                unsafe_allow_html=True,
            )

    with col_saida:
        st.markdown("**4. Entrega / Saída**")
        finalizados = [
            p for p in engine.pedidos if p.status in ("CONCLUIDO", "ABANDONADO")
        ]
        if not finalizados:
            st.markdown(
                '<div style="background-color: #47523f; color: #cccccc; '
                'padding: 14px; border-radius: 6px; text-align: center;">'
                "Nenhum pedido finalizado</div>",
                unsafe_allow_html=True,
            )
        for p in finalizados:
            tag = " | ✅ Servido" if p.status == "CONCLUIDO" else " | ❌ Abandonado"
            st.markdown(_renderizar_cartao_pedido(p, tag), unsafe_allow_html=True)


def renderizar_app() -> None:
    """Monta a interface principal do protótipo em Streamlit."""
    st.title("🍳 CPU Kitchen")

    cenarios = carregar_cenarios()
    mapa_cenarios = {c.titulo: c for c in cenarios}

    # --- SELETOR DE FASES EM LARGURA TOTAL ---
    titulo_escolhido = st.selectbox(
        "Fases Disponíveis:",
        options=list(mapa_cenarios.keys()),
    )
    cenario = mapa_cenarios[titulo_escolhido]
    st.caption(cenario.descricao)

    c_algo, c_quant = st.columns(2)
    with c_algo:
        if cenario.algoritmo_fixo:
            algoritmo = cenario.algoritmo_fixo
        else:
            algoritmo = st.radio(
                "Algoritmo de Escalonamento",
                options=["FCFS", "Round Robin"],
                horizontal=True,
            )

    with c_quant:
        if algoritmo == "Round Robin":
            quantum = st.slider(
                "Quantum (unidades de tempo)",
                min_value=1,
                max_value=6,
                value=cenario.quantum_padrao,
            )
        else:
            quantum = 0

    assinatura_atual = (cenario.id, algoritmo, quantum)
    if (
        "engine" not in st.session_state
        or st.session_state.get("assinatura_config") != assinatura_atual
    ):
        _inicializar_engine(cenario, algoritmo, quantum)

    engine: CozinhaEngine = st.session_state["engine"]

    # --- ESTAÇÕES DA COZINHA ---
    st.divider()
    _renderizar_estacoes_cozinha(engine)

    # --- RELÓGIO E CONTROLES ABAIXO DAS ESTAÇÕES ---
    st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
    col_relogio, col_retornar, col_avancar, col_reiniciar, col_completo = st.columns(
        [1.2, 1, 1, 1, 1.5],
        vertical_alignment="center",
    )

    with col_relogio:
        st.metric("**Relógio da Cozinha**", f"{engine.tempo}u")

    with col_retornar:
        if st.button(
            "<",
            disabled=engine.tempo == 0,
            use_container_width=True,
        ):
            _retroceder_um_tick(cenario, algoritmo, quantum, engine.tempo)
            st.rerun()

    with col_avancar:
        if st.button(
            ">",
            disabled=not engine.tem_trabalho_pendente(),
            use_container_width=True,
        ):
            engine.tick()
            st.rerun()

    with col_reiniciar:
        if st.button(
            "⟳",
            disabled=engine.tempo == 0,
            use_container_width=True,
        ):
            _inicializar_engine(cenario, algoritmo, quantum)
            st.rerun()

    with col_completo:
        if st.button(
            "▶ Executar Turno Completo",
            type="primary",
            disabled=not engine.tem_trabalho_pendente(),
            use_container_width=True,
        ):
            engine.executar_completo()
            st.rerun()

    resultado = engine.gerar_resultado()
    if resultado.gantt:

        blocos_unificados = _unificar_slots_gantt(resultado.gantt)
        blocos_html = [
            '<div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px;">'
        ]
        for bloco in blocos_unificados:
            cor_texto = "#FFFFFF" if bloco["tipo"] == "TROCA_PANELA" else "#111827"
            largura_min = max(64, bloco["duracao"] * 56)
            intervalo_txt = f"{bloco['inicio']}u → {bloco['fim']}u ({bloco['duracao']}u)"
            blocos_html.append(
                f'<div style="background-color: {bloco["cor"]}; color: {cor_texto}; '
                f"padding: 8px 12px; border-radius: 6px; text-align: center; "
                f"flex: {bloco['duracao']} 1 {largura_min}px; "
                f'font-weight: bold; border: 1px solid #94A3B8;">'
                f"{bloco['label']}<br>"
                f'<span style="font-size: 11px; font-weight: normal;">{intervalo_txt}</span>'
                f"</div>"
            )
        blocos_html.append("</div>")
        st.markdown("".join(blocos_html), unsafe_allow_html=True)

    if not engine.tem_trabalho_pendente():
        avaliacao = avaliar_turno(
            resultado=resultado,
            melhor_espera_media=cenario.melhor_espera_media,
            selo_turno=cenario.selo,
        )

        st.divider()
        st.subheader("Resultados do Turno")

        m1, m2, m3, m4 = st.columns(4)
        estrelas_visuais = (
            "⭐" * avaliacao.estrelas if avaliacao.estrelas > 0 else "0 estrelas"
        )
        m1.metric("Estrelas", estrelas_visuais)
        m2.metric("Eficiência", f"{avaliacao.eficiencia_percentual:.0f}%")
        m3.metric(
            "Espera Média",
            f"{avaliacao.espera_media:.2f}u",
            delta=f"Ideal: {avaliacao.melhor_espera_media:.2f}u",
            delta_color="off",
        )
        m4.metric("Trocas de Panela", f"{resultado.trocas_panela}u")

        if avaliacao.selo_conquistado:
            st.success(f"🏅 **Selo Conquistado:** {avaliacao.selo_conquistado}")

        st.markdown("**Paciência dos Clientes (Espera vs. Limite 2x Preparo):**")
        for p in resultado.pedidos:
            progresso = min(p.espera / p.limite_paciencia, 1.0)
            status_legenda = (
                "✅ Cliente satisfeito"
                if p.status == "CONCLUIDO"
                else "❌ Cliente foi embora"
            )
            st.write(
                f"**{p.id} ({p.nome})** — Espera: `{p.espera}u / {p.limite_paciencia}u` — {status_legenda}"
            )
            st.progress(progresso)

        for dica in resultado.dicas:
            st.warning(f"💡 **Dica do Chef:** {dica}")


if __name__ == "__main__":
    renderizar_app()