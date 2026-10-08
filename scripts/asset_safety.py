"""受管部署的输入校验与文件安全原语。

不执行部署、不自动接管现有资产。调用者须先预检全部目标并持有部署锁。
原子替换只针对单文件；指纹复核不能阻止不遵守锁协议的外部写入者。
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import hashlib
import os
from pathlib import Path
import stat
import tempfile

import yaml


class AssetError(ValueError):
    """输入、所有权或部署边界不满足安全契约。"""


class UniqueLoader(yaml.SafeLoader):
    """拒绝重复键，不允许损坏配置降级为空对象。"""


def _mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in result
        except TypeError as exc:
            raise AssetError("YAML 包含非法映射键") from exc
        if duplicate:
            raise AssetError(f"YAML 重复键：{key!r}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping
)


def parse_modes(content: bytes) -> dict:
    """解析已有配置；缺失文件由调用者处理，空文件不是合法空配置。"""
    try:
        data = yaml.load(content.decode("utf-8"), Loader=UniqueLoader)
    except (UnicodeError, yaml.YAMLError) as exc:
        raise AssetError(f"模式配置解析失败：{exc}") from exc
    if not isinstance(data, dict):
        raise AssetError("模式配置顶层必须为映射")
    modes = data.get("customModes", [])
    if not isinstance(modes, list):
        raise AssetError("customModes 必须为列表")
    seen = set()
    for mode in modes:
        if not isinstance(mode, dict):
            raise AssetError("模式必须为映射")
        slug = mode.get("slug")
        if not isinstance(slug, str) or not slug.strip():
            raise AssetError("模式缺少有效 slug")
        if slug in seen:
            raise AssetError(f"重复模式标识：{slug}")
        seen.add(slug)
    return data


def checked_path(path: Path) -> Path:
    """拒绝路径及任何已有父目录的符号链接；不创建目录。"""
    path = Path(path)
    if ".." in path.parts:
        raise AssetError(f"拒绝父目录穿越：{path}")
    path = Path(os.path.abspath(path))
    for candidate in (*reversed(path.parents), path):
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode):
            raise AssetError(f"拒绝符号链接：{candidate}")
        if candidate != path and not stat.S_ISDIR(info.st_mode):
            raise AssetError(f"父路径不是目录：{candidate}")
    return path


@dataclass(frozen=True)
class Snapshot:
    content: bytes | None
    mode: int | None

    @property
    def digest(self) -> str | None:
        if self.content is None:
            return None
        return hashlib.sha256(self.content).hexdigest()


def snapshot(path: Path) -> Snapshot:
    path = checked_path(path)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return Snapshot(None, None)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise AssetError(f"目标不是普通文件：{path}")
        if info.st_nlink != 1:
            raise AssetError(f"拒绝多硬链接文件：{path}")
        content = stream.read()
        after = os.fstat(stream.fileno())
        if (info.st_size, info.st_mtime_ns, info.st_ctime_ns) != (
            after.st_size, after.st_mtime_ns, after.st_ctime_ns
        ):
            raise AssetError(f"读取期间文件发生变化：{path}")
        return Snapshot(content, stat.S_IMODE(info.st_mode))


def require_unchanged(path: Path, expected: Snapshot) -> None:
    if snapshot(path) != expected:
        raise AssetError(f"文件已被外部修改，拒绝覆盖：{path}")


def check_writable_parent(path: Path) -> None:
    """非写入式权限预检；真实写入错误仍须由事务调用者处理。"""
    path = checked_path(path)
    parent = path.parent
    while not parent.exists():
        parent = parent.parent
    info = parent.stat()
    if not stat.S_ISDIR(info.st_mode):
        raise AssetError(f"目标父路径不是目录：{parent}")
    if not info.st_mode & 0o222 or not os.access(parent, os.W_OK | os.X_OK):
        raise AssetError(f"目标父目录不可写：{parent}")


def atomic_replace(
    path: Path, content: bytes, expected: Snapshot, *, mode: int | None = None
) -> None:
    """同目录原子替换；调用者准备父目录，可显式指定目标普通权限。

    默认保留已有权限，新文件默认 0600。替换后的目录同步仍可能失败，
    调用者必须检查实际目标状态后恢复，不能假设异常代表目标未改变。
    """
    if not isinstance(content, bytes):
        raise AssetError("替换内容必须为字节")
    target_mode = mode if mode is not None else (
        expected.mode if expected.mode is not None else 0o600
    )
    if type(target_mode) is not int or not 0 <= target_mode <= 0o777:
        raise AssetError("拒绝非法权限或特殊权限位")
    path = checked_path(path)
    require_unchanged(path, expected)
    fd, temporary = tempfile.mkstemp(prefix=".bmad-write-", dir=path.parent)
    temporary = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fchmod(stream.fileno(), target_mode)
            os.fsync(stream.fileno())
        checked_path(path)
        require_unchanged(path, expected)
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def deployment_lock(path: Path):
    """非阻塞单写者锁；锁文件永久保留，避免删除后形成不同锁 inode。"""
    path = checked_path(path)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise AssetError(f"锁路径不是独占普通文件：{path}")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise AssetError("另一部署进程持有锁；本次未获得写入权限") from exc
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
