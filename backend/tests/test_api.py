from __future__ import annotations

from pathlib import Path


def test_authentication_and_admin_protection(client) -> None:
    unauthorized = client.get("/api/admin/index-status")
    assert unauthorized.status_code == 401

    login = client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    assert login.status_code == 200

    authorized = client.get("/api/admin/index-status")
    assert authorized.status_code == 200


def test_tree_endpoint_rejects_path_traversal(scanned_client) -> None:
    response = scanned_client.get("/api/tree", params={"path": "../outside"})
    assert response.status_code == 400


def test_tree_endpoint_returns_breadcrumbs_and_files(scanned_client) -> None:
    response = scanned_client.get("/api/tree", params={"path": "nested"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["breadcrumbs"][-1]["path"] == "nested"
    assert any(item["filename"] == "alpha.png" for item in payload["files"])


def test_image_search_finds_filename_path_and_metadata(scanned_client) -> None:
    filename_response = scanned_client.get("/api/images", params={"q": "plain"})
    metadata_response = scanned_client.get("/api/images", params={"q": "홍길동"})
    path_response = scanned_client.get("/api/images", params={"q": "nested/deeper"})

    assert filename_response.status_code == 200
    assert metadata_response.status_code == 200
    assert path_response.status_code == 200
    assert any(item["filename"] == "plain.png" for item in filename_response.json()["items"])
    assert any(item["filename"] == "meta.png" for item in metadata_response.json()["items"])
    assert any(item["filename"] == "deep.png" for item in path_response.json()["items"])


def test_structured_filters_and_facets(scanned_client) -> None:
    filtered = scanned_client.get("/api/images", params={"directory": "nested", "has_alpha": True})
    facets = scanned_client.get("/api/metadata/facets", params={"directory": "nested"})

    assert filtered.status_code == 200
    assert facets.status_code == 200
    payload = filtered.json()
    assert all(item["relative_path"].startswith("nested/") for item in payload["items"])
    assert any(item["filename"] == "alpha.png" for item in payload["items"])
    facet_payload = facets.json()
    assert "status_counts" in facet_payload
    assert "directory_counts" in facet_payload


def test_thumbnail_and_file_endpoints(scanned_client) -> None:
    list_response = scanned_client.get("/api/images", params={"q": "meta"})
    image_id = list_response.json()["items"][0]["id"]

    thumbnail_response = scanned_client.get(f"/api/images/{image_id}/thumbnail", params={"size": 128})
    file_response = scanned_client.get(f"/api/images/{image_id}/file")

    assert thumbnail_response.status_code == 200
    assert thumbnail_response.headers["content-type"] == "image/png"
    assert file_response.status_code == 200
    assert file_response.headers["content-type"] == "image/png"


def test_corrupted_png_is_visible_with_status(scanned_client) -> None:
    response = scanned_client.get("/api/images", params={"status": "corrupted"})
    assert response.status_code == 200
    assert any(item["filename"] == "broken.png" for item in response.json()["items"])


def test_metadata_key_search(scanned_client) -> None:
    response = scanned_client.get(
        "/api/images",
        params={"metadata_key": "textual_metadata.Author", "metadata_value": "홍길동"},
    )
    assert response.status_code == 200
    assert any(item["filename"] == "meta.png" for item in response.json()["items"])
