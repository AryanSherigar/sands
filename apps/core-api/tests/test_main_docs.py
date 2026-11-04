from app.main import docs_urls


def test_production_serves_no_api_docs() -> None:
    assert docs_urls("production") == {
        "docs_url": None,
        "redoc_url": None,
        "openapi_url": None,
    }


def test_development_keeps_the_api_docs() -> None:
    urls = docs_urls("development")

    assert urls["docs_url"] == "/docs"
    assert urls["openapi_url"] == "/openapi.json"
