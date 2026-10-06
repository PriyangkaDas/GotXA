import sys
import unittest
from unittest.mock import MagicMock
from collections import defaultdict
from pathlib import Path

from flask import Flask

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

# Mock heavy PDF generator dependency if running outside container with reportlab
if 'app.pdf_generator' not in sys.modules:
    try:
        import app.pdf_generator
    except ImportError:
        mock_pdf = MagicMock()
        sys.modules['app.pdf_generator'] = mock_pdf

from app import (
    api_v1,
    api_v1_actions,
    api_v1_consolidated,
    api_v1_extended,
    api_v1_db,
    api_v1_reports,
    api_corporate,
    api_ingestion,
)


def _collect_route_map():
    app = Flask(__name__)
    for blueprint in [
        api_v1.api,
        api_v1_actions.api,
        api_v1_extended.api,
        api_v1_consolidated.api,
        api_v1_db.api,
        api_v1_reports.api,
        api_corporate.api,
        api_ingestion.api,
    ]:
        app.register_blueprint(blueprint)

    routes = defaultdict(set)
    for rule in app.url_map.iter_rules():
        if rule.rule.startswith('/static'):
            continue
        for method in rule.methods - {'HEAD', 'OPTIONS'}:
            routes[(rule.rule, method)].add(rule.endpoint)
    return routes


def test_duplicate_api_routes_are_not_registered():
    routes = _collect_route_map()
    duplicates = [
        (rule, method)
        for (rule, method), endpoints in routes.items()
        if len(endpoints) > 1
    ]
    assert not duplicates, f"Duplicate endpoints found: {duplicates}"


def test_batch_operation_routes_exist():
    routes = _collect_route_map()
    required = {
        ('/api/alerts/batch-operations', 'POST'),
        ('/api/incidents/<incident_id>/batch-update', 'POST'),
        ('/api/access/jit-sessions/batch-action', 'POST'),
        ('/api/db/batch-operations', 'POST'),
    }
    for route in required:
        assert route in routes, f"Missing route {route}"


class RouteConsolidationTests(unittest.TestCase):
    def test_duplicate_api_routes_are_not_registered(self):
        test_duplicate_api_routes_are_not_registered()

    def test_batch_operation_routes_exist(self):
        test_batch_operation_routes_exist()


if __name__ == '__main__':
    unittest.main()
