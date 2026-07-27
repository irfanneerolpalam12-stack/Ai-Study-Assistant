"""
Template context processors for the AI Study Assistant.
"""

from django.conf import settings


def google_auth(request):
    """Expose GOOGLE_CLIENT_ID to every template rendered by Django."""
    return {
        'GOOGLE_CLIENT_ID': getattr(settings, 'GOOGLE_CLIENT_ID', ''),
    }
