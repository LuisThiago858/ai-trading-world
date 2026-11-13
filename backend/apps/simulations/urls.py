from django.urls import path
from apps.ledger.views import LedgerHistoryView
from apps.market_data.views import MarketOverviewView
from apps.portfolios.views import PortfolioHistoryView
from apps.orders.views import (
    FillListView, OrderListView, ProposalApproveView, ProposalListCreateView,
    ProposalRejectView, ProposalRiskView,
)
from apps.agents.views import AnalysisListCreateView
from .views import PortfolioDetailView, SimulationCreateView, SimulationDetailView
urlpatterns = [
    path("", SimulationCreateView.as_view(), name="simulation-create"),
    path("<uuid:simulation_id>/", SimulationDetailView.as_view(), name="simulation-detail"),
    path("<uuid:simulation_id>/portfolio/", PortfolioDetailView.as_view(), name="portfolio-detail"),
    path("<uuid:simulation_id>/portfolio/history/", PortfolioHistoryView.as_view(), name="portfolio-history"),
    path("<uuid:simulation_id>/ledger/", LedgerHistoryView.as_view(), name="ledger-history"),
    path("<uuid:simulation_id>/market/", MarketOverviewView.as_view(), name="market-overview"),
    path("<uuid:simulation_id>/proposals/", ProposalListCreateView.as_view(), name="proposal-list-create"),
    path("<uuid:simulation_id>/proposals/<uuid:proposal_id>/risk/", ProposalRiskView.as_view(), name="proposal-risk"),
    path("<uuid:simulation_id>/proposals/<uuid:proposal_id>/approve/", ProposalApproveView.as_view(), name="proposal-approve"),
    path("<uuid:simulation_id>/proposals/<uuid:proposal_id>/reject/", ProposalRejectView.as_view(), name="proposal-reject"),
    path("<uuid:simulation_id>/orders/", OrderListView.as_view(), name="order-list"),
    path("<uuid:simulation_id>/fills/", FillListView.as_view(), name="fill-list"),
    path("<uuid:simulation_id>/analysis-runs/", AnalysisListCreateView.as_view(), name="analysis-list-create"),
]

