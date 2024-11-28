"""
URL configuration for worker project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
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
import jwt
from django.urls import path
from .models import ParamLink
from django.conf import settings
from django.shortcuts import render
from django.contrib import admin, messages
from .utils import deobfuscate_data, json, produce

def commonLogic(request, data, trusted):
    _, new = ParamLink.objects.get_or_create(string = data)
    if new:
        decoded_data = jwt.decode(
            deobfuscate_data(data), 
            settings.SECRET_KEY, 
            algorithms=['HS256']
        )
        decoded_data["trusted"] = trusted
        produce(
            queue = decoded_data["pseudo_queue"],
            data = jwt.encode(
                decoded_data, 
                settings.SECRET_KEY, 
                algorithm='HS256'
            )
        )
        messages.success(request, "Done")
    else:
        messages.warning(request, "Nothing")

def confirmView(request, data):
    commonLogic(
        data = data,
        trusted = True,
        request = request
    )
    return render(request=request, template_name="index.html")

def cancelView(request, data):
    commonLogic(
        data = data,
        trusted = False,
        request = request
    )
    return render(request=request, template_name="index.html")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('<str:data>/confirm', confirmView),
    path('<str:data>/cancel', cancelView)
]
