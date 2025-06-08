from django.urls import path
from .views import WebcamStreamView,Categories

urlpatterns = [
    path('stream/', WebcamStreamView.as_view(), name='WebcamStreamView'),
    path('categories',Categories.as_view())
]
