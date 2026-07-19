# urls.py - COMPLETE ENHANCED VERSION
# Copy and paste this entire file

from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from . import views
from .forms import LoginForm

urlpatterns = [
    # Authentication URLs
    path('', views.feed_view, name='home'), 
    path('signup/', views.signup, name='register'),
    path('login/', LoginView.as_view(template_name='registration/login.html', authentication_form=LoginForm), name='login'),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
    
    # Profile URLs
    path('profile/', views.profile_view, name='profile'),

    path('confirm-meet/<int:safemeet_id>/', views.confirm_safe_meet_view, name='confirm_safe_meet'),

    
    # Messaging URLs
    path('messages/', views.messages_view, name='messages'),
    path('chat/<int:match_id>/', views.chat_view, name='chat'),
    path('chat/<int:match_id>/send/', views.send_message_view, name='send_message'),
    path('chat/<int:match_id>/hookup/', views.send_hookup_request_view, name='send_hookup_request'),
    path('message/<int:message_id>/accept/', views.accept_hookup_view, name='accept_hookup'),
    
    # Subscription URL
    path('subscribe/', views.subscribe_view, name='subscribe'),
    
    # Swipe URL
    path('swipe/<int:profile_id>/<str:action>/', views.swipe_action, name='swipe_action'),
    
    # Knocks URLs
    path('knocks/', views.knocks_view, name='knocks'),
    path('knocks/<int:like_id>/accept/', views.accept_knock_view, name='accept_knock'),
    path('knocks/<int:like_id>/reject/', views.reject_knock_view, name='reject_knock'),
    
    # ============================================================
    # NEW SAFETY FEATURE URLS
    # ============================================================
    
    # Safety Center
    path('safety/', views.safety_center_view, name='safety_center'),
    
    # Report User
    path('report/<int:user_id>/', views.report_user_view, name='report_user'),
    
    # Block User
    path('block/<int:user_id>/', views.block_user_view, name='block_user'),
    
    # Safe Meeting Scheduling
    path('safe-meet/<int:match_id>/', views.schedule_safe_meet_view, name='schedule_safe_meet'),
    
    # Emergency Check-in
    path('emergency-check-in/<int:safemeet_id>/', views.emergency_check_in_view, name='emergency_check_in'),
    
    # ============================================================
    # NEW API ENDPOINTS
    # ============================================================
    
    # API: Smart Feed
    path('api/feed/', views.api_feed_view, name='api_feed'),
    
    # API: Swipe Action
    path('api/swipe/', views.api_swipe_view, name='api_swipe'),
    
    # API: Get Matches
    path('api/matches/', views.api_matches_view, name='api_matches'),
    
    # API: User Stats
    path('api/stats/', views.api_user_stats_view, name='api_stats'),
]
