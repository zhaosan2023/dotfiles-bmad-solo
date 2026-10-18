"""任务期 Pi 流式转发：实际网关请求共用预算，不修改既有网关。

仅监听临时回环端口；每个 Pi 会话结束后同步关闭和等待线程退出。
真实凭据仅保存在父进程内存，Pi 使用临时内部令牌。计量仅覆盖
此路径到固定网关的 HTTP 正文，不覆盖工具旁路或网关内部重试。
"""
from __future__ import annotations

import hmac
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import math
import re
import secrets
import socket
import threading
import time

from bmad_pi_budget import PiNetworkBudget
from bmad_supervisor import SupervisorError


GATEWAY_HOST = "127.0.0.1"
GATEWAY_PORT = 8080
REQUEST_PATH = "/v1/chat/completions"
CHUNK_BYTES = 8192
DONE = re.compile(rb"(?:^|\n)data: ?\[DONE\]\r?\n\r?\n")


class PiTransport:
    """一次会话的受管转发；跨会话计数必须复用调用方的同一预算。"""

    def __init__(self, *, budget, credential, model, session_deadline):
        if not isinstance(budget, PiNetworkBudget):
            raise SupervisorError("Pi 转发必须使用任务期共享网络预算")
        if (not isinstance(credential, str) or not credential
                or not credential.isascii()
                or any(ord(char) < 33 or ord(char) > 126 for char in credential)):
            raise SupervisorError("Pi 转发缺少有效的独立凭据；不回显内容")
        if not isinstance(model, str) or not model or len(model) > 256:
            raise SupervisorError("Pi 转发必须绑定明确模型")
        if (type(session_deadline) not in {int, float}
                or not math.isfinite(session_deadline)
                or not time.monotonic() < session_deadline <= budget.deadline):
            raise SupervisorError("Pi 转发会话截止不得超过任务截止")
        self.budget = budget
        self.model = model
        self.session_deadline = session_deadline
        self.token = secrets.token_hex(32)
        self._credential = credential
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._server = None
        self._thread = None
        self._client = None
        self._upstream = None
        self._error = ""
        self.cleanup_ok = False

    def _fail(self, reason):
        with self._lock:
            if not self._error:
                self._error = reason

    def _remaining(self):
        if self._stop.is_set():
            raise SupervisorError("Pi 转发已停止")
        self.budget.response_allowance()
        remaining = self.session_deadline - time.monotonic()
        if remaining <= 0:
            raise SupervisorError("Pi 转发会话截止时间耗尽")
        return remaining

    @property
    def base_url(self):
        if self._server is None or self._thread is None or not self._thread.is_alive():
            raise SupervisorError("Pi 转发尚未启动或已退出")
        return "http://127.0.0.1:" + str(self._server.server_port) + "/v1"

    def __enter__(self):
        if self._server is not None:
            raise SupervisorError("Pi 转发实例不得重复启动或重置预算")
        self._remaining()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"
            server_version = "bmad-task-transport"
            sys_version = ""

            def log_message(self, format, *args):
                # HTTP 路径、请求头、凭据及提供方诊断都不进入日志。
                pass

            def _reply(self, status):
                body = b"BMAD_PI_TRANSPORT_BLOCKED\n"
                self.close_connection = True
                self.send_response(status)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(body)
                self.wfile.flush()

            def do_GET(self):
                owner._fail("Pi 转发拒绝非模型请求")
                self._reply(405)

            do_HEAD = do_GET
            do_PUT = do_GET
            do_DELETE = do_GET
            do_PATCH = do_GET
            do_OPTIONS = do_GET

            def do_POST(self):
                number = None
                upstream = None
                status = None
                outcome = "NETWORK_ERROR"
                headers_sent = False
                self.close_connection = True
                with owner._lock:
                    owner._client = self.connection
                try:
                    self.connection.settimeout(owner._remaining())
                    if self.path != REQUEST_PATH or self.headers.get("Transfer-Encoding") is not None:
                        raise SupervisorError("Pi 转发仅接受固定模型路径及定长正文")
                    authorizations = self.headers.get_all("Authorization", [])
                    if (len(authorizations) != 1
                            or not hmac.compare_digest(
                                authorizations[0], "Bearer " + owner.token)):
                        raise SupervisorError("Pi 转发内部认证失败")
                    lengths = self.headers.get_all("Content-Length", [])
                    if (len(lengths) != 1
                            or re.fullmatch(r"[1-9][0-9]{0,7}", lengths[0]) is None):
                        raise SupervisorError("Pi 转发必须提供唯一有界正文长度")
                    size = int(lengths[0])
                    if size > owner.budget.response_allowance():
                        outcome = "BUDGET_STOP"
                        raise SupervisorError("Pi 请求正文将超过任务数据预算")
                    raw = self.rfile.read(size)
                    if len(raw) != size:
                        raise SupervisorError("Pi 请求正文不完整")
                    request = json.loads(raw)
                    if (not isinstance(request, dict)
                            or request.get("model") != owner.model
                            or request.get("stream") is not True):
                        raise SupervisorError("Pi 请求必须使用绑定模型及流式模式")
                    with owner._lock:
                        if owner._error:
                            raise SupervisorError("Pi 转发此前已失败；不再发送请求")
                    # 每次真实发送前收费；失败不返还，内部重试也走此路径。
                    number = owner.budget.reserve_request(len(raw))
                    upstream = http.client.HTTPConnection(
                        GATEWAY_HOST, GATEWAY_PORT, timeout=owner._remaining())
                    with owner._lock:
                        owner._upstream = upstream
                    upstream.request("POST", REQUEST_PATH, body=raw, headers={
                        "Authorization": "Bearer " + owner._credential,
                        "Content-Type": "application/json",
                        "Accept": "text/event-stream",
                        "Connection": "close",
                    })
                    response = upstream.getresponse()
                    status = response.status
                    if status != 200:
                        outcome = "HTTP_ERROR"
                        owner._fail("Pi 网关返回非成功状态；不重试")
                        self._reply(status if 400 <= status <= 599 else 502)
                        return
                    content_type = response.getheader("Content-Type", "").split(";", 1)[0].strip().lower()
                    if content_type != "text/event-stream":
                        raise SupervisorError("Pi 网关未返回流式响应")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Connection", "close")
                    self.end_headers()
                    headers_sent = True
                    tail = b""
                    while True:
                        timeout = owner._remaining()
                        allowance = owner.budget.response_allowance()
                        if allowance == 0:
                            outcome = "BUDGET_STOP"
                            raise SupervisorError("Pi 响应正文预算耗尽；停止读取")
                        if upstream.sock is not None:
                            upstream.sock.settimeout(timeout)
                        # 不先无界读取再计量；每块不超过剩余授权预算。
                        chunk = response.read1(min(CHUNK_BYTES, allowance))
                        if not chunk:
                            raise SupervisorError("Pi 网关流式响应提前结束，缺少 DONE")
                        owner.budget.accept_response(number, len(chunk))
                        self.wfile.write(chunk)
                        self.wfile.flush()
                        scan = tail + chunk
                        if DONE.search(scan) is not None:
                            outcome = "COMPLETE"
                            break
                        tail = scan[-256:]
                except SupervisorError:
                    owner._fail("Pi 转发前提、协议、取消或预算门禁失败")
                    if outcome != "BUDGET_STOP":
                        outcome = "BUDGET_STOP" if owner._stop.is_set() else "NETWORK_ERROR"
                    if not headers_sent:
                        try:
                            self._reply(502)
                        except OSError:
                            pass
                except (OSError, http.client.HTTPException, ValueError, TypeError):
                    owner._fail("Pi 实际 HTTP 转发失败；不输出请求或响应正文")
                    if not headers_sent:
                        try:
                            self._reply(502)
                        except OSError:
                            pass
                finally:
                    if upstream is not None:
                        upstream.close()
                    if number is not None:
                        try:
                            owner.budget.finish_request(
                                number, http_status=status, outcome=outcome)
                        except SupervisorError:
                            owner._fail("Pi HTTP 请求结束证据登记失败")
                    with owner._lock:
                        owner._client = None
                        owner._upstream = None

        self._server = HTTPServer(("127.0.0.1", 0), Handler)
        self._server.timeout = 0.1
        self._thread = threading.Thread(
            target=self._serve, name="bmad-pi-task-transport", daemon=False)
        try:
            self._thread.start()
        except BaseException:
            self._server.server_close()
            self.cleanup_ok = True
            raise
        return self

    def _serve(self):
        try:
            while not self._stop.is_set():
                self._server.handle_request()
        except (OSError, ValueError):
            if not self._stop.is_set():
                self._fail("Pi 转发线程异常退出")

    def snapshot(self):
        with self._lock:
            error = self._error
        return {
            "status": "BLOCKED" if error else "READY",
            "reason": error,
            "network_budget": self.budget.snapshot(),
            "cleanup_ok": self.cleanup_ok,
            "thread_active": self._thread is not None and self._thread.is_alive(),
            "gateway": "http://127.0.0.1:8080/v1",
            "evidence_boundary": "仅经此任务期转发的实际 HTTP 请求；不证明工具旁路、网关内部重试、模型费用或业务完成",
        }

    @staticmethod
    def _close_socket(connection):
        if connection is None:
            return
        try:
            connection.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            connection.close()
        except OSError:
            pass

    def __exit__(self, exc_type, exc, traceback):
        self._stop.set()
        with self._lock:
            client = self._client
            upstream = self._upstream
        self._close_socket(client)
        if upstream is not None:
            self._close_socket(upstream.sock)
        self._server.server_close()
        self._thread.join(timeout=2.0)
        self.cleanup_ok = not self._thread.is_alive()
        self._credential = ""
        self.token = ""
        if not self.cleanup_ok:
            self._fail("Pi 转发线程清理未知；禁止下一次调用")
            raise SupervisorError("Pi 转发线程未确认退出；保留成果并阻塞")
        return False
