"""测试专用内核共享锁夹具；不依赖退役运行时，不提供任务调度。"""
from contextlib import contextmanager
import fcntl
import os


class SharedLockError(RuntimeError):
    pass


@contextmanager
def suite_lease(root):
    path = root / ".bmad-solo-deployment/deployment.lock"
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise SharedLockError("部署正在进行") from exc
        yield descriptor
    finally:
        os.close(descriptor)
