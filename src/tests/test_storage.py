import json
from pathlib import Path

from siteqa_mcp.storage import save_audit


def test_repeated_audits_preserve_both_reports(tmp_path):
    report = {
        "start_url": "https://example.com/",
        "findings": [],
    }

    first = save_audit(report, 10, tmp_path)
    second = save_audit(report, 10, tmp_path)

    assert first["audit_id"] != second["audit_id"]
    assert len(list(tmp_path.glob("*.json"))) == 2

    for document in [first, second]:
        saved = json.loads(
            Path(document["report_path"]).read_text(encoding="utf-8")
        )
        assert saved == document


def test_explicit_directory_overrides_environment(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "SITEQA_AUDIT_DIR", str(tmp_path / "environment")
    )
    explicit = tmp_path / "chosen"

    document = save_audit(
        {"findings": []},
        max_pages=5,
        output_dir=explicit,
    )

    assert Path(document["report_path"]).parent == explicit.resolve()
    assert not (tmp_path / "environment").exists()
