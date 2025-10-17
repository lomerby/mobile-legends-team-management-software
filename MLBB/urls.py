"""
URL configuration for MLBB project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include
from django.http import HttpResponseRedirect

def redirect_to_draft(request):
    return HttpResponseRedirect('/draft/')

urlpatterns = [
    path('', redirect_to_draft, name='redirect_to_draft'),
    path('api/', include('apps.mlbb_api.urls')),
    # path('api/', include('apps.mpl_api.urls')),  # Temporarily disabled due to crypto issues
    path('', include('apps.mlbb_web.urls')),
]
