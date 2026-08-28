from django.contrib import admin

from .models import Post, GalleryImage


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_published', 'published_at')
    list_filter = ('is_published',)
    search_fields = ('title', 'body')
    prepopulated_fields = {'slug': ('title',)}


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'album', 'sort_order', 'is_published', 'created_at')
    list_filter = ('is_published', 'album')
