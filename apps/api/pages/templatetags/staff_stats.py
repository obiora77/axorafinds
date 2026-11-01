"""Counts and email health for the Django admin home page."""
from django import template

from config.emails import email_status
from inspections.models import Inspection, InspectionStatus, PaymentStatus
from listings.models import Property, Status
from pages.models import ContactMessage, NewsletterSubscriber, Review

register = template.Library()


@register.simple_tag
def staff_stats() -> dict:
    listings = Property.objects.all()
    inspections = Inspection.objects.all()
    reviews = Review.objects.all()
    return {
        'listings': {
            'pending': listings.filter(status=Status.PENDING).count(),
            'published': listings.filter(status=Status.PUBLISHED).count(),
            'rejected': listings.filter(status=Status.REJECTED).count(),
        },
        'inspections': {
            'pending': inspections.filter(status=InspectionStatus.PENDING).count(),
            'awaiting_payment': inspections.filter(
                status=InspectionStatus.PENDING,
                payment_status=PaymentStatus.UNPAID,
                fee_amount__gt=0,
            ).count(),
            'ready_to_confirm': inspections.filter(
                status=InspectionStatus.PENDING,
                payment_status__in=[PaymentStatus.VERIFIED, PaymentStatus.NOT_REQUIRED],
            ).count(),
        },
        'reviews': {
            'pending': reviews.filter(is_published=False).count(),
            'published': reviews.filter(is_published=True).count(),
        },
        'contacts': ContactMessage.objects.count(),
        'subscribers': NewsletterSubscriber.objects.count(),
        'email': email_status(),
    }
