"""macOS osascript の display notification ラッパ。

bash の `notify()` をそのまま Python 化したもの。OS 非対応 / osascript 不在環境では
NullNotifier に切替えてログだけ残す。
"""
from __future__ import annotations

import shutil
import subprocess
from typing import Protocol


def _escape_for_osascript(text: str) -> str:
    """osascript 文字列リテラル用に " と \\ をエスケープし、改行を空白に置換する。"""
    return (
        text.replace("\r", " ")
        .replace("\n", " ")
        .replace("\\", "\\\\")
        .replace('"', '\\"')
    )


class Notifier(Protocol):
    def notify(self, subtitle: str, message: str, sound: str | None = None) -> None: ...


class OsascriptNotifier:
    """macOS の `osascript -e 'display notification ...'` 呼出ラッパ。

    title は固定値で渡される（既定: "Episodic Recording Sync"）。
    """

    def __init__(self, title: str = "Episodic Recording Sync") -> None:
        self.title = title

    def notify(self, subtitle: str, message: str, sound: str | None = None) -> None:
        if shutil.which("osascript") is None:
            return
        sub_esc = _escape_for_osascript(subtitle)
        msg_esc = _escape_for_osascript(message)
        title_esc = _escape_for_osascript(self.title)
        script = (
            f'display notification "{msg_esc}" with title "{title_esc}"'
            f' subtitle "{sub_esc}"'
        )
        if sound:
            sound_esc = _escape_for_osascript(sound)
            script += f' sound name "{sound_esc}"'
        try:
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                check=False,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            pass


class NullNotifier:
    """no-op Notifier（osascript 不在環境 / テスト用）。"""

    def notify(self, subtitle: str, message: str, sound: str | None = None) -> None:
        return


def default_notifier(title: str = "Episodic Recording Sync") -> Notifier:
    """osascript があれば OsascriptNotifier、無ければ NullNotifier を返す。"""
    if shutil.which("osascript") is None:
        return NullNotifier()
    return OsascriptNotifier(title=title)
