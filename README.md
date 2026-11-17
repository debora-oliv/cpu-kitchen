# 🍳 CPU Kitchen

Protótipo de software educacional gamificado para o ensino de **Escalonamento de CPU (FCFS e Round Robin)**. Inspirado na dinâmica de gestão de fluxo, o sistema traduz métricas de escalonamento de processos em decisões visuais e determinísticas dentro da cozinha de um restaurante.

O protótipo oferece duas interfaces desacopladas do núcleo de simulação: **execução passo a passo** (*tick a tick*), diretamente no terminal; e **interface web**, com visualização das estações da cozinha, barras de paciência em tempo real e Gráfico de Gantt colorido

---

### **Sobre o Projeto**

O **CPU Kitchen** permite observar, comparar e experimentar o comportamento de dois algoritmos clássicos de escalonamento de processos em um mesmo ambiente controlado:

- **FCFS (*First-Come, First-Served*):** Política não-preemptiva em que o chef prepara cada pedido integralmente na ordem de chegada, evidenciando o *Efeito Comboio* quando pratos demorados chegam antes de pedidos rápidos.
- **Round Robin (RR):** Política preemptiva baseada em fatia de tempo (*quantum*), permitindo ajustar o tamanho do *quantum* para equilibrar o tempo de resposta da fila e o custo de troca de contexto.

### **Mapeamento Conceitual**

| Conceito de Sistemas Operacionais | Representação no CPU Kitchen | Papel na Simulação |
| :--- | :--- | :--- |
| **CPU (Processador)** | **Chef / Fogão** | Executa apenas um pedido por unidade de tempo. |
| **Processo (PCB)** | **Pedido** | Possui identificador, cor própria, instante de chegada, *burst* e tempo restante. |
| **Fila de Prontos** | **Bancada de Espera** | Armazena os pedidos que já chegaram e aguardam atendimento. |
| **Quantum** | **Tempo de Fogão por Turno** | Limite máximo de unidades consecutivas antes da preempção no Round Robin. |
| **Troca de Contexto (*Context Switch*)** | **Troca de Panela** | Custo fixo de `1u` parada sempre que o chef alterna entre pedidos diferentes. |
| **Tempo de Espera / *Starvation*** | **Paciência do Cliente** | Limite determinístico de espera antes que o cliente desista do pedido. |

---

### **Mecânicas Pedagógicas**

O jogo utiliza três mecânicas determinísticas (sem sorteio aleatório) conectadas diretamente às métricas de escalonamento para permitir comparação justa entre tentativas:

**1. Paciência dos Clientes (`2 × burst`):**
   - Cada pedido tolera esperar na bancada até o dobro do seu tempo de preparo (`limite_paciencia = 2 * burst`).
   - Se a espera ultrapassar esse limite, o cliente vai embora, o restaurante perde **1 estrela** e o sistema exibe uma dica explicando o fenômeno ocorrido (sem encerrar o turno bruscamente).

**2. Custo Visível de Troca de Panela (`1u`):**
   - Sempre que o chef troca de pedido no fogão, a cozinha fica parada por **1 unidade de tempo**, exibida como um **bloco cinza (`#9E9E9E`)** no Gráfico de Gantt.
   - Enquanto a troca ocorre, os pedidos na bancada continuam acumulando espera, tornando concreto o dilema da escolha do *quantum*.

**3. Estrelas por Eficiência e Selo Único:**
   - A avaliação de `0` a `3` estrelas é calculada pela razão entre a espera média ideal do cenário e a espera média obtida pelo jogador:
     $$\text{Eficiência} = \min\left(100\%, \frac{\text{Melhor Espera Média}}{\text{Espera Média Obtida}}\right)$$
   - **Faixas de pontuação:** $\ge 90\%$ = `3 estrelas` | $\ge 70\%$ = `2 estrelas` | $\ge 50\%$ = `1 estrela` (descontando `1 estrela` por cada cliente que abandonou a fila).
   - Concluir um turno com **3 estrelas** desbloqueia o selo exclusivo daquela etapa.

### **Arquitetura do Projeto**

```text
cpu-kitchen/
├── data/
│   └── cenarios.json               # Definição determinística das 4 etapas da fase única
└── src/
    └── cpu_kitchen/
        ├── domain/                 # Regras puras de Sistemas Operacionais e simulação
        │   ├── models.py           # Entidades: Pedido, SlotGantt, EventoTurno, ResultadoTurno
        │   ├── strategies.py       # Padrão Strategy: FCFSStrategy e RoundRobinStrategy
        │   ├── engine.py           # CozinhaEngine: máquina de estados tick-a-tick
        │   └── scoring.py          # Cálculo de eficiência, estrelas (0–3) e selos
        ├── application/            # Casos de uso e leitura de dados
        │   └── loader.py           # Carregamento e validação de data/cenarios.json
        └── adapters/               # Interfaces de exibição intercambiáveis
            ├── cli.py              # Interface interativa para terminal (console)
            └── streamlit_app.py    # Interface web com Gantt e barras de paciência
```

O código segue os princípios da **Arquitetura Hexagonal (*Ports & Adapters*)** combinada com o **Padrão *Strategy*** e um **Motor de Simulação *Tick-a-Tick***:

- **`domain/`**: Implementado em Python puro, sem dependências de interface gráfica ou entrada/saída, permitindo evoluir a camada visual sem alterar as regras de escalonamento.
- **`strategies.py`**: `FCFSStrategy` e `RoundRobinStrategy` implementam o contrato `EscalonadorStrategy`, facilitando a adição futura de outros algoritmos (como SJF ou Prioridade).
- **`data/cenarios.json`**: Os pedidos, tempos de chegada, *bursts* e metas de eficiência são carregados e validados a partir de JSON.

### **Teste e Execução**

#### Pré-requisitos
- Python 3.13+
- Streamlit (necessário apenas para a interface web)

**1. Instalar pacotes e dependências** 

```
uv pip install -e .
```

**2. Executar a Versão Web (Streamlit)**
```
streamlit run src/cpu_kitchen/adapters/streamlit_app.py
```

**3. Executar a Versão Console (Terminal)**
```
python -m cpu_kitchen.adapters.cli
```
