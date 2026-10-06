import os
import sys
import unittest
from unittest.mock import patch

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.api_ingestion import _collector_authorized


class CollectorAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)

    def check_header(self, headers):
        with self.app.test_request_context('/', headers=headers):
            return _collector_authorized()

    def test_configured_token_is_required(self):
        with patch.dict(os.environ, {'COLLECTOR_INGEST_TOKEN': 'configured-secret'}):
            self.assertTrue(self.check_header({'X-Collector-Token': 'configured-secret'}))
            self.assertTrue(self.check_header({'Authorization': 'Bearer configured-secret'}))
            self.assertFalse(self.check_header({'X-Collector-Token': 'test-token'}))
            self.assertFalse(self.check_header({}))

    def test_unconfigured_token_is_rejected(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('COLLECTOR_INGEST_TOKEN', None)
            self.assertFalse(self.check_header({}))


if __name__ == '__main__':
    unittest.main()