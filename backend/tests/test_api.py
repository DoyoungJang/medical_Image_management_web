from __future__ import annotations

from pathlib import Path


def test_root_endpoint_explains_backend_server(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "백엔드가 실행 중입니다" in response.text
    assert "/api/health" in response.text
    assert "/docs" in response.text


def test_favicon_endpoint_is_quiet(client) -> None:
    response = client.get("/favicon.ico")

    assert response.status_code == 204


def test_authentication_and_admin_protection(client) -> None:
    unauthorized = client.get("/api/admin/index-status")
    assert unauthorized.status_code == 401

    login = client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    assert login.status_code == 200
    assert login.json()["is_admin"] is True

    authorized = client.get("/api/admin/index-status")
    assert authorized.status_code == 200


def test_manual_rescan_requires_admin_account(client, monkeypatch) -> None:
    container = client.app.state.container
    trigger_calls = []
    monkeypatch.setattr(
        container.index_service,
        "trigger_background_scan",
        lambda *, reason: trigger_calls.append(reason) or True,
    )
    viewer_token = container.auth_service.create_session_token("viewer")
    client.cookies.set(container.settings.auth_cookie_name, viewer_token)

    status_response = client.get("/api/admin/index-status")
    rescan_response = client.post("/api/admin/rescan")

    assert status_response.status_code == 200
    assert rescan_response.status_code == 403

    login = client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    assert login.status_code == 200

    admin_rescan_response = client.post("/api/admin/rescan")
    assert admin_rescan_response.status_code == 200
    assert trigger_calls == ["manual"]


def test_tree_endpoint_rejects_path_traversal(scanned_client) -> None:
    response = scanned_client.get("/api/tree", params={"path": "../outside"})
    assert response.status_code == 400


def test_tree_endpoint_returns_breadcrumbs_and_files(scanned_client) -> None:
    response = scanned_client.get("/api/tree", params={"path": "nested"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["breadcrumbs"][-1]["path"] == "nested"
    assert any(item["filename"] == "alpha.png" for item in payload["files"])


def test_tree_endpoint_includes_empty_storage_folders(scanned_client) -> None:
    root_response = scanned_client.get("/api/tree")
    assert root_response.status_code == 200
    root_payload = root_response.json()
    root_folder_names = {folder["name"] for folder in root_payload["folders"]}
    assert "empty-parent" in root_folder_names
    assert "empty-top" in root_folder_names

    child_response = scanned_client.get("/api/tree", params={"path": "empty-parent"})
    assert child_response.status_code == 200
    child_payload = child_response.json()
    assert any(folder["name"] == "child" and folder["descendant_file_count"] == 0 for folder in child_payload["folders"])


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


def test_image_search_includes_jpeg_and_bmp(scanned_client) -> None:
    jpg_response = scanned_client.get("/api/images", params={"q": "photo"})
    jpeg_response = scanned_client.get("/api/images", params={"q": "scan"})
    bmp_response = scanned_client.get("/api/images", params={"q": "bitmap"})

    assert jpg_response.status_code == 200
    assert jpeg_response.status_code == 200
    assert bmp_response.status_code == 200
    assert any(item["filename"] == "photo.jpg" and item["extension"] == ".jpg" for item in jpg_response.json()["items"])
    assert any(item["filename"] == "scan.jpeg" and item["extension"] == ".jpeg" for item in jpeg_response.json()["items"])
    assert any(item["filename"] == "bitmap.bmp" and item["extension"] == ".bmp" for item in bmp_response.json()["items"])


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


def test_original_file_endpoint_uses_image_media_type(scanned_client) -> None:
    jpg_response = scanned_client.get("/api/images", params={"q": "photo"})
    image_id = jpg_response.json()["items"][0]["id"]

    file_response = scanned_client.get(f"/api/images/{image_id}/file")
    thumbnail_response = scanned_client.get(f"/api/images/{image_id}/thumbnail", params={"size": 128})

    assert file_response.status_code == 200
    assert file_response.headers["content-type"] == "image/jpeg"
    assert thumbnail_response.status_code == 200
    assert thumbnail_response.headers["content-type"] == "image/png"


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
