# Roadmap — AI Trading World 3D

## E1 — Fundação + escritório 3D graybox

Monorepo, Django + DRF + PostgreSQL, React/TypeScript/Vite e **Three.js + React Three Fiber + Drei**. Criar sessão demo com 10.000 USDT fictícios, endpoint de carteira, healthcheck e cena 3D isométrica com mesas, monitores, piso, paredes e Alex/Maya/Victor geométricos clicáveis. HUD integrado e testes mínimos. Sem IA nem ordens. **Detalhes em `tasks/001-foundation.md`.**

## E2 — Núcleo financeiro de paper trading

Ledger virtual de partidas balanceadas, posições, fixture de preço, ordem simulada, taxas, slippage, limites de risco, propostas, autorização explícita, idempotência, locking e testes de concorrência. UI permite visualizar e executar o ciclo completo sem IA.

## E3 — Agentes de IA e propostas

Alex, Maya e Victor com análises estruturadas; orquestrador Python/LangGraph, snapshots, evidências, orçamento de tokens e mocks. Cenas 3D refletem os estados dos agentes. **Implementado:** execução assíncrona Celery/Redis, checkpoints persistentes, adaptadores mock/OpenAI, propostas `AI_AGENT` sujeitas ao Risk Engine e aprovação humana, central de análises e estados visuais no escritório.

## E4 — Escritório 3D aprimorado

Assets low-poly glTF/GLB (Blender), personagens rigados e animações, salas de reunião, interações espaciais, estados reativos, notificações; WebSocket ou polling resiliente. O jogo permanece funcional sem animações/canvas.

## E5 — Replay, backtest e laboratório

Relógio de simulação, histórico, execução determinística, prevenção de acesso a dados futuros, benchmarks e evolução versionada de estratégias. Laboratório 3D opcional como interface para esses serviços.

## E6 — Expansão

Personalização do escritório, novas salas e agentes, equipes independentes, rankings ajustados ao risco, acessibilidade e otimização de performance.

## Prioridade

Integridade financeira e isolamento > fluxo mínimo funcional > jogo 3D de base > IA e justificativas > arte/animações sofisticadas > modos extras.

Obs.: o protótipo 3D básico aparece **já em E1**, não é adiado para depois do desenvolvimento da IA.
