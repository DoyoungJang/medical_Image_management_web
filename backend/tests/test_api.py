from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import select

from app.models import Image as ImageModel
from app.services.object_storage import ObjectStorageError


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


def test_admin_can_set_signup_code_and_user_can_register_then_change_password(client) -> None:
    login = client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    assert login.status_code == 200

    code_response = client.patch("/api/admin/signup-code", json={"signup_code": "join-2026"})
    assert code_response.status_code == 200
    assert code_response.json()["signup_code"] == "join-2026"

    client.post("/api/auth/logout")
    bad_register = client.post(
        "/api/auth/register",
        json={"username": "viewer", "password": "viewerpass1", "signup_code": "wrong"},
    )
    assert bad_register.status_code == 403

    register = client.post(
        "/api/auth/register",
        json={"username": "viewer", "password": "viewerpass1", "signup_code": "join-2026"},
    )
    assert register.status_code == 200
    assert register.json()["username"] == "viewer"
    assert register.json()["is_admin"] is False

    rescan_response = client.post("/api/admin/rescan")
    assert rescan_response.status_code == 403

    change_response = client.post(
        "/api/auth/change-password",
        json={"current_password": "viewerpass1", "new_password": "viewerpass2"},
    )
    assert change_response.status_code == 200

    client.post("/api/auth/logout")
    old_login = client.post("/api/auth/login", json={"username": "viewer", "password": "viewerpass1"})
    new_login = client.post("/api/auth/login", json={"username": "viewer", "password": "viewerpass2"})
    assert old_login.status_code == 401
    assert new_login.status_code == 200


def test_admin_can_change_own_password(client) -> None:
    login = client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    assert login.status_code == 200

    change_response = client.post(
        "/api/auth/change-password",
        json={"current_password": "secret123", "new_password": "newsecret123"},
    )
    assert change_response.status_code == 200
    assert change_response.json()["is_admin"] is True

    client.post("/api/auth/logout")
    old_login = client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    new_login = client.post("/api/auth/login", json={"username": "admin", "password": "newsecret123"})
    assert old_login.status_code == 401
    assert new_login.status_code == 200


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


def test_authenticated_user_can_request_folder_rescan(client, monkeypatch) -> None:
    container = client.app.state.container
    trigger_calls = []
    monkeypatch.setattr(
        container.index_service,
        "trigger_background_scan",
        lambda *, reason, target_path="": trigger_calls.append((reason, target_path)) or True,
    )
    viewer_token = container.auth_service.create_session_token("viewer")
    client.cookies.set(container.settings.auth_cookie_name, viewer_token)

    response = client.post("/api/folders/rescan", json={"path": "nested"})

    assert response.status_code == 200
    assert response.json() == {"status": "accepted", "path": "nested"}
    assert trigger_calls == [("folder", "nested")]


def test_folder_rescan_reports_conflict_when_any_scan_is_running(authenticated_client, monkeypatch) -> None:
    container = authenticated_client.app.state.container
    monkeypatch.setattr(container.index_service, "trigger_background_scan", lambda *, reason, target_path="": False)

    response = authenticated_client.post("/api/folders/rescan", json={"path": "nested"})

    assert response.status_code == 409
    assert "스캔" in response.json()["detail"]


def test_folder_scan_removes_deleted_files_only_inside_target_folder(scanned_client, test_paths: dict[str, Path]) -> None:
    container = scanned_client.app.state.container
    (test_paths["png_root"] / "nested" / "deeper" / "deep.png").unlink()
    (test_paths["png_root"] / "plain.png").unlink()

    result = container.index_service.scan_now(reason="folder-test", target_path="nested")

    assert result.target_path == "nested"
    assert result.missing_marked >= 1

    plain_response = scanned_client.get("/api/images", params={"q": "plain"})
    deep_response = scanned_client.get("/api/images", params={"q": "deep"})

    assert any(item["filename"] == "plain.png" for item in plain_response.json()["items"])
    assert not deep_response.json()["items"]


def test_image_root_config_requires_admin_account(client, tmp_path: Path) -> None:
    container = client.app.state.container
    viewer_token = container.auth_service.create_session_token("viewer")
    client.cookies.set(container.settings.auth_cookie_name, viewer_token)
    next_root = tmp_path / "viewer-root"
    next_root.mkdir()

    get_response = client.get("/api/admin/root")
    update_response = client.patch("/api/admin/root", json={"root_dir": str(next_root), "rescan": False})

    assert get_response.status_code == 403
    assert update_response.status_code == 403


