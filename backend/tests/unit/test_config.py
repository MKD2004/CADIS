from cadis.config import get_settings


def test_defaults():
    s = get_settings()
    assert s.qa_model == "deepset/roberta-base-squad2"
    assert s.emb_model == "all-MiniLM-L6-v2"
    assert s.cors_origins == ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001"]
    assert s.health_name == "CADIS API v2.1"


def test_cadis_prefixed_variable(monkeypatch):
    monkeypatch.setenv("CADIS_QA_MODEL", "my/qa")
    assert get_settings().qa_model == "my/qa"


def test_v1_variable_still_works(monkeypatch):
    monkeypatch.setenv("QA_MODEL", "legacy/qa")
    assert get_settings().qa_model == "legacy/qa"


def test_prefixed_variable_wins_over_v1(monkeypatch):
    monkeypatch.setenv("QA_MODEL", "legacy/qa")
    monkeypatch.setenv("CADIS_QA_MODEL", "new/qa")
    assert get_settings().qa_model == "new/qa"


def test_frontend_url_v1_single_origin(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "https://cadis.vercel.app/")
    assert get_settings().cors_origins[-1] == "https://cadis.vercel.app"


def test_frontend_urls_comma_separated_without_duplicates(monkeypatch):
    monkeypatch.setenv("CADIS_FRONTEND_URLS", "https://a.app, https://b.app,http://localhost:3000")
    origins = get_settings().cors_origins
    assert origins[-2:] == ["https://a.app", "https://b.app"]
    assert origins.count("http://localhost:3000") == 1


def test_numeric_settings_are_typed(monkeypatch):
    monkeypatch.setenv("CADIS_QA_WINDOW", "256")
    assert get_settings().qa_window == 256
