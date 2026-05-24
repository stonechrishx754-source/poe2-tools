# Phase 4: Polish, Tests & Security — Implementation Plan

**Goal:** Add Alembic migrations, pytest tests, SSE reconnect hardening, POESESSID notice, and startup polish.

**Architecture:** Alembic replaces `create_all` for schema management. pytest with httpx TestClient covers core routes. SSE already has client-side auto-reconnect (EventSource native); we add server-side connection tracking. POESESSID notice as a dismissible banner on /monitor.

---

### Task 1: Alembic Migration Setup

**Files:** Create `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`

- [ ] **Step 1: Install and init Alembic**

```bash
cd E:/project-poe2 && pip install alembic && alembic init alembic
```

- [ ] **Step 2: Configure alembic/env.py to use our async engine and Base**

```python
# alembic/env.py
from app.database import DATABASE_URL
from app.models.base import Base
from app.models import *  # noqa — register all models

target_metadata = Base.metadata
config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("+aiosqlite", ""))
```

- [ ] **Step 3: Generate and apply initial migration**

```bash
cd E:/project-poe2 && alembic revision --autogenerate -m "initial" && alembic upgrade head
```

- [ ] **Step 4: Replace create_all in main.py lifespan**

```python
# In lifespan, replace: await conn.run_sync(Base.metadata.create_all)
# With: import alembic.command; alembic.command.upgrade(alembic.config.Config("alembic.ini"), "head")
# Or simply keep create_all for dev and note Alembic for production in README
```

- [ ] **Step 5: Commit**

```bash
git add alembic/ alembic.ini app/main.py
git commit -m "chore: add Alembic migration support"
```

---

### Task 2: Pytest Test Suite

**Files:** Create `tests/test_routes.py`, update `tests/conftest.py`

- [ ] **Step 1: Update test conftest with FastAPI TestClient**

```python
# tests/conftest.py — add
from app.main import app as _app
from fastapi.testclient import TestClient
import pytest

@pytest.fixture
def client():
    return TestClient(_app)
```

- [ ] **Step 2: Create route test file**

```python
# tests/test_routes.py
def test_dashboard_loads(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "POE2" in r.text

def test_currency_page(client):
    r = client.get("/currency")
    assert r.status_code == 200

def test_items_page(client):
    r = client.get("/items")
    assert r.status_code == 200

def test_gems_page(client):
    r = client.get("/gems")
    assert r.status_code == 200

def test_trades_page(client):
    r = client.get("/trades")
    assert r.status_code == 200

def test_monitor_page(client):
    r = client.get("/monitor")
    assert r.status_code == 200

def test_purchases_page(client):
    r = client.get("/purchases")
    assert r.status_code == 200

def test_watchlist_api(client):
    r = client.get("/api/v1/watchlist")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_deals_api(client):
    r = client.get("/api/v1/deals")
    assert r.status_code == 200

def test_summary_api(client):
    r = client.get("/api/v1/dashboard/summary")
    assert r.status_code == 200
    assert "total_items" in r.json()

def test_create_rule_validation(client):
    r = client.post("/api/v1/watchlist", json={})
    assert r.status_code == 422  # Pydantic validation

def test_create_and_delete_rule(client):
    r = client.post("/api/v1/watchlist", json={"name":"Test","item_name":"X","max_price":100})
    assert r.status_code == 200
    rid = r.json()["id"]
    r = client.delete(f"/api/v1/watchlist/{rid}")
    assert r.status_code == 200
```

- [ ] **Step 3: Run tests**

```bash
cd E:/project-poe2 && python -m pytest tests/ -v
```

Expected: 12/12 passing.

- [ ] **Step 4: Commit**

```bash
git add tests/ requirements.txt
git commit -m "test: add pytest test suite for all pages and APIs"
```

---

### Task 3: SSE Reconnect Hardening

**Files:** Modify `app/services/alert_service.py`

- [ ] **Step 1: Add subscriber tracking to AlertService**

```python
# Add to AlertService.__init__:
self._subscriber_count = 0

# Add method:
def subscribe(self):
    self._subscriber_count += 1
    return self._subscriber_count

def unsubscribe(self):
    self._subscriber_count = max(0, self._subscriber_count - 1)
    return self._subscriber_count
```

- [ ] **Step 2: Update SSE endpoint to track subscribers**

In `api_monitor.py` `deal_stream()`:
```python
# After getting alert_service, call alert_service.subscribe()
# In a finally block (via generator close), call alert_service.unsubscribe()
```

- [ ] **Step 3: Add browser-side reconnect to monitor.html**

JS already does this — EventSource auto-reconnects. Add a reconnect counter display:
```javascript
let sseReconnectCount = 0;
sse.addEventListener('open', () => {
    if (sseReconnectCount > 0) {
        document.getElementById('sse-status').textContent = t('SSE: connected') + ' (x' + sseReconnectCount + ')';
    }
});
sse.addEventListener('error', () => {
    sseReconnectCount++;
});
```

- [ ] **Step 4: Commit**

---

### Task 4: POESESSID Not Configured Notice on /monitor

**Files:** Modify `app/templates/monitor.html`

- [ ] **Step 1: Add a dismissible banner if POESESSID is empty (server-side check)**

In `app/routers/web.py` monitor_page:
```python
from app.config import settings
poesessid_missing = not settings.GGG_POESESSID
```

Pass `poesessid_missing` to template. In monitor.html, show banner:
```html
{% if poesessid_missing %}
<div class="toast-error mb-3" id="poesessid-warning">
    <span>POESESSID not set — monitoring disabled. Add it in .env</span>
    <button onclick="document.getElementById('poesessid-warning').remove()">x</button>
</div>
{% endif %}
```

- [ ] **Step 2: Commit**

---

### Task 5: Startup Script Polish + README Update

**Files:** Modify `start.bat`, `start.sh`, update `README.md`

- [ ] **Step 1: Update start.bat**

```bat
@echo off
echo Starting POE2 Analytics...
cd /d E:\project-poe2
pip install -r requirements.txt >nul 2>&1
echo.
echo ============================================
echo  POE2 Analytics
echo  http://127.0.0.1:8006
echo  API docs: http://127.0.0.1:8006/docs
echo ============================================
echo.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8006 --reload
pause
```

- [ ] **Step 2: Update README with Phase 3+4 features**

Add to README: Trades page section, Purchases page section, Analytics section.

- [ ] **Step 3: Commit**
