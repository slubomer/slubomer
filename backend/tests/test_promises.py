from sqlalchemy import func, select

from app.models import Promise
from app.seed import seed


def test_list_returns_all_sample_promises(client):
    body = client.get("/api/v1/promises").json()

    assert body["total"] == 16
    assert len(body["items"]) == 16
    first = body["items"][0]
    assert first["slug"] == "skoly"  # newest verdict comes first
    assert first["verdict"]["value"] == "splnene"
    assert first["subject"]["slug"] == "subjekt-b"


def test_filters_combine(client):
    body = client.get(
        "/api/v1/promises", params={"category": "doprava", "verdict": "ciastocne"}
    ).json()

    assert {p["slug"] for p in body["items"]} == {"doprava", "cyklotrasy"}


def test_search_ignores_diacritics(client):
    body = client.get("/api/v1/promises", params={"q": "ucebnice"}).json()

    assert [p["slug"] for p in body["items"]] == ["ucebnice"]


def test_pagination(client):
    body = client.get("/api/v1/promises", params={"page": 2, "page_size": 5}).json()

    assert body["total"] == 16
    assert body["page"] == 2
    assert len(body["items"]) == 5


def test_empty_result(client):
    body = client.get("/api/v1/promises", params={"q": "nic-take-neexistuje"}).json()

    assert body == {"items": [], "total": 0, "page": 1, "page_size": 20}


def test_invalid_filter_value_returns_422(client):
    assert client.get("/api/v1/promises", params={"verdict": "v_procese"}).status_code == 422


def test_detail_has_quote_evidence_and_history(client):
    body = client.get("/api/v1/promises/obchvat").json()

    assert body["quote"].startswith("Do konca volebného obdobia")
    assert body["description"] == body["quote"]
    assert body["verdict"]["value"] == "nesplnene"
    assert {e["role"] for e in body["evidence"]} == {"zdroj", "podklad"}
    # Newest version first; the older one is kept for history.
    assert [v["value"] for v in body["history"]] == ["nesplnene", "ciastocne"]
    assert body["ai_generated"] is True


def test_detail_unknown_slug_returns_404(client):
    assert client.get("/api/v1/promises/neexistuje").status_code == 404


def test_seed_can_run_twice(db):
    seed(db)

    assert db.scalar(select(func.count(Promise.id))) == 16
