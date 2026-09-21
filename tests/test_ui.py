from fastapi.testclient import TestClient
from ui.server import app

def test_ui_and_benchmark_inventory():
    with TestClient(app) as client:
        assert client.get('/').status_code==200
        assert len(client.get('/api/benchmarks').json())==20

def test_unknown_case_cannot_launch_an_investigation():
    with TestClient(app) as client:
        assert client.post('/api/run',json={'case_id':'not-a-case'}).status_code==404
        assert client.post('/api/run',json={'case_id':'HHG-001','response':'invented'}).status_code==422

def test_environment_file_is_not_public():
    with TestClient(app) as client:
        assert client.get('/.env').status_code==404
        assert client.get('/static/../.env').status_code==404
