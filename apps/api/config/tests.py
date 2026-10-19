"""
Contract tests for the rules in the Axora Finds brief. Run with: python manage.py test
"""
import io
import tempfile
import time
from datetime import timedelta
from unittest import mock

from django.core import signing
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient, APITestCase

from accounts.models import Role, User
from inspections.models import Inspection, InspectionStatus, PaymentStatus
from inspections.views import TOKEN_SALT
from listings.models import Property, Status
from pages.models import ContactMessage, NewsletterSubscriber, SiteSettings

PASSWORD = 'Tr0ub4dor-and-3'


def png(name='photo.png'):
    buffer = io.BytesIO()
    Image.new('RGB', (40, 30), 'red').save(buffer, 'PNG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')


def future_date(days=3):
    return (timezone.localdate() + timedelta(days=days)).isoformat()


class BaseCase(APITestCase):
    fixtures = ['properties']

    def setUp(self):
        cache.clear()  # throttle counters

    def register(self, email, role='seeker'):
        client = APIClient()
        response = client.post(
            '/api/auth/register',
            {'name': 'Ada Obi', 'email': email, 'password': PASSWORD, 'role': role},
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.content)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return client, response.data

    def staff(self):
        return User.objects.create_user('staff@axora.test', PASSWORD, role=Role.STAFF)

    def inspection_payload(self, prop_id, **extra):
        data = {
            'name': 'Chidi Eze', 'phone': '07012345678', 'email': 'chidi@example.com',
            'property': prop_id, 'date': future_date(),
        }
        data.update(extra)
        return data


class ListingTests(BaseCase):
    def test_seed_grid_has_eight_published_rentals_including_onitsha(self):
        response = self.client.get('/api/properties')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 8)
        onitsha = [p for p in response.data['results'] if p['city'] == 'Onitsha']
        self.assertGreaterEqual(len(onitsha), 2)
        for item in onitsha:
            self.assertEqual(item['price'], '300000.00')
            self.assertEqual(item['short_type'], '2 Rooms and parlour')
            self.assertEqual(item['location'], 'Onitsha, Anambra State')
            self.assertTrue(item['cover'].startswith('http'))

    def test_filters(self):
        get = lambda q: self.client.get('/api/properties', q).data['count']  # noqa: E731
        self.assertEqual(get({'state': 'Anambra'}), 3)
        self.assertEqual(get({'city': 'onitsha'}), 2)
        self.assertEqual(get({'max_price': 300000}), 4)
        self.assertEqual(get({'bedrooms': 3}), 3)
        self.assertEqual(get({'type': 'self_contain'}), 1)
        self.assertEqual(get({'q': 'onitsha flat'}), 2)
        self.assertEqual(get({'q': 'nowhere at all'}), 0)

    def test_detail_by_slug(self):
        response = self.client.get('/api/properties/spacious-2-bedroom-flat-at-fegge-onitsha')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['photos']), 3)
        self.assertEqual(response.data['inspection_fee'], '5000.00')
        self.assertIn('Prepaid meter', response.data['amenities'])

    def test_fct_location_label(self):
        response = self.client.get('/api/properties', {'state': 'FCT'})
        self.assertEqual(response.data['results'][0]['location'], 'Abuja, FCT')

    def test_only_owner_accounts_can_submit(self):
        self.assertEqual(self.client.post('/api/properties', {}, format='json').status_code, 401)
        seeker, _ = self.register('seeker@example.com', 'seeker')
        self.assertEqual(seeker.post('/api/properties', {}, format='json').status_code, 403)

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_owner_listing_is_pending_and_hidden_until_staff_publish(self):
        owner, _ = self.register('owner@example.com', 'owner')
        response = owner.post(
            '/api/properties',
            {
                'title': 'Brand new flat', 'property_type': 'flat', 'price': '450000', 'state': 'Anambra',
                'city': 'Nnewi', 'description': 'A lovely flat with plenty of light and space.',
                'bedrooms': 2, 'bathrooms': 2, 'inspection_fee': '2000',
                'amenities': ['Water', 'Light'], 'photos': [png('a.png'), png('b.png')],
                'status': 'published',  # must be ignored
            },
            format='multipart',
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.data['status'], 'pending')
        self.assertEqual(len(response.data['photos']), 2)

        slug = response.data['slug']
        self.assertEqual(self.client.get('/api/properties').data['count'], 8)
        self.assertEqual(self.client.get(f'/api/properties/{slug}').status_code, 404)

        Property.objects.get(slug=slug).publish(self.staff())
        self.assertEqual(self.client.get('/api/properties').data['count'], 9)
        self.assertEqual(self.client.get(f'/api/properties/{slug}').status_code, 200)

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_listing_needs_a_real_image(self):
        owner, _ = self.register('owner2@example.com', 'owner')
        base = {
            'title': 'Flat without photos', 'property_type': 'flat', 'price': '450000', 'state': 'Anambra',
            'city': 'Nnewi', 'description': 'A lovely flat with plenty of light and space.',
        }
        self.assertEqual(owner.post('/api/properties', base, format='multipart').status_code, 400)
        fake = SimpleUploadedFile('x.png', b'not an image', content_type='image/png')
        self.assertEqual(owner.post('/api/properties', {**base, 'photos': [fake]}, format='multipart').status_code, 400)

    def test_cannot_publish_without_photos(self):
        owner = User.objects.create_user('o3@example.com', PASSWORD, role=Role.OWNER)
        prop = Property.objects.create(
            owner=owner, title='Bare', property_type='flat', price=1000, state='Lagos', city='Ikeja', description='x'
        )
        with self.assertRaises(ValidationError):
            prop.publish(self.staff())


