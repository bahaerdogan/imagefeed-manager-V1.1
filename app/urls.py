from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    path('health/', views.health_check, name='health_check'),
    path('health/db/', views.health_check_db, name='health_check_db'),
    path('health/redis/', views.health_check_redis, name='health_check_redis'),
    path('health/metrics/', views.health_metrics, name='health_metrics'),
    
    path('', views.dashboard, name='dashboard'),
    path('frames/', views.frame_list, name='frame_list'),
    path('frames/create/', views.frame_create, name='frame_create'),
    path('frames/<int:pk>/', views.frame_detail, name='frame_detail'),
    path('frames/<int:pk>/preview/', views.frame_preview, name='frame_preview'),
    path('frames/<int:pk>/delete/', views.frame_delete, name='frame_delete'),
    
    path('frames/<int:pk>/preview-image/', views.generate_preview_image, name='generate_preview_image'),
    path('frames/<int:pk>/outputs-data/', views.frame_outputs_data, name='frame_outputs_data'),
]
