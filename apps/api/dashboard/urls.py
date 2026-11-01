from django.urls import path

from .views import (
    ContactMessageDetailView,
    ContactMessageListView,
    EmailStatusView,
    EmailTestView,
    InspectionConfirmView,
    InspectionListView,
    InspectionRejectView,
    InspectionResendEmailView,
    InspectionVerifyPaymentView,
    ListingListView,
    ListingPublishView,
    ListingRejectView,
    ListingResendEmailView,
    OverviewView,
    ReviewListView,
    ReviewPublishView,
    ReviewResendEmailView,
    ReviewUnpublishView,
    SiteSettingsView,
    SubscriberDetailView,
    SubscriberListView,
    UserListView,
)

urlpatterns = [
    path('overview', OverviewView.as_view(), name='staff-overview'),

    path('listings', ListingListView.as_view(), name='staff-listing-list'),
    path('listings/<int:pk>/publish', ListingPublishView.as_view(), name='staff-listing-publish'),
    path('listings/<int:pk>/reject', ListingRejectView.as_view(), name='staff-listing-reject'),
    path('listings/<int:pk>/resend-email', ListingResendEmailView.as_view(), name='staff-listing-resend-email'),

    path('inspections', InspectionListView.as_view(), name='staff-inspection-list'),
    path('inspections/<int:pk>/verify-payment', InspectionVerifyPaymentView.as_view(), name='staff-inspection-verify'),
    path('inspections/<int:pk>/confirm', InspectionConfirmView.as_view(), name='staff-inspection-confirm'),
    path('inspections/<int:pk>/reject', InspectionRejectView.as_view(), name='staff-inspection-reject'),
    path('inspections/<int:pk>/resend-email', InspectionResendEmailView.as_view(), name='staff-inspection-resend-email'),

    path('reviews', ReviewListView.as_view(), name='staff-review-list'),
    path('reviews/<int:pk>/publish', ReviewPublishView.as_view(), name='staff-review-publish'),
    path('reviews/<int:pk>/unpublish', ReviewUnpublishView.as_view(), name='staff-review-unpublish'),
    path('reviews/<int:pk>/resend-email', ReviewResendEmailView.as_view(), name='staff-review-resend-email'),

    path('messages', ContactMessageListView.as_view(), name='staff-message-list'),
    path('messages/<int:pk>', ContactMessageDetailView.as_view(), name='staff-message-detail'),

    path('subscribers', SubscriberListView.as_view(), name='staff-subscriber-list'),
    path('subscribers/<int:pk>', SubscriberDetailView.as_view(), name='staff-subscriber-detail'),

    path('settings', SiteSettingsView.as_view(), name='staff-settings'),
    path('users', UserListView.as_view(), name='staff-user-list'),

    path('email', EmailStatusView.as_view(), name='staff-email-status'),
    path('email/test', EmailTestView.as_view(), name='staff-email-test'),
]
