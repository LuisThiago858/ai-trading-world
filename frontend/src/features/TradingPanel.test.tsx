import { fireEvent, render, screen } from "@testing-library/react";

import * as api from "../shared/api/client";
import type { MarketOverview, TradeProposal } from "../shared/api/types";
import { TradingPanel } from "./TradingPanel";

vi.mock("../shared/api/client",()=>({
  createProposal:vi.fn(),approveProposal:vi.fn(),rejectProposal:vi.fn(),
  listProposals:vi.fn(),listOrders:vi.fn(),listFills:vi.fn(),
}));

const market:MarketOverview={snapshot_id:"snapshot",source:"DEMO_FIXTURE",status:"READY",observed_at:"2026-01-01",valid_until:"2099-01-01",stale:false,using_fallback:false,error:null,quotes:[{symbol:"BTC/USDT",price:"50000.00000000",observed_at:"2026-01-01"},{symbol:"ETH/USDT",price:"3000.00000000",observed_at:"2026-01-01"}],demo_notice:"Fixture"};
const pending:TradeProposal={id:"proposal",asset:"BTC/USDT",side:"BUY",requested_quantity:"0.004992511234",requested_amount:"250.00000000",reference_price:"50000.00000000",estimated_notional:"249.99999999",estimated_fee:"0.25000000",estimated_total:"250.24999999",justification:"Manual",risk_summary:{approved:true,codes:[],metrics:{},policy_version:1},version:1,status:"PENDING_APPROVAL",snapshot_id:"snapshot",authorized_at:null,expires_at:"2099-01-01",created_at:"2026-01-01"};

describe("TradingPanel",()=>{
  beforeEach(()=>{
    vi.mocked(api.listProposals).mockResolvedValue([]);
    vi.mocked(api.listOrders).mockResolvedValue([]);
    vi.mocked(api.listFills).mockResolvedValue([]);
    vi.mocked(api.createProposal).mockResolvedValue(pending);
    vi.mocked(api.approveProposal).mockResolvedValue({proposal:{...pending,status:"EXECUTED"},order:{id:"order",proposal_id:"proposal",asset:"BTC/USDT",side:"BUY",order_type:"MARKET",state:"FILLED",requested_quantity:pending.requested_quantity,execution_price:"50075.00000000",reserved_amount:"250.25000000",total_fee:"0.25000000",market_snapshot_id:"snapshot",created_at:"2026-01-01",executed_at:"2026-01-01",fills:[]},duplicate:false});
  });
  afterEach(()=>vi.clearAllMocks());

  it("cria, revisa e aprova uma operação virtual sem recarregar",async()=>{
    const refresh=vi.fn().mockResolvedValue(undefined);
    render(<TradingPanel simulationId="session" sessionToken="token" market={market} onPortfolioChanged={refresh}/>);
    fireEvent.change(screen.getByLabelText("Valor fictício (USDT)"),{target:{value:"250"}});
    fireEvent.click(screen.getByRole("button",{name:"Criar proposta"}));
    expect(await screen.findByRole("button",{name:"Aprovar e executar"})).toBeEnabled();
    expect(screen.getByText("249,99999999 USDT")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button",{name:"Aprovar e executar"}));
    expect(await screen.findByText("Operação virtual executada.")).toBeInTheDocument();
    expect(api.approveProposal).toHaveBeenCalledOnce();
    expect(refresh).toHaveBeenCalledOnce();
  });
});
