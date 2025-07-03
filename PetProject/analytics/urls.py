from django.urls import path
from .views import UploadView, DashboardView, InsightView

urlpatterns = [
    path('upload/', UploadView.as_view(), name='upload'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('insights/', InsightView.as_view(), name='insights'),
]
