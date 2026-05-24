"""Core route tests for POE2 Analytics."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_dashboard_loads():
    r = client.get("/")
    assert r.status_code == 200
    assert "POE2" in r.text


def test_currency_page():
    assert client.get("/currency").status_code == 200


def test_items_page():
    assert client.get("/items").status_code == 200


def test_gems_page():
    assert client.get("/gems").status_code == 200


def test_trades_page():
    assert client.get("/trades").status_code == 200


def test_monitor_page():
    assert client.get("/monitor").status_code == 200


def test_purchases_page():
    assert client.get("/purchases").status_code == 200


def test_summary_api():
    r = client.get("/api/v1/dashboard/summary")
    assert r.status_code == 200
    assert "total_items" in r.json()


def test_watchlist_api():
    r = client.get("/api/v1/watchlist")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_deals_api():
    assert client.get("/api/v1/deals").status_code == 200


def test_create_rule_validation():
    assert client.post("/api/v1/watchlist", json={}).status_code == 422


def test_create_and_delete_rule():
    r = client.post("/api/v1/watchlist", json={"name": "P4Test", "item_name": "X", "max_price": 100})
    assert r.status_code == 200
    rid = r.json()["id"]
    assert client.delete(f"/api/v1/watchlist/{rid}").status_code == 200
