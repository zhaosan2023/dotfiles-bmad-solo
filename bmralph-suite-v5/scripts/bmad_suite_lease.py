"""已部署套件的协作式只读租约；供任务期运行调用方持有。

使用部署入口已经创建的固定锁文件，不创建部署状态、不启动任务。
租约与受管部署的排他锁互斥，但不核验套件来源，也不替代工作区
单写入者或在途进程监督。调用方必须先核验来源，并在所有 Agent
及验证子进程确认结束后才释放租约。目前尚未接入任务期循环。
同账号删除锁文件、不遵守协议的写入或持锁进程崩溃不在保证范围。
"""
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import stat

from bmad_supervisor import SupervisorError, contained_path, workspace_path


LOCK_FILE = ".bmad-solo-deployment/deployment.lock"


def lock_identity(info):
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise SupervisorError("部署租约锁必须是单硬链接普通文件")
    return info.st_dev, info.st_ino


def require_same_lock(root, descriptor):
    path = contained_path(root, LOCK_FILE)
    current = path.lstat()
    held = os.fstat(descriptor)
    # 原子替换后旧描述符可能已无目录链接；先比较身份，避免类型校验
    # 抢先覆盖锁替换诊断。身份相同时仍严格检查类型与硬链接数。
    if (current.st_dev, current.st_ino) != (held.st_dev, held.st_ino):
        raise SupervisorError("部署锁身份发生变化；停止对账，不替换锁文件")
    lock_identity(current)
    lock_identity(held)


@contextmanager
def suite_lease(deployment_root: Path):
    """持有现有部署锁的共享租约；排他部署在此期间不能获得写权限。

    多个任务可读取同一部署套件；工作区单写入者须由运行调用方另管。
    缺失锁不视为安全的新安装，不创建或补造锁，不接受软链接、FIFO
    或多硬链接。进入与退出边界复核锁身份；退出复核不是业务重测。
    """
    root = workspace_path(deployment_root)
    path = contained_path(root, LOCK_FILE)
    # 先拒绝特殊文件，再以非阻塞、不跟随链接方式打开；打开后再次复核。
    lock_identity(path.lstat())
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        lock_identity(os.fstat(descriptor))
        try:
            fcntl.flock(descriptor, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise SupervisorError("部署正在进行；任务未获得套件读取租约") from exc
        require_same_lock(root, descriptor)
        try:
            yield
        except BaseException:
            # 保留调用方的原始失败，不以退出检查覆盖业务异常。
            raise
        else:
            require_same_lock(root, descriptor)
    finally:
        # 不删除锁文件；关闭本描述符释放租约，不对其他进程发送信号。
        os.close(descriptor)
