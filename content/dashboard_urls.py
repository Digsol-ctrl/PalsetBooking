from django.urls import path

from . import dashboard_views

app_name = 'dashboard_content'

urlpatterns = [
    # Blog
    path('blog/', dashboard_views.PostListView.as_view(), name='posts'),
    path('blog/new/', dashboard_views.PostCreateView.as_view(), name='post_create'),
    path('blog/<int:pk>/edit/', dashboard_views.PostEditView.as_view(), name='post_edit'),
    path('blog/<int:pk>/delete/', dashboard_views.PostDeleteView.as_view(), name='post_delete'),

    # Gallery
    path('gallery/', dashboard_views.GalleryManageView.as_view(), name='gallery'),
    path('gallery/<int:pk>/delete/', dashboard_views.GalleryDeleteView.as_view(), name='gallery_delete'),
    path('gallery/<int:pk>/toggle/', dashboard_views.GalleryToggleView.as_view(), name='gallery_toggle'),
]
