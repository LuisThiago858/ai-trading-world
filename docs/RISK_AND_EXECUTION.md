# Risco e execução virtual

Este documento define as regras determinísticas da Task 003. Todos os valores financeiros são `Decimal`/`NUMERIC`; nenhuma decisão depende de LLM e nenhuma ordem é enviada a uma corretora.

## Política por sessão

Cada sessão possui uma `RiskPolicy` versionada. Os padrões são:

- operação: no máximo 5% do patrimônio atual;
- exposição projetada por ativo: no máximo 15% do patrimônio atual;
- perda realizada diária: no máximo 2% do patrimônio de referência do dia;
- desvio de preço entre proposta e execução: no máximo 1%;
- taxa: 0,1%; spread total: 0,1%; slippage: 0,05%;
- validade da proposta: 300 segundos;
- alavancagem e venda a descoberto: proibidas.

## Cálculos de risco

Para compra:

1. `limite_operacao = patrimonio_atual * 5%`;
2. `exposicao_existente = quantidade_da_posicao * cotacao_atual`;
3. `exposicao_pendente = soma do notional das outras compras pendentes/autorizadas do ativo`;
4. `exposicao_projetada = existente + pendente + notional_da_proposta`;
5. o custo total, incluindo taxa, deve caber no saldo disponível;
6. a perda diária é `max(0, pnl_realizado_na_abertura - pnl_realizado_atual)`.

Para venda, a exposição projetada diminui. A quantidade solicitada deve ser menor ou igual a `quantidade_da_posicao - quantidade_reservada`. Isso impede short selling. Vendas permanecem permitidas quando o limite diário de perda é atingido para que o jogador possa reduzir risco; novas compras são bloqueadas.

A decisão retorna `approved`, códigos estáveis, métricas em representação decimal e a versão da política. A pré-validação é informativa; aprovação sempre executa uma segunda avaliação sob transação e bloqueio da sessão.

## Preço e arredondamento

Ordens MARKET são preenchidas integralmente no MVP:

- compra: `preco = cotacao * (1 + spread/2 + slippage)`;
- venda: `preco = cotacao * (1 - spread/2 - slippage)`;
- preço e moeda: 8 casas, `ROUND_HALF_UP`;
- quantidade: 12 casas, sempre `ROUND_DOWN`;
- taxa: 8 casas, sempre `ROUND_UP` para não subestimar custo;
- quantidade residual abaixo de 10^-12 permanece fora da operação.

Ticker/OHLC não representa livro de ofertas. Portanto, o fill integral é uma simplificação determinística do jogo, não uma promessa de preço, liquidez ou execução realista.

## Aprovação, idempotência e atomicidade

O fluxo é `DRAFT -> PENDING_APPROVAL -> AUTHORIZED -> EXECUTED`, com saídas explícitas para `RISK_REJECTED`, `REJECTED`, `EXPIRED`, `INVALIDATED` e `FAILED`. A autorização registra a sessão, a versão exata da proposta, a decisão e a chave de idempotência.

A execução bloqueia a sessão, proposta, carteira e posição no PostgreSQL. Reserva, ordem, fill, taxa, ledger, posição e snapshot de carteira pertencem à mesma transação. Falha em qualquer etapa desfaz tudo. A mesma proposta nunca cria uma segunda ordem, mesmo com outra chave; repetir a mesma chave devolve o resultado já registrado.

Nenhuma chamada externa de mercado acontece dentro da transação. A execução usa somente snapshots persistidos pelo Market Data Service e invalida a proposta se a cotação estiver vencida ou tiver variado além da política.

## Ledger

Compras movem USDT de disponível para reservado e liquidam notional e taxa separadamente; o ativo recebido é contrapartida de clearing. Vendas reservam a quantidade, liquidam o ativo, creditam o valor bruto e debitam a taxa. Cada transação soma zero por ativo. As posições armazenam quantidade, quantidade reservada, custo médio e P&L realizado; o P&L não realizado é calculado pela cotação persistida atual.
