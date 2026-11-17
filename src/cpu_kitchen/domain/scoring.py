"""Cálculo de eficiência, estrelas e selos de recompensa por turno."""

from cpu_kitchen.domain.models import AvaliacaoTurno, ResultadoTurno


def avaliar_turno(
    resultado: ResultadoTurno,
    melhor_espera_media: float,
    selo_turno: str,
) -> AvaliacaoTurno:
    """Calcula estrelas (1 a 3) e selo com base na eficiência da espera média.

    Args:
        resultado: Dados consolidados da execução do turno.
        melhor_espera_media: Tempo médio de espera ótimo definido no cenário.
        selo_turno: Título do selo concedido ao atingir 3 estrelas.

    Returns:
        Objeto AvaliacaoTurno com estrelas, eficiência percentual e selo.
    """
    total_pedidos = len(resultado.pedidos)
    if total_pedidos == 0:
        espera_media = 0.0
    else:
        espera_media = sum(p.espera for p in resultado.pedidos) / total_pedidos

    if espera_media <= 0.0:
        eficiencia = 1.0
    elif melhor_espera_media <= 0.0:
        eficiencia = 1.0 / (1.0 + espera_media)
    else:
        eficiencia = min(1.0, melhor_espera_media / espera_media)

    if eficiencia >= 0.90:
        estrelas_base = 3
    elif eficiencia >= 0.70:
        estrelas_base = 2
    elif eficiencia >= 0.50:
        estrelas_base = 1
    else:
        estrelas_base = 0

    estrelas_finais = max(0, estrelas_base - resultado.abandonos)
    selo_conquistado = selo_turno if estrelas_finais == 3 else None

    return AvaliacaoTurno(
        estrelas=estrelas_finais,
        eficiencia_percentual=round(eficiencia * 100, 1),
        espera_media=round(espera_media, 2),
        melhor_espera_media=round(melhor_espera_media, 2),
        selo_conquistado=selo_conquistado,
    )