"""Build an auditable source-only candidate archive from a fixed allowlist."""

import ast
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILES = [
    "_manifest.json",
    "plugin.py",
    "errors.py",
    "baidu_client.py",
    "search_service.py",
    "quota_manager.py",
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
    ".gitignore",
    "pyproject.toml",
    "requirements-dev.txt",
    "build_release.py",
    "tests/conftest.py",
    "tests/test_baidu_client.py",
    "tests/test_search_service.py",
    "tests/test_quota_manager.py",
    "tests/test_plugin.py",
    "tests/test_runner_integration.py",
    "tests/test_host_tool_contract.py",
    "tests/test_wire_integration.py",
    "tests/quota_worker.py",
    "docs/TEST_REPORT.md",
    "docs/THIRD_PARTY_NOTICES.md",
    "docs/VALIDATION.json",
    "docs/LIVE_API_TEST.json",
    "docs/ACCEPTANCE_REPORT.md",
    "docs/ACCEPTANCE_RESULT.json",
]


def build():
    manifest = json.loads((ROOT / "_manifest.json").read_text("utf-8"))
    assert manifest["version"] == "0.1.0" and manifest["manifest_version"] == 2
    blobs = {}
    for name in FILES:
        blob = (ROOT / name).read_bytes()
        source = blob.decode("utf-8")
        if name.endswith(".py"):
            ast.parse(source, filename=name)
        # A narrow, documented check, not a guarantee of absence of every secret.
        assert not re.search(r"-----BEGIN (?:OPENSSH|RSA|EC) PRIVATE KEY-----|bce-v3/[A-Za-z0-9_-]{16,}", source), name
        blobs[name] = blob
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    archive_path = output / "maibot-baidu-search-0.1.0.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, blob in sorted(blobs.items()):
            info = zipfile.ZipInfo("maibot-baidu-search/" + name, date_time=(2026, 10, 24, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, blob)
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == len(FILES)
        for name, blob in blobs.items():
            assert archive.read("maibot-baidu-search/" + name) == blob
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    (output / "SHA256SUMS.txt").write_text(f"{digest}  {archive_path.name}\n", encoding="utf-8")
    print(json.dumps({"archive": str(archive_path), "files": len(FILES), "sha256": digest}, ensure_ascii=False))


if __name__ == "__main__":
    build()
