from django.urls import path

from .views import BlogListView, BlogDetailView, GalleryView

app_name = 'content'

urlpatterns = [
    path('blog/', BlogListView.as_view(), name='blog_list'),
    path('blog/<slug:slug>/', BlogDetailView.as_view(), name='blog_detail'),
    path('gallery/', GalleryView.as_view(), name='gallery'),
]
