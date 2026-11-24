from base64 import b64encode
from collections.abc import Callable
from pathlib import Path

import pytest
from kubernetes.client import V1ObjectMeta, V1Secret
from kubernetes.watch import Watch

from kube_certificates_syncer import main


def secret(value: str = "certificate") -> V1Secret:
    return V1Secret(
        metadata=V1ObjectMeta(
            name="example",
            annotations={"enabled": "true", "dry-run": "false"},
        ),
        data={"tls.crt": b64encode(value.encode()).decode()},
    )


@pytest.fixture
def run_events(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Callable[[list[dict[str, object]]], None]:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SYNCDIR", str(tmp_path))
    monkeypatch.setenv("NAMESPACE", "test")
    (tmp_path / "config.yaml").write_text(
        "filter:\n  annotations:\n    enabled: 'true'\n    dry-run: 'false'\n"
        "remap:\n  - name: tls.crt\n    value: '{{secretName}}.crt'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(main, "load_kube_config", lambda: None)

    def run(events: list[dict[str, object]]) -> None:
        monkeypatch.setattr(Watch, "stream", lambda *args, **kwargs: iter(events))
        main.main()

    return run


def test_secret_lifecycle(
    tmp_path: Path, run_events: Callable[[list[dict[str, object]]], None]
) -> None:
    certificate = tmp_path / "example.crt"
    unrelated = tmp_path / "unrelated.crt"
    unrelated.write_text("keep", encoding="utf-8")
    run_events([{"type": "ADDED", "object": secret()}])
    assert certificate.read_text(encoding="utf-8") == "certificate"
    run_events([{"type": "MODIFIED", "object": secret("renewed")}])
    assert certificate.read_text(encoding="utf-8") == "renewed"
    run_events([{"type": "DELETED", "object": secret()}])
    assert not certificate.exists()
    assert unrelated.read_text(encoding="utf-8") == "keep"


def test_all_annotations_must_match(
    tmp_path: Path, run_events: Callable[[list[dict[str, object]]], None]
) -> None:
    filtered = secret()
    assert filtered.metadata is not None
    filtered.metadata.annotations = {"enabled": "true", "dry-run": "true"}
    run_events([{"type": "ADDED", "object": filtered}])
    assert not (tmp_path / "example.crt").exists()


def test_write_error_does_not_stop_later_events(
    tmp_path: Path,
    run_events: Callable[[list[dict[str, object]]], None],
    caplog: pytest.LogCaptureFixture,
) -> None:
    (tmp_path / "example.crt").mkdir()
    later = secret("next certificate")
    assert later.metadata is not None
    later.metadata.name = "later"
    run_events(
        [
            {"type": "ADDED", "object": secret()},
            {"type": "ADDED", "object": later},
        ]
    )
    assert "cannot be synced" in caplog.text
    assert (tmp_path / "later.crt").read_text(encoding="utf-8") == "next certificate"


@pytest.mark.parametrize("value", ["!invalid!", b64encode(b"\xff").decode()])
def test_invalid_certificate_keeps_existing_file(
    value: str,
    tmp_path: Path,
    run_events: Callable[[list[dict[str, object]]], None],
) -> None:
    certificate = tmp_path / "example.crt"
    certificate.write_text("previous certificate", encoding="utf-8")
    invalid = secret()
    invalid.data = {"tls.crt": value}
    run_events([{"type": "MODIFIED", "object": invalid}])
    assert certificate.read_text(encoding="utf-8") == "previous certificate"
