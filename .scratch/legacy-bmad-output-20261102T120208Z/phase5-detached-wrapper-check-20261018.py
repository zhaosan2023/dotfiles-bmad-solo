"""隔离验证实际包装前缀的终端脱离及HUP处理；不启动控制器或模型。"""
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
WRAPPER = ROOT / "_bmad-output/scratch/phase5-pi-detached-run-20261018.sh"


def main():
    result = {"status": "BLOCKED", "model_started": False, "cleanup_ok": False}
    server_started = False
    code = 1
    with tempfile.TemporaryDirectory(prefix="hup-", dir=ROOT / "_bmad-output/scratch") as temporary:
        directory = Path(temporary)
        socket = str(directory / "sock")
        env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "SHELL": "/bin/bash",
               "LANG": "C.UTF-8", "TERM": "xterm"}

        def tmux(*arguments, check=True):
            return subprocess.run(["/usr/bin/tmux", "-S", socket, "-f", "/dev/null", *arguments],
                                  cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  text=True, timeout=3, check=check)

        try:
            original = WRAPPER.read_text()
            marker = "# 控制器自身任务预算600秒"
            if original.count(marker) != 1 or "trap '' HUP" not in original.split(marker)[0]:
                raise ValueError("包装前缀缺少明确HUP防线或截取边界")
            prefix = original.split(marker)[0]
            if "bmad-loop.py start" in prefix or "--credential-file" in prefix:
                raise ValueError("隔离前缀意外包含真实启动入口")
            log = directory / "probe.log"
            exit_file = directory / "probe.exit"
            lines = prefix.splitlines()
            if sum(line.startswith("LOG=") for line in lines) != 1:
                raise ValueError("日志绑定不唯一")
            if sum(line.startswith("EXIT_RECEIPT=") for line in lines) != 1:
                raise ValueError("退出回执绑定不唯一")
            lines = ["LOG=" + shlex.quote(str(log)) if line.startswith("LOG=") else
                     "EXIT_RECEIPT=" + shlex.quote(str(exit_file)) if line.startswith("EXIT_RECEIPT=")
                     else line for line in lines]
            fixture = directory / "fixture.sh"
            fixture.write_text("\n".join(lines) + "\n"
                               "kill -HUP \"$$\"\n"
                               "printf 'SYNTHETIC_HUP_SURVIVED\\n'\n"
                               "sleep 0.2\n"
                               "printf 'SYNTHETIC_WRAPPER_COMPLETE\\n'\n"
                               "printf '0\\n' > \"$EXIT_RECEIPT\"\n"
                               "exit 0\n")
            subprocess.run(["/bin/bash", "-n", str(fixture)], cwd=ROOT, env=env,
                           stdin=subprocess.DEVNULL, capture_output=True, timeout=3, check=True)
            created = tmux("new-session", "-d", "-P", "-F", "#{pane_id}",
                           "-s", "wrapper-probe", "-c", str(ROOT),
                           "/bin/bash " + shlex.quote(str(fixture)))
            server_started = True
            pane = created.stdout.strip()
            deadline = time.monotonic() + 4
            pane_state = ""
            while time.monotonic() < deadline:
                pane_state = tmux("display-message", "-p", "-t", pane,
                                  "#{pane_dead}|#{pane_dead_status}|#{pane_dead_signal}").stdout.strip()
                if pane_state.startswith("1|"):
                    break
                time.sleep(0.05)
            if not pane_state.startswith("1|0|"):
                raise ValueError("隔离包装未正常退出：" + pane_state)
            content = log.read_text()
            if "SYNTHETIC_HUP_SURVIVED" not in content or "SYNTHETIC_WRAPPER_COMPLETE" not in content:
                raise ValueError("关闭终端描述符或HUP后缺少完整执行证据")
            if exit_file.read_text() != "0\n":
                raise ValueError("隔离包装缺少实际退出回执")
            result.update(status="PASS", pane_state=pane_state,
                          hup_survived=True, terminal_descriptors_closed=True,
                          evidence_boundary="实际包装前缀在独立tmux服务器通过；只证明终端脱离及HUP处理，不证明真实Pi或断开推进")
            code = 0
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            result.update(status="BLOCKED", reason=str(exc)[:512])
            # 清理前保留本轮实际诊断，不因临时目录删除而丢失失败证据。
            # 以下仅采集本隔离夹具；不读取真实任务日志或凭据。
            if server_started:
                try:
                    diagnostic = tmux("display-message", "-a", "-t", pane, check=False)
                    result["pane_diagnostic"] = [
                        line for line in diagnostic.stdout.splitlines()
                        if line.startswith(("pane_dead", "pane_pid=", "pane_start_command="))
                    ][:12]
                    captured = tmux("capture-pane", "-p", "-t", pane, "-S", "-20", check=False)
                    result["pane_output"] = captured.stdout[-2048:]
                except (OSError, subprocess.SubprocessError) as diagnostic_error:
                    result["diagnostic_error"] = str(diagnostic_error)[:256]
            if "log" in locals():
                result["fixture_log_exists"] = log.is_file()
                if log.is_file():
                    result["fixture_log_bytes"] = log.stat().st_size
                    with log.open("rb") as stream:
                        result["fixture_log"] = stream.read(2048).decode("utf-8", errors="replace")
            if "exit_file" in locals():
                result["fixture_exit_exists"] = exit_file.is_file()
                if exit_file.is_file():
                    with exit_file.open("rb") as stream:
                        result["fixture_exit"] = stream.read(128).decode("utf-8", errors="replace")
        finally:
            if server_started:
                try:
                    tmux("kill-server")
                    check = tmux("list-sessions", check=False)
                    if check.returncode == 0:
                        raise ValueError("隔离tmux服务器仍活动")
                    result["cleanup_ok"] = True
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    result.update(status="BLOCKED", cleanup_ok=False, reason=str(exc)[:512])
                    code = 1
            else:
                result["cleanup_ok"] = True
        print(json.dumps(result, ensure_ascii=False), flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
