from karaoke_server.config import Settings

from .conftest import MakeClient


def test_spa_fallback_and_immutable_assets(settings: Settings, make_client: MakeClient) -> None:
    web = settings.web_dir
    assert web is not None
    (web / "_app" / "immutable").mkdir(parents=True)
    (web / "index.html").write_text("<!doctype html><title>app</title>")
    (web / "_app" / "immutable" / "start.abc.js").write_text("console.log(1)")
    (web / "service-worker.js").write_text("self")
    client = make_client("remote")
    page = client.get("/cantar/mar-de-vigo")
    assert page.status_code == 200
    assert "<title>app</title>" in page.text
    assert page.headers["cache-control"] == "no-cache"
    asset = client.get("/_app/immutable/start.abc.js")
    assert asset.headers["cache-control"] == "public, max-age=31536000, immutable"
    worker = client.get("/service-worker.js")
    assert worker.headers["cache-control"] == "no-cache"
    assert client.get("/_app/immutable/missing.js").status_code == 404
    assert client.get("/../karaoke.db").status_code == 404


def test_missing_build_explains_how_to_make_it(make_client: MakeClient) -> None:
    response = make_client("local").get("/")
    assert response.status_code == 503
    assert "pnpm --dir web build" in response.text
