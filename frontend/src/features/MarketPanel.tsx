import type { MarketOverview } from "../shared/api/types";

interface Props {
  market: MarketOverview | null;
  loading: boolean;
}

function formatPrice(value: string) {
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(value));
}

export function MarketPanel({ market, loading }: Props) {
  return (
    <section className="panel market-panel" aria-busy={loading} aria-live="polite">
      <div className="market-heading">
        <div>
          <p className="eyebrow">Ativos monitorados</p>
          <h2>Mercado</h2>
        </div>
        {market && (
          <span className={`quote-state ${market.stale ? "stale" : "current"}`}>
            {market.stale ? "Desatualizado" : "Atualizado"}
          </span>
        )}
      </div>
      {!market ? (
        <p className="muted">{loading ? "Carregando cotações…" : "Crie uma sessão para carregar o mercado."}</p>
      ) : (
        <>
          <div className="quote-list">
            {market.quotes.map((quote) => (
              <div className="quote-row" key={quote.symbol}>
                <span>{quote.symbol}</span>
                <strong>{formatPrice(quote.price)} <small>USDT</small></strong>
              </div>
            ))}
          </div>
          <p className="market-meta">
            Fonte: {market.source === "DEMO_FIXTURE" ? "fixture fictícia" : "Kraken pública"}
            {market.using_fallback ? " · fallback em uso" : ""}
          </p>
          {market.demo_notice && <p className="demo-notice">{market.demo_notice}</p>}
          {market.error && <p className="error" role="status">{market.error}</p>}
        </>
      )}
    </section>
  );
}
