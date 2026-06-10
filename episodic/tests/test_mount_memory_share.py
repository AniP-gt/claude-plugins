"""bin/mount_memory_share.py の単体テスト。"""
from __future__ import annotations

import importlib
import platform
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "bin"))


@pytest.fixture
def mod(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("MEMORIES_CONFIG_DIR", str(tmp_path / "config"))
    sys.modules.pop("mount_memory_share", None)
    m = importlib.import_module("mount_memory_share")
    importlib.reload(m)
    return m


def test_non_macos_skips(mod, monkeypatch) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    assert mod.run() == 0


def test_required_command_missing(mod, monkeypatch) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    # /sbin/mount_smbfs が無い前提で os.access を強制 False に
    monkeypatch.setattr(mod.os, "access", lambda p, m: False)
    assert mod.run() == 0


def test_toml_get_basic(mod, tmp_path: Path) -> None:
    p = tmp_path / "c.toml"
    p.write_text('memories_dir = "/x/y"\nsmb_share = "//u@h/s"\n')
    assert mod._toml_get("memories_dir", p) == "/x/y"
    assert mod._toml_get("smb_share", p) == "//u@h/s"
    assert mod._toml_get("missing", p) == ""


def test_mask_smb_url(mod) -> None:
    assert mod._mask_smb_url("smb://user@host/share") == "smb://***@host/share"
    assert mod._mask_smb_url("smb://host/share") == "smb://host/share"


# --------------------------------------------------------------------------- #
# _load_secrets_env（パーミッション判定）
# --------------------------------------------------------------------------- #
def _write_secrets(mod, content: str, mode: int) -> Path:
    """SECRETS_ENV を所定パーミッションで作成する。"""
    mod.SECRETS_ENV.parent.mkdir(parents=True, exist_ok=True)
    mod.SECRETS_ENV.write_text(content, encoding="utf-8")
    mod.SECRETS_ENV.chmod(mode)
    return mod.SECRETS_ENV


def test_load_secrets_env_missing_file_returns_empty(mod) -> None:
    assert not mod.SECRETS_ENV.exists()
    assert mod._load_secrets_env() == {}


def test_load_secrets_env_skips_non_0600(mod) -> None:
    """0o600 以外（ここでは 0o644）のときは漏洩防止のため読み込みをスキップする。"""
    _write_secrets(mod, "MEMORIES_SMB_USER=alice\n", 0o644)
    assert mod._load_secrets_env() == {}
    # スキップ理由が smb-mount.log に warn として記録される
    assert mod.LOG_FILE.exists()
    log = mod.LOG_FILE.read_text(encoding="utf-8")
    assert "permissions" in log and "Skipping load" in log


def test_load_secrets_env_reads_when_0600(mod) -> None:
    """0o600 のときは読み込み、クォートとコメントを正しく処理する。"""
    _write_secrets(
        mod,
        '# comment line\n'
        'MEMORIES_SMB_USER=alice\n'
        'MEMORIES_SMB_SHARE="//srv.local/share"\n'
        "MEMORIES_SMB_PING_HOST='srv.local'\n"
        "\n"
        "INVALID LINE WITHOUT EQUALS\n",
        0o600,
    )
    out = mod._load_secrets_env()
    assert out == {
        "MEMORIES_SMB_USER": "alice",
        "MEMORIES_SMB_SHARE": "//srv.local/share",
        "MEMORIES_SMB_PING_HOST": "srv.local",
    }


# --------------------------------------------------------------------------- #
# run()（mount コマンド組立・canary 検証・fallback 分岐）
# --------------------------------------------------------------------------- #
class _FakeResult:
    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def _patch_darwin(mod, monkeypatch) -> None:
    """run() の macOS 前提ゲート（platform/コマンド実行ビット）を通過させる。

    /sbin/mount・/sbin/ping・/sbin/mount_smbfs の存在は macOS の実ファイルに依存する
    （本テストは darwin 上で実行する前提）。実行ビット判定のみ os.access で True 固定する。
    """
    monkeypatch.setattr(mod.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(mod.os, "access", lambda p, m: True)


def _setup_mount_point(mod, tmp_path: Path, *, with_canary: bool, extra_file: bool = False) -> Path:
    mp = tmp_path / "mnt"
    mp.mkdir(parents=True, exist_ok=True)
    if with_canary:
        (mp / ".mount-canary").write_text("", encoding="utf-8")
    if extra_file:
        (mp / "stub-leftover.txt").write_text("legacy", encoding="utf-8")
    return mp


def _make_subprocess(mount_calls, *, mount_output="", ping_rc=0, mount_smbfs_rc=0):
    """args[0] でルーティングする subprocess.run スタブ。mount_smbfs 呼び出しを記録する。"""
    def fake_run(args, **kw):
        cmd = args[0]
        if cmd == "/sbin/mount":
            return _FakeResult(stdout=mount_output, returncode=0)
        if cmd == "/sbin/ping":
            return _FakeResult(returncode=ping_rc)
        if cmd == "/sbin/mount_smbfs":
            mount_calls.append(args)
            return _FakeResult(returncode=mount_smbfs_rc)
        raise AssertionError(f"unexpected subprocess call: {args}")

    return fake_run


def test_run_assembles_mount_smbfs_command_with_masked_log(mod, monkeypatch, tmp_path) -> None:
    """mount_smbfs の引数組立と、認証情報入り SMB URL のマスクログを検証する。"""
    _patch_darwin(mod, monkeypatch)
    mp = _setup_mount_point(mod, tmp_path, with_canary=True)
    monkeypatch.setenv("MEMORIES_DIR", str(mp))
    monkeypatch.setenv("MEMORIES_SMB_SHARE", "//srv.local/share")
    monkeypatch.setenv("MEMORIES_SMB_USER", "alice")

    calls: list = []
    monkeypatch.setattr(mod.subprocess, "run", _make_subprocess(calls))

    rc = mod.run()
    assert rc == 0
    assert len(calls) == 1
    expected_share = "//alice@srv.local/share"
    assert calls[0] == [
        "/sbin/mount_smbfs", "-N", "-o", "nobrowse,nodev,nosuid",
        expected_share, str(mp),
    ]
    # ログには認証情報がマスクされた URL のみが残り、生のユーザー名は出ない
    log = mod.LOG_FILE.read_text(encoding="utf-8")
    assert "smb://***@srv.local/share" in log
    assert "alice" not in log


def test_run_noop_when_already_mounted(mod, monkeypatch, tmp_path) -> None:
    _patch_darwin(mod, monkeypatch)
    mp = _setup_mount_point(mod, tmp_path, with_canary=True)
    monkeypatch.setenv("MEMORIES_DIR", str(mp))
    monkeypatch.setenv("MEMORIES_SMB_SHARE", "//srv.local/share")

    calls: list = []
    monkeypatch.setattr(
        mod.subprocess, "run",
        _make_subprocess(calls, mount_output=f" on {mp} (smbfs)\n"),
    )
    rc = mod.run()
    assert rc == 0
    # 既マウントなら mount_smbfs は呼ばれない
    assert calls == []


def test_run_returns_1_when_host_unreachable(mod, monkeypatch, tmp_path) -> None:
    _patch_darwin(mod, monkeypatch)
    mp = _setup_mount_point(mod, tmp_path, with_canary=True)
    monkeypatch.setenv("MEMORIES_DIR", str(mp))
    monkeypatch.setenv("MEMORIES_SMB_SHARE", "//srv.local/share")

    calls: list = []
    monkeypatch.setattr(mod.subprocess, "run", _make_subprocess(calls, ping_rc=1))
    rc = mod.run()
    assert rc == 1
    assert calls == []


def test_run_returns_4_when_mount_point_missing(mod, monkeypatch, tmp_path) -> None:
    _patch_darwin(mod, monkeypatch)
    missing = tmp_path / "absent"  # 作成しない
    monkeypatch.setenv("MEMORIES_DIR", str(missing))
    monkeypatch.setenv("MEMORIES_SMB_SHARE", "//srv.local/share")

    calls: list = []
    monkeypatch.setattr(mod.subprocess, "run", _make_subprocess(calls))
    # マウントポイント未作成のため mp.is_dir() が False となり 4 を返す
    rc = mod.run()
    assert rc == 4
    assert calls == []


def test_run_returns_5_on_stale_stub_without_canary(mod, monkeypatch, tmp_path) -> None:
    """canary 不在かつ非空のマウントポイントは stale stub として 5 で中断する。"""
    _patch_darwin(mod, monkeypatch)
    mp = _setup_mount_point(mod, tmp_path, with_canary=False, extra_file=True)
    monkeypatch.setenv("MEMORIES_DIR", str(mp))
    monkeypatch.setenv("MEMORIES_SMB_SHARE", "//srv.local/share")

    calls: list = []
    monkeypatch.setattr(mod.subprocess, "run", _make_subprocess(calls))
    rc = mod.run()
    assert rc == 5
    # stale stub 検出時点で中断し mount_smbfs に到達しない
    assert calls == []


def test_run_returns_2_when_mount_fails(mod, monkeypatch, tmp_path) -> None:
    """mount_smbfs が非ゼロ終了したときは 2 を返し失敗ログを残す。"""
    _patch_darwin(mod, monkeypatch)
    mp = _setup_mount_point(mod, tmp_path, with_canary=True)
    monkeypatch.setenv("MEMORIES_DIR", str(mp))
    monkeypatch.setenv("MEMORIES_SMB_SHARE", "//srv.local/share")
    monkeypatch.setenv("MEMORIES_SMB_USER", "alice")

    calls: list = []
    monkeypatch.setattr(
        mod.subprocess, "run", _make_subprocess(calls, mount_smbfs_rc=2),
    )
    rc = mod.run()
    assert rc == 2
    assert len(calls) == 1
    log = mod.LOG_FILE.read_text(encoding="utf-8")
    assert "mount failed" in log
    assert "alice" not in log  # 失敗ログでも認証情報はマスクされる
