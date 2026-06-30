"""Profile URLs."""
from django.urls import path
from .views import ProfileView, PublicUserView

urlpatterns = [
    path('me/', ProfileView.as_view(), name='my-profile'),
    path('<int:user_id>/public/', PublicUserView.as_view(), name='public-user'),
]
