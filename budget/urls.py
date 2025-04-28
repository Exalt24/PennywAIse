from django.urls import path
from . import views

app_name = 'budget'
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('auth/', views.AuthView.as_view(), name='auth'),
    path('forgot-password/', views.ForgotPasswordView.as_view(), name='forgot_password'),
    path('reset-password/<str:token>/', views.ResetPasswordView.as_view(), name='reset_password'),
    # path('entries/add/', views.entry_create, name='entry_create'),
    # path('entries/<int:pk>/edit/', views.entry_update, name='entry_update'),
    # path('entries/<int:pk>/delete/', views.entry_delete, name='entry_delete'),
    # path('export/csv/', views.export_csv, name='export_csv'),
    # path('api/chart-data/', views.chart_data, name='chart_data'),
]
