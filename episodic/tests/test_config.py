"""lib/config.py の単体テスト。

mount canary（is_mount_active）による normal/staged 切替、env override、
load_config の lru_cache 挙動、host_hash の安定性（_machine_id をモック）を検証する。

config.* は lru_cache（load_config / host_hash / _machine_id）を持つため、
他テストへ状態が漏れないよう fixture の前後で必ず cache_clear する。
実ユーザの ~/.config/episodic/config.toml が混入しないよう CONFIG_PATH も差し替える。
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lib import config as config_mod  # noqa: E402


@pytest.fixture
def cfg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """MEMORIES_DIR / FALLBACK_DIR を tmp に固定し、config の各 lru_cache をクリアする。"""
    mem = tmp_path / "memory"
    fb = tmp_path / "staging"
    mem.mkdir()
    fb.mkdir()
    monkeypatch.setenv("MEMORIES_DIR", str(mem))
    monkeypatch.setenv("MEMORIES_FALLBACK_DIR", str(fb))
    # 実ユーザ config.toml の混入を防ぐ（CONFIG_PATH は import 時に確定するため差し替え）
    monkeypatch.setattr(config_mod, "CONFIG_PATH", tmp_path / "no-such-config.toml")
    config_mod.load_config.cache_clear()
    config_mod.host_hash.cache_clear()
    yield {"config": config_mod, "memories": mem, "fallback": fb}
    config_mod.load_config.cache_clear()
    config_mod.host_hash.cache_clear()


# ---------------------------------------------------------------- env override


def test_env_override_memories_and_fallback(cfg) -> None:
    config = cfg["config"]
    assert config.resolve_memories_dir() == cfg["memories"].resolve()
    assert config.resolve_fallback_dir() == cfg["fallback"].resolve()


# ---------------------------------------------------------------- is_mount_active


def test_is_mount_active_reflects_canary(cfg) -> None:
    config = cfg["config"]
    assert config.is_mount_active() is False
    (cfg["memories"] / ".mount-canary").write_text("ok")
    assert config.is_mount_active() is True


# ---------------------------------------------------------------- effective_raw_root


def test_effective_raw_root_normal_when_mounted(cfg) -> None:
    config = cfg["config"]
    (cfg["memories"] / ".mount-canary").write_text("ok")
    root, staged = config.effective_raw_root()
    assert staged is False
    assert root == cfg["memories"].resolve() / "raw" / "session"


def test_effective_raw_root_staged_when_unmounted(cfg) -> None:
    config = cfg["config"]
    root, staged = config.effective_raw_root()
    assert staged is True
    assert root == cfg["fallback"].resolve()


# ---------------------------------------------------------------- effective_snapshot_root


def test_effective_snapshot_root_normal_when_mounted(cfg) -> None:
    config = cfg["config"]
    (cfg["memories"] / ".mount-canary").write_text("ok")
    root, staged = config.effective_snapshot_root()
    assert staged is False
    assert root == cfg["memories"].resolve() / "raw" / "session-source"


def test_effective_snapshot_root_staged_when_unmounted(cfg) -> None:
    config = cfg["config"]
    root, staged = config.effective_snapshot_root()
    assert staged is True
    assert root == cfg["fallback"].resolve() / "session-source"


# ---------------------------------------------------------------- load_config lru_cache


def test_load_config_caches_same_object(cfg) -> None:
    config = cfg["config"]
    first = config.load_config()
    assert config.load_config() is first


def test_load_config_env_change_needs_cache_clear(cfg, monkeypatch) -> None:
    config = cfg["config"]
    first = config.load_config()
    assert first["stop_debounce_seconds"] == 60  # 既定
    monkeypatch.setenv("MEMORIES_STOP_DEBOUNCE_SECONDS", "123")
    # クリア前は反映されない（同一キャッシュ）
    assert config.load_config()["stop_debounce_seconds"] == 60
    config.load_config.cache_clear()
    assert config.load_config()["stop_debounce_seconds"] == 123


# ---------------------------------------------------------------- host_hash


def test_host_hash_stable_and_length(cfg, monkeypatch) -> None:
    config = cfg["config"]
    monkeypatch.setattr(config, "_machine_id", lambda: "FIXED-UUID-1234")
    config.host_hash.cache_clear()
    expected = hashlib.sha1(b"FIXED-UUID-1234").hexdigest()
    assert config.host_hash() == expected[:8]  # 既定長 8
    # 同一マシン ID なら安定
    assert config.host_hash() == config.host_hash()
    # 明示長
    assert config.host_hash(12) == expected[:12]


def test_host_hash_length_from_env(cfg, monkeypatch) -> None:
    config = cfg["config"]
    monkeypatch.setattr(config, "_machine_id", lambda: "ABC")
    monkeypatch.setenv("MEMORIES_HOSTNAME_HASH_LENGTH", "10")
    config.load_config.cache_clear()
    config.host_hash.cache_clear()
    expected = hashlib.sha1(b"ABC").hexdigest()
    assert config.host_hash() == expected[:10]


def test_host_hash_machine_id_change_after_clear(cfg, monkeypatch) -> None:
    config = cfg["config"]
    monkeypatch.setattr(config, "_machine_id", lambda: "machine-A")
    config.host_hash.cache_clear()
    a = config.host_hash()
    monkeypatch.setattr(config, "_machine_id", lambda: "machine-B")
    config.host_hash.cache_clear()
    b = config.host_hash()
    assert a != b
    assert a == hashlib.sha1(b"machine-A").hexdigest()[:8]
    assert b == hashlib.sha1(b"machine-B").hexdigest()[:8]


# ---------------------------------------------------------------- notification_level


def test_notification_level_default_is_all(cfg, monkeypatch) -> None:
    # conftest の autouse ガードが MEMORIES_NOTIFICATION_LEVEL=none を注入するため、
    # 「env 未設定時の既定値」を検証する本テストでは明示的に外す。
    monkeypatch.delenv("MEMORIES_NOTIFICATION_LEVEL", raising=False)
    cfg["config"].load_config.cache_clear()
    assert cfg["config"].resolve_notification_level() == "all"


def test_notification_level_env_override(cfg, monkeypatch) -> None:
    config = cfg["config"]
    monkeypatch.setenv("MEMORIES_NOTIFICATION_LEVEL", "failure")
    config.load_config.cache_clear()
    assert config.resolve_notification_level() == "failure"


def test_notification_level_invalid_falls_back_to_all(cfg, monkeypatch) -> None:
    config = cfg["config"]
    monkeypatch.setenv("MEMORIES_NOTIFICATION_LEVEL", "quiet")
    config.load_config.cache_clear()
    assert config.resolve_notification_level() == "all"
