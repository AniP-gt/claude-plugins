"""mkdir 方式の排他ロック。

`mkdir` の atomic 性を利用した PID 付きロック。bash 実装（sync-pending.sh）の
acquire_lock / release_lock を完全互換で Python 化したもの。

主要不変条件:
- PID は別ファイル経由で atomic に書き込む（write tmp → mv）
- pid 空ファイル状態は「別プロセスが mkdir 直後で書込み中」と解釈し、stale 扱いしない
- stale（プロセス不在）は奪取可能
"""
from __future__ import annotations

import contextlib
import os
import subprocess
from pathlib import Path


def _is_pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        # last resort: ps -p
        try:
            return subprocess.run(
                ["ps", "-p", str(pid)],
                capture_output=True,
                check=False,
            ).returncode == 0
        except OSError:
            return False


class MkdirLock:
    """mkdir 方式の排他ロック。

    Usage:
        lock = MkdirLock(state_dir / "sync-pending.lock.d")
        if not lock.acquire():
            return
        try:
            ...
        finally:
            lock.release()

    あるいは context manager:
        with MkdirLock(...) as ok:
            if not ok:
                return
            ...
    """

    def __init__(self, lock_dir: Path) -> None:
        self.lock_dir = Path(lock_dir)
        self.pid_file = self.lock_dir / "pid"
        self._acquired = False

    def _write_pid_atomic(self) -> None:
        tmp = self.lock_dir / f"pid.{os.getpid()}"
        try:
            tmp.write_text(f"{os.getpid()}\n", encoding="utf-8")
            os.replace(tmp, self.pid_file)
        except OSError:
            with contextlib.suppress(OSError):
                tmp.unlink()

    def _try_mkdir(self) -> bool:
        try:
            self.lock_dir.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.chmod(self.lock_dir.parent, 0o700)
            except OSError:
                pass
            self.lock_dir.mkdir()
            return True
        except FileExistsError:
            return False
        except OSError:
            return False

    def _read_pid(self) -> int | None:
        try:
            text = self.pid_file.read_text(encoding="utf-8").strip()
        except OSError:
            return None
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None

    def acquire(self) -> bool:
        """ロック取得を試みる。取得成功で True。"""
        if self._try_mkdir():
            self._write_pid_atomic()
            self._acquired = True
            return True

        old_pid = self._read_pid()
        if old_pid is None:
            # PID 空 = 別プロセスが mkdir 直後で書込み中
            return False
        if _is_pid_alive(old_pid):
            return False

        # stale ロック奪取
        try:
            self._remove_lock_dir()
        except OSError:
            return False
        if self._try_mkdir():
            self._write_pid_atomic()
            self._acquired = True
            return True
        return False

    def _remove_lock_dir(self) -> None:
        if not self.lock_dir.exists():
            return
        for child in self.lock_dir.iterdir():
            with contextlib.suppress(OSError):
                child.unlink()
        with contextlib.suppress(OSError):
            self.lock_dir.rmdir()

    def release(self) -> None:
        """ロック解放。pid が自分の時のみ削除する（他 PID 保全）。"""
        if not self._acquired:
            return
        pid = self._read_pid()
        if pid == os.getpid():
            with contextlib.suppress(OSError):
                self._remove_lock_dir()
        self._acquired = False

    def __enter__(self) -> bool:
        return self.acquire()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()
