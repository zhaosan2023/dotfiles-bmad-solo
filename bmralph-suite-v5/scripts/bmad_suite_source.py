"""V5 已部署套件来源绑定；只读取明确部署根，不访问来源仓库。

读取租约内核验物理分发文件、所有权及来源记录，边界复核发现变化
即阻塞。没有任务循环、宿主加载、模式语义或同账号防篡改保证。
来源提交是已部署记录，不等于当前仓库 HEAD 或远程版本证明。
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

from bmad_suite_lease import suite_lease
from bmad_supervisor import SupervisorError, contained_path, workspace_path


PLUGIN = ".gemini/config/plugins/bmad-suite"
OWNERSHIP = ".bmad-solo-deployment/ownership.json"
PROVENANCE = PLUGIN + "/.manifest.json"
MAX_FILES = 4096
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024
IDENTITY = {
    "schema_version": 1,
    "suite_id": "bmralph-suite-v5",
    "major_version": "v5",
    "source_path": "bmralph-suite-v5",
}
REQUIRED = {
    "plugin.json", "suite.json", "rules/bmad-constitution.md",
    "rules/bmad-core.md", "roo/rules/01-bmad-constitution.md",
    "roo/rules/02-bmad-core.md",
    "roo/rules-ana-architect/01-ana-solo-core.md",
    "roo/rules-bmad-engineer/01-bmad-engineer-core.md",
    "roo/settings/custom_modes.yaml", "skills/ana-solo/SKILL.md",
    "skills/bmad/SKILL.md", "scripts/bmad-exec.py",
    "scripts/bmad_suite_source.py", "scripts/bmad_suite_lease.py",
}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SupervisorError("套件来源记录包含重复字段")
        result[key] = value
    return result


def relative_path(value):
    if (not isinstance(value, str) or not value or "\\" in value
            or any(ord(character) < 32 for character in value)):
        raise SupervisorError("来源路径必须为明确的规范相对路径")
    path = PurePosixPath(value)
    if (path.is_absolute() or any(part in {"", ".", ".."}
                                for part in value.split("/"))
            or str(path) != value):
        raise SupervisorError("来源路径非法或越界")
    return value


def validate_records(records):
    if not isinstance(records, dict) or not records or len(records) > MAX_FILES:
        raise SupervisorError("来源文件记录缺失或超出数量预算")
    for relative, record in records.items():
        relative_path(relative)
        if (not isinstance(record, dict) or set(record) != {"sha256", "mode"}
                or not isinstance(record["sha256"], str)
                or re.fullmatch(r"[0-9a-f]{64}", record["sha256"]) is None
                or type(record["mode"]) is not int
                or not 0 <= record["mode"] <= 0o777):
            raise SupervisorError("来源文件摘要或权限记录非法")


def read_asset(root, relative, budget):
    path = contained_path(root, relative_path(relative))
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or stat.S_IMODE(before.st_mode) > 0o777):
            raise SupervisorError("套件资产必须为单硬链接、普通权限的物理文件")
        if before.st_size > MAX_FILE_BYTES:
            raise SupervisorError("套件资产超出单文件读取预算")
        content = stream.read(MAX_FILE_BYTES + 1)
        after = os.fstat(stream.fileno())
    budget[0] += len(content)
    if len(content) > MAX_FILE_BYTES or budget[0] > MAX_TOTAL_BYTES:
        raise SupervisorError("套件来源读取超出预算；未丢弃必要资产")
    def identity(info):
        return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
                info.st_ctime_ns, info.st_mode, info.st_nlink)
    current = path.lstat()
    if identity(before) != identity(after) or identity(after) != identity(current):
        raise SupervisorError("套件资产读取期间变化；停止对账")
    record = {"sha256": hashlib.sha256(content).hexdigest(),
              "mode": stat.S_IMODE(after.st_mode)}
    return content, {"record": record, "identity": identity(after)}


def object_asset(content):
    try:
        data = json.loads(content, object_pairs_hook=unique_object)
    except (ValueError, UnicodeError) as exc:
        raise SupervisorError("套件来源 JSON 损坏或包含重复字段") from exc
    if not isinstance(data, dict):
        raise SupervisorError("套件来源 JSON 必须为对象")
    return data


def plugin_files(root):
    directory = contained_path(root, PLUGIN)
    if not directory.is_dir():
        raise SupervisorError("已部署 V5 套件物理目录缺失")
    found = set()
    directories = 0
    pending = [directory]
    while pending:
        parent = pending.pop()
        with os.scandir(parent) as entries:
            children = list(entries)
        directories += 1
        if directories > MAX_FILES:
            raise SupervisorError("套件目录数量超出预算")
        for entry in children:
            if entry.is_symlink():
                raise SupervisorError("已部署套件不得包含软链接")
            path = contained_path(root, Path(entry.path).relative_to(root).as_posix())
            if entry.is_dir(follow_symlinks=False):
                pending.append(path)
            elif entry.is_file(follow_symlinks=False):
                found.add(path.relative_to(directory).as_posix())
                if len(found) > MAX_FILES:
                    raise SupervisorError("套件物理文件数量超出预算")
            else:
                raise SupervisorError("已部署套件包含特殊文件")
    return found


def capture(deployment_root):
    """核验分发文件与清单；不读取宿主模式文件或源仓库。"""
    root = workspace_path(deployment_root)
    # 拒绝通过已有父目录链接访问明确部署根。
    for path in (root, *deployment_root.absolute().parents):
        if path.is_symlink():
            raise SupervisorError("部署来源根不得通过软链接")
    budget = [0]
    observed = {}
    ownership_bytes, observed[OWNERSHIP] = read_asset(root, OWNERSHIP, budget)
    ownership = object_asset(ownership_bytes)
    if (set(ownership) != {"schema_version", "files", "modes"}
            or type(ownership["schema_version"]) is not int
            or ownership["schema_version"] != 1
            or not isinstance(ownership["modes"], dict)):
        raise SupervisorError("受管所有权清单结构非法")
    validate_records(ownership["files"])
    for relative, modes in ownership["modes"].items():
        relative_path(relative)
        if (relative in ownership["files"] or not isinstance(modes, dict)
                or any(not isinstance(slug, str) or not slug.strip()
                       or not isinstance(digest, str)
                       or re.fullmatch(r"[0-9a-f]{64}", digest) is None
                       for slug, digest in modes.items())):
            raise SupervisorError("受管模式来源记录非法")
    payloads = {}
    for relative, expected in sorted(ownership["files"].items()):
        if relative.startswith(".bmad-solo-deployment/"):
            raise SupervisorError("受管分发文件与部署状态重叠")
        content, observed[relative] = read_asset(root, relative, budget)
        if observed[relative]["record"] != expected:
            raise SupervisorError("已部署受管文件与来源摘要不一致：" + relative)
        if relative in {PROVENANCE, PLUGIN + "/plugin.json", PLUGIN + "/suite.json"}:
            payloads[relative] = content
    if PROVENANCE not in payloads:
        raise SupervisorError("缺少已受管的套件来源清单")
    provenance = object_asset(payloads[PROVENANCE])
    expected_files = {key: value for key, value in ownership["files"].items()
                      if key != PROVENANCE}
    if (type(provenance.get("schema_version")) is not int
            or provenance["schema_version"] != 1
            or provenance.get("managed_files") != expected_files
            or provenance.get("managed_modes") != ownership["modes"]):
        raise SupervisorError("套件来源与所有权记录不一致")
    if any(provenance.get(key) != value for key, value in IDENTITY.items()
           if key != "schema_version"):
        raise SupervisorError("活动来源必须明确为 V5；不回退其他套件")
    directory = provenance.get("source_directory")
    repository = provenance.get("source_repository")
    commit = provenance.get("source_commit")
    kind = provenance.get("source_kind")
    dirty = provenance.get("source_dirty")
    if (not isinstance(directory, str) or not Path(directory).is_absolute()
            or Path(directory).name != IDENTITY["source_path"]
            or not isinstance(repository, str) or not Path(repository).is_absolute()
            or not isinstance(commit, str)
            or re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit) is None
            or kind not in {"worktree", "commit_cache"}
            or type(dirty) is not bool or (kind == "commit_cache" and dirty)):
        raise SupervisorError("V5 来源版本记录缺失、未知或相互矛盾")
    sources = provenance.get("source_files")
    validate_records(sources)
    if not REQUIRED.issubset(sources) or ".manifest.json" in sources:
        raise SupervisorError("V5 来源缺少必需运行资产或混入生成清单")
    if plugin_files(root) != set(sources) | {".manifest.json"}:
        raise SupervisorError("套件物理文件集合与来源记录不一致；不删除额外资产")
    mapped = {PLUGIN + "/" + relative: record for relative, record in sources.items()}
    for relative, record in sources.items():
        if relative in {"rules/bmad-constitution.md", "rules/bmad-core.md"}:
            mapped[".gemini/config/" + relative] = record
        if any(relative.startswith("roo/" + section + "/") for section in (
                "rules", "rules-ana-architect", "rules-bmad-engineer")):
            mapped[".roo/" + relative.removeprefix("roo/")] = record
    if mapped != expected_files:
        raise SupervisorError("套件源码与物理分发映射不一致")
    identity = object_asset(payloads[PLUGIN + "/suite.json"])
    plugin = object_asset(payloads[PLUGIN + "/plugin.json"])
    if (type(identity.get("schema_version")) is not int or identity != IDENTITY
            or plugin.get("name") != "bmad-suite"
            or plugin.get("displayName") != "BMRalph V5"):
        raise SupervisorError("V5 身份资产与来源记录不一致")
    # 再读已观察文件，避免将采集期间外部变更接受为稳定绑定。
    final_budget = [0]
    for relative, expected in observed.items():
        _, current = read_asset(root, relative, final_budget)
        if current != expected:
            raise SupervisorError("绑定期间套件或清单变化；停止对账")
    if plugin_files(root) != set(sources) | {".manifest.json"}:
        raise SupervisorError("绑定期间套件文件集合变化")
    return {"deployment_root": str(root), "suite_root": str(root / PLUGIN),
            "suite_id": IDENTITY["suite_id"], "source_commit": commit,
            "source_kind": kind, "source_dirty": dirty, "files": observed,
            "source_files": sorted(sources),
            "evidence_boundary": "已部署 V5 物理分发文件与来源记录一致性；未核验宿主模式语义、运行时加载、来源仓库当前状态或同账号防篡改"}


@dataclass(frozen=True)
class SourceBinding:
    deployment_root: Path
    _snapshot: dict

    @property
    def suite_root(self):
        return self.deployment_root / PLUGIN

    def check(self):
        """接管、契约变化及阶段边界复核；不执行测试或写状态。"""
        if capture(self.deployment_root) != self._snapshot:
            raise SupervisorError("已绑定套件来源发生变化；停止对账，不恢复旧文件")


@contextmanager
def bound_suite(deployment_root: Path):
    """先持读取租约，再核验来源；调用方仍须确认所有在途进程结束。"""
    with suite_lease(deployment_root):
        root = workspace_path(deployment_root)
        binding = SourceBinding(root, capture(deployment_root))
        yield binding
        # 调用方原始失败继续传播，不由正常退出复核覆盖。
        binding.check()
