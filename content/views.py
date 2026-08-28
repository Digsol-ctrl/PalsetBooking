"""Public-facing blog and gallery pages."""

from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views import View

from .models import Post, GalleryImage


def _published_posts():
    """Posts visible to the public: published, and not future-dated."""
    return Post.objects.filter(is_published=True, published_at__lte=timezone.now())


class BlogListView(View):
    def get(self, request):
        paginator = Paginator(_published_posts(), 6)
        page = paginator.get_page(request.GET.get('page'))
        return render(request, 'content/blog_list.html', {
            'page_obj': page,
            'posts': page.object_list,
            'section': 'blog',
        })


class BlogDetailView(View):
    def get(self, request, slug):
        post = get_object_or_404(_published_posts(), slug=slug)
        others = _published_posts().exclude(pk=post.pk)[:3]
        return render(request, 'content/blog_detail.html', {
            'post': post,
            'other_posts': others,
            'section': 'blog',
        })


class GalleryView(View):
    def get(self, request):
        images = GalleryImage.objects.filter(is_published=True)

        # Group into albums, preserving the model's ordering within each
        albums = {}
        for image in images:
            albums.setdefault(image.display_album, []).append(image)

        return render(request, 'content/gallery.html', {
            'albums': sorted(albums.items(), key=lambda pair: pair[0].lower()),
            'total_images': len(images),
            'section': 'gallery',
        })
