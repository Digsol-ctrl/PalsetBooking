from django import forms

from .models import Post, GalleryImage


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'summary', 'body', 'cover_image', 'is_published', 'published_at']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-ctrl', 'placeholder': 'e.g. Our trip to Victoria Falls'}),
            'summary': forms.TextInput(attrs={'class': 'form-ctrl', 'placeholder': 'One-line teaser for the listing page'}),
            'body': forms.Textarea(attrs={'class': 'form-ctrl', 'rows': 14, 'placeholder': 'Write your news or trip report here...'}),
            'cover_image': forms.ClearableFileInput(attrs={'class': 'form-ctrl', 'accept': 'image/*'}),
            'published_at': forms.DateTimeInput(attrs={'class': 'form-ctrl', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['published_at'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M']
        self.fields['summary'].required = False


class GalleryImageForm(forms.ModelForm):
    class Meta:
        model = GalleryImage
        fields = ['image', 'title', 'caption', 'album', 'sort_order', 'is_published']
        widgets = {
            'image': forms.ClearableFileInput(attrs={'class': 'form-ctrl', 'accept': 'image/*'}),
            'title': forms.TextInput(attrs={'class': 'form-ctrl', 'placeholder': 'Optional title'}),
            'caption': forms.TextInput(attrs={'class': 'form-ctrl', 'placeholder': 'Optional caption shown under the photo'}),
            'album': forms.TextInput(attrs={'class': 'form-ctrl', 'placeholder': 'e.g. Victoria Falls trip', 'list': 'album_options'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-ctrl', 'min': 0}),
        }
