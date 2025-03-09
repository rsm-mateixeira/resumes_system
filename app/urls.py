from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path("chat/", views.chatbot_response, name="chatbot_response"),
    path('resumes/', views.resumes_page_view, name='resumes'),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)