def test_admin_can_update_image_root_and_scan_new_folder(client, test_paths: dict[str, Path], tmp_path: Path) -> None:
    login = client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    assert login.status_code == 200
    new_root = tmp_path / "new-root"
    new_root.mkdir()
    Image.new("RGB", (16, 12), color=(10, 20, 30)).save(new_root / "new-root-image.png")

    root_response = client.get("/api/admin/root")
    assert root_response.status_code == 200
    assert root_response.json()["root_dir"] == str(test_paths["png_root"].resolve())

    update_response = client.patch("/api/admin/root", json={"root_dir": str(new_root), "rescan": False})
    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["root_dir"] == str(new_root.resolve())
    assert payload["source"] == "database"
    assert payload["changed"] is True
    assert payload["rescan_accepted"] is False

    container = client.app.state.container
    assert container.file_system_service.root_path == new_root.resolve()
    container.index_service.scan_now(reason="test-root-change")

    new_image_response = client.get("/api/images", params={"q": "new-root-image"})
    old_image_response = client.get("/api/images", params={"q": "plain"})

    assert new_image_response.status_code == 200
    assert any(item["filename"] == "new-root-image.png" for item in new_image_response.json()["items"])
    assert old_image_response.status_code == 200
    assert not old_image_response.json()["items"]


def test_admin_image_root_update_rejects_invalid_path(client, test_paths: dict[str, Path], tmp_path: Path) -> None:
    login = client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    assert login.status_code == 200
    missing_root = tmp_path / "missing-root"

    response = client.patch("/api/admin/root", json={"root_dir": str(missing_root), "rescan": False})

    assert response.status_code == 400
    container = client.app.state.container
    assert container.file_system_service.root_path == test_paths["png_root"].resolve()


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
    image_id = next(item["id"] for item in list_response.json()["items"] if item["filename"] == "meta.png")

    thumbnail_response = scanned_client.get(f"/api/images/{image_id}/thumbnail", params={"size": 128})
    file_response = scanned_client.get(f"/api/images/{image_id}/file")

    assert thumbnail_response.status_code == 200
    assert thumbnail_response.headers["content-type"] == "image/png"
    assert file_response.status_code == 200
    assert file_response.headers["content-type"] == "image/png"


def test_concurrent_thumbnail_generation_uses_one_valid_cache_file(scanned_client) -> None:
    container = scanned_client.app.state.container
    with container.session_factory() as session:
        image = session.execute(select(ImageModel).where(ImageModel.filename == "meta.png")).scalar_one()

    def get_thumbnail_path() -> Path:
        return container.thumbnail_service.get_thumbnail_path(image, 128)

    with ThreadPoolExecutor(max_workers=8) as executor:
        paths = list(executor.map(lambda _index: get_thumbnail_path(), range(16)))

    assert len({path for path in paths}) == 1
    assert paths[0].exists()
    with Image.open(paths[0]) as thumbnail:
        thumbnail.verify()


def test_original_file_endpoint_uses_image_media_type(scanned_client) -> None:
    jpg_response = scanned_client.get("/api/images", params={"q": "photo"})
    image_id = next(item["id"] for item in jpg_response.json()["items"] if item["filename"] == "photo.jpg")

    file_response = scanned_client.get(f"/api/images/{image_id}/file")
    thumbnail_response = scanned_client.get(f"/api/images/{image_id}/thumbnail", params={"size": 128})

    assert file_response.status_code == 200
    assert file_response.headers["content-type"] == "image/jpeg"
    assert thumbnail_response.status_code == 200
    assert thumbnail_response.headers["content-type"] == "image/png"


def test_image_rescan_force_refreshes_single_image_metadata(scanned_client, test_paths: dict[str, Path]) -> None:
    jpg_response = scanned_client.get("/api/images", params={"q": "photo"})
    image_id = next(item["id"] for item in jpg_response.json()["items"] if item["filename"] == "photo.jpg")
    target_path = test_paths["png_root"] / "photo.jpg"
    original_stat = target_path.stat()
    original_bytes = target_path.read_bytes()
    updated_bytes = original_bytes.replace(b"<custom:View>4CV</custom:View>", b"<custom:View>5CV</custom:View>")
    target_path.write_bytes(updated_bytes)
    os.utime(target_path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))

    response = scanned_client.post(f"/api/images/{image_id}/rescan")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "refreshed"
    assert payload["image"]["tracked_metadata"].get("View") in {None, "5CV"}
    detail_response = scanned_client.get(f"/api/images/{image_id}")
    assert detail_response.json()["metadata"]["xmp"]["fields"]["View"] == ["5CV"]


