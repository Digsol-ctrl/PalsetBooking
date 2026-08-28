"""Blog posts and gallery images for the public site.

Images use FileField rather than ImageField on purpose: ImageField requires
Pillow, and this project deploys to shared hosting where adding a compiled
dependency is a risk. Uploads are restricted by extension instead. If Pillow is
installed later, these can be switched to ImageField for dimension validation.
"""

from django.db import models
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from django.utils.text import slugify

IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp', 'gif']
_image_validator = FileExtensionValidator(allowed_extensions=IMAGE_EXTENSIONS)


class Post(models.Model):
    """A news item or trip write-up shown on the public blog."""

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    summary = models.CharField(
        max_length=300, blank=True,
        help_text='Short teaser shown on the blog listing. Leave blank to use the opening of the post.'
    )
    body = models.TextField(help_text='The post itself. Blank lines start a new paragraph.')
    cover_image = models.FileField(
        upload_to='blog/%Y/%m/', blank=True, null=True,
        validators=[_image_validator],
        help_text='Optional header image (JPG, PNG, WEBP or GIF).'
    )
    is_published = models.BooleanField(
        default=True, help_text='Untick to keep this as a draft, hidden from the public site.'
    )
    published_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at', '-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_slug()
        super().save(*args, **kwargs)

    def _unique_slug(self):
        base = slugify(self.title)[:200] or 'post'
        slug = base
        suffix = 2
        while Post.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f'{base}-{suffix}'
            suffix += 1
        return slug

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('content:blog_detail', kwargs={'slug': self.slug})

    @property
    def teaser(self):
        """Summary if given, otherwise the first stretch of the body."""
        if self.summary:
            return self.summary
        text = ' '.join((self.body or '').split())
        return text[:200] + ('...' if len(text) > 200 else '')


class GalleryImage(models.Model):
    """A photo shown in the public gallery, optionally grouped into an album."""

    title = models.CharField(max_length=200, blank=True)
    caption = models.CharField(max_length=300, blank=True)
    image = models.FileField(
        upload_to='gallery/%Y/%m/',
        validators=[_image_validator],
        help_text='JPG, PNG, WEBP or GIF.'
    )
    album = models.CharField(
        max_length=100, blank=True,
        help_text='Optional grouping, e.g. "Victoria Falls trip". Photos with the same album show together.'
    )
    sort_order = models.PositiveSmallIntegerField(
        default=0, help_text='Lower numbers show first within an album.'
    )
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', '-created_at']

    def __str__(self):
        return self.title or self.album or f'Gallery image {self.pk}'

    @property
    def display_album(self):
        return self.album or 'Gallery'
