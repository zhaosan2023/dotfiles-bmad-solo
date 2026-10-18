"""任务启动时显式加载私有凭据；不执行 Shell、不访问全局认证文件。

本模块只提供进程内临时环境，不启动模型、不打印或返回秘密正文。
私有目录必须为当前账号所有的 0700 目录，凭据为单链接 0600 文件。
"""
from contextlib import contextmanager
import os
from pathlib import Path
import re
import stat

from bmad_supervisor import SupervisorError, workspace_path


PRIVATE_DIRECTORY = ".bmad-private"
CREDENTIAL_NAME = "BMAD_PI_API_KEY"
MAX_CREDENTIAL_BYTES = 8192
_LITERAL = re.compile(r"[A-Za-z0-9._~+/:=@%!-]+\Z")


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _validate_directory(info):
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) != 0o700):
        raise SupervisorError("私有配置目录须为当前账号所有的 0700 普通目录")


def _validate_file(info):
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1
            or not 0 < info.st_size <= MAX_CREDENTIAL_BYTES):
        raise SupervisorError("私有凭据须为当前账号所有的单链接 0600 有界普通文件")


def _parse(payload):
    """仅接受一个字面量赋值；不支持 source、export、插值或命令替换。"""
    try:
        text = payload.decode("ascii")
    except UnicodeError:
        raise SupervisorError("私有凭据格式非法；不回显正文") from None
    value = None
    for line in text.split("\n"):
        line = line.strip(" \t\r")
        if not line or line.startswith("#"):
            continue
        name, separator, candidate = line.partition("=")
        if name != CREDENTIAL_NAME or separator != "=" or value is not None:
            raise SupervisorError("私有凭据只允许一个指定变量；未知或重复字段阻断")
        if candidate.startswith(("\"", "'")):
            quote = candidate[0]
            if len(candidate) < 2 or candidate[-1] != quote:
                raise SupervisorError("私有凭据引号不完整；不回显正文")
            candidate = candidate[1:-1]
        if not candidate or _LITERAL.fullmatch(candidate) is None:
            raise SupervisorError("私有凭据须为非空字面量；禁止 Shell 语法及插值")
        value = candidate
    if value is None:
        raise SupervisorError("私有凭据缺少指定变量；不回显正文")
    return value


def _read_credential(workspace, relative):
    if not isinstance(relative, str):
        raise SupervisorError("须显式指定工作区私有凭据相对路径")
    parts = relative.split("/")
    if (len(parts) != 2 or parts[0] != PRIVATE_DIRECTORY
            or parts[1] in {"", ".", ".."} or "\x00" in relative
            or "\\" in relative):
        raise SupervisorError("凭据仅允许位于工作区私有目录的直接子文件")
    root = workspace_path(Path(workspace))
    root_fd = directory_fd = file_fd = None
    try:
        root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        directory_fd = os.open(PRIVATE_DIRECTORY,
                               os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                               dir_fd=root_fd)
        directory_before = os.fstat(directory_fd)
        _validate_directory(directory_before)
        file_fd = os.open(parts[1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                          dir_fd=directory_fd)
        before = os.fstat(file_fd)
        _validate_file(before)
        payload = bytearray()
        while len(payload) <= MAX_CREDENTIAL_BYTES:
            chunk = os.read(file_fd, MAX_CREDENTIAL_BYTES + 1 - len(payload))
            if not chunk:
                break
            payload.extend(chunk)
        after = os.fstat(file_fd)
        named_file = os.stat(parts[1], dir_fd=directory_fd, follow_symlinks=False)
        named_directory = os.stat(PRIVATE_DIRECTORY, dir_fd=root_fd,
                                  follow_symlinks=False)
        _validate_directory(named_directory)
        _validate_file(named_file)
        if (len(payload) > MAX_CREDENTIAL_BYTES or len(payload) != before.st_size
                or _identity(before) != _identity(after)
                or _identity(before) != _identity(named_file)
                or _identity(directory_before) != _identity(named_directory)):
            raise SupervisorError("私有配置读取期间发生变化或超预算；阻断启动")
        return _parse(bytes(payload))
    except OSError:
        raise SupervisorError("私有凭据不可用；拒绝缺失、符号链接或无权访问的配置") from None
    finally:
        for descriptor in (file_fd, directory_fd, root_fd):
            if descriptor is not None:
                os.close(descriptor)


@contextmanager
def credential_environment(workspace, relative=None):
    """仅在明确启动范围内注入一个变量，正常或异常退出均恢复原环境。

    此接口面向现有串行任务入口；不宣称线程隔离或操作系统秘密隔离。
    未提供路径时不探测私有目录，保持原有环境变量接口。
    """
    if relative is None:
        yield
        return
    value = _read_credential(workspace, relative)
    existed = CREDENTIAL_NAME in os.environ
    previous = os.environ.get(CREDENTIAL_NAME)
    try:
        os.environ[CREDENTIAL_NAME] = value
        yield
    finally:
        if existed:
            os.environ[CREDENTIAL_NAME] = previous
        else:
            os.environ.pop(CREDENTIAL_NAME, None)
