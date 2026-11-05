#!/usr/bin/env python3
"""构建冻结的 Windows Cline-only 载荷；不安装、不联网、不发布。

运行校验来自当前仓库，不执行候选来源中的脚本。保留原始套件，
适配后的正文仍须满足原有技能闭包；使用者无需 Python。
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import posixpath
import re
import stat
import subprocess
import zipfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "zhaosan2023/dotfiles-bmad-solo"
HOST_VERSION = "4.1.26"
ROUTER = "cline/templates/bmad-router.md"
CONSTITUTION = "rules/bmad-constitution.md"
INSTALL_ONLY = "skills/bmad/scripts/validate-solo-package.py"
NAMES = {"bmad": "bmad-solo", "ana-solo": "ana-solo"}
LINKS = re.compile(r"\[[^\]\n]*\]\(([^)\n]+)\)")


class PackageError(ValueError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_name(name):
    if not isinstance(name, str) or not name or name.startswith("/"):
        raise PackageError(f"非法包路径：{name!r}")
    for part in name.split("/"):
        if (part in {"", ".", ".."} or part.endswith((".", " "))
                or re.search(r'[\\:<>"|?*\x00-\x1f]', part)
                or re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", part)):
            raise PackageError(f"非法 Windows 包路径：{name!r}")
    return name


def physical(path):
    path = Path(os.path.abspath(path))
    for component in (*reversed(path.parents), path):
        info = component.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise PackageError(f"来源包含链接或重解析点：{component}")
    return path


def snapshot_source(source):
    source = physical(source)
    assets = {}
    seen = set()
    for directory, dirs, files in os.walk(source, followlinks=False):
        for name in sorted(dirs + files):
            path = physical(Path(directory) / name)
            info = path.stat()
            if stat.S_ISDIR(info.st_mode):
                continue
            relative = safe_name(path.relative_to(source).as_posix())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise PackageError(f"来源不是单硬链接普通文件：{path}")
            if relative.casefold() in seen:
                raise PackageError(f"来源存在 Windows 路径碰撞：{relative}")
            seen.add(relative.casefold())
            assets[relative] = path.read_bytes()
    return assets


def validator():
    path = physical(ROOT / INSTALL_ONLY.replace("skills/", "bmad-suite-v4/skills/", 1))
    spec = importlib.util.spec_from_file_location("win10_trusted_skill_validator", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(*args):
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0")
    result = subprocess.run(["git", "--no-pager", "-C", str(ROOT), *args],
                            stdin=subprocess.DEVNULL, capture_output=True, timeout=15, env=env)
    if result.returncode:
        raise PackageError("Git 来源核验失败：" + result.stderr.decode("utf-8", errors="replace"))
    return result.stdout


def validate_skills(source, assets):
    module = validator()
    try:
        return module.validate_assets(source / "skills", {
            name[7:]: data for name, data in assets.items() if name.startswith("skills/")
        })
    except (module.PackageError, UnicodeError, yaml.YAMLError) as exc:
        raise PackageError(str(exc)) from exc


def replace_required(text, old, new):
    if text.count(old) != 1:
        raise PackageError(f"平台适配锚点发生变化，需重检：{old}")
    return text.replace(old, new)


def adapt_text(name, text):
    text = re.sub(r"\]\((\.\./bmad/[^)\s]+)\)",
                  lambda m: "](../bmad-solo/" + m[1][8:] + ")", text)
    if name == "skills/bmad/SKILL.md":
        text = replace_required(text, "`timeout 15s git --no-pager status --short < /dev/null`",
                                "经当前平台进程级 15 秒限时并封闭输入的 `git --no-pager status --short`")
        text = replace_required(text, "- **输入封闭**：附加 `< /dev/null`，仅选用当前命令实际支持的非交互参数。",
                                "- **输入封闭**：使用当前平台的标准输入关闭能力，Windows 不使用 `/dev/null`；仅选用命令支持的非交互参数。")
    return text



def adapt_constitution(text):
    start = text.index("## 8.5 ")
    end = text.index("## 9. 停止条件", start)
    return text[:start] + """## 8.5 Windows 终端执行纪律

仅在获准工程阶段执行命令。分析不使用终端；规则不是程序门禁。