def test_regular_user_can_force_rescan_single_image(scanned_client) -> None:
    container = scanned_client.app.state.container
    viewer_token = container.auth_service.create_session_token("viewer")
    scanned_client.cookies.set(container.settings.auth_cookie_name, viewer_token)
    list_response = scanned_client.get("/api/images", params={"q": "meta"})
    image_id = next(item["id"] for item in list_response.json()["items"] if item["filename"] == "meta.png")

    response = scanned_client.post(f"/api/images/{image_id}/rescan")

    assert response.status_code == 200
    assert response.json()["status"] == "refreshed"


def test_image_rescan_removes_deleted_file_from_database(scanned_client, test_paths: dict[str, Path]) -> None:
    list_response = scanned_client.get("/api/images", params={"q": "plain"})
    image_id = next(item["id"] for item in list_response.json()["items"] if item["filename"] == "plain.png")
    (test_paths["png_root"] / "plain.png").unlink()

    response = scanned_client.post(f"/api/images/{image_id}/rescan")
    list_after_delete = scanned_client.get("/api/images", params={"q": "plain"})

    assert response.status_code == 404
    assert list_after_delete.status_code == 200
    assert not list_after_delete.json()["items"]


def test_image_rescan_reports_conflict_when_scan_is_running(scanned_client, monkeypatch) -> None:
    container = scanned_client.app.state.container
    monkeypatch.setattr(container.index_service, "rescan_image_now", lambda image_id: None)
    monkeypatch.setattr(container.index_service, "is_scanning", lambda: True)

    response = scanned_client.post("/api/images/1/rescan")

    assert response.status_code == 409


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


def test_metadata_summary_hides_low_value_metadata_keys(scanned_client) -> None:
    response = scanned_client.get("/api/images", params={"q": "photo"})

    assert response.status_code == 200
    item = next(item for item in response.json()["items"] if item["filename"] == "photo.jpg")
    summary_keys = {summary["key"] for summary in item["metadata_summary"]}
    assert "icc_profile.present" not in summary_keys
    assert "icc_profile.summary" not in summary_keys
    assert "exif_present" not in summary_keys


def test_multiple_metadata_filters_are_combined_with_and(scanned_client) -> None:
    response = scanned_client.get(
        "/api/images",
        params=[
            ("metadata_key", "textual_metadata.Author"),
            ("metadata_value", "홍길동"),
            ("metadata_key", "textual_metadata.View"),
            ("metadata_value", "3VV"),
        ],
    )

    assert response.status_code == 200
    filenames = {item["filename"] for item in response.json()["items"]}
    assert "meta.png" in filenames
    assert "plain.png" not in filenames


