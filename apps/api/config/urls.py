from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.views import LoginView, MeView, RegisterView
from inspections.views import InspectionCreateView, PaymentAccountView
from listings.views import FavoriteDetailView, FavoriteListView, PropertyViewSet
from pages.views import ContactView, NewsletterView

admin.site.site_header = 'Axora Finds staff'
admin.site.site_title = 'Axora Finds'
admin.site.index_title = 'Verify payments, confirm inspections, publish listings'

# trailing_slash=False so the URLs match the API contract exactly (/api/properties, /api/properties/:slug).
router = SimpleRouter(trailing_slash=False)
router.register('properties', PropertyViewSet, basename='property')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/register', RegisterView.as_view(), name='register'),
    path('api/auth/token', LoginView.as_view(), name='token'),
    path('api/auth/token/refresh', TokenRefreshView.as_view(), name='token-refresh'),
    path('api/auth/me', MeView.as_view(), name='me'),
    path('api/inspections', InspectionCreateView.as_view(), name='inspection-create'),
    path('api/payments/account', PaymentAccountView.as_view(), name='payment-account'),
    path('api/newsletter', NewsletterView.as_view(), name='newsletter'),
    path('api/contact', ContactView.as_view(), name='contact'),
    path('api/favorites', FavoriteListView.as_view(), name='favorite-list'),
    path('api/favorites/<int:pk>', FavoriteDetailView.as_view(), name='favorite-detail'),
    path('api/', include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
