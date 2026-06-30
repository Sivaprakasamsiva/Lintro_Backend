"""Categories URLs."""
from django.urls import path
from .views import (
    CategoryListView, CategoryDetailView,
    CategoryCreateView, CategoryUpdateView, CategoryDeleteView,
    CategoryFieldListView, CategoryFieldDetailView,
)

urlpatterns = [
    path('', CategoryListView.as_view(), name='category-list'),
    path('<slug:slug>/', CategoryDetailView.as_view(), name='category-detail'),
    # Admin
    path('admin/create/', CategoryCreateView.as_view(), name='category-create'),
    path('admin/<int:pk>/update/', CategoryUpdateView.as_view(), name='category-update'),
    path('admin/<int:pk>/delete/', CategoryDeleteView.as_view(), name='category-delete'),
    path('admin/<int:category_pk>/fields/', CategoryFieldListView.as_view(), name='category-field-list'),
    path('admin/<int:category_pk>/fields/<int:pk>/', CategoryFieldDetailView.as_view(), name='category-field-detail'),
]