1. 串行、前台同步：等待真实退出，不遗留后台进程。
2. 进程级限时：探测 15 秒、验证 30 秒、构建 600 秒；Windows 不假设存在 GNU timeout。
3. 标准输入关闭：使用 ProcessStartInfo.RedirectStandardInput 并关闭输入流，不使用 `/dev/null`。
4. 超时结束进程并确认清理；无法确认子进程结束时阻塞，不把等待期限当成通过。
5. 文件读写用宿主原生工具；不通过终端拼接多行代码改文件。

PowerShell 命令包装器需由当前项目提供并核验。安装方法论不安装目标项目工具；
参考材料中的 POSIX 命令只适用于其原环境，不在 Windows 原样执行。
没有实际可用的限时、非交互入口时停止相关执行，不能忽略约束或隐式安装依赖。

""" + text[end:]


def make_payload(source, sources):
    declaration = sources.get("VERSION", b"").decode("ascii")
    if not re.fullmatch(r"v4\.(?:[3-9]|[1-9][0-9]+)\n", declaration):
        raise PackageError("Windows 载荷需要有效 v4.3 或更新 VERSION")
    validate_skills(source, sources)
    files = {}
    for name, data in sorted(sources.items()):
        if not name.startswith("skills/") or name == INSTALL_ONLY:
            continue
        _, directory, resource = name.split("/", 2)
        if directory not in NAMES:
            raise PackageError(f"未支持的技能目录：{directory}")
        target = f"skills/{NAMES[directory]}/{resource}"
        files[safe_name(target)] = adapt_text(name, data.decode("utf-8")).encode("utf-8") if name.endswith(".md") else data
    if ROUTER not in sources or CONSTITUTION not in sources:
        raise PackageError("缺少路由或公共纪律")
    router = sources[ROUTER].decode("utf-8")

    def link(match):
        relative = match[1][len("bmad-suite-v4/"):]
        physical_name = re.sub(r":\d+$", "", relative.split("#", 1)[0])
        if physical_name not in sources:
            raise PackageError(f"路由来源引用缺失：{relative}")
        suffix = relative[len(physical_name):]
        if physical_name.startswith("skills/"):
            _, directory, resource = physical_name.split("/", 2)
            if directory not in NAMES or physical_name == INSTALL_ONLY:
                raise PackageError("路由引用未分发技能")
            target = f"../skills/{NAMES[directory]}/{resource}"
        elif physical_name == CONSTITUTION:
            target = "../bmad-solo/resources/bmad-constitution.md"
        else:
            raise PackageError(f"路由引用未分发资源：{relative}")
        return "](" + target + suffix + ")"

    router = re.sub(r"\]\((bmad-suite-v4/[^)\s]+)\)", link, router)
    files["rules/bmad-router.md"] = router.encode("utf-8")
    files["bmad-solo/resources/bmad-constitution.md"] = adapt_constitution(sources[CONSTITUTION].decode("utf-8")).encode("utf-8")
    validate_payload(files)
    return declaration.strip(), files


def validate_payload(files):
    seen = set()
    for name, data in files.items():
        safe_name(name)
        if name.casefold() in seen:
            raise PackageError(f"包路径碰撞：{name}")
        seen.add(name.casefold())
        if not isinstance(data, bytes) or not data:
            raise PackageError(f"资源为空：{name}")
    for directory in NAMES.values():
        name = f"skills/{directory}/SKILL.md"
        lines = files[name].decode("utf-8").splitlines()
        header = yaml.safe_load("\n".join(lines[1:lines.index("---", 1)]))
        if header.get("name") != directory or not isinstance(header.get("description"), str) or len(header["description"]) > 1024:
            raise PackageError(f"宿主技能身份无效：{name}")
    count = 0
    for name, data in files.items():
        if not name.endswith(".md"):
            continue
        for destination in LINKS.findall(data.decode("utf-8")):
            if destination.startswith(("https://", "http://", "#")):
                continue
            # 路由的项目导航属于目标工作区，不属于全局载荷。
            if name == "rules/bmad-router.md" and not destination.startswith("../"):
                continue
            located = re.fullmatch(r"(.*?)(?::(\d+))?(?:#.*)?", destination)
            target = posixpath.normpath(posixpath.join(posixpath.dirname(name), located[1]))
            if target not in files:
                raise PackageError(f"适配引用缺失或越界：{name} -> {destination}")
            if located[2] and not 1 <= int(located[2]) <= len(files[target].decode("utf-8").splitlines()):
                raise PackageError(f"引用行号无效：{destination}")
            count += 1
    if not count:
        raise PackageError("适配资源零引用")
    return count


def build(output, *, development=False):
    """开发包明示工作树来源，发布包须核对已提交来源；禁止混装。"""
    source = physical(ROOT / "bmad-suite-v4")
    sources = snapshot_source(source)
    version, files = make_payload(source, sources)
    commit = git("rev-parse", "HEAD").decode("ascii").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise PackageError("来源提交身份无效")
    template_path = physical(ROOT / "install-win10.ps1")
    template = template_path.read_text(encoding="utf-8-sig")
    if template.count("@@WIN10_RELEASE_BINDING@@") != 1:
        raise PackageError("旧冻结 ZIP 构建入口不适用于菜单安装脚本；请直接运行 install-win10.ps1 并选择菜单操作。未生成安装包。")
    if not development:
        tracked = git("ls-tree", "-r", "--name-only", "HEAD", "--", "bmad-suite-v4").decode("utf-8").splitlines()
        if {name.removeprefix("bmad-suite-v4/") for name in tracked} != set(sources):
            raise PackageError("发布来源集合与提交不同")
        for name, data in sources.items():
            if git("show", "HEAD:bmad-suite-v4/" + name) != data:
                raise PackageError(f"发布来源未提交或被修改：{name}")
        if git("show", "HEAD:install-win10.ps1").decode("utf-8-sig") != template:
            raise PackageError("安装脚本未提交，不能生成发布包")
    manifest = {
        "schema": 1, "repository": REPOSITORY, "version": version,
        "commit": commit, "development": development, "host_version": HOST_VERSION,
        "source_sha256": digest(json.dumps({name: digest(data) for name, data in sorted(sources.items())}, sort_keys=True).encode()),
        "files": [{"path": name, "sha256": digest(data), "size": len(data)} for name, data in sorted(files.items())],
    }
    # 输出必须在工作区内且全新；不覆盖用户的包或跟随链接。
    output = Path(os.path.abspath(output))
    if not output.is_relative_to(ROOT) or output == ROOT or output.exists():
        raise PackageError("输出必须是工作区内尚不存在的目录")
    physical(output.parent)
    output.mkdir()
    package = output / "bmad-win10-cline.zip"
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    with zipfile.ZipFile(package, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted({**files, "manifest.json": manifest_bytes}.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, data)
    sha = digest(package.read_bytes())
    binding = {key: manifest[key] for key in ("schema", "repository", "version", "commit", "development", "host_version", "source_sha256")}
    binding.update(zip_sha256=sha, zip_size=package.stat().st_size)
    # UTF-8 BOM ensures Windows PowerShell 5.1 decodes the release script correctly.
    encoded = template.replace("@@WIN10_RELEASE_BINDING@@", json.dumps(binding, separators=(",", ":"))).encode("utf-8-sig")
    (output / "install-win10.ps1").write_bytes(encoded)
    (output / "manifest.json").write_bytes(manifest_bytes)
    (output / "SHA256SUMS").write_text(f"{sha}  {package.name}\n{digest(encoded)}  install-win10.ps1\n", encoding="ascii")
    # 复读输出集合，不把构建写出等同于验收。
    with zipfile.ZipFile(package) as archive:
        if set(archive.namelist()) != set(files) | {"manifest.json"}:
            raise PackageError("写出包的文件集合发生变化")
        if any(archive.read(name) != data for name, data in files.items()):
            raise PackageError("写出包的字节不匹配")
    if snapshot_source(source) != sources or template_path.read_text(encoding="utf-8-sig") != template:
        raise PackageError("构建期间来源变化，禁止使用输出")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--development", action="store_true", help="仅生成拒绝真实安装的工作树测试包")
    args = parser.parse_args(argv)
    try:
        manifest = build(args.output, development=args.development)
        print(json.dumps({"version": manifest["version"], "assets": len(manifest["files"]), "development": manifest["development"]}, ensure_ascii=False))
        return 0
    except (PackageError, OSError, UnicodeError, ValueError, KeyError, yaml.YAMLError, subprocess.TimeoutExpired) as exc:
        print(f"Windows 包构建失败：{exc}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
