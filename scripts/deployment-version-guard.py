#!/usr/bin/env python3
"""已有部署的版本操作守卫；跨 Bash 新版移交持续持有固定排他锁。

只执行指定来源仓库的 bs.sh，不创建部署目录或补造缺失锁。通过
exec 替换自身，避免额外后台监督进程；外层调用者负责进程级超时。
描述符编号不是持锁证据，继承检查必须核验 Linux 内核锁记录。
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import stat
import sys

from asset_safety import (
    AssetError, checked_path, deployment_lock,
    validate_inherited_deployment_lock,
)


LOCK_RELATIVE = ".bmad-solo-deployment/deployment.lock"
LOCK_ENVIRONMENT = "BMAD_VERSION_LOCK_FD"


def existing_lock(root: Path) -> Path:
    root = checked_path(root)
    if not root.is_dir():
        raise AssetError("版本操作的部署根目录必须已经存在")
    path = checked_path(root / LOCK_RELATIVE)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise AssetError("版本操作锁必须是现有单硬链接普通文件")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="核验或持有已有部署锁，再进入固定版本操作入口",
    )
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--repository", type=Path)
    parser.add_argument("--check-fd", type=int)
    parser.add_argument("entry_arguments", nargs=argparse.REMAINDER)
    arguments = parser.parse_args(argv)
    try:
        lock = existing_lock(arguments.root)
        if arguments.check_fd is not None:
            if arguments.repository is not None or arguments.entry_arguments:
                raise AssetError("继承锁只读核验不能同时请求执行入口")
            validate_inherited_deployment_lock(lock, arguments.check_fd)
            return 0
        if arguments.repository is None:
            raise AssetError("版本操作必须明确提供实际来源仓库根目录")
        repository = checked_path(arguments.repository)
        if not repository.is_dir():
            raise AssetError("来源仓库根目录必须已经存在")
        entry = checked_path(repository / "bs.sh")
        info = entry.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise AssetError("版本操作入口必须是单硬链接普通文件")
        entry_arguments = arguments.entry_arguments
        if not entry_arguments or entry_arguments[0] != "--":
            raise AssetError("版本操作必须用独立分隔符明确传递原始参数")
        entry_arguments = entry_arguments[1:]
        if not entry_arguments:
            raise AssetError("版本操作参数不能为空")
        # 先核验现有文件，再取得排他锁；获取后的内核核验拒绝身份替换。
        # 不允许缺失锁通过 deployment_lock 的常规首次创建分支恢复。
        with deployment_lock(lock, create=False) as descriptor:
            validate_inherited_deployment_lock(lock, descriptor)
            os.set_inheritable(descriptor, True)
            environment = dict(os.environ)
            environment[LOCK_ENVIRONMENT] = str(descriptor)
            # 固定调用仓库入口，不接收任意命令或 Shell 代码。
            # exec 后同一描述符跨新版移交保留；最终部署仅借用，不解锁。
            os.execvpe(
                "bash", ["bash", str(entry), *entry_arguments], environment,
            )
        raise AssetError("版本操作入口未实际替换守卫进程")
    except (AssetError, OSError, ValueError) as exc:
        print(f"版本操作阻塞：{exc}；未获得版本操作权限。", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
