from django.urls import path
from django.conf import settings
from . import views

urlpatterns = [
    path('favicon.ico', views.favicon_view, name='favicon'),
]

# Add other web endpoints only if available
if settings.IS_AVAILABLE:
    urlpatterns.extend([
        path('hero-list/', views.MLBBWebViews.hero_list_web, name='hero_list_web'),
        path('hero-rank/', views.MLBBWebViews.hero_rank_web, name='hero_rank_web'),
        path('hero-position/', views.MLBBWebViews.hero_position_web, name='hero_position_web'),
        path('hero-detail/<int:hero_id>/', views.MLBBWebViews.hero_detail_web, name='hero_detail_web'),
    ])

# Draft System URLs - always available
urlpatterns.extend([
    path('draft/', views.draft_home, name='draft_home'),
    path('draft/create/', views.create_draft, name='create_draft'),
    path('draft/<int:draft_id>/', views.draft_session, name='draft_session'),
    path('draft/<int:draft_id>/action/', views.draft_action, name='draft_action'),
    path('draft/<int:draft_id>/data/', views.draft_data, name='draft_data'),
    path('draft/<int:draft_id>/save-template/', views.save_template, name='save_template'),
    path('draft/<int:draft_id>/recommendations/', views.get_recommendations, name='get_recommendations'),
    path('draft/<int:draft_id>/analytics/', views.draft_analytics, name='draft_analytics'),
    path('api/heroes/', views.get_heroes_api, name='get_heroes_api'),
    path('api/hero/<int:hero_id>/details/', views.get_hero_details_api, name='get_hero_details_api'),
])
