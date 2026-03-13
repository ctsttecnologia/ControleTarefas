from django.test import TestCase, override_settings
from unittest.mock import Mock

from storage_backends import MediaStorage, StaticStorage


@override_settings(
    GS_BUCKET_NAME='test-bucket',
    GS_PROJECT_ID='test-project',
    GS_CREDENTIALS=Mock(name='mock_credentials')
)
class StorageBackendsTest(TestCase):
    """Test suite for custom Google Cloud storage backends."""

    def test_static_storage_settings(self):
        """Tests that StaticStorage is configured correctly from settings."""
        storage = StaticStorage()
        self.assertEqual(storage.location, 'static')
        self.assertIsNone(storage.default_acl)
        self.assertEqual(storage.bucket_name, 'test-bucket')
        self.assertEqual(storage.project_id, 'test-project')
        self.assertEqual(storage.credentials.name, 'mock_credentials')

    def test_media_storage_settings(self):
        """Tests that MediaStorage is configured correctly from settings."""
        storage = MediaStorage()
        self.assertEqual(storage.location, 'media')
        self.assertIsNone(storage.default_acl)
        self.assertFalse(storage.file_overwrite)
        self.assertEqual(storage.bucket_name, 'test-bucket')
        self.assertEqual(storage.project_id, 'test-project')
        self.assertEqual(storage.credentials.name, 'mock_credentials')
