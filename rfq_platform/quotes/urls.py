from django.urls import path
from . import views

from .views import (
    RFQIntakeView,
    ActiveQuotesView,
    CompletedQuotesView,
    CompleteQuoteView,
    StatsSummaryView,
)

urlpatterns = [
    path("intake/", RFQIntakeView.as_view(), name="rfq-intake"),
    path("active/", ActiveQuotesView.as_view(), name="active-quotes"),
    path("completed/", CompletedQuotesView.as_view(), name="completed-quotes"),
    path("<int:pk>/complete/", CompleteQuoteView.as_view(), name="complete-quote"),
    path("stats/summary/", StatsSummaryView.as_view(), name="stats-summary"),
]