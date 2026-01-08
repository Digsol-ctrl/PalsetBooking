from django.conf import settings
from django.core.cache import cache
import requests
import json

from rides.services.distance import DistanceService


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def test_distance_parsing(monkeypatch):
    cache.clear()
    monkeypatch.setattr(settings, 'GOOGLE_MAPS_API_KEY', 'fake-key')

    data = {
        "destination_addresses": ["Dest"],
        "origin_addresses": ["Orig"],
        "rows": [
            {"elements": [{"status": "OK", "distance": {"text": "12.345 km", "value": 12345}, "duration": {"text": "15 mins", "value": 900}}]}
        ],
        "status": "OK",
    }

    def fake_get(url, params=None, timeout=None):
        return FakeResponse(data)

    monkeypatch.setattr(requests, 'get', fake_get)

    dist = DistanceService.get_distance_km((-17.8, 31.0), (-17.9, 31.1))
    assert abs(dist - 12.345) < 0.0001


def test_distance_caching(monkeypatch):
    cache.clear()
    monkeypatch.setattr(settings, 'GOOGLE_MAPS_API_KEY', 'fake-key')

    call_count = {'n': 0}

    def fake_get(url, params=None, timeout=None):
        call_count['n'] += 1
        data = {
            "destination_addresses": ["Dest"],
            "origin_addresses": ["Orig"],
            "rows": [
                {"elements": [{"status": "OK", "distance": {"text": "5.000 km", "value": 5000}, "duration": {"text": "7 mins", "value": 420}}]}
            ],
            "status": "OK",
        }
        return FakeResponse(data)

    monkeypatch.setattr(requests, 'get', fake_get)

    o = (-17.8, 31.0)
    d = (-17.9, 31.1)

    d1 = DistanceService.get_distance_km(o, d)
    d2 = DistanceService.get_distance_km(o, d)

    # requests.get should be called only once due to caching
    assert call_count['n'] == 1
    assert abs(d1 - 5.0) < 0.0001
    assert abs(d2 - 5.0) < 0.0001
