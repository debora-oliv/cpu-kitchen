"""Adaptador web whitebox em Streamlit para o protótipo CPU Kitchen."""

import streamlit as st

from cpu_kitchen.application import carregar_cenarios
from cpu_kitchen.domain import (
    CenarioTurno,
    CozinhaEngine,
    Pedido,
    avaliar_turno,
    criar_escalonador,
)

st.set_page_config(
    page_title="CPU Kitchen — Escalonamento de CPU",
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
    st.subheader("Planta da Cozinha (Estado Atual das Estações)")
    col_chegada, col_bancada, col_chef, col_saida = st.columns(4)

    with col_chegada:
        st.markdown("**1. Balcão de Chegada**")
        aguardando = [p for p in engine.pedidos if p.status == "AGUARDANDO"]
        if not aguardando:
            st.caption("Nenhum pedido pendente de chegada.")
        for p in aguardando:
            st.markdown(_renderizar_cartao_pedido(p), unsafe_allow_html=True)

    with col_bancada:
        st.markdown("**2. Bancada (Fila de Prontos)**")
        if not engine.fila_prontos:
            st.caption("Fila de prontos vazia.")
        for pos, p in enumerate(engine.fila_prontos, start=1):
            st.markdown(
                _renderizar_cartao_pedido(p, f" | Posição: <code>#{pos}</code>"),
                unsafe_allow_html=True,
            )

    with col_chef:
        st.markdown("**3. Chef / Fogão (CPU)**")
        if engine.pedido_atual and engine.estado_chef == "TROCANDO":
            st.markdown(
                '<div style="background-color: #9E9E9E; color: #FFFFFF; '
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
                '<div style="background-color: #E5E7EB; color: #374151; '
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
            st.caption("Nenhum pedido finalizado ainda.")
        for p in finalizados:
            tag = " | ✅ Servido" if p.status == "CONCLUIDO" else " | ❌ Abandonou"
            st.markdown(_renderizar_cartao_pedido(p, tag), unsafe_allow_html=True)


def renderizar_app() -> None:
    """Monta a interface principal do protótipo em Streamlit."""
    st.title("🍳 CPU Kitchen — Escalonamento FCFS e Round Robin")

    cenarios = carregar_cenarios()
    mapa_cenarios = {c.titulo: c for c in cenarios}

    # --- PAINEL SUPERIOR DE CONTROLE ---
    col_cfg, col_acoes = st.columns([2, 1])

    with col_cfg:
        titulo_escolhido = st.selectbox(
            "Etapa da Fase Única",
            options=list(mapa_cenarios.keys()),
        )
        cenario = mapa_cenarios[titulo_escolhido]
        st.caption(cenario.descricao)

        c_algo, c_quant = st.columns(2)
        with c_algo:
            if cenario.algoritmo_fixo:
                algoritmo = cenario.algoritmo_fixo
                st.info(f"**Algoritmo fixo:** {algoritmo}")
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
                st.caption("FCFS não utiliza preempção por quantum.")

    assinatura_atual = (cenario.id, algoritmo, quantum)
    if (
        "engine" not in st.session_state
        or st.session_state.get("assinatura_config") != assinatura_atual
    ):
        _inicializar_engine(cenario, algoritmo, quantum)

    engine: CozinhaEngine = st.session_state["engine"]

    with col_acoes:
        st.markdown("**Controles do Turno**")
        st.metric("Relógio da Cozinha", f"{engine.tempo}u")

        b1, b2 = st.columns(2)
        with b1:
            if st.button(
                "⏭ Avançar 1 Tick",
                disabled=not engine.tem_trabalho_pendente(),
                use_container_width=True,
            ):
                engine.tick()
                st.rerun()
        with b2:
            if st.button(
                "🔄 Reiniciar",
                use_container_width=True,
            ):
                _inicializar_engine(cenario, algoritmo, quantum)
                st.rerun()

        if st.button(
            "▶ Executar Turno Completo",
            type="primary",
            disabled=not engine.tem_trabalho_pendente(),
            use_container_width=True,
        ):
            engine.executar_completo()
            st.rerun()

    st.divider()
    _renderizar_estacoes_cozinha(engine)

    # --- GRÁFICO DE GANTT ---
    resultado = engine.gerar_resultado()
    if resultado.gantt:
        st.divider()
        st.subheader("Linha do Tempo da CPU / Chef (Gráfico de Gantt)")

        blocos = ['<div style="display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 8px;">']
        for slot in resultado.gantt:
            cor_texto = "#FFFFFF" if slot.tipo == "TROCA_PANELA" else "#111827"
            blocos.append(
                f'<div style="background-color: {slot.cor}; color: {cor_texto}; '
                f"padding: 8px 10px; border-radius: 4px; text-align: center; "
                f'min-width: 52px; font-weight: bold; border: 1px solid #94A3B8;">'
                f"{slot.label}<br>"
                f'<span style="font-size: 11px; font-weight: normal;">t={slot.tempo}</span>'
                f"</div>"
            )
        blocos.append("</div>")
        st.markdown("".join(blocos), unsafe_allow_html=True)
        st.caption(
            "Blocos coloridos = Pedido na CPU | Bloco cinza (Troca) = 1u parada para troca de panela."
        )

    # --- QUADRO DE RESULTADOS AO FINAL DO TURNO ---
    if not engine.tem_trabalho_pendente():
        avaliacao = avaliar_turno(
            resultado=resultado,
            melhor_espera_media=cenario.melhor_espera_media,
            selo_turno=cenario.selo,
        )

        st.divider()
        st.subheader("Quadro de Resultados do Turno")

        m1, m2, m3, m4 = st.columns(4)
        estrelas_visuais = "⭐" * avaliacao.estrelas if avaliacao.estrelas > 0 else "0 estrelas"
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
                "✅ Pedido entregue"
                if p.status == "CONCLUIDO"
                else "❌ Cliente foi embora (-1 ⭐)"
            )
            st.write(
                f"**{p.id} ({p.nome})** — Espera: `{p.espera}u / {p.limite_paciencia}u` — {status_legenda}"
            )
            st.progress(progresso)

        for dica in resultado.dicas:
            st.warning(f"💡 **Dica do Chef:** {dica}")


if __name__ == "__main__":
    renderizar_app()