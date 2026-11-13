# Visão do Produto — AI Trading World 3D

## Conceito

Jogo web de gerenciamento de uma empresa virtual de investimentos. O jogador entra em um **escritório tridimensional real, visto por câmera isométrica**, acompanha funcionários que são agentes de IA, analisa propostas e autoriza operações **apenas com dinheiro fictício**. O objetivo é aprender, experimentar e comparar estratégias com métricas verificáveis, não garantir lucros.

## Experiência desejada

- Escritório 3D em visão isométrica, estilo jogo de gestão: piso, paredes, estações de trabalho, sala de reunião e painéis/monitores.
- Personagens 3D clicáveis: caminham (etapa futura), sentam-se e se reúnem conforme estados reais dos agentes.
- Câmera ortográfica, com zoom e pan limitados para não perder o enquadramento do escritório; rotação opcional futura.
- Clicar no personagem abre painel React com papel, atividade atual, justificativas e histórico.
- Reuniões surgem quando existe proposta; jogador pode abrir o relatório, aprovar/rejeitar e ver a atualização virtual da carteira.
- O jogo deve funcionar em modo demo sem credenciais de IA ou exchanges.

## MVP

- Aplicação web desktop-first, layout adaptável.
- Uma empresa e uma simulação por jogador no fluxo inicial.
- Capital inicial: **10.000 USDT fictícios**.
- Mercados iniciais: BTC/USDT e ETH/USDT, **spot sem alavancagem**.
- Alex: agente de análise técnica, com indicadores gerados por código, não por texto inventado.
- Maya: agente de estratégia e composição de carteira.
- Victor: personagem de risco que apresenta avaliações do motor determinístico.
- Propostas estruturadas, datadas, versionadas, com justificativas, snapshot e prazo de aprovação.
- Toda ordem nova exige autorização do jogador, com revalidação de riscos e saldo.
- Carteira virtual, histórico, ordens, fills, taxas, movimentos do ledger e diário de decisões.
- **Escritório 3D verdadeiro** (na tarefa 001, graybox com objetos e avatares simples; assets modelados em fase futura).

## Loop principal

1. Jogador cria simulação e define limites.
2. Dados de mercado são capturados e congelados em snapshot por rodada.
3. Agentes analisam, confrontam hipóteses e elaboram proposta.
4. Risk Engine determinístico decide se é elegível.
5. Jogador aprova/rejeita, ou proposta expira.
6. Backend revalida cotação/versões, reserva saldo e cria ordem atomicamente.
7. Paper Engine simula preenchimento, spread, slippage e taxas.
8. Ledger, posição, patrimônio e eventos são atualizados.
9. Escritório 3D responde aos eventos e o diário recebe justificativas e resultados.

## Salas e progressão visual

- **Análise:** estações de trabalho e computadores dos agentes.
- **Reuniões:** personagens discutem uma proposta com o jogador.
- **Operações:** painel de ordens, saldo e resultado.
- **Laboratório:** replays, backtests e novas versões de estratégias (etapa futura).

Os objetos da cena são uma metáfora do estado real dos serviços. A lógica financeira independe da renderização ou do FPS.

## Restrições

- Sem contas reais, depósito, saque, custódia, corretora operando dinheiro ou promessa de lucro.
- Sem derivativos, margem ou alavancagem no MVP.
- Sem multiplayer, NFT, marketplace ou moeda monetizável.
- Sem autonomia total para realizar **novas** operações no MVP.
- Sem modelos 3D caros ou animação sofisticada como pré-requisito técnico.
- Não usar arquitetura 2D disfarçada: cenário e personagens são 3D mesmo com câmera isométrica.

## Medidas de sucesso

Ciclo completo executável; taxa de propostas corretamente aprovadas/rejeitadas; integridade do ledger; precisão, taxa e slippage simulados; tempo/custo de análise; clareza das justificativas; desempenho ajustado ao risco versus estratégias simples; FPS e tempo de carregamento da cena.
