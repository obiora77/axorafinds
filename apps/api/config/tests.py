"""
Contract tests for the rules in the Axora Finds brief. Run with: python manage.py test
"""
import io
import tempfile
import time
from datetime import timedelta
from unittest import mock

from django.core import mail, signing
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient, APITestCase

from accounts.models import Role, User
from config.emails import email_enabled, send_test_email
from inspections.models import Inspection, InspectionStatus, PaymentStatus
from inspections.views import TOKEN_SALT
from listings.models import Property, Status
from pages.models import ContactMessage, NewsletterSubscriber, Review, SiteSettings

PASSWORD = 'Tr0ub4dor-and-3'


def png(name='photo.png'):
    buffer = io.BytesIO()
    Image.new('RGB', (40, 30), 'red').save(buffer, 'PNG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')


def future_date(days=3):
    return (timezone.localdate() + timedelta(days=days)).isoformat()


# Tests must never touch a real mail server, whatever .env says.
@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_HOST='',
    EMAIL_HOST_USER='',
    EMAIL_HOST_PASSWORD='',
    EMAIL_USE_TLS=False,
    EMAIL_USE_SSL=False,
)
class BaseCase(APITestCase):
    fixtures = ['properties']

    def setUp(self):
        cache.clear()  # throttle counters
        mail.outbox.clear()  # emails are not reset between test methods

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

    def test_owner_sees_their_own_listings_in_every_state(self):
        owner, _ = self.register('mine@example.com', 'owner')
        user = User.objects.get(email='mine@example.com')
        pending = Property.objects.create(
            owner=user, title='Pending flat', property_type='flat', price=1000, state='Lagos', city='Ikeja',
            description='This listing is still waiting for review.',
        )

        mine = owner.get('/api/properties/mine')
        self.assertEqual(mine.status_code, 200)
        self.assertEqual([p['id'] for p in mine.data], [pending.pk])
        self.assertEqual(mine.data[0]['status'], 'pending')

        seeker, _ = self.register('notmine@example.com', 'seeker')
        self.assertEqual(seeker.get('/api/properties/mine').status_code, 403)
        self.assertEqual(self.client.get('/api/properties/mine').status_code, 401)


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


class ReviewTests(BaseCase):
    """Home page testimonials: public read, signed-in submission, staff moderation."""

    def test_seeded_reviews_are_public_with_an_average(self):
        response = self.client.get('/api/reviews')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 6)
        self.assertEqual(response.data['average_rating'], 4.7)
        self.assertEqual(len(response.data['results']), 6)
        self.assertEqual(response.data['results'][0]['name'], 'Chiamaka Okafor')

    def test_unpublished_reviews_are_hidden_and_the_limit_is_capped(self):
        Review.objects.create(name='Hidden', rating=1, text='This review has not been approved.', is_published=False)
        self.assertEqual(self.client.get('/api/reviews').data['count'], 6)
        self.assertEqual(len(self.client.get('/api/reviews', {'limit': 2}).data['results']), 2)

    def test_signed_in_visitors_can_submit_a_review_for_moderation(self):
        payload = {'rating': 5, 'text': 'I found my flat in four days.'}
        self.assertEqual(self.client.post('/api/reviews', payload, format='json').status_code, 401)

        seeker, _ = self.register('reviewer@example.com')
        response = seeker.post(
            '/api/reviews', {**payload, 'location': 'Onitsha, Anambra State'}, format='json'
        )
        self.assertEqual(response.status_code, 201, response.content)

        review = Review.objects.get(user__email='reviewer@example.com')
        self.assertEqual(review.name, 'Ada Obi')
        self.assertFalse(review.is_published)
        self.assertEqual(self.client.get('/api/reviews').data['count'], 6)

        self.assertEqual(seeker.post('/api/reviews', {'rating': 6, 'text': 'Too many stars.'}, format='json').status_code, 400)
        self.assertEqual(seeker.post('/api/reviews', {'rating': 4, 'text': 'short'}, format='json').status_code, 400)


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
            '/admin/pages/sitesettings/email-test/',
            '/admin/pages/newslettersubscriber/', '/admin/pages/contactmessage/',
            '/admin/pages/review/', '/admin/pages/review/1/change/',
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
        # A role "staff" account can work the queues in Django admin straight away.
        self.assertTrue(created.has_perm('listings.change_property'))
        self.assertTrue(created.has_perm('inspections.change_inspection'))
        self.assertTrue(created.has_perm('pages.change_review'))
        self.assertFalse(created.has_perm('accounts.change_user'))

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

    def test_staff_publish_reviews_in_admin(self):
        review = Review.objects.create(name='Waiting', rating=4, text='A testimonial waiting for review.')
        self.assertFalse(review.is_published)

        self.run_action('pages/review', 'publish_reviews', [review.pk])
        review.refresh_from_db()
        self.assertTrue(review.is_published)
        self.assertEqual(self.client.get('/api/reviews').data['count'], 7)

        self.run_action('pages/review', 'unpublish_reviews', [review.pk])
        review.refresh_from_db()
        self.assertFalse(review.is_published)
        self.assertEqual(self.client.get('/api/reviews').data['count'], 6)


