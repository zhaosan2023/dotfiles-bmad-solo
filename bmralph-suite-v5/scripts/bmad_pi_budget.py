"""Pi 实际 HTTP 调用路径的共享预算；不读取凭据、不发送请求。

调用方必须在每次向获准网关发送请求前预留，逐块计量响应正文。
计量范围是 Pi 到网关的 HTTP 请求与响应正文，不包含传输层开销，
也不证明网关内部重试次数、Token 或费用。单测不证明实际路径接入。
"""
from __future__ import annotations

import copy
import math
import threading
import time

from bmad_supervisor import SupervisorError, utc_now


MAX_REQUESTS = 30
MAX_DATA_BYTES = 15_000_000


class PiNetworkBudget:
    """整个任务期共用一份计数；超限锁定，不允许下一会话重置。"""

    def __init__(self, *, maximum_requests, maximum_bytes, deadline,
                 cancel_requested=None):
        if (type(maximum_requests) is not int
                or not 1 <= maximum_requests <= MAX_REQUESTS):
            raise SupervisorError("Pi 真实 HTTP 请求预算须为 1 至 30")
        if (type(maximum_bytes) is not int
                or not 256 <= maximum_bytes <= MAX_DATA_BYTES):
            raise SupervisorError("Pi HTTP 正文预算须为 256 至 15000000 字节")
        if (type(deadline) not in {int, float} or not math.isfinite(deadline)
                or deadline <= time.monotonic()):
            raise SupervisorError("Pi 网络预算缺少有效任务截止时间")
        if cancel_requested is not None and not callable(cancel_requested):
            raise SupervisorError("Pi 网络取消入口必须可调用")
        self.maximum_requests = maximum_requests
        self.maximum_bytes = maximum_bytes
        self.deadline = deadline
        self.cancel_requested = cancel_requested
        self.requests = 0
        self.request_bytes = 0
        self.response_bytes = 0
        self.reason = ""
        self.events = []
        self._lock = threading.Lock()

    def _block(self, reason):
        if not self.reason:
            self.reason = reason
        raise SupervisorError(self.reason)

    def _check(self):
        if self.reason:
            raise SupervisorError(self.reason)
        if self.cancel_requested is not None and self.cancel_requested():
            self._block("Pi 网络调用收到停止请求")
        if time.monotonic() >= self.deadline:
            self._block("Pi 网络调用任务截止时间耗尽")

    @staticmethod
    def _size(value):
        if type(value) is not int or value < 0:
            raise SupervisorError("HTTP 正文计量须为非负整数字节数")

    def reserve_request(self, body_bytes):
        """发送前预留一次尝试及完整请求正文；失败也不返还预算。"""
        self._size(body_bytes)
        with self._lock:
            self._check()
            if self.requests >= self.maximum_requests:
                self._block("Pi 真实 HTTP 请求次数预算耗尽")
            if self.request_bytes + self.response_bytes + body_bytes > self.maximum_bytes:
                self._block("Pi HTTP 请求正文将超过累计数据预算")
            if any(event["finished_at"] is None for event in self.events):
                self._block("存在在途 Pi HTTP 请求；拒绝并发发送")
            self.requests += 1
            self.request_bytes += body_bytes
            self.events.append({
                "request_number": self.requests,
                "started_at": utc_now(), "finished_at": None,
                "request_bytes": body_bytes, "response_bytes": 0,
                "http_status": None, "outcome": "IN_FLIGHT",
            })
            return self.requests

    def response_allowance(self):
        """限制下一次实际读取量；不得先无界读取再检查大小。"""
        with self._lock:
            self._check()
            return self.maximum_bytes - self.request_bytes - self.response_bytes

    def _event(self, request_number):
        if (type(request_number) is not int
                or not 1 <= request_number <= len(self.events)):
            self._block("Pi HTTP 响应缺少当前请求预留")
        event = self.events[request_number - 1]
        if event["finished_at"] is not None:
            self._block("Pi HTTP 请求结束后仍有响应活动")
        return event

    def accept_response(self, request_number, body_bytes):
        """逐块登记响应正文；该检查不能替代调用方的读取长度上限。"""
        self._size(body_bytes)
        with self._lock:
            self._check()
            event = self._event(request_number)
            if self.request_bytes + self.response_bytes + body_bytes > self.maximum_bytes:
                self._block("Pi HTTP 响应正文超过累计数据预算")
            self.response_bytes += body_bytes
            event["response_bytes"] += body_bytes

    def finish_request(self, request_number, *, http_status, outcome):
        """保存真实结束元数据；停止后仍允许登记清理结果，不清除阻断。"""
        if http_status is not None and (
                type(http_status) is not int or not 100 <= http_status <= 599):
            raise SupervisorError("HTTP 状态码必须来自实际响应")
        if outcome not in {"COMPLETE", "HTTP_ERROR", "NETWORK_ERROR", "CANCELLED", "BUDGET_STOP"}:
            raise SupervisorError("Pi HTTP 结束类别非法")
        with self._lock:
            event = self._event(request_number)
            event.update(http_status=http_status, outcome=outcome,
                         finished_at=utc_now())

    def snapshot(self):
        """只读调用事实，不登记任务完成、不包含任何请求或响应正文。"""
        with self._lock:
            return {
                "status": "BLOCKED" if self.reason else "READY",
                "reason": self.reason,
                "maximum_model_request_attempts": self.maximum_requests,
                "maximum_data_bytes": self.maximum_bytes,
                "model_request_attempts": self.requests,
                "request_bytes": self.request_bytes,
                "response_bytes": self.response_bytes,
                "data_bytes": self.request_bytes + self.response_bytes,
                "events": copy.deepcopy(self.events),
                "measurement": "HTTP 请求和响应正文的实际字节数",
                "upstream_gateway_retry_coverage": "UNKNOWN",
                "evidence_boundary": "仅经本预算入口的 Pi 到网关请求；不证明网关内部调用、费用或业务完成",
            }
