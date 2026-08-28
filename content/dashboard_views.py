"""Dashboard CRUD for blog posts and gallery images.

Access reuses the rides dashboard helpers so there is a single definition of who
may see the dashboard and who may edit it.
"""

from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from rides.dashboard_views import _require_dashboard, _can_edit

from .forms import PostForm, GalleryImageForm
from .models import Post, GalleryImage


def _require_edit(view_fn):
    """Block viewers from changing content, mirroring the bookings dashboard."""
    def wrapper(self, request, *args, **kwargs):
        if not _can_edit(request.user):
            messages.error(request, 'You do not have permission to change content.')
            return redirect('dashboard_content:posts')
        return view_fn(self, request, *args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Blog posts
# ---------------------------------------------------------------------------

class PostListView(View):
    @_require_dashboard
    def get(self, request):
        paginator = Paginator(Post.objects.all(), 15)
        page = paginator.get_page(request.GET.get('page'))
        return render(request, 'dashboard/content/posts.html', {
            'page_obj': page,
            'posts': page.object_list,
            'can_edit': _can_edit(request.user),
        })


class PostCreateView(View):
    @_require_dashboard
    @_require_edit
    def get(self, request):
        return render(request, 'dashboard/content/post_form.html', {
            'form': PostForm(),
            'is_new': True,
        })

    @_require_dashboard
    @_require_edit
    def post(self, request):
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save()
            messages.success(request, f'Post "{post.title}" saved.')
            return redirect('dashboard_content:posts')
        return render(request, 'dashboard/content/post_form.html', {
            'form': form,
            'is_new': True,
        })


class PostEditView(View):
    @_require_dashboard
    @_require_edit
    def get(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        return render(request, 'dashboard/content/post_form.html', {
            'form': PostForm(instance=post),
            'post': post,
            'is_new': False,
        })

    @_require_dashboard
    @_require_edit
    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, f'Post "{post.title}" updated.')
            return redirect('dashboard_content:posts')
        return render(request, 'dashboard/content/post_form.html', {
            'form': form,
            'post': post,
            'is_new': False,
        })


class PostDeleteView(View):
    @_require_dashboard
    @_require_edit
    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        title = post.title
        post.delete()
        messages.success(request, f'Post "{title}" deleted.')
        return redirect('dashboard_content:posts')


# ---------------------------------------------------------------------------
# Gallery
# ---------------------------------------------------------------------------

class GalleryManageView(View):
    @_require_dashboard
    def get(self, request):
        images = GalleryImage.objects.all()
        albums = sorted({img.album for img in images if img.album})
        return render(request, 'dashboard/content/gallery.html', {
            'images': images,
            'albums': albums,
            'form': GalleryImageForm(),
            'can_edit': _can_edit(request.user),
        })

    @_require_dashboard
    @_require_edit
    def post(self, request):
        form = GalleryImageForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Photo added to the gallery.')
            return redirect('dashboard_content:gallery')

        images = GalleryImage.objects.all()
        albums = sorted({img.album for img in images if img.album})
        messages.error(request, 'Could not add that photo. Please check the file and try again.')
        return render(request, 'dashboard/content/gallery.html', {
            'images': images,
            'albums': albums,
            'form': form,
            'can_edit': True,
        })


class GalleryDeleteView(View):
    @_require_dashboard
    @_require_edit
    def post(self, request, pk):
        image = get_object_or_404(GalleryImage, pk=pk)
        image.delete()
        messages.success(request, 'Photo removed from the gallery.')
        return redirect('dashboard_content:gallery')


class GalleryToggleView(View):
    """Show or hide a photo without deleting it."""

    @_require_dashboard
    @_require_edit
    def post(self, request, pk):
        image = get_object_or_404(GalleryImage, pk=pk)
        image.is_published = not image.is_published
        image.save(update_fields=['is_published'])
        messages.success(
            request,
            'Photo is now visible on the site.' if image.is_published else 'Photo is now hidden from the site.'
        )
        return redirect('dashboard_content:gallery')