@override_settings(
    TEAM_EMAIL='team@axora.test',
    DEFAULT_FROM_EMAIL='Axora Finds <no-reply@axora.test>',
    SITE_URL='https://axora.test',
)
class EmailTests(BaseCase):
    """Every transactional flow renders both a text and an HTML part."""

    def html(self, message):
        self.assertTrue(message.alternatives)
        html, mimetype = message.alternatives[0]
        self.assertEqual(mimetype, 'text/html')
        return html

    def test_every_message_has_both_html_and_text_templates(self):
        from django.template.loader import get_template

        from config.emails import EMAIL_TEMPLATES

        for name in EMAIL_TEMPLATES:
            for extension in ('html', 'txt'):
                # Raises TemplateDoesNotExist if a part is missing; this is the bug that
                # previously made every send fail silently.
                get_template(f'emails/{name}.{extension}')

    def test_smtp_disconnect_error_includes_network_guidance(self):
        import smtplib

        from config.emails import _smtp_guidance

        hint = _smtp_guidance(smtplib.SMTPServerDisconnected('Connection unexpectedly closed'))
        self.assertIn('port 465', hint)
        self.assertIn('Outbound SMTP', hint)

    def test_registration_sends_the_welcome_email(self):
        self.register('welcome@example.com')

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ['welcome@example.com'])
        self.assertEqual(message.subject, 'Welcome to Axora Finds')
        self.assertEqual(message.from_email, 'Axora Finds <no-reply@axora.test>')
        self.assertEqual(message.reply_to, ['team@axora.test'])
        self.assertIn('Welcome, Ada', message.body)
        self.assertIn('seeker account is ready', message.body)
        self.assertIn('https://axora.test/properties', message.body)
        self.assertIn('Welcome, Ada', self.html(message))

    def test_html_email_embeds_the_logo_inline(self):
        self.register('logo@example.com')

        message = mail.outbox[0]
        html = self.html(message)
        self.assertIn('cid:axora-finds-logo', html)

        mime = message.message()
        self.assertEqual(mime.get_content_type(), 'multipart/related')
        logos = [part for part in mime.walk() if part.get_content_maintype() == 'image']
        self.assertEqual(len(logos), 1)
        self.assertEqual(logos[0].get('Content-ID'), '<axora-finds-logo>')
        self.assertEqual(logos[0].get_content_disposition(), 'inline')
        self.assertEqual(logos[0].get_content_type(), 'image/png')

    def test_newsletter_subscription_emails_the_subscriber_and_team(self):
        response = self.client.post(
            '/api/newsletter', {'email': 'Reader@Example.com'}, format='json'
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 2)

        subscriber, team = mail.outbox
        self.assertEqual(subscriber.to, ['reader@example.com'])
        self.assertEqual(subscriber.subject, 'You are subscribed to Axora Finds')
        self.assertIn('https://axora.test/properties', subscriber.body)
        self.assertIn('You are subscribed', self.html(subscriber))

        self.assertEqual(team.to, ['team@axora.test'])
        self.assertEqual(team.subject, 'New newsletter subscriber')
        self.assertIn('reader@example.com', team.body)

        # Subscribing the same address again does not send duplicate mail.
        mail.outbox.clear()
        self.client.post('/api/newsletter', {'email': 'reader@example.com'}, format='json')
        self.assertEqual(mail.outbox, [])

    def test_contact_form_notifies_the_team_and_acknowledges_the_visitor(self):
        response = self.client.post(
            '/api/contact',
            {'name': 'Ife', 'email': 'ife@example.com', 'message': 'Is the flat still free?'},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 2)

        team, visitor = mail.outbox
        self.assertEqual(team.to, ['team@axora.test'])
        self.assertEqual(team.reply_to, ['ife@example.com'])  # staff can reply straight to the visitor
        self.assertIn('New contact message', team.subject)
        self.assertIn('Is the flat still free?', team.body)

        self.assertEqual(visitor.to, ['ife@example.com'])
        self.assertEqual(visitor.reply_to, ['team@axora.test'])
        self.assertEqual(visitor.subject, 'We received your message')
        self.assertIn('Is the flat still free?', visitor.body)
        self.assertIn('Is the flat still free?', self.html(visitor))

    def test_plain_text_parts_are_not_html_escaped(self):
        message = "It's a lovely flat, isn't it?"
        self.client.post(
            '/api/contact',
            {'name': "Ife O'Brien", 'email': 'ife@example.com', 'message': message},
            format='json',
        )
        team, visitor = mail.outbox
        for email_message in (team, visitor):
            self.assertIn(message, email_message.body)
            self.assertNotIn('&#x27;', email_message.body)
            self.assertIn("Ife O'Brien", email_message.body)

    def test_transfer_request_emails_never_expose_the_bank_account(self):
        site = SiteSettings.load()
        site.bank_name = 'Test Bank'
        site.account_name = 'Axora Finds Holdings'
        site.account_number = '9876543210'
        site.save()

        response = self.client.post(
            '/api/inspections', self.inspection_payload(1, payment_choice='transfer'), format='json'
        )
        self.assertEqual(response.status_code, 201, response.content)
        inspection = Inspection.objects.get(pk=response.data['id'])
        self.assertEqual(len(mail.outbox), 2)

        team, visitor = mail.outbox
        combined = visitor.body + self.html(visitor) + team.body + self.html(team)
        for detail in ('Test Bank', 'Axora Finds Holdings', '9876543210'):
            self.assertNotIn(detail, combined)

        self.assertEqual(visitor.to, ['chidi@example.com'])
        self.assertIn(f'inspection request for {inspection.property.title}', visitor.body)
        self.assertIn(inspection.reference, visitor.body)
        self.assertIn('we do not include bank details in email', visitor.body)
        self.assertIn(f'https://axora.test/properties/{inspection.property.slug}', visitor.body)

        self.assertEqual(team.to, ['team@axora.test'])
        self.assertEqual(team.reply_to, ['chidi@example.com'])
        self.assertIn('New inspection request', team.subject)
        self.assertIn('07012345678', team.body)

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_listing_submission_emails_the_owner_and_the_team(self):
        owner, _ = self.register('owner@example.com', 'owner')
        mail.outbox.clear()

        response = owner.post(
            '/api/properties',
            {
                'title': 'Brand new flat', 'property_type': 'flat', 'price': '450000', 'state': 'Anambra',
                'city': 'Nnewi', 'description': 'A lovely flat with plenty of light and space.',
                'inspection_fee': '2000', 'photos': [png('a.png')],
            },
            format='multipart',
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(len(mail.outbox), 2)

        receipt, team = mail.outbox
        self.assertEqual(receipt.to, ['owner@example.com'])
        self.assertEqual(receipt.subject, 'We received your listing')
        self.assertIn('Brand new flat', receipt.body)
        self.assertIn('pending review', receipt.body)
        self.assertNotIn('https://axora.test/properties/', receipt.body)  # not public yet

        self.assertEqual(team.to, ['team@axora.test'])
        self.assertEqual(team.reply_to, ['owner@example.com'])
        self.assertIn('New listing waiting for review', team.subject)
        self.assertIn('owner@example.com', team.body)

    def test_review_submission_emails_the_team_and_the_author(self):
        seeker, _ = self.register('reviewer@example.com')
        mail.outbox.clear()

        response = seeker.post(
            '/api/reviews',
            {'rating': 5, 'text': 'I found my flat in four days.', 'location': 'Onitsha, Anambra State'},
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(len(mail.outbox), 2)

        team, author = mail.outbox
        self.assertEqual(team.to, ['team@axora.test'])
        self.assertEqual(team.reply_to, ['reviewer@example.com'])
        self.assertIn('New review waiting for moderation', team.subject)

        self.assertEqual(author.to, ['reviewer@example.com'])
        self.assertEqual(author.reply_to, ['team@axora.test'])
        self.assertEqual(author.subject, 'Thanks for your review')
        self.assertIn('once our team approves it', author.body)
        self.assertIn('I found my flat in four days.', author.body)
        self.assertIn('I found my flat in four days.', self.html(author))

    def test_send_test_email_command(self):
        stdout = io.StringIO()
        call_command('send_test_email', '--to', 'ops@example.com', stdout=stdout)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ['ops@example.com'])
        self.assertEqual(message.subject, 'Axora Finds email test')
        self.assertIn('locmem', message.body)
        self.assertIn('Email is working', self.html(message))
        self.assertIn('Test email sent to ops@example.com.', stdout.getvalue())

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend', EMAIL_HOST='')
    def test_nothing_is_sent_when_no_mail_server_is_configured(self):
        self.assertFalse(email_enabled())
        self.assertFalse(send_test_email('ops@example.com'))


@override_settings(
    TEAM_EMAIL='team@axora.test',
    DEFAULT_FROM_EMAIL='Axora Finds <no-reply@axora.test>',
    SITE_URL='https://axora.test',
)
class AdminEmailTests(BaseCase):
    """Staff decisions in Django admin send the matching email."""

    def setUp(self):
        super().setUp()
        self.admin_user = User.objects.create_superuser('mail-admin@axora.test', PASSWORD)
        self.client.force_login(self.admin_user)
        mail.outbox.clear()

    def run_action(self, model_path, action, pks):
        return self.client.post(
            f'/admin/{model_path}/', {'action': action, '_selected_action': pks, 'index': 0}, follow=True
        )

    def test_inspection_payment_and_decision_emails(self):
        paid = self.client.post(
            '/api/inspections',
            {'name': 'A B', 'phone': '07012345678', 'email': 'visitor@example.com', 'property': 1,
             'date': future_date(), 'payment_choice': 'in_person'},
            format='json',
        ).data['id']
        mail.outbox.clear()
        path = 'inspections/inspection'

        self.run_action(path, 'mark_payment_verified', [paid])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['visitor@example.com'])
        self.assertIn('Payment verified', mail.outbox[0].subject)

        mail.outbox.clear()
        self.run_action(path, 'confirm_inspections', [paid])
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('confirmed', mail.outbox[0].subject)

        rejected = self.client.post(
            '/api/inspections',
            {'name': 'C D', 'phone': '07012345678', 'email': 'visitor2@example.com', 'property': 2,
             'date': future_date()},
            format='json',
        ).data['id']
        mail.outbox.clear()
        self.run_action(path, 'reject_inspections', [rejected])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['visitor2@example.com'])
        self.assertIn('could not be confirmed', mail.outbox[0].subject)

    def test_listing_publish_and_reject_emails(self):
        owner = User.objects.get(email='seed-owner@axora.test')
        with_photo = Property.objects.create(
            owner=owner, title='Pending with photo', property_type='flat', price=1000, state='Lagos',
            city='Ikeja', description='A pending listing waiting for staff review.',
        )
        with_photo.photos.create(external_url='https://example.com/a.jpg')
        to_reject = Property.objects.create(
            owner=owner, title='Pending to reject', property_type='flat', price=1000, state='Lagos',
            city='Ikeja', description='A pending listing that staff will reject.',
        )
        mail.outbox.clear()

        self.run_action('listings/property', 'publish_listings', [with_photo.pk])
        self.assertEqual(len(mail.outbox), 1)
        published = mail.outbox[0]
        self.assertEqual(published.to, [owner.email])
        self.assertEqual(published.subject, 'Your listing is live on Axora Finds')
        self.assertIn(f'https://axora.test/properties/{with_photo.slug}', published.body)

        mail.outbox.clear()
        self.run_action('listings/property', 'reject_listings', [to_reject.pk])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [owner.email])
        self.assertEqual(mail.outbox[0].subject, 'Your listing was not approved')

    def test_review_publication_email(self):
        self.register('author@example.com')
        reviewer = User.objects.get(email='author@example.com')
        review = Review.objects.create(
            user=reviewer, name='Ada Obi', rating=5, text='I found my flat in four days.',
        )
        mail.outbox.clear()

        self.run_action('pages/review', 'publish_reviews', [review.pk])
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ['author@example.com'])
        self.assertEqual(message.subject, 'Your review is live on Axora Finds')
        self.assertIn('https://axora.test/#reviews', message.body)
        self.assertIn('I found my flat in four days.', self.html(message))

        # Publishing it again does not send a duplicate.
        mail.outbox.clear()
        self.run_action('pages/review', 'publish_reviews', [review.pk])
        self.assertEqual(mail.outbox, [])


