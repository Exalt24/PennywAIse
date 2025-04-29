from django.urls import path
from . import views

app_name = 'budget'
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('auth/', views.AuthView.as_view(), name='auth'),
    path('forgot-password/', views.ForgotPasswordView.as_view(), name='forgot_password'),
    path('reset-password/<str:token>/', views.ResetPasswordView.as_view(), name='reset_password'),
    path('entries/filter/', views.EntriesAjaxView.as_view(), name='entries-filter'),
    path('reports/filter/', views.ReportsAjaxView.as_view(), name='reports-filter'),
]
