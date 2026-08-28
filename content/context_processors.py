"""Template context shared by the public blog and gallery pages."""

from django.conf import settings


def main_site(request):
    """Expose the main marketing site URL so templates can link back to it."""
    return {'MAIN_SITE_URL': getattr(settings, 'MAIN_SITE_URL', 'https://easytransit.co.zw')}