# Django's test runner forces DEBUG off; the seeded demo account is only shown with DEBUG on (or is_live).
@override_settings(DEBUG=True)
class InspectionTests(BaseCase):
    fegge = 1  # fee 5000
    woliwo = 2  # no fee

    def test_transfer_request_is_pending_and_unconfirmed_and_issues_token(self):
        response = self.client.post(
            '/api/inspections', self.inspection_payload(self.fegge, payment_choice='transfer'), format='json'
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.data['status'], 'pending')
        self.assertEqual(response.data['payment_status'], 'unpaid')
        self.assertEqual(response.data['fee_amount'], '5000.00')
        self.assertIn('payment_token', response.data)
        self.assertNotIn('account_number', response.data)  # the account is never in this response

    def test_client_cannot_confirm_in_the_same_request(self):
        response = self.client.post(
            '/api/inspections',
            self.inspection_payload(
                self.fegge, payment_choice='transfer', status='confirmed', payment_status='verified', fee_amount='0'
            ),
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        inspection = Inspection.objects.get(pk=response.data['id'])
        self.assertEqual(inspection.status, InspectionStatus.PENDING)
        self.assertEqual(inspection.payment_status, PaymentStatus.UNPAID)
        self.assertEqual(str(inspection.fee_amount), '5000.00')

    def test_in_person_is_unpaid_unconfirmed_with_no_token_or_account(self):
        response = self.client.post(
            '/api/inspections', self.inspection_payload(self.fegge, payment_choice='in_person'), format='json'
        )
        self.assertEqual(response.status_code, 201)
        self.assertNotIn('payment_token', response.data)
        inspection = Inspection.objects.get(pk=response.data['id'])
        self.assertEqual((inspection.status, inspection.payment_status), ('pending', 'unpaid'))
        forged = signing.dumps({'i': inspection.pk}, salt=TOKEN_SALT)
        denied = self.client.get('/api/payments/account', HTTP_X_INSPECTION_TOKEN=forged)
        self.assertEqual(denied.status_code, 403)

    def test_fee_property_requires_a_payment_choice(self):
        response = self.client.post('/api/inspections', self.inspection_payload(self.fegge), format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('payment_choice', response.data)

    def test_no_fee_property(self):
        response = self.client.post('/api/inspections', self.inspection_payload(self.woliwo), format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['payment_status'], 'not_required')
        self.assertNotIn('payment_token', response.data)

    def test_validation(self):
        bad_phone = self.inspection_payload(self.woliwo, phone='abc')
        self.assertEqual(self.client.post('/api/inspections', bad_phone, format='json').status_code, 400)
        past = self.inspection_payload(self.woliwo, date=(timezone.localdate() - timedelta(days=1)).isoformat())
        self.assertEqual(self.client.post('/api/inspections', past, format='json').status_code, 400)
        unknown = self.inspection_payload(9999)
        self.assertEqual(self.client.post('/api/inspections', unknown, format='json').status_code, 400)

    def _transfer_token(self, client=None):
        client = client or self.client
        response = client.post(
            '/api/inspections', self.inspection_payload(self.fegge, payment_choice='transfer'), format='json'
        )
        return response.data['id'], response.data['payment_token']

    def test_account_is_only_given_to_the_creator_of_the_transfer_request(self):
        _, token = self._transfer_token()
        ok = self.client.get('/api/payments/account', HTTP_X_INSPECTION_TOKEN=token)
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.data['account_number'], '0000000000')  # from SiteSettings, not from code
        self.assertEqual(ok.data['amount'], '5000.00')
        self.assertTrue(ok.data['reference'].startswith('AX-'))
        self.assertEqual(ok['Cache-Control'], 'no-store')

        self.assertEqual(self.client.get('/api/payments/account').status_code, 403)
        self.assertEqual(self.client.get('/api/payments/account', HTTP_X_INSPECTION_TOKEN='junk').status_code, 403)
        self.assertEqual(self.client.get('/api/payments/account', {'inspection': 1}).status_code, 403)

    def test_token_expires(self):
        inspection_id, _ = self._transfer_token()
        # A token stamped 31 minutes ago is refused (the limit is 30).
        with mock.patch('time.time', return_value=time.time() - 31 * 60):
            old = signing.dumps({'i': inspection_id}, salt=TOKEN_SALT)
        self.assertEqual(self.client.get('/api/payments/account', HTTP_X_INSPECTION_TOKEN=old).status_code, 403)

    def test_signed_in_creator_is_the_only_one_who_can_see_the_account(self):
        seeker, _ = self.register('payer@example.com')
        _, token = self._transfer_token(seeker)
        self.assertEqual(self.client.get('/api/payments/account', HTTP_X_INSPECTION_TOKEN=token).status_code, 403)
        self.assertEqual(seeker.get('/api/payments/account', HTTP_X_INSPECTION_TOKEN=token).status_code, 200)

    def test_account_hidden_until_staff_mark_it_live(self):
        _, token = self._transfer_token()
        with override_settings(DEBUG=False):
            self.assertEqual(self.client.get('/api/payments/account', HTTP_X_INSPECTION_TOKEN=token).status_code, 503)
            SiteSettings.objects.filter(pk=1).update(is_live=True, account_number='0123456789')
            response = self.client.get('/api/payments/account', HTTP_X_INSPECTION_TOKEN=token)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['account_number'], '0123456789')

    def test_cannot_confirm_until_payment_is_verified(self):
        inspection_id, token = self._transfer_token()
        inspection = Inspection.objects.get(pk=inspection_id)
        staff = self.staff()

        with self.assertRaises(ValidationError):
            inspection.confirm(staff)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Inspection.objects.filter(pk=inspection_id).update(status='confirmed')  # DB guard

        inspection.verify_payment(staff)
        inspection.confirm(staff)
        inspection.refresh_from_db()
        self.assertEqual((inspection.status, inspection.payment_status), ('confirmed', 'verified'))
        self.assertEqual(self.client.get('/api/payments/account', HTTP_X_INSPECTION_TOKEN=token).status_code, 403)

    def test_no_fee_inspection_can_be_confirmed_and_rejected(self):
        a = self.client.post('/api/inspections', self.inspection_payload(self.woliwo), format='json').data['id']
        b = self.client.post('/api/inspections', self.inspection_payload(self.woliwo), format='json').data['id']
        staff = self.staff()
        Inspection.objects.get(pk=a).confirm(staff)
        Inspection.objects.get(pk=b).reject(staff)
        self.assertEqual(Inspection.objects.get(pk=a).status, 'confirmed')
        self.assertEqual(Inspection.objects.get(pk=b).status, 'rejected')


