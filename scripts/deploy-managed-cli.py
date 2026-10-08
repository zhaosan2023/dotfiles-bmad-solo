#!/usr/bin/env python3
"""受管部署命令入口；路径通过参数传入，不在代码中插值执行。

目标发现与版本选择由外层入口负责。本命令仅报告文件分发状态，
不会把文件写入成功描述为 Roo 已加载或权限验收通过。
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from asset_safety import AssetError, checked_path
from deploy_managed import deploy
from deployment_source import collect_source, verify_source
from deployment_provenance import MANIFEST_TARGET, build_manifest
from managed_files import validate_relative_path


def parser():
    result = argparse.ArgumentParser(description="安全分发或卸载受管 BMAD 资产")
    result.add_argument("--root", required=True, type=Path,
                        help="已存在的部署根目录；隔离测试须指定项目内目录")
    result.add_argument("--source", type=Path, help="物理套件源目录")
    result.add_argument("--repository", type=Path,
                        help="实际来源仓库根目录；未提供时明确记录为未版本化来源")
    result.add_argument("--mode-target", action="append", default=[],
                        help="相对于部署根目录的模式配置文件，可重复")
    result.add_argument("--adopt-file", action="append", default=[],
                        help="明确授权首次接管的相对文件路径，可重复")
    result.add_argument("--adopt-mode", action="append", default=[],
                        help="明确授权首次接管，格式为目标相对路径=模式标识")
    result.add_argument("--dry-run", action="store_true")
    result.add_argument("--uninstall", action="store_true")
    return result


def main(argv=None):
    arguments = parser().parse_args(argv)
    try:
        root = checked_path(arguments.root)
        if not root.is_dir():
            raise AssetError("部署根目录必须已经存在")
        # 固定状态位置，避免通过切换状态目录绕过同一根目录的部署锁。
        state = root / ".bmad-solo-deployment"
        if arguments.uninstall:
            if (arguments.source is not None or arguments.repository is not None
                    or arguments.mode_target or arguments.adopt_file or arguments.adopt_mode):
                raise AssetError("卸载不能同时指定套件源、模式目标或接管授权")
            files, modes = {}, {}
            adopt_modes = {}
        else:
            if arguments.source is None:
                raise AssetError("部署必须显式指定套件源")
            source = checked_path(arguments.source)
            files, modes, sources = collect_source(
                source, tuple(arguments.mode_target)
            )
            adopt_modes = {}
            for specification in arguments.adopt_mode:
                relative, separator, slug = specification.rpartition("=")
                if not separator or not slug.strip():
                    raise AssetError("模式接管授权格式必须为目标相对路径=模式标识")
                validate_relative_path(relative)
                if relative not in modes:
                    raise AssetError(f"接管授权指向未选中的模式目标：{relative}")
                adopt_modes.setdefault(relative, set()).add(slug)
            # 来源清单是受管文件，必须参与全目标预检、所有权和事务恢复。
            # 禁止与模式目标重叠，不在部署成功后另行写入。
            if MANIFEST_TARGET in files or MANIFEST_TARGET in modes:
                raise AssetError("部署来源清单与输入目标冲突")
            files[MANIFEST_TARGET] = build_manifest(
                source, sources, files, modes, repository=arguments.repository,
            )
            # 禁止部署目标或状态目录覆盖源目录；部署根目录可以包含仓库。
            for relative in (*files, *modes, ".bmad-solo-deployment"):
                target = checked_path(root / relative)
                if (target == source or target.is_relative_to(source)
                        or source.is_relative_to(target)):
                    raise AssetError(f"部署目标与套件源重叠：{relative}")
            verify_source(source, sources)

        outcome = deploy(
            root, state, files, modes,
            dry_run=arguments.dry_run,
            uninstall=arguments.uninstall,
            adopt_files=set(arguments.adopt_file),
            adopt_modes=adopt_modes,
        )
        if arguments.dry_run:
            changed = [item for item in outcome if item.before != item.after]
            print(f"模拟预检通过：拟变更 {len(changed)} 个文件；未执行写入。")
            for item in changed:
                action = "删除" if item.after.content is None else "写入"
                print(f"  {action}：{item.path.relative_to(root)}")
        elif arguments.uninstall:
            print("受管卸载处理完成；未知资产保留，未验证运行时卸载状态。")
        elif outcome is None:
            print("受管资产无需变更；未验证 Roo 运行时加载状态。")
        else:
            print(f"受管文件分发完成；提交记录：{outcome}")
            print("未验证 Roo 运行时加载状态或权限行为。")
        if not arguments.uninstall and not modes:
            print("未选中模式配置目标：仅处理文件资产，不能视为完整激活。")
        return 0
    except (AssetError, OSError) as exc:
        print(f"部署未完成：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
