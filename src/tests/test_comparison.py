import pytest

from siteqa_mcp.comparison import compare_saved_audits
from siteqa_mcp.storage import load_audit, save_audit


def report(findings, **overrides):
    return {
        "start_url": "https://example.com/",
        "inspected_urls": ["https://example.com/"],
        "limit_reached": False,
        "remaining_urls": [],
        "fetch_issues": [],
        "scope": "Test audit rules",
        "findings": findings,
        **overrides,
    }


def finding(code):
    return {
        "code": code,
        "page_url": "https://example.com/",
        "message": code,
        "evidence": {},
    }


def compare_documents(tmp_path, before, after):
    first = save_audit(before, 10, tmp_path)
    second = save_audit(after, 10, tmp_path)

    return compare_saved_audits(
        first["audit_id"],
        second["audit_id"],
        tmp_path,
    )


def test_classifies_changes(tmp_path):
    result = compare_documents(
        tmp_path,
        report([
            finding("missing_title"),
            finding("multiple_canonicals"),
        ]),
        report([
            finding("multiple_canonicals"),
            finding("invalid_canonical"),
        ]),
    )

    assert result["summary"] == {
        "resolved": 1,
        "remaining": 1,
        "newly_observed": 1,
        "unverified": 0,
    }
    assert result["resolved"][0]["code"] == "missing_title"
    assert result["coverage_warnings"] == []


@pytest.mark.parametrize(
    "changes",
    [
        {"limit_reached": True},
        {"inspected_urls": []},
        {"fetch_issues": [{"reason": "Timeout"}]},
    ],
)
def test_incomplete_coverage_cannot_prove_resolution(tmp_path, changes):
    result = compare_documents(
        tmp_path,
        report([finding("missing_title")]),
        report([], **changes),
    )

    assert result["summary"]["resolved"] == 0
    assert result["summary"]["unverified"] == 1
    assert result["coverage_warnings"]


def test_rejects_different_sites(tmp_path):
    with pytest.raises(ValueError, match="starting URL"):
        compare_documents(
            tmp_path,
            report([]),
            report([], start_url="https://other.com/"),
        )


def test_rejects_path_instead_of_audit_id(tmp_path):
    with pytest.raises(ValueError, match="Invalid audit ID"):
        load_audit("../outside", tmp_path)
