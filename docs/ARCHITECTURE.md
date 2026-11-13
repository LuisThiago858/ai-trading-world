# Arquitetura técnica — AI Trading World 3D

## Princípio

**Separação rigorosa entre motor de jogo 3D, UI financeira, orquestração dos agentes e contabilidade.** A cena Three.js nunca calcula nem altera patrimônio: reage a eventos públicos e solicita ações pela API autenticada.

```text
Browser
  React / TypeScript ── HUD: propostas, carteira, relatórios
      |
      └── React Three Fiber + Three.js + Drei
          ├── OrthographicCamera, luzes, sombras
          ├── World3D: salas e mobiliário (.glb no futuro)
          ├── Agent3D: Alex / Maya / Victor
          └── GameEventBridge: anima estado, seleciona personagem
                   | REST (WebSocket em fase futura)
Django + DRF
  ├── Simulation / Company / Permissions
  ├── Market Data + Snapshots
  ├── Agent Orchestrator (LangGraph + schemas estruturados)
  ├── TradeProposal + User Approval
  ├── Risk Engine (determinístico)
  ├── Paper Execution Engine (sem broker real)
  ├── Portfolio + Virtual Double-Entry Ledger
  └── Game Events (DTOs públicos, versionados)
PostgreSQL (estado de domínio) / Redis + Celery (análises) / Channels posteriormente
```

## Módulos sugeridos

- `frontend/src/game3d/`: cena, câmera, iluminação, objetos, personagens, seleção, estado visual e assets.
- `frontend/src/features/`: sessão, carteira, propostas, relatórios, HUD.
- `frontend/src/shared/api/`: clientes HTTP e contratos tipados.
- `backend/apps/simulations/`: sessões, propriedade do usuário, relógio.
- `backend/apps/portfolios/`: visão de carteira.
- `backend/apps/market_data/`: candles, snapshots e adaptadores.
- `backend/apps/agents/`: runs, estratégias e orquestração.
- `backend/apps/risk/`: políticas e avaliações.
- `backend/apps/orders/`: propostas, aprovações e execução simulada.
- `backend/apps/ledger/`: lançamentos balanceados e invariantes.
- `backend/apps/game_events/`: eventos para refletir na cena 3D.

## Entidades de domínio

`User`, `Company`, `Simulation`, `RiskPolicy`, `Asset`, `MarketCandle`, `MarketSnapshot`, `AgentDefinition`, `AgentRun`, `StrategyVersion`, `AnalysisRun`, `TradeProposal`, `RiskAssessment`, `TradeOrder`, `TradeFill`, `LedgerAccount`, `LedgerTransaction`, `LedgerEntry`, `Position`, `PortfolioSnapshot`, `GameEvent`.

## Fluxo oficial de uma ordem

`market snapshot → análises → proposta versionada → risco determinístico → aprovação explícita → revalidação de risco e dados → reserva atômica de saldo + criação de ordem → paper execution → fills + ledger → posição/patrimônio → game event → animação 3D e HUD`.

Saídas adicionais: `REJECTED`, `EXPIRED`, `INVALIDATED`, `FAILED`, `CANCELLED`. Ordem com fills parciais preserva fills já feitos e libera reservas excedentes.

## Fluxo multiagente

Uma requisição idempotente cria um `AnalysisRun` e agenda o worker Celery. O grafo LangGraph executa Alex, Maya, Victor e a consolidação em sequência, persistindo um checkpoint após cada nó. Alex interpreta indicadores calculados por código; Maya considera carteira e política; o Risk Engine avalia deterministicamente a proposta; Victor explica o resultado sem poder substituí-lo. Somente então o serviço existente de propostas pode criar uma `TradeProposal` `AI_AGENT` pendente.

LLMs não recebem ferramentas de escrita financeira. Uma falha, timeout, snapshot expirado ou saída fora do schema encerra o run sem criar proposta. Aprovação, reserva, ordem, fill e ledger permanecem fora do grafo e sob as invariantes da Task 003.

## Política de risco demonstrativa

- Mercado spot e sem alavancagem.
- Máximo por nova operação: 5% do patrimônio, configurável.
- Exposição máxima por ativo: 15% do patrimônio.
- Limite de perda diária: 2% (especificar fórmula antes da implementação).
- Saldo disponível cobre compra, custos e reservas.
- Bloqueio por proposta expirada, cotação velha ou versão de risco inválida.

Percentuais são **exemplos experimentais**, não recomendações financeiras.

## Invariantes financeiras

- Todos os recursos são virtuais e não conversíveis em dinheiro real.
- `Decimal`/`NUMERIC` para valores; não persistir valores monetários com float.
- Ledger de partidas balanceadas, sem edição arbitrária de saldos.
- Isolamento por simulação, autenticação e permissões.
- Reserva + criação da ordem na mesma transação e lock apropriado.
- Idempotência de autorização, submissão, fills e eventos; retries não criam ordens duplicadas.
- Dados de mercado com fonte, timestamp e snapshot. Em replay não ler futuro.
- Resultado de execução com critério de preço, taxas, slippage e status.

## Contrato de eventos da cena

Tipos iniciais: `agent.analysis.started`, `agent.analysis.completed`, `meeting.started`, `proposal.ready`, `risk.rejected`, `order.filled`, `portfolio.updated`. Cada evento possui `id`, `type`, `simulation_id`, `occurred_at`, `schema_version`, `payload` público. O frontend mapeia eventos para animações, sem interpretar events como ordens financeiras.

No início, usar estado demo/mock para os avatares e carregar sessão via REST. Evoluir para WebSocket depois; garantir que queda do Canvas não impossibilite aceitar/rejeitar proposta pelo HUD.

## Aspectos 3D

- Cena tridimensional com malhas reais; câmera ortográfica em orientação diagonal de aproximadamente 45° de azimute e 30°–35° de elevação (ajustável por arte/direção).
- `@react-three/fiber` fornece Canvas e renderização declarativa; Drei pode auxiliar câmera, controles e modelos.
- Inicialmente piso, paredes baixas, mesas, monitores e avatares feitos com primitivas 3D para evitar dependências.
- Depois importar GLB de Blender, com animações de idle/trabalhando/caminhando/reunião; não atrelar nomes de animações ao backend.
- Configurar limites de zoom/pan, iluminação básica, sombras moderadas, redução de pixel ratio e render sob demanda quando adequado.
- Componentes acessíveis HTML para ações essenciais; fallback no navegador sem WebGL.

## Testes essenciais

- Criação de sessão e saldo inicial exato.
- Isolamento/autorização entre usuários/sessões.
- Risco e limites em valores de fronteira.
- Concorrência (dupla aprovação), idempotência e precisão.
- Replay determinístico e prevenção de look-ahead bias.
- Renderização inicial da cena 3D e seleção de um agente.
- HUD funcional com/sem WebGL.

## Observabilidade

Logs com correlação por simulação, análise, proposta e ordem; healthchecks; migrações; `.env.example`, CI, histórico auditável e segregação de dados demo versus dados externos.
