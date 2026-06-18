"""codex CLI を subprocess で起動し、timeout / SIGTERM 昇格を扱うランナー。

bash runner.sh の `run_codex_exec` を抽出。session / wiki 両方で使う。

特徴:
- `start_new_session=True` でプロセスグループを分離
- timeout 経過時は SIGTERM → 10s 待機 → SIGKILL
- `-o capture_file` で codex の last_message を取得
- CODEX_BIN は world-writable ディレクトリ配下の場合 reject（PATH 攻撃対策）
"""
from __future__ import annotations

import datetime
import os
import shutil
import signal
import stat
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CodexResult:
    returncode: int
    timed_out: bool = False
    last_message: str = ""
    log_appended_bytes: int = 0


@dataclass
class CodexRunner:
    """codex CLI 起動ヘルパ。

    Args:
        codex_bin: codex 実行ファイルパス（None なら $CODEX_BINARY → which("codex")）
        model: model 名（例 "gpt-5.4-mini"）
        effort: model_reasoning_effort（minimal/low/medium/high/xhigh）
        timeout_seconds: 0 で無効
        multi_agent: True で `-c features.multi_agent=true` を付与し、lead が
            subagent を spawn できるようにする（subagent は lead と同一モデルを
            full-history fork で継承するため追加のモデル指定はしない）。
            full-history fork は subagent ごとに lead の全履歴を複製しトークン
            消費を数倍にするため、既定は False（subagent 無効）。
        web_search: True で `-c tools.web_search=true` を付与し、codex から
            web 検索ツールを利用可能にする（org の公式情報裏取り用）。サーバ側
            ツールのため read-only / workspace-write いずれの sandbox でも機能する。
        bypass_sandbox: True（既定）で `--dangerously-bypass-approvals-and-sandbox`
            を付与し、技術的サンドボックスを無効化する（現状互換）。この場合
            `--sandbox` 値は事実上無視され、untrusted Web コンテンツ由来の埋め込み
            指示が codex に実行された際にユーザー権限で任意ファイル書き込みが理論上可能。
            False にすると bypass フラグを外し、`--sandbox`（既定 workspace-write）を
            実効化したうえで `-c approval_policy=never` を付与して非対話 exec が承認
            待ちでブロックしないようにする。書き込み先を workspace に限定したいジョブ
            （wiki ディレクトリのみ書き込む等）で `cwd_dir` と併用する。
        cwd_dir: codex の作業ルート（`-C` で指定）。workspace-write 時の書き込み
            許可範囲を当該ディレクトリに限定したい場合に指定する。None で未指定。
        extra_args: codex exec の前段に追加する引数（cwd など必要なら）
        env_overrides: subprocess env への追加
    """

    model: str
    effort: str
    timeout_seconds: int = 300
    codex_bin: str | None = None
    sandbox_mode: str = "workspace-write"
    multi_agent: bool = False
    web_search: bool = False
    bypass_sandbox: bool = True
    cwd_dir: str | None = None
    extra_args: list[str] = field(default_factory=list)
    env_overrides: dict[str, str] = field(default_factory=dict)

    def resolve_binary(self) -> str:
        binary = self.codex_bin or os.environ.get("CODEX_BINARY") or shutil.which("codex")
        if not binary:
            raise FileNotFoundError("codex binary not found in PATH and CODEX_BINARY unset")
        if not os.access(binary, os.X_OK):
            raise PermissionError(f"codex binary not executable: {binary}")
        real = os.path.realpath(binary)
        # world-writable ディレクトリ配下を拒否（PATH 攻撃対策）。
        for parent in (Path(real).parent, *Path(real).parents):
            try:
                st = parent.stat()
            except OSError:
                continue
            if st.st_mode & stat.S_IWOTH:
                raise PermissionError(f"codex binary parent is world-writable: {parent}")
            if str(parent) == "/":
                break
        return real

    def build_cmd(self, capture_file: Path) -> list[str]:
        binary = self.resolve_binary()
        cmd = [
            binary,
            "exec",
            "--disable",
            "hooks",
            "--ignore-user-config",
            "--ephemeral",
            "--skip-git-repo-check",
            "--sandbox",
            self.sandbox_mode,
        ]
        if self.bypass_sandbox:
            # 現状互換: 技術的サンドボックスを無効化する（外部サンドボックス前提）。
            # この場合 --sandbox 値は事実上無視される。
            cmd.append("--dangerously-bypass-approvals-and-sandbox")
        else:
            # 実サンドボックス運用: bypass せず --sandbox を実効化する。
            # exec は非対話で承認に応答できないため never を明示してブロックを防ぐ。
            cmd += ["-c", "approval_policy=never"]
        if self.cwd_dir:
            cmd += ["-C", self.cwd_dir]
        cmd += ["-c", f"model_reasoning_effort={self.effort}"]
        if self.multi_agent:
            # runner は --ignore-user-config を渡すため config.toml に頼れない。
            # CLI フラグで multi_agent を有効化し、lead が subagent を spawn できるようにする。
            cmd += ["-c", "features.multi_agent=true"]
        if self.web_search:
            # codex exec では `--search` フラグは非対応。`-c tools.web_search=true` で
            # サーバ側 web 検索ツールを有効化する。effort=low 以上で動作する。
            cmd += ["-c", "tools.web_search=true"]
        cmd += [
            "-m",
            self.model,
            "-o",
            str(capture_file),
            *self.extra_args,
        ]
        return cmd

    def run(
        self,
        input_path: Path,
        log_file: Path,
        capture_file: Path | None = None,
    ) -> CodexResult:
        """codex を実行し、結果を返す。stdin に input_path を流し込む。"""
        if capture_file is None:
            capture_file = Path(
                str(log_file) + ".codex-capture"
            )  # 呼び出し側で明示推奨
        cmd = self.build_cmd(capture_file)
        env = dict(os.environ)
        env["EPISODIC_RECORDING_ACTIVE"] = "1"
        env.update(self.env_overrides)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        timed_out = False
        appended = 0
        with open(input_path, "rb") as stdin, open(log_file, "ab") as logf:
            proc = subprocess.Popen(
                cmd,
                stdin=stdin,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                start_new_session=True,
            )
            timeout = self.timeout_seconds or None
            try:
                out, _ = proc.communicate(timeout=timeout)
                if out:
                    logf.write(out)
                    appended = len(out)
                rc = proc.returncode
            except subprocess.TimeoutExpired:
                timed_out = True
                ts = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                msg = (
                    f"[{ts}] error: codex exec timeout after {self.timeout_seconds}s; "
                    f"terminating process group pid={proc.pid}\n"
                ).encode()
                logf.write(msg)
                appended += len(msg)
                self._terminate_group(proc.pid, signal.SIGTERM)
                try:
                    out, _ = proc.communicate(timeout=10)
                    if out:
                        logf.write(out)
                        appended += len(out)
                except subprocess.TimeoutExpired:
                    ts = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                    msg = (
                        f"[{ts}] error: codex exec still running after SIGTERM; "
                        f"killing process group pid={proc.pid}\n"
                    ).encode()
                    logf.write(msg)
                    appended += len(msg)
                    self._terminate_group(proc.pid, signal.SIGKILL)
                    out, _ = proc.communicate()
                    if out:
                        logf.write(out)
                        appended += len(out)
                rc = 124

        last_msg = ""
        try:
            last_msg = capture_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
        return CodexResult(
            returncode=rc,
            timed_out=timed_out,
            last_message=last_msg,
            log_appended_bytes=appended,
        )

    @staticmethod
    def _terminate_group(pid: int, sig: int) -> None:
        try:
            os.killpg(pid, sig)
        except ProcessLookupError:
            pass
        except OSError:
            pass
