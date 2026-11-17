from app.core.text import normalize, sk_sort_key


def test_overview_counts_match_the_list(client):
    body = client.get("/api/v1/stats/overview").json()

    assert body["total"] == 16
    assert body["by_verdict"] == {"splneny": 5, "nesplneny": 5, "v_procese": 6}
    assert sum(body["by_verdict"].values()) == body["total"]


def test_stats_per_subject(client):
    body = client.get("/api/v1/stats/subjects").json()

    by_slug = {row["subject"]["slug"]: row for row in body}
    assert by_slug["subjekt-a"]["total"] == 6
    assert sum(r["total"] for r in body) == 16


def test_subjects_and_categories_have_counts(client):
    subjects = client.get("/api/v1/subjects").json()
    categories = client.get("/api/v1/categories").json()

    assert [s["slug"] for s in subjects] == ["subjekt-a", "subjekt-b", "subjekt-c"]
    assert sum(c["promise_count"] for c in categories) == 16


def test_glossary_uses_slovak_alphabet(client):
    names = [t["name"] for t in client.get("/api/v1/glossary").json()]

    assert len(names) == 21
    # "Štátny rozpočet" (Š) comes after all S words.
    assert names.index("Štátny rozpočet") > names.index("Samospráva")
    assert names.index("Zákon") < names.index("Zdravotná starostlivosť")


def test_glossary_term_detail_and_404(client):
    term = client.get("/api/v1/glossary/statny-rozpocet").json()

    assert term["name"] == "Štátny rozpočet"
    assert "rozpoč" in term["stems"]
    assert client.get("/api/v1/glossary/neexistuje").status_code == 404


def test_text_helpers():
    assert normalize("  Školstvo ") == "skolstvo"
    assert sk_sort_key("chata") > sk_sort_key("hrad")  # ch after h
    assert sk_sort_key("čaj") > sk_sort_key("cesta")  # č after c
