from io import BytesIO
from uuid import UUID

from PIL import Image

from reflow_ocr.schemas.document import Document, DocumentBlock, DocumentPage, TextSpan
from reflow_ocr.services import get_session_store


def _fake_png_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (32, 32), color=(255, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


def test_session_lifecycle(client) -> None:
    create_resp = client.post("/api/sessions/", json={"name": "Test Session"})
    assert create_resp.status_code == 201
    session = create_resp.json()
    session_id = UUID(session["id"])
    assert session["name"] == "Test Session"

    upload_resp = client.post(
        f"/api/sessions/{session_id}/pages",
        files={"files": ("page.png", _fake_png_bytes(), "image/png")},
    )
    assert upload_resp.status_code == 200
    detail = upload_resp.json()
    assert detail["page_count"] == 1
    page_id = UUID(detail["pages"][0]["id"])

    reorder_resp = client.post(
        f"/api/sessions/{session_id}/pages/reorder",
        json={"order": [str(page_id)]},
    )
    assert reorder_resp.status_code == 200

    list_resp = client.get("/api/sessions/")
    assert list_resp.status_code == 200
    assert any(item["id"] == str(session_id) for item in list_resp.json())

    patch_resp = client.patch(f"/api/sessions/{session_id}", json={"description": "Demo"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["description"] == "Demo"

    archive_resp = client.get(f"/api/sessions/{session_id}/archive")
    assert archive_resp.status_code == 200
    archive_data = archive_resp.content
    assert archive_data.startswith(b"PK")

    import_resp = client.post(
        "/api/sessions/import",
        files={"file": ("import.reflow-session", archive_data, "application/zip")},
    )
    assert import_resp.status_code == 200
    imported = import_resp.json()
    assert imported["id"] != str(session_id)
    assert imported["page_count"] == 1
    client.delete(f"/api/sessions/{imported['id']}")

    delete_page_resp = client.delete(f"/api/sessions/{session_id}/pages/{page_id}")
    assert delete_page_resp.status_code == 200
    assert delete_page_resp.json()["page_count"] == 0

    delete_resp = client.delete(f"/api/sessions/{session_id}")
    assert delete_resp.status_code == 204


def test_export_document(client) -> None:
    create_resp = client.post("/api/sessions/", json={"name": "Export Session"})
    session_id = UUID(create_resp.json()["id"])
    store = get_session_store()
    doc = Document(
        pages=[
            DocumentPage(
                index=0,
                width=100,
                height=100,
                blocks=[
                    DocumentBlock(
                        id="b1",
                        type="paragraph",
                        bbox=[0, 0, 100, 20],
                        spans=[TextSpan(text="Пример текста", confidence=0.9, bbox=[0, 0, 50, 10])],
                    )
                ],
            )
        ]
    )
    store.save_document(session_id, doc)

    export_resp = client.post(f"/api/sessions/{session_id}/export", json={"format": "markdown"})
    assert export_resp.status_code == 200
    assert export_resp.headers["content-type"].startswith("text/markdown")
    assert "Пример текста" in export_resp.content.decode("utf-8")

    client.delete(f"/api/sessions/{session_id}")
