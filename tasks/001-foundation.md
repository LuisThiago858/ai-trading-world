# Tarefa 001 — Fundação e primeiro escritório 3D isométrico

## Objetivo

Criar a primeira versão **executável** do AI Trading World, com backend de sessão/carteira fictícia e um escritório **3D verdadeiro** renderizado no navegador, sem dependências de IA, exchange, modelos comprados ou ativos externos.

## Escopo do backend

1. Criar Django + DRF + PostgreSQL com módulos simples (`simulations`, `portfolios`, `health` ou equivalentes).
2. Entidade de simulação com capital inicial de 10.000 USDT fictícios. Campo financeiro `Decimal`/`NUMERIC`.
3. Endpoints mínimos:
   - `GET /api/health/`
   - `POST /api/simulations/` — cria sessão demo
   - `GET /api/simulations/{id}/`
   - `GET /api/simulations/{id}/portfolio/` — saldo e posições vazias
4. Definir isolamento/autorização adequados. Se demo for local sem login, documentar a restrição explícita ao localhost e impedir exposição pública inadvertida.
5. Testes de criação de sessão, saldo inicial Decimal e isolamento entre sessões.

## Escopo do frontend/3D

1. Criar React + Vite + TypeScript + Three.js + `@react-three/fiber` + `@react-three/drei`. Selecionar versões estáveis compatíveis e documentar no package lock.
2. Implementar `OfficeScene3D` com `Canvas`, **câmera ortográfica isométrica**, luz ambiente e direcional e sombras moderadas.
3. Usar geometria real para piso, paredes baixas, **três mesas**, **três monitores** e três avatares 3D geométricos de Alex, Maya e Victor. Sem sprites/pixel art 2D.
4. Permitir clique em cada avatar, highlight e painel lateral React contendo nome, função e status. Estados vazios/loading/erro.
5. Exibir painel de carteira e botão para criar sessão demo, consumindo os endpoints reais do backend.
6. Zoom limitado; pan opcional se não comprometer a experiência inicial; câmera deve permanecer em ângulo isométrico.
7. Responsividade desktop e fallback acessível caso WebGL esteja indisponível.
8. Smoke test da UI e, se viável, teste de seleção do agente/contrato do evento.

## Infraestrutura e qualidade

- Docker Compose com backend, frontend e PostgreSQL ou documentação de execução local equivalente; `.env.example`, `.gitignore`, migrações, healthcheck e README.
- Sem chaves de API para rodar. Mocks/fixtures da experiência de agentes, nunca dados reais inventados.
- Não integrar Celery, LangGraph, CCXT, WebSocket, ordens, fills nem trading real nesta tarefa.

## Critérios de aceite

- Aplicação sobe com instruções claras.
- Backend cria e consulta sessão com exatamente 10.000 USDT fictícios e zero posições.
- Cena contém volumes tridimensionais reais com vista isométrica ortográfica.
- Alex/Maya/Victor são objetos 3D clicáveis; clique abre seus dados no HUD React.
- Sem Phaser nem abordagem 2D ou 2.5D.
- HUD funciona mesmo sem WebGL, com aviso apropriado.
- Testes executados, ou relato preciso de impedimentos; nunca afirmar execução sem evidência.

## Entrega esperada do Codex

Ao final informar **Contexto/Problema**, **Solução**, **Resultados dos testes**, **Arquivos alterados**, **Como rodar**, **Limitações** e **Sugestão de commit**. Não fazer commit automaticamente.
