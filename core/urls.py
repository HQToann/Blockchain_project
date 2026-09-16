from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from election import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Trang HTML
    path('', TemplateView.as_view(template_name='index.html')),
    path('election/<int:election_id>/', TemplateView.as_view(template_name='detail.html')),
    path('verify/', TemplateView.as_view(template_name='verify.html')),
    
    # System Logs
    path('logs/', views.system_logs),
    path('api/logs/', views.get_latest_logs),

    # API Auth
    path('api/auth/nonce/', views.get_nonce),
    path('api/auth/verify/', views.verify_signature),

    # API
    path('api/elections/', views.get_elections),
    path('api/elections/<int:election_id>/', views.get_election_detail),
    path('api/elections/<int:election_id>/whitelist/', views.add_whitelist_api),
    path('api/verify/', views.verify_vote_api),
    path('api/internal/notify_vote/', views.internal_notify_vote),
]