class AuthAndFavoriteTests(BaseCase):
    def test_register_login_refresh_me(self):
        _, data = self.register('Ada.Obi@Example.com')
        self.assertEqual(data['user']['role'], 'seeker')
        self.assertEqual(data['user']['email'], 'ada.obi@example.com')

        login = self.client.post('/api/auth/token', {'email': 'ADA.OBI@example.com', 'password': PASSWORD}, format='json')
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.data['user']['name'], 'Ada Obi')

        refreshed = self.client.post('/api/auth/token/refresh', {'refresh': login.data['refresh']}, format='json')
        self.assertEqual(refreshed.status_code, 200)
        self.assertIn('access', refreshed.data)

        authed = APIClient()
        authed.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        self.assertEqual(authed.get('/api/auth/me').data['email'], 'ada.obi@example.com')
        self.assertEqual(self.client.get('/api/auth/me').status_code, 401)

    def test_bad_login_and_duplicate_and_weak_password(self):
        self.register('dup@example.com')
        self.assertEqual(self.client.post('/api/auth/token', {'email': 'dup@example.com', 'password': 'wrong'}, format='json').status_code, 401)
        again = self.client.post('/api/auth/register', {'name': 'X Y', 'email': 'DUP@example.com', 'password': PASSWORD}, format='json')
        self.assertEqual(again.status_code, 400)
        weak = self.client.post('/api/auth/register', {'name': 'X Y', 'email': 'weak@example.com', 'password': '12345678'}, format='json')
        self.assertEqual(weak.status_code, 400)
        self.assertIn('password', weak.data)

    def test_staff_role_cannot_be_self_assigned(self):
        response = self.client.post(
            '/api/auth/register', {'name': 'Sneaky One', 'email': 'sneaky@example.com', 'password': PASSWORD, 'role': 'staff'}, format='json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(email='sneaky@example.com').exists())

    def test_favorites_persist_per_user_and_only_for_seekers(self):
        seeker, _ = self.register('fan@example.com')
        self.assertEqual(seeker.post('/api/favorites/1').status_code, 201)
        self.assertEqual(seeker.post('/api/favorites/1').status_code, 200)  # idempotent
        self.assertEqual(seeker.post('/api/favorites/3').status_code, 201)
        self.assertEqual({p['id'] for p in seeker.get('/api/favorites').data}, {1, 3})

        # A fresh login still sees them.
        login = self.client.post('/api/auth/token', {'email': 'fan@example.com', 'password': PASSWORD}, format='json')
        again = APIClient()
        again.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        self.assertEqual(len(again.get('/api/favorites').data), 2)

        # Another seeker has their own list.
        other, _ = self.register('other@example.com')
        self.assertEqual(other.get('/api/favorites').data, [])

        self.assertEqual(seeker.delete('/api/favorites/1').status_code, 204)
        self.assertEqual({p['id'] for p in seeker.get('/api/favorites').data}, {3})

        owner, _ = self.register('landlord@example.com', 'owner')
        self.assertEqual(owner.post('/api/favorites/1').status_code, 403)
        self.assertEqual(self.client.get('/api/favorites').status_code, 401)
        self.assertEqual(seeker.post('/api/favorites/9999').status_code, 404)

    def test_newsletter_and_contact(self):
        for _ in range(2):
            self.assertEqual(self.client.post('/api/newsletter', {'email': 'Reader@Example.com'}, format='json').status_code, 201)
        self.assertEqual(NewsletterSubscriber.objects.count(), 1)
        self.assertEqual(self.client.post('/api/newsletter', {'email': 'nope'}, format='json').status_code, 400)

        sent = self.client.post('/api/contact', {'name': 'Ife', 'email': 'ife@example.com', 'message': 'Is the flat still free?'}, format='json')
        self.assertEqual(sent.status_code, 201)
        self.assertEqual(ContactMessage.objects.count(), 1)


class AdminQueueTests(BaseCase):
    """The staff queue lives in Django admin: verify payment -> confirm/reject, publish/reject listings."""

    def setUp(self):
        super().setUp()
        self.admin_user = User.objects.create_superuser('admin@axora.test', PASSWORD)
        self.client.force_login(self.admin_user)

    def run_action(self, model_path, action, pks):
        return self.client.post(
            f'/admin/{model_path}/', {'action': action, '_selected_action': pks, 'index': 0}, follow=True
        )

    def test_admin_pages_render(self):
        owner = User.objects.get(email='seed-owner@axora.test')
        insp = self.client.post(
            '/api/inspections',
            {'name': 'A B', 'phone': '07012345678', 'email': 'a@b.co', 'property': 1, 'date': future_date(), 'payment_choice': 'transfer'},
            format='json',
        ).data['id']
        for url in [
            '/admin/', '/admin/accounts/user/', '/admin/accounts/user/add/', f'/admin/accounts/user/{owner.pk}/change/',
            '/admin/listings/property/', '/admin/listings/property/add/', '/admin/listings/property/1/change/',
            '/admin/inspections/inspection/', f'/admin/inspections/inspection/{insp}/change/',
            '/admin/pages/sitesettings/', '/admin/pages/sitesettings/1/change/',
            '/admin/pages/newslettersubscriber/', '/admin/pages/contactmessage/',
        ]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
        # Inspections are created by the website only.
        self.assertEqual(self.client.get('/admin/inspections/inspection/add/').status_code, 403)

    def test_staff_can_create_users_with_roles(self):
        response = self.client.post(
            '/admin/accounts/user/add/',
            {'email': 'new.staff@axora.test', 'first_name': 'New', 'last_name': 'Staff', 'role': 'staff',
             'password1': PASSWORD, 'password2': PASSWORD},
        )
        self.assertEqual(response.status_code, 302, getattr(response, 'content', b'')[:500])
        created = User.objects.get(email='new.staff@axora.test')
        self.assertTrue(created.is_staff)
        self.assertEqual(created.role, 'staff')

    def test_verify_then_confirm_inspection_in_admin(self):
        paid = self.client.post(
            '/api/inspections',
            {'name': 'A B', 'phone': '07012345678', 'email': 'a@b.co', 'property': 1, 'date': future_date(), 'payment_choice': 'in_person'},
            format='json',
        ).data['id']
        path = 'inspections/inspection'

        self.run_action(path, 'confirm_inspections', [paid])  # blocked: payment not verified
        self.assertEqual(Inspection.objects.get(pk=paid).status, 'pending')

        self.run_action(path, 'mark_payment_verified', [paid])
        inspection = Inspection.objects.get(pk=paid)
        self.assertEqual(inspection.payment_status, 'verified')
        self.assertEqual(inspection.payment_verified_by, self.admin_user)
        self.assertEqual(inspection.status, 'pending')  # verifying does not confirm

        self.run_action(path, 'confirm_inspections', [paid])
        inspection.refresh_from_db()
        self.assertEqual(inspection.status, 'confirmed')
        self.assertEqual(inspection.decided_by, self.admin_user)

    def test_reject_inspection_in_admin(self):
        pk = self.client.post(
            '/api/inspections',
            {'name': 'A B', 'phone': '07012345678', 'email': 'a@b.co', 'property': 2, 'date': future_date()},
            format='json',
        ).data['id']
        self.run_action('inspections/inspection', 'reject_inspections', [pk])
        self.assertEqual(Inspection.objects.get(pk=pk).status, 'rejected')

    def test_publish_and_reject_listings_in_admin(self):
        owner = User.objects.get(email='seed-owner@axora.test')
        with_photo = Property.objects.create(
            owner=owner, title='Pending with photo', property_type='flat', price=1000, state='Lagos', city='Ikeja',
            description='A pending listing waiting for staff review.',
        )
        with_photo.photos.create(external_url='https://example.com/a.jpg')
        no_photo = Property.objects.create(
            owner=owner, title='Pending bare', property_type='flat', price=1000, state='Lagos', city='Ikeja',
            description='A pending listing without any photo at all.',
        )
        to_reject = Property.objects.create(
            owner=owner, title='Pending to reject', property_type='flat', price=1000, state='Lagos', city='Ikeja',
            description='A pending listing that staff will reject.',
        )
        self.assertEqual(self.client.get('/api/properties').data['count'], 8)

        self.run_action('listings/property', 'publish_listings', [with_photo.pk, no_photo.pk])
        with_photo.refresh_from_db()
        no_photo.refresh_from_db()
        self.assertEqual(with_photo.status, Status.PUBLISHED)
        self.assertEqual(with_photo.reviewed_by, self.admin_user)
        self.assertEqual(no_photo.status, Status.PENDING)  # needs a photo first
        self.assertEqual(self.client.get('/api/properties').data['count'], 9)

        self.run_action('listings/property', 'reject_listings', [to_reject.pk])
        to_reject.refresh_from_db()
        self.assertEqual(to_reject.status, Status.REJECTED)
        self.assertEqual(self.client.get(f'/api/properties/{to_reject.slug}').status_code, 404)

    def test_bank_account_is_edited_in_site_settings(self):
        response = self.client.post(
            '/admin/pages/sitesettings/1/change/',
            {'bank_name': 'Real Bank', 'account_name': 'Axora Finds Ltd', 'account_number': '0123456789',
             'transfer_note': 'Use your reference.', 'is_live': 'on'},
        )
        self.assertEqual(response.status_code, 302)
        site = SiteSettings.load()
        self.assertEqual((site.bank_name, site.account_number, site.is_live), ('Real Bank', '0123456789', True))
        self.assertFalse(self.client.get('/admin/pages/sitesettings/add/').status_code == 200)  # singleton
