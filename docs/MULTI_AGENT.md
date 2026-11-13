# Inteligência multiagente

## Escopo e garantias

Alex, Maya e Victor produzem análises auditáveis sobre capital exclusivamente fictício. O grafo nunca executa ordens, altera posições ou grava no ledger. Uma sugestão `BUY` ou `SELL` pode criar somente uma `TradeProposal` pendente; a execução continua dependendo da aprovação explícita do jogador e da revalidação determinística do Risk Engine da Task 003.

O modo padrão é `mock`, determinístico e identificado como simulação na API e na interface. Ele existe para desenvolvimento offline e testes, não representa análise atual de um modelo real.

## Fluxo

```text
POST analysis-runs (Idempotency-Key)
  -> AnalysisRun PENDING
  -> Celery/Redis
  -> valida sessão, ativos e snapshot persistido
  -> calcula indicadores por funções Python puras
  -> Alex: leitura técnica estruturada
  -> Maya: estratégia e composição estruturadas
  -> Risk Engine determinístico
  -> Victor: explica a decisão de risco, sem poder alterá-la
  -> consolidação BUY | SELL | HOLD
  -> opcionalmente TradeProposal AI_AGENT/PENDING
  -> AnalysisRun COMPLETED
  -> aprovação/rejeição humana no fluxo existente
```

Cada nó persiste um `AnalysisCheckpoint`. Cada agente persiste um `AgentResult` validado por schema, com provedor/modelo, horários, evidências, indicadores, hipóteses, discordâncias, uso de tokens e custo informado pelo provedor quando disponível. Em nova tentativa, resultados válidos já concluídos são reutilizados; respostas incompletas ou inválidas falham de forma controlada e não geram proposta.

Os candles são limitados ao instante do snapshot usado na execução. Snapshots expirados interrompem a análise antes de consultar o LLM. O estado persistido usa `PENDING`, `RUNNING`, `COMPLETED`, `FAILED` ou `CANCELLED`.

## Provedores

Variáveis principais:

```env
LLM_PROVIDER=mock
LLM_MODEL=gpt-6-astra
LLM_API_KEY=
LLM_TIMEOUT_SECONDS=30
LLM_MAX_OUTPUT_TOKENS=1200
LLM_MAX_ATTEMPTS=2
```

- `mock`: padrão offline, determinístico e claramente rotulado.
- `openai`: chama a Responses API com saída estruturada validada por Pydantic. A chave permanece exclusivamente no backend.

Para usar o provedor real, defina `LLM_PROVIDER=openai`, `LLM_API_KEY` e um modelo compatível no ambiente do backend e do worker. Reinicie ambos após alterar as variáveis. Não coloque a chave em `.env.example` nem em arquivos versionados.

Falhas transitórias possuem tentativas limitadas; timeouts e limites rígidos do Celery impedem execução indefinida. Indisponibilidade, resposta inválida ou orçamento incompleto marcam o run como `FAILED` sem criar proposta.

## API

Todas as rotas exigem `X-Demo-Session-Token`; a criação também exige `Idempotency-Key`.

- `POST /api/simulations/{simulation_id}/analysis-runs/`
- `GET /api/simulations/{simulation_id}/analysis-runs/`
- `GET /api/analysis-runs/{run_id}/`
- `GET /api/analysis-runs/{run_id}/agent-results/`
- `POST /api/analysis-runs/{run_id}/cancel/`

Exemplo de criação:

```json
{
  "assets": ["BTC/USDT", "ETH/USDT"]
}
```

Listagens são paginadas. O acesso é isolado pela combinação de sessão e token. Repetir a criação com a mesma chave na mesma sessão devolve o mesmo run; a mesma chave em sessões diferentes não compartilha dados.

## Desenvolvimento

O Docker Compose inicia PostgreSQL, Redis, backend, worker Celery e frontend:

```powershell
docker compose up --build
docker compose exec backend python manage.py test
```

Sem Docker, Redis precisa estar disponível e backend e worker devem compartilhar as mesmas variáveis:

```powershell
cd backend
python manage.py migrate
celery -A config worker --loglevel=info
python manage.py runserver 127.0.0.1:8000
```

O frontend usa polling controlado somente enquanto o run está ativo. A cena 3D recebe estados derivados do backend, enquanto todas as ações essenciais permanecem disponíveis em componentes HTML acessíveis.