class StaffApiTests(BaseCase):
    """The signed-in staff dashboard reuses the same rules as Django admin."""

    def setUp(self):
        super().setUp()
        self.staff_user = User.objects.create_user('dashboard@axora.test', PASSWORD, role=Role.STAFF)
        self.client.force_authenticate(self.staff_user)

    def pending_listing(self, title='Pending flat', *, photo=True):
        owner = User.objects.get(email='seed-owner@axora.test')
        prop = Property.objects.create(
            owner=owner, title=title, property_type='flat', price=1000, state='Enugu', city='Nsukka',
            description='A pending listing waiting for staff review.',
        )
        if photo:
            prop.photos.create(external_url='https://example.com/a.jpg')
        return prop

    def test_only_staff_can_open_the_dashboard(self):
        self.assertEqual(APIClient().get('/api/staff/overview').status_code, 401)
        seeker, _ = self.register('not-staff@example.com')
        self.assertEqual(seeker.get('/api/staff/overview').status_code, 403)

        response = self.client.get('/api/staff/overview')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.data['counts']['listings']['published'], 8)
        self.assertTrue(response.data['email']['templates_ready'])
        self.assertEqual(response.data['email']['missing_templates'], [])

    def test_a_createsuperuser_account_can_open_the_dashboard(self):
        # The dashboard gate mirrors is_staff, so the documented createsuperuser
        # login reaches the same staff-only API as a role "staff" account.
        superuser = User.objects.create_superuser('super@axora.test', PASSWORD)
        client = APIClient()
        client.force_authenticate(superuser)
        self.assertEqual(client.get('/api/staff/overview').status_code, 200)

        login = APIClient().post(
            '/api/auth/token', {'email': 'super@axora.test', 'password': PASSWORD}, format='json'
        )
        self.assertEqual(login.status_code, 200, login.content)
        self.assertTrue(login.data['user']['is_staff'])

    def test_staff_publish_and_reject_listings_and_send_email(self):
        prop = self.pending_listing()
        mail.outbox.clear()

        response = self.client.post(f'/api/staff/listings/{prop.pk}/publish')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.data['email_sent'])
        prop.refresh_from_db()
        self.assertEqual(prop.status, Status.PUBLISHED)
        self.assertEqual(prop.reviewed_by, self.staff_user)
        self.assertEqual(self.client.get('/api/properties').data['count'], 9)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [prop.owner.email])

        response = self.client.post(f'/api/staff/listings/{prop.pk}/reject')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.data['email_sent'])
        prop.refresh_from_db()
        self.assertEqual(prop.status, Status.REJECTED)

    def test_listing_without_a_photo_cannot_be_published_from_the_dashboard(self):
        prop = self.pending_listing(photo=False)
        response = self.client.post(f'/api/staff/listings/{prop.pk}/publish')
        self.assertEqual(response.status_code, 400)
        self.assertIn('photo', response.data['detail'].lower())
        prop.refresh_from_db()
        self.assertEqual(prop.status, Status.PENDING)

    def test_payment_must_be_verified_before_confirming(self):
        created = self.client.post(
            '/api/inspections', self.inspection_payload(1, payment_choice='in_person'), format='json'
        )
        self.assertEqual(created.status_code, 201, created.content)
        pk = created.data['id']
        mail.outbox.clear()

        blocked = self.client.post(f'/api/staff/inspections/{pk}/confirm')
        self.assertEqual(blocked.status_code, 400)
        self.assertIn('Verify the payment', blocked.data['detail'])

        verified = self.client.post(f'/api/staff/inspections/{pk}/verify-payment')
        self.assertEqual(verified.status_code, 200, verified.content)
        self.assertTrue(verified.data['email_sent'])
        self.assertTrue(verified.data['can_confirm'])
        self.assertFalse(verified.data['can_verify_payment'])

        confirmed = self.client.post(f'/api/staff/inspections/{pk}/confirm')
        self.assertEqual(confirmed.status_code, 200, confirmed.content)
        self.assertEqual(confirmed.data['status'], 'confirmed')
        inspection = Inspection.objects.get(pk=pk)
        self.assertEqual((inspection.status, inspection.payment_status), ('confirmed', 'verified'))
        self.assertEqual(len(mail.outbox), 2)

    def test_reviews_can_be_published_and_hidden(self):
        review = Review.objects.create(name='Waiting', rating=4, text='A testimonial waiting for review.')

        response = self.client.post(f'/api/staff/reviews/{review.pk}/publish')
        self.assertEqual(response.status_code, 200)
        review.refresh_from_db()
        self.assertTrue(review.is_published)
        self.assertEqual(self.client.get('/api/reviews').data['count'], 7)

        response = self.client.post(f'/api/staff/reviews/{review.pk}/unpublish')
        self.assertEqual(response.status_code, 200)
        review.refresh_from_db()
        self.assertFalse(review.is_published)

    def test_settings_and_email_test(self):
        response = self.client.put(
            '/api/staff/settings',
            {
                'bank_name': 'Real Bank', 'account_name': 'Axora Finds Ltd',
                'account_number': '0123456789', 'transfer_note': 'Use your reference.',
                'is_live': True,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(SiteSettings.load().account_number, '0123456789')

        mail.outbox.clear()
        tested = self.client.post('/api/staff/email/test', {'to': 'ops@example.com'}, format='json')
        self.assertEqual(tested.status_code, 200, tested.content)
        self.assertTrue(tested.data['sent'])
        self.assertTrue(tested.data['status']['templates_ready'])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['ops@example.com'])
        self.assertIn('Email is working', mail.outbox[0].body)

    def test_resending_a_listing_email_does_not_change_the_listing(self):
        prop = self.pending_listing()
        self.client.post(f'/api/staff/listings/{prop.pk}/publish')
        mail.outbox.clear()

        response = self.client.post(f'/api/staff/listings/{prop.pk}/resend-email')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.data['email_sent'])
        self.assertEqual(len(mail.outbox), 1)
        prop.refresh_from_db()
        self.assertEqual(prop.status, Status.PUBLISHED)

        undecided = self.pending_listing(title='Not decided yet')
        response = self.client.post(f'/api/staff/listings/{undecided.pk}/resend-email')
        self.assertEqual(response.status_code, 400)

    def test_resending_an_inspection_email_does_not_change_the_inspection(self):
        created = self.client.post(
            '/api/inspections', self.inspection_payload(1, payment_choice='in_person'), format='json'
        )
        pk = created.data['id']
        self.client.post(f'/api/staff/inspections/{pk}/verify-payment')
        self.client.post(f'/api/staff/inspections/{pk}/confirm')
        mail.outbox.clear()

        response = self.client.post(f'/api/staff/inspections/{pk}/resend-email')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.data['email_sent'])
        self.assertEqual(len(mail.outbox), 1)
        inspection = Inspection.objects.get(pk=pk)
        self.assertEqual((inspection.status, inspection.payment_status), ('confirmed', 'verified'))

        pending = Inspection.objects.create(
            property=Inspection.objects.get(pk=pk).property,
            name='Waiting', phone='08030000000', email='waiting@example.com',
            preferred_date=Inspection.objects.get(pk=pk).preferred_date,
            payment_choice='in_person',
        )
        response = self.client.post(f'/api/staff/inspections/{pending.pk}/resend-email')
        self.assertEqual(response.status_code, 400)

    def test_resending_a_review_email_requires_a_published_linked_review(self):
        author = User.objects.create_user('reviewer@axora.test', PASSWORD)
        review = Review.objects.create(
            user=author, name='Reviewer', rating=5, text='A review with a linked account.'
        )

        response = self.client.post(f'/api/staff/reviews/{review.pk}/resend-email')
        self.assertEqual(response.status_code, 400)

        self.client.post(f'/api/staff/reviews/{review.pk}/publish')
        mail.outbox.clear()
        response = self.client.post(f'/api/staff/reviews/{review.pk}/resend-email')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.data['email_sent'])
        self.assertEqual(len(mail.outbox), 1)
        review.refresh_from_db()
        self.assertTrue(review.is_published)

    def test_lists_are_filterable(self):
        self.pending_listing(title='Pending in Enugu')
        response = self.client.get('/api/staff/listings', {'status': 'pending', 'q': 'Nsukka'})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.data['count'], 1)

        inspections = self.client.get('/api/staff/inspections', {'status': 'pending'})
        self.assertEqual(inspections.status_code, 200)
        self.assertIn('results', inspections.data)

        users = self.client.get('/api/staff/users', {'role': 'staff'})
        self.assertEqual(users.status_code, 200)
        self.assertEqual(users.data['count'], 1)
