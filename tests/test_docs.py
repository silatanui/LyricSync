import pytest

def test_docs_page_routes(client):
    # Test /docs route
    res_docs = client.get("/docs")
    assert res_docs.status_code == 200
    html_docs = res_docs.get_data(as_text=True)
    
    # Verify core documentation elements
    assert "System Architecture &amp; Technical Documentation" in html_docs or "System Architecture" in html_docs
    assert "copy-code-btn" in html_docs
    assert "mermaid" in html_docs
    assert "docs.css" in html_docs
    assert "Outfit" in html_docs
    assert "Diagram 1" in html_docs
    assert "Diagram 7" in html_docs
    
    # Verify that sensitive secrets are sanitized and not leaked
    assert "sk-" not in html_docs  # No real OpenAI key prefixes
    assert "SECRET_KEY = os.getenv" in html_docs or "OPENAI_API_KEY" in html_docs

    # Test /documentation alias
    res_doc_alias = client.get("/documentation")
    assert res_doc_alias.status_code == 200

    # Verify home page has prominent links to documentation
    res_home = client.get("/")
    assert res_home.status_code == 200
    html_home = res_home.get_data(as_text=True)
    assert "/docs" in html_home
    assert "Documentation" in html_home