def test_export_filtered_images_copies_matches_under_export_root(scanned_client, test_paths: dict[str, Path]) -> None:
    response = scanned_client.post(
        "/api/images/export-filtered",
        json={"destination_dir": "review-set", "q": "photo"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["copied"] >= 1
    assert (test_paths["export_root"] / "review-set" / "photo.jpg").exists()


def test_export_filtered_images_can_flatten_and_use_selected_ids(scanned_client, test_paths: dict[str, Path]) -> None:
    list_response = scanned_client.get("/api/images", params={"q": "nested", "page_size": 1000})
    image_id = next(item["id"] for item in list_response.json()["items"] if item["filename"] == "deep.png")

    response = scanned_client.post(
        "/api/images/export-filtered",
        json={"destination_dir": "flat-selection", "structure_mode": "flat", "image_ids": [image_id]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["copied"] == 1
    assert (test_paths["export_root"] / "flat-selection" / "deep.png").exists()
    assert not (test_paths["export_root"] / "flat-selection" / "nested" / "deeper" / "deep.png").exists()


def test_export_filtered_images_can_upload_to_object_storage(scanned_client, monkeypatch) -> None:
    container = scanned_client.app.state.container
    container.settings.object_storage_endpoint_url = "http://minio:9000"
    container.settings.object_storage_access_key_id = "access"
    container.settings.object_storage_secret_access_key = "secret"
    container.settings.object_storage_bucket = "medical-images"
    container.settings.object_storage_prefix = "lakefs/main"
    uploaded: list[tuple[Path, str, str]] = []

    def fake_upload(source_path: Path, object_key: str, *, filename: str):
        uploaded.append((source_path, object_key, filename))

    monkeypatch.setattr(container.object_storage_service, "upload_file", fake_upload)

    response = scanned_client.post(
        "/api/images/export-filtered",
        json={
            "destination_dir": "review-set",
            "q": "photo",
            "storage_backend": "object",
            "structure_mode": "preserve",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["copied"] >= 1
    assert payload["destination_dir"] == "s3://medical-images/lakefs/main/review-set"
    assert any(object_key.endswith("review-set/photo.jpg") for _source_path, object_key, _filename in uploaded)


def test_object_storage_rejects_remote_endpoint_by_default(scanned_client, tmp_path: Path) -> None:
    container = scanned_client.app.state.container
    container.settings.object_storage_endpoint_url = "https://s3.amazonaws.com"
    container.settings.object_storage_access_key_id = "access"
    container.settings.object_storage_secret_access_key = "secret"
    container.settings.object_storage_bucket = "medical-images"
    container.settings.object_storage_allow_remote_endpoint = False

    with pytest.raises(ObjectStorageError):
        container.object_storage_service.upload_file(tmp_path / "image.png", "review-set/image.png", filename="image.png")


def test_export_filtered_images_rejects_path_traversal(scanned_client) -> None:
    response = scanned_client.post(
        "/api/images/export-filtered",
        json={"destination_dir": "../outside", "q": "photo"},
    )

    assert response.status_code == 400


def test_admin_can_update_export_root_without_env_change(client, tmp_path: Path) -> None:
    login = client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    assert login.status_code == 200
    new_export_root = tmp_path / "runtime-exports"

    update_response = client.patch("/api/admin/export-root", json={"root_dir": str(new_export_root)})

    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["root_dir"] == str(new_export_root.resolve())
    assert payload["source"] == "database"
    assert new_export_root.exists()


def test_admin_tracked_metadata_keys_are_returned_with_null_for_missing_values(scanned_client) -> None:
    add_response = scanned_client.post("/api/admin/tracked-metadata-keys", json={"key": "View"})
    assert add_response.status_code == 200
    assert add_response.json()["keys"] == ["View"]

    keys_response = scanned_client.get("/api/metadata/tracked-keys")
    assert keys_response.status_code == 200
    assert keys_response.json()["keys"] == ["View"]

    image_response = scanned_client.get("/api/images", params={"q": "png"})
    assert image_response.status_code == 200
    items = image_response.json()["items"]
    meta_item = next(item for item in items if item["filename"] == "meta.png")
    plain_item = next(item for item in items if item["filename"] == "plain.png")
    assert meta_item["tracked_metadata"]["View"] == "3VV"
    assert plain_item["tracked_metadata"]["View"] is None

    xmp_response = scanned_client.get("/api/images", params={"q": "photo"})
    assert xmp_response.status_code == 200
    xmp_item = next(item for item in xmp_response.json()["items"] if item["filename"] == "photo.jpg")
    assert xmp_item["tracked_metadata"]["View"] == "4CV"

    detail_response = scanned_client.get(f"/api/images/{meta_item['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["tracked_metadata"]["View"] == "3VV"


def test_concurrent_tracked_metadata_key_add_is_idempotent(scanned_client) -> None:
    container = scanned_client.app.state.container

    def add_key() -> list[str]:
        with container.session_factory() as session:
            return container.search_service.add_tracked_metadata_key(session, "View")

    with ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(lambda _index: add_key(), range(12)))

    assert all(result == ["View"] for result in results)


def test_tracked_metadata_key_mutation_requires_admin_account(client) -> None:
    container = client.app.state.container
    viewer_token = container.auth_service.create_session_token("viewer")
    client.cookies.set(container.settings.auth_cookie_name, viewer_token)

    add_response = client.post("/api/admin/tracked-metadata-keys", json={"key": "View"})
    remove_response = client.request("DELETE", "/api/admin/tracked-metadata-keys", json={"key": "View"})

    assert add_response.status_code == 403
    assert remove_response.status_code == 403
