from io import BytesIO
import os
import tempfile
from unittest.mock import patch

from PIL import Image
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from base.models import Message, Profile, Room, Topic
from studybud.settings import database_config


class DatabaseUrlConfigTests(SimpleTestCase):
    def test_absolute_sqlite_url_is_supported(self):
        database_url = 'sqlite:////home/example/StudyRoom/db.sqlite3'
        with patch.dict(os.environ, {'DATABASE_URL': database_url}):
            config = database_config()

        self.assertEqual(config['ENGINE'], 'django.db.backends.sqlite3')
        self.assertEqual(config['NAME'], '/home/example/StudyRoom/db.sqlite3')

    def test_relative_sqlite_url_is_rejected(self):
        with patch.dict(os.environ, {'DATABASE_URL': 'sqlite:///db.sqlite3'}):
            with self.assertRaises(ImproperlyConfigured):
                database_config()


class ProfileAvatarTests(TestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        media_settings = override_settings(MEDIA_ROOT=self.media_directory.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)

        image_buffer = BytesIO()
        Image.new('RGB', (1, 1)).save(image_buffer, format='PNG')
        self.image = SimpleUploadedFile(
            'avatar.png',
            image_buffer.getvalue(),
            content_type='image/png',
        )

    def test_registration_saves_uploaded_avatar(self):
        response = self.client.post(
            reverse('register'),
            {
                'username': 'NewUser',
                'password1': 'StudyRoomPass123!',
                'password2': 'StudyRoomPass123!',
                'avatar': self.image,
            },
        )

        self.assertRedirects(response, reverse('home'))
        user = User.objects.get(username='newuser')
        self.assertTrue(user.profile.avatar.name.startswith('avatars/'))

    def test_registration_without_avatar_uses_default_icon(self):
        response = self.client.post(
            reverse('register'),
            {
                'username': 'NewUser',
                'password1': 'StudyRoomPass123!',
                'password2': 'StudyRoomPass123!',
            },
        )

        self.assertRedirects(response, reverse('home'))
        user = User.objects.get(username='newuser')
        self.assertFalse(user.profile.avatar)
        profile_response = self.client.get(reverse('user-profile', args=[user.id]))
        self.assertContains(profile_response, 'images/icons/user.')

    def test_registration_rejects_case_insensitive_duplicate_username(self):
        User.objects.create_user(username='newuser', password='StudyRoomPass123!')

        response = self.client.post(
            reverse('register'),
            {
                'username': 'NEWUSER',
                'password1': 'StudyRoomPass123!',
                'password2': 'StudyRoomPass123!',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username__iexact='newuser').count(), 1)

    def test_profile_update_saves_uploaded_avatar(self):
        user = User.objects.create_user(username='member', password='StudyRoomPass123!')
        self.client.force_login(user)

        response = self.client.post(
            reverse('update-user'),
            {
                'username': 'member',
                'email': 'member@example.com',
                'avatar': self.image,
            },
        )

        self.assertRedirects(response, reverse('user-profile', args=[user.id]))
        user.refresh_from_db()
        self.assertTrue(user.profile.avatar.name.startswith('avatars/'))

    def test_profile_without_avatar_uses_default_icon(self):
        user = User.objects.create_user(username='member', password='StudyRoomPass123!')

        response = self.client.get(reverse('user-profile', args=[user.id]))

        self.assertContains(response, 'images/icons/user.')


class ProfileAboutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='profile_owner',
            password='StudyRoomPass123!',
        )
        self.profile = Profile.objects.create(
            user=self.user,
            bio='A learner who enjoys sharing ideas.',
        )
        self.client.force_login(self.user)

    def test_owner_can_edit_and_display_about_description(self):
        edit_response = self.client.get(reverse('update-user'))
        self.assertContains(edit_response, 'A learner who enjoys sharing ideas.')

        response = self.client.post(
            reverse('update-user'),
            {
                'username': 'profile_owner',
                'email': 'owner@example.com',
                'bio': 'I enjoy learning with others.',
            },
        )

        self.assertRedirects(
            response,
            reverse('user-profile', args=[self.user.id]),
        )
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.bio, 'I enjoy learning with others.')

        profile_response = self.client.get(
            reverse('user-profile', args=[self.user.id])
        )
        self.assertContains(profile_response, 'I enjoy learning with others.')
        self.assertNotContains(profile_response, 'Lorem ipsum')

    def test_profile_page_uses_owner_username_and_omits_empty_bio(self):
        self.profile.bio = ''
        self.profile.save(update_fields=['bio'])

        response = self.client.get(reverse('user-profile', args=[self.user.id]))

        self.assertContains(response, 'Study Rooms Hosted by profile_owner')
        self.assertNotContains(response, 'dennis_ivy')
        self.assertNotContains(response, 'Lorem ipsum')


class ProductionSafetyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='member',
            password='StudyRoomPass123!',
        )
        topic = Topic.objects.create(name='Django')
        self.room = Room.objects.create(
            host=self.user,
            topic=topic,
            name='Production readiness',
        )

    def test_anonymous_room_post_redirects_to_login_without_creating_message(self):
        response = self.client.post(
            reverse('room', args=[self.room.id]),
            {'body': 'A message from an anonymous visitor'},
        )

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('room', args=[self.room.id])}",
        )
        self.assertEqual(Message.objects.count(), 0)

    def test_logout_requires_post(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('logout'))

        self.assertEqual(response.status_code, 405)
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_logout_post_ends_session(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('logout'))

        self.assertRedirects(response, reverse('home'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_missing_api_room_returns_not_found(self):
        response = self.client.get(reverse('api:room-detail', args=[999999]))

        self.assertEqual(response.status_code, 404)
