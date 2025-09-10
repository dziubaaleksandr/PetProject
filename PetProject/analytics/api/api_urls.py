from django.urls import path

from . import api_views

urlpatterns = [
    path(
        "transactions/", api_views.TransactionListCreateAPIView.as_view(),
        name="api-transactions",
    ),
    path("kpis/", api_views.KPIAPIView.as_view(), name="api-kpis"),
    path("insights/", api_views.InsightAPIView.as_view(), name="api-insights"),
]
