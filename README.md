# AI Trading World — 3D Isométrico

Jogo web de gerenciamento de um escritório de investimentos em **3D verdadeiro, com câmera isométrica**, agentes de IA e **capital exclusivamente fictício**.

## Visão

O jogador gerencia uma empresa de investimentos virtual, acompanha três personagens 3D (Alex, Maya e Victor), observa análises e debates, aprova/rejeita propostas e vê a carteira de paper trading ser atualizada por um motor financeiro independente. Os resultados não são promessas de rendimento.

## Decisões técnicas

- **Jogo:** Three.js + React Three Fiber (R3F) + Drei. **Não usar Phaser, sprites/pixel art 2D ou falso isométrico 2.5D.**
- **Câmera:** ortográfica, ângulo isométrico, zoom/pan limitados; controles de rotação são opcionais para versões posteriores.
- **Assets:** objetos e personagens 3D, preferencialmente `.glb`/glTF; Blender na pipeline de arte. Primeiro protótipo usa geometria 3D básica, sem assets externos.
- **HUD:** React/TypeScript com painéis de carteira, propostas e agentes sobre/ao lado do Canvas 3D.
- **Servidor:** Django + DRF + PostgreSQL, Celery/Redis e LangGraph; WebSocket permanece para uma etapa futura.
- **Trading:** somente capital fictício; primeiro escopo BTC/USDT e ETH/USDT, spot sem alavancagem. 10.000 USDT fictícios de saldo inicial.

## Comece aqui no Codex Desktop

1. Extraia o ZIP e abra esta pasta como projeto no Codex Desktop.
2. Leia `CODEX_START_HERE.md` e envie seu conteúdo ao Codex.
3. Solicite a execução **somente** da tarefa 001.

## Executar a aplicação

```bash
docker compose up --build
```

Abra `http://127.0.0.1:5173`; o healthcheck fica em `http://127.0.0.1:8000/api/health/`. As portas são publicadas somente em localhost. O token de sessão demo não é autenticação de produção; não exponha esta aplicação na internet.

Para testar sem Docker:

```powershell
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py test
python manage.py runserver 127.0.0.1:8000

cd ..\frontend
npm ci
npm test
npm run build
npm run dev
```

As consultas de uma sessão exigem o header `X-Demo-Session-Token` recebido na criação.

### API disponível

- `GET /api/health/`
- `POST /api/simulations/`
- `GET /api/simulations/{id}/`
- `GET /api/simulations/{id}/portfolio/`
- `GET /api/simulations/{id}/portfolio/history/`
- `GET /api/simulations/{id}/ledger/`
- `GET /api/simulations/{id}/market/`
- `POST /api/simulations/{id}/market/` força nova coleta, sem criar ordens ou posições
- `GET|POST /api/simulations/{id}/proposals/`
- `POST /api/simulations/{id}/proposals/{proposal_id}/risk/`
- `POST /api/simulations/{id}/proposals/{proposal_id}/approve/`
- `POST /api/simulations/{id}/proposals/{proposal_id}/reject/`
- `GET /api/simulations/{id}/orders/`
- `GET /api/simulations/{id}/fills/`
- `GET|POST /api/simulations/{id}/analysis-runs/`
- `GET /api/analysis-runs/{run_id}/`
- `GET /api/analysis-runs/{run_id}/agent-results/`
- `POST /api/analysis-runs/{run_id}/cancel/`

Os endpoints de aprovação e rejeição exigem `Idempotency-Key`, o token da sessão e a versão exata da proposta. Criar uma proposta nunca executa a operação; somente a aprovação explícita, seguida de nova validação no backend, pode iniciar a execução virtual.

A criação de uma análise também exige `Idempotency-Key`. Ela apenas agenda um worker assíncrono; o progresso e os resultados são consultados pela API. Propostas originadas pelos agentes são marcadas como `AI_AGENT`, permanecem pendentes e usam exatamente o mesmo fluxo humano de risco, aprovação e paper execution das propostas manuais.

## Dados de mercado

O padrão `MARKET_DATA_MODE=fixture` usa preços determinísticos e explicitamente fictícios para BTC/USDT e ETH/USDT. Isso mantém testes e desenvolvimento offline reproduzíveis.

Para testar o adaptador público somente leitura da Kraken:

```powershell
$env:MARKET_DATA_MODE="live"
python manage.py runserver 127.0.0.1:8000
```

O adaptador usa apenas ticker e candles OHLC públicos, sem chave, conta ou credencial de corretora. Snapshots registram fonte, horário e validade. Em indisponibilidade, a tentativa é registrada e o último snapshot válido pode ser devolvido como fallback desatualizado.

## Núcleo financeiro atual

- capital virtual inicial de 10.000 USDT;
- ledger balanceado por ativo, atômico, idempotente e imutável pela camada de domínio;
- saldos disponível e reservado separados;
- posições com quantidade, custo médio, exposição, valor de mercado e P&L preparado;
- histórico de carteira somente leitura;
- propostas manuais de compra e venda para BTC/USDT e ETH/USDT;
- motor de risco determinístico, configurável por sessão e revalidado na execução;
- aprovação humana versionada e idempotente;
- execução MARKET integral e exclusivamente virtual, com spread, slippage e taxa;
- reservas, fills, taxas, custo médio e P&L registrados atomicamente no ledger;
- terminal React acessível, separado do Canvas 3D e atualizado sem recarregar a página.

## Agentes de IA

Alex, Maya e Victor são orquestrados por LangGraph em um worker Celery. Indicadores são calculados por código Python sobre candles persistidos; cada saída é validada por schema e armazenada com evidências, discordâncias, horários, modelo e snapshot utilizado. O Risk Engine determinístico continua soberano.

O padrão `LLM_PROVIDER=mock` é determinístico, funciona offline e aparece rotulado na interface. Para habilitar o adaptador real, configure `LLM_PROVIDER=openai`, `LLM_API_KEY` e `LLM_MODEL` somente no ambiente do backend e do worker. Consulte `docs/MULTI_AGENT.md` para limites, fluxo e API.

## Documentação

- `AGENTS.md`: regras permanentes para o Codex.
- `docs/PRODUCT.md`: conceito, mecânicas e escopo.
- `docs/ARCHITECTURE.md`: módulos, regras financeiras, contrato dos eventos e separação 3D/backend.
- `docs/RISK_AND_EXECUTION.md`: fórmulas, limites, arredondamentos e fluxo de paper trading.
- `docs/MULTI_AGENT.md`: grafo, provedores, checkpoints, segurança e endpoints de análise.
- `docs/WORLD_3D.md`: especificação do escritório isométrico e dos personagens.
- `docs/ROADMAP.md`: sequência de entregas.
- `tasks/001-foundation.md`: primeira implementação.
- `CODEX_START_HERE.md`: prompt pronto para colar no Codex.

**Status:** fundação 3D, núcleo financeiro, paper trading/risk engine e inteligência multiagente estão implementados para capital exclusivamente fictício. Não há integração de ordens com corretoras; agentes não possuem acesso de escrita ao ledger ou à execução.
