import type { AnalysisPage, AnalysisRun, CreatedSimulation, MarketOverview, Portfolio, ProposalActionResponse, TradeFill, TradeOrder, TradeProposal } from "./types";
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";
async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail ?? "Não foi possível conectar ao servidor demo."); }
  return response.json() as Promise<T>;
}
export async function createDemoSession(): Promise<CreatedSimulation> {
  return parseResponse(await fetch(`${API_BASE}/simulations/`, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:"AI Trading World Demo"})}));
}
export async function getPortfolio(id:string, token:string): Promise<Portfolio> {
  return parseResponse(await fetch(`${API_BASE}/simulations/${id}/portfolio/`, {headers:{"X-Demo-Session-Token":token}}));
}
export async function getMarketOverview(id:string, token:string): Promise<MarketOverview> {
  return parseResponse(await fetch(`${API_BASE}/simulations/${id}/market/`, {headers:{"X-Demo-Session-Token":token}}));
}
const sessionHeaders = (token:string) => ({"Content-Type":"application/json","X-Demo-Session-Token":token});
export async function listProposals(id:string,token:string):Promise<TradeProposal[]>{return parseResponse(await fetch(`${API_BASE}/simulations/${id}/proposals/`,{headers:sessionHeaders(token)}))}
export async function createProposal(id:string,token:string,input:{asset:string;side:"BUY"|"SELL";amount?:string;quantity?:string}):Promise<TradeProposal>{return parseResponse(await fetch(`${API_BASE}/simulations/${id}/proposals/`,{method:"POST",headers:sessionHeaders(token),body:JSON.stringify(input)}))}
export async function approveProposal(id:string,token:string,proposal:TradeProposal,key:string):Promise<ProposalActionResponse>{return parseResponse(await fetch(`${API_BASE}/simulations/${id}/proposals/${proposal.id}/approve/`,{method:"POST",headers:{...sessionHeaders(token),"Idempotency-Key":key},body:JSON.stringify({version:proposal.version})}))}
export async function rejectProposal(id:string,token:string,proposal:TradeProposal,key:string):Promise<{proposal:TradeProposal;duplicate:boolean}>{return parseResponse(await fetch(`${API_BASE}/simulations/${id}/proposals/${proposal.id}/reject/`,{method:"POST",headers:{...sessionHeaders(token),"Idempotency-Key":key},body:JSON.stringify({version:proposal.version})}))}
export async function listOrders(id:string,token:string):Promise<TradeOrder[]>{return parseResponse(await fetch(`${API_BASE}/simulations/${id}/orders/`,{headers:sessionHeaders(token)}))}
export async function listFills(id:string,token:string):Promise<TradeFill[]>{return parseResponse(await fetch(`${API_BASE}/simulations/${id}/fills/`,{headers:sessionHeaders(token)}))}
export async function listAnalysisRuns(id:string,token:string):Promise<AnalysisPage>{return parseResponse(await fetch(`${API_BASE}/simulations/${id}/analysis-runs/?limit=10`,{headers:sessionHeaders(token)}))}
export async function createAnalysisRun(id:string,token:string,assets:string[],key:string):Promise<AnalysisRun>{return parseResponse(await fetch(`${API_BASE}/simulations/${id}/analysis-runs/`,{method:"POST",headers:{...sessionHeaders(token),"Idempotency-Key":key},body:JSON.stringify({assets})}))}
export async function getAnalysisRun(id:string,token:string):Promise<AnalysisRun>{return parseResponse(await fetch(`${API_BASE}/analysis-runs/${id}/`,{headers:sessionHeaders(token)}))}
export async function cancelAnalysisRun(id:string,token:string):Promise<AnalysisRun>{return parseResponse(await fetch(`${API_BASE}/analysis-runs/${id}/cancel/`,{method:"POST",headers:sessionHeaders(token),body:"{}"}))}

