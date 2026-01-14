import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'rides_project.settings'
os.environ['GOOGLE_MAPS_SERVER_KEY'] = 'server-key'
import django
django.setup()
from rides.services.distance import DistanceService
import requests

called = {}

def fake_get(url, params=None, timeout=None):
    called['params'] = params
    # Minimal fake response structure
    return type('R', (), {'raise_for_status': lambda self: None, 'json': lambda self: {"destination_addresses":["D"], "origin_addresses":["O"], "rows":[{"elements":[{"status":"OK","distance":{"text":"1.000 km","value":1000}}]}], "status":"OK"}})()

orig_get = requests.get
requests.get = fake_get

try:
    d = DistanceService.get_distance_km((-17.8, 31.0), (-17.9, 31.1))
    print('distance_km=', d)
    print('sent_key=', called.get('params', {}).get('key'))
finally:
    requests.get = orig_get
