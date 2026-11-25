#!/usr/bin/env bash
# BMAD-Solo V5.1 独立受管生命周期管理器 (scripts/dispatch_v5.sh)
#
# 核心架构契约：
# 1. 独立 XDG 受管核心：<HOME>/.local/share/bmad-solo/v5/（不被 Cline/Gemini/Roo 自动扫描）
#    - manifest.json  唯一受管所有权与正文 SHA-256 指纹真理源
#    - deploy.lock    排他锁（彻底移出 ~/.cline/）
#    - backups/       受管备份快照
#    - skills/        只读方法论资产 (0444)：ana-solo.md, bmad-solo.md
# 2. Cline 优先试点单一薄入口：<HOME>/.cline/rules/bmad-v5-router.md (0644 兼容 UI 开关)
# 3. 物理冻结隔离：硬编码禁止任何对 <HOME>/.gemini/ 的写操作
# 4. 完整生命周期：--deploy | --test | --doctor | --status | --rollback | --uninstall
# 5. 隔离测试支持：--home-dir <TMP_DIR> 在沙箱目录完整演练，绝不触碰真实家目录

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DEFAULT="$(cd "${SCRIPT_DIR}/.." && pwd)"

exec python3 - "${WORKSPACE_DEFAULT}" "$@" <<'PYEOF'
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile

MANAGED_SPECS = [
    {
        "id": "router",
        "source_rel": "bmad-v5-router.md",
        "target_rel": ".cline/rules/bmad-v5-router.md",
        "mode": 0o644,
        "allow_frontmatter_toggle": True,
    },
    {
        "id": "ana-solo",
        "source_rel": "skills/ana-solo.md",
        "target_rel": ".local/share/bmad-solo/v5/skills/ana-solo.md",
        "mode": 0o444,
        "allow_frontmatter_toggle": False,
    },
    {
        "id": "bmad-solo",
        "source_rel": "skills/bmad-solo.md",
        "target_rel": ".local/share/bmad-solo/v5/skills/bmad-solo.md",
        "mode": 0o444,
        "allow_frontmatter_toggle": False,
    },
]

BMAD_SIGNATURE_RE = re.compile(
    r"(BMAD-Solo|BMAD\s+V4|bmad-core|bmad-router|/ana-solo|/bmad-solo|ana-solo\.md|bmad-solo\.md)",
    re.IGNORECASE,
)


def split_frontmatter(text: str) -> tuple[bool, str]:
    """分离 YAML frontmatter 中的 disabled 开关与正文，避免 Cline UI 开关切换误报篡改。"""
    if text.startswith("---\n") or text.startswith("---\r\n"):
        lines = text.splitlines(keepends=True)
        for idx in range(1, len(lines)):
            if lines[idx].strip() == "---":
                fm_text = "".join(lines[1:idx])
                body = "".join(lines[idx + 1 :]).lstrip("\r\n")
                disabled = bool(
                    re.search(r"^\s*disabled\s*:\s*true\s*$", fm_text, re.IGNORECASE | re.MULTILINE)
                )
                return disabled, body
    return False, text


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def body_sha256(text: str) -> tuple[bool, str]:
    disabled, body = split_frontmatter(text)
    return disabled, sha256_bytes(body.encode("utf-8"))


def check_no_gemini_touch(home_dir: Path, path: Path) -> None:
    gemini_root = (home_dir / ".gemini").resolve()
    resolved = path.resolve()
    if (
        resolved == gemini_root
        or gemini_root in resolved.parents
        or ".gemini" in home_dir.resolve().parts
        or ".gemini" in resolved.parts
    ):
        raise ValueError(
            f"GEMINI_ISOLATION_VIOLATION: 禁止任何 V5 操作触碰 Antigravity-Gemini V4 目录: {resolved}"
        )


def atomic_write_bytes(target: Path, data: bytes, mode: int, home_dir: Path) -> None:
    check_no_gemini_touch(home_dir, target)
    if target.is_symlink():
        raise ValueError(f"安全拒绝：目标路径为符号链接，拒绝写入: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.tmp.")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, target)
    except Exception:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


@contextmanager
def exclusive_lock(lock_file: Path, home_dir: Path):
    check_no_gemini_touch(home_dir, lock_file)
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock_file, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"排他分发锁被占用，存在并发操作: {lock_file}") from exc
        yield lock_file
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


class V5Manager:
    def __init__(self, home_dir: Path, source_dir: Path):
        self.home_dir = home_dir.resolve()
        self.source_dir = source_dir.resolve()
        self.core_root = self.home_dir / ".local/share/bmad-solo/v5"
        self.manifest_path = self.core_root / "manifest.json"
        self.lock_file = self.core_root / "deploy.lock"
        self.backup_dir = self.core_root / "backups"
        self.cline_rules_dir = self.home_dir / ".cline/rules"
        self.cline_skills_dir = self.home_dir / ".cline/skills"
        self.gemini_dir = self.home_dir / ".gemini"

        check_no_gemini_touch(self.home_dir, self.core_root)
        check_no_gemini_touch(self.home_dir, self.cline_rules_dir)

    def _target_path(self, spec: dict) -> Path:
        p = self.home_dir / spec["target_rel"]
        check_no_gemini_touch(self.home_dir, p)
        return p

    def _source_path(self, spec: dict) -> Path:
        return self.source_dir / spec["source_rel"]

    def _load_manifest(self) -> tuple[dict | None, str | None]:
        if not self.manifest_path.exists():
            return None, None
        if self.manifest_path.is_symlink() or not self.manifest_path.is_file():
            return None, f"manifest.json 类型非法或为符号链接: {self.manifest_path}"
        try:
            data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except Exception as exc:
            return None, f"manifest.json JSON 损坏: {exc}"
        if (
            not isinstance(data, dict)
            or data.get("schema_version") != 1
            or data.get("version") != "5.1"
            or not isinstance(data.get("files"), dict)
        ):
            return None, "manifest.json 结构或版本不受支持"
        return data, None

    def _build_manifest_payload(self, source_hashes: dict[str, str]) -> dict:
        files_entry = {}
        for spec in MANAGED_SPECS:
            files_entry[spec["id"]] = {
                "target_rel": spec["target_rel"],
                "mode": oct(spec["mode"]),
                "body_sha256": source_hashes[spec["id"]],
                "allow_frontmatter_toggle": spec["allow_frontmatter_toggle"],
            }
        return {
            "schema_version": 1,
            "version": "5.1",
            "host_target": "cline",
            "installed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_dir": str(self.source_dir),
            "files": files_entry,
        }

    def cmd_test(self) -> int:
        print("=" * 64)
        print("BMAD-Solo V5.1 Dispatch Preflight Verification (--test)")
        print("=" * 64)
        print("  [DISCLOSURE] --test 非绝对只读：会创建并触碰排他锁目录与锁文件")
        print(f"               ({self.lock_file})，但不覆写任何目标规则或技能文件。")
        print("  [DISCLOSURE] 客户端运行时加载状态: [UNKNOWN]（静态预检不证明 Cline 已加载）")

        # 1. 验证全部 3 份源资产存在
        for spec in MANAGED_SPECS:
            src = self._source_path(spec)
            if not src.is_file():
                print(
                    f"  [FAIL] 缺失编译源资产: {src}（请先运行 python3 scripts/distill_v5_kernel.py）",
                    file=sys.stderr,
                )
                return 1
            print(f"  [PASS] 源资产就绪: {src}")

        # 2. 验证 Gemini 隔离路径守卫
        for spec in MANAGED_SPECS:
            check_no_gemini_touch(self.home_dir, self._target_path(spec))
        print(f"  [PASS] Gemini 隔离守卫通过（零触碰 {self.gemini_dir}）")

        # 3. 验证目标父目录可写性
        for parent in (self.core_root, self.cline_rules_dir):
            probe = parent
            while not probe.exists() and probe != probe.parent:
                probe = probe.parent
            if not os.access(probe, os.W_OK):
                print(f"  [FAIL] 目标父目录不可写: {probe}", file=sys.stderr)
                return 1
        print(f"  [PASS] 目标目录可写性校验通过 ({self.core_root}, {self.cline_rules_dir})")

        # 4. 验证排他锁（位于 ~/.local/share/bmad-solo/v5/deploy.lock，不污染 ~/.cline/）
        with exclusive_lock(self.lock_file, self.home_dir):
            print(f"  [PASS] 成功获取非阻塞排他锁: {self.lock_file}")

        print("-" * 64)
        print("Status: PREFLIGHT_PASS (未覆写目标规则配置；客户端加载状态: [UNKNOWN])")
        print("=" * 64)
        return 0

    def cmd_deploy(self, force: bool = False) -> int:
        print("=" * 64)
        print("BMAD-Solo V5.1 Managed Deployment (--deploy)")
        print("=" * 64)

        sources: dict[str, bytes] = {}
        source_body_hashes: dict[str, str] = {}
        for spec in MANAGED_SPECS:
            src = self._source_path(spec)
            if not src.is_file():
                print(f"FAIL: 缺失源资产 {src}，请先运行 python3 scripts/distill_v5_kernel.py", file=sys.stderr)
                return 1
            raw = src.read_bytes()
            sources[spec["id"]] = raw
            _, digest = body_sha256(raw.decode("utf-8"))
            source_body_hashes[spec["id"]] = digest

        with exclusive_lock(self.lock_file, self.home_dir):
            manifest, manifest_err = self._load_manifest()
            if manifest_err:
                print(f"FAIL: 现有受管清单异常，拒绝盲目覆盖: {manifest_err}", file=sys.stderr)
                return 1

            # 防踩踏校验：若目标文件已存在，检查是否受管且未被外部篡改
            existing_targets: list[tuple[dict, Path, bytes]] = []
            for spec in MANAGED_SPECS:
                tgt = self._target_path(spec)
                if tgt.is_symlink():
                    print(f"FAIL: 拒绝覆盖符号链接目标: {tgt}", file=sys.stderr)
                    return 1
                if tgt.exists():
                    cur_bytes = tgt.read_bytes()
                    existing_targets.append((spec, tgt, cur_bytes))
                    _, cur_body_hash = body_sha256(cur_bytes.decode("utf-8", errors="replace"))
                    owned = manifest.get("files", {}).get(spec["id"]) if manifest else None
                    if owned is None:
                        if not force:
                            print(
                                f"WARN: 目标文件非当前 V5.1 清单受管资产，拒绝静默覆盖: {tgt}（确认覆盖请追加 --force）",
                                file=sys.stderr,
                            )
                            return 1
                    elif owned.get("body_sha256") != cur_body_hash:
                        if not force:
                            print(
                                f"WARN: 受管文件正文已被外部修改，拒绝静默覆盖: {tgt}（确认覆盖请追加 --force）",
                                file=sys.stderr,
                            )
                            return 1

            # 创建备份快照（仅当已有受管或目标文件存在时）
            if existing_targets:
                ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ_%f")
                snap_dir = self.backup_dir / ts
                snap_dir.mkdir(parents=True, exist_ok=True)
                for spec, _, cur_bytes in existing_targets:
                    snap_file = snap_dir / spec["source_rel"]
                    snap_file.parent.mkdir(parents=True, exist_ok=True)
                    snap_file.write_bytes(cur_bytes)
                if manifest is not None:
                    (snap_dir / "manifest.json").write_text(
                        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                    )
                print(f"  - 已创建受管备份快照: {snap_dir}")

            # 原子写入 3 份受管资产（skills/*.md 0444，router 0644）
            for spec in MANAGED_SPECS:
                tgt = self._target_path(spec)
                atomic_write_bytes(tgt, sources[spec["id"]], spec["mode"], self.home_dir)
                print(
                    f"  - 已受管交付 [{spec['id']}]: {tgt} (mode={oct(spec['mode'])}, "
                    f"body_sha256={source_body_hashes[spec['id']][:16]}...)"
                )

            new_manifest = self._build_manifest_payload(source_body_hashes)
            atomic_write_bytes(
                self.manifest_path,
                (json.dumps(new_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
                    "utf-8"
                ),
                0o600,
                self.home_dir,
            )

        print("-" * 64)
        print("Status: DEPLOY_SUCCESS")
        print(f"  - Core Root: {self.core_root}")
        print(f"  - Cline Thin Entry: {self.cline_rules_dir / 'bmad-v5-router.md'}")
        print("  - Runtime Client Load Status: [UNKNOWN]（磁盘分发成功不证明 Cline 进程已热加载）")
        print("=" * 64)
        return 0

    def cmd_rollback(self) -> int:
        print("=" * 64)
        print("BMAD-Solo V5.1 Safe Rollback (--rollback)")
        print("=" * 64)
        if not self.backup_dir.is_dir():
            print(f"FAIL: 未找到备份目录: {self.backup_dir}", file=sys.stderr)
            return 1
        snaps = sorted([p for p in self.backup_dir.iterdir() if p.is_dir()], reverse=True)
        if not snaps:
            print("FAIL: 无可用受管快照，拒绝盲目回滚", file=sys.stderr)
            return 1
        latest = snaps[0]
        with exclusive_lock(self.lock_file, self.home_dir):
            restored = 0
            for spec in MANAGED_SPECS:
                snap_file = latest / spec["source_rel"]
                if snap_file.is_file():
                    tgt = self._target_path(spec)
                    atomic_write_bytes(tgt, snap_file.read_bytes(), spec["mode"], self.home_dir)
                    print(f"  - 已还原 [{spec['id']}]: {tgt}")
                    restored += 1
            snap_manifest = latest / "manifest.json"
            if snap_manifest.is_file():
                atomic_write_bytes(self.manifest_path, snap_manifest.read_bytes(), 0o600, self.home_dir)
            if restored == 0:
                print(f"FAIL: 快照中不包含任何受管文件: {latest}", file=sys.stderr)
                return 1
        print("-" * 64)
        print(f"Status: ROLLBACK_SUCCESS (来源快照: {latest})")
        print("=" * 64)
        return 0

    def cmd_uninstall(self, force: bool = False) -> int:
        print("=" * 64)
        print("BMAD-Solo V5.1 Clean Uninstall (--uninstall)")
        print("=" * 64)

        manifest, manifest_err = self._load_manifest()
        if manifest_err:
            if not force:
                print(f"FAIL: manifest.json 异常，为防误删已停止卸载: {manifest_err}", file=sys.stderr)
                return 1
        if manifest is None:
            leftovers = [self._target_path(spec) for spec in MANAGED_SPECS if self._target_path(spec).exists()]
            if not leftovers and not self.core_root.exists():
                print("INFO: 当前未检测到任何 V5.1 受管资产，已是干净卸载态 (UNINSTALLED)。")
                print("=" * 64)
                return 0
            if leftovers and not force:
                print(
                    f"FAIL: 未找到 manifest.json 但存在疑似文件 {[str(p) for p in leftovers]}，"
                    "拒绝盲删（确认删除请追加 --force）",
                    file=sys.stderr,
                )
                return 1

        # 持锁校验并精确删除 manifest 登记资产
        if self.core_root.exists():
            with exclusive_lock(self.lock_file, self.home_dir):
                removed: list[str] = []
                for spec in MANAGED_SPECS:
                    tgt = self._target_path(spec)
                    if tgt.is_symlink():
                        print(f"FAIL: 目标路径为符号链接，拒绝删除: {tgt}", file=sys.stderr)
                        return 1
                    if not tgt.exists():
                        continue
                    owned = manifest.get("files", {}).get(spec["id"]) if manifest else None
                    if owned is not None and not force:
                        _, cur_hash = body_sha256(tgt.read_text(encoding="utf-8", errors="replace"))
                        if cur_hash != owned.get("body_sha256"):
                            print(
                                f"FAIL: 受管文件正文已被用户修改，拒绝静默删除: {tgt}（确认删除请追加 --force）",
                                file=sys.stderr,
                            )
                            return 1
                    # 0444 文件在可写目录中可直接 unlink
                    tgt.unlink()
                    removed.append(str(tgt))
                    print(f"  - 已精确移除 [{spec['id']}]: {tgt}")

                if self.manifest_path.exists():
                    self.manifest_path.unlink()
                    removed.append(str(self.manifest_path))
                if self.backup_dir.is_dir():
                    shutil.rmtree(self.backup_dir)
                    removed.append(str(self.backup_dir))

            # 释放锁后清理锁文件与空目录（绝不递归删除非空第三方目录）
            if self.lock_file.exists():
                self.lock_file.unlink()
            for d in (
                self.core_root / "skills",
                self.core_root,
                self.core_root.parent,
            ):
                if d.is_dir():
                    try:
                        d.rmdir()
                    except OSError:
                        pass
        else:
            # manifest 缺失但 --force 清理遗留目标文件
            for spec in MANAGED_SPECS:
                tgt = self._target_path(spec)
                if tgt.is_file() and not tgt.is_symlink():
                    tgt.unlink()
                    print(f"  - 已强制移除遗留文件 [{spec['id']}]: {tgt}")

        # 复核全部受管目标已清空
        still_present = [str(self._target_path(s)) for s in MANAGED_SPECS if self._target_path(s).exists()]
        if still_present or self.manifest_path.exists():
            print(f"FAIL: 卸载后仍有残留文件: {still_present}", file=sys.stderr)
            return 1

        print("-" * 64)
        print("Status: UNINSTALL_SUCCESS (受管资产零残留；第三方文件与 ~/.gemini/ 未受影响)")
        print("=" * 64)
        return 0

    def _scan_rules_dir(self, directory: Path, skip_paths: set[Path], scope_label: str) -> tuple[list[str], list[str]]:
        """扫描目录中的 BMAD 规则文件，返回 (enabled_conflicts, disabled_residues)。"""
        conflicts: list[str] = []
        residues: list[str] = []
        if not directory.is_dir():
            return conflicts, residues
        for item in sorted(directory.iterdir()):
            if not item.is_file():
                continue
            if item.resolve() in skip_paths:
                continue
            try:
                text = item.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if BMAD_SIGNATURE_RE.search(text) or "bmad" in item.name.lower() or item.name == ".clinerules":
                is_disabled, _ = split_frontmatter(text)
                entry = f"[{scope_label}] {item}"
                if is_disabled:
                    residues.append(entry)
                else:
                    conflicts.append(entry)
        return conflicts, residues

    def _scan_skills_dir(self, directory: Path, scope_label: str) -> list[str]:
        """扫描 Cline 自动发现的 skills 目录是否存在 BMAD 技能引发自加载冲突。"""
        conflicts: list[str] = []
        if not directory.is_dir():
            return conflicts
        for item in sorted(directory.rglob("*")):
            if not item.is_file():
                continue
            rel = str(item.relative_to(directory)).lower()
            if "ana-solo" in rel or "bmad" in rel:
                conflicts.append(f"[{scope_label}:auto-skill] {item}")
        return conflicts

    def _scan_gemini_v5_leak(self) -> list[str]:
        """只读检查 ~/.gemini/ 下是否意外泄露任何 V5 资产。"""
        leaks: list[str] = []
        if not self.gemini_dir.is_dir():
            return leaks
        for item in sorted(self.gemini_dir.rglob("*.md")):
            if not item.is_file():
                continue
            name_low = item.name.lower()
            if "bmad-v5" in name_low:
                leaks.append(f"[gemini-v5-leak] {item}")
                continue
            try:
                head = item.read_text(encoding="utf-8", errors="replace")[:512]
            except OSError:
                continue
            if "BMAD-Solo V5" in head:
                leaks.append(f"[gemini-v5-leak] {item}")
        return leaks

    def evaluate_health(self, workspace: Path | None = None) -> dict:
        manifest, manifest_err = self._load_manifest()
        managed_targets = {spec["id"]: self._target_path(spec) for spec in MANAGED_SPECS}
        any_target_exists = any(p.exists() or p.is_symlink() for p in managed_targets.values())

        broken_reasons: list[str] = []
        conflicts: list[str] = []
        warnings: list[str] = []
        router_disabled: bool | None = None

        # 1. 干净未安装状态判定
        if manifest is None and manifest_err is None and not any_target_exists:
            g_conf, g_res = self._scan_rules_dir(self.cline_rules_dir, set(), "global")
            conflicts.extend(g_conf)
            warnings.extend([f"全局历史禁用残留: {x}" for x in g_res])
            if workspace is not None:
                ws = workspace.resolve()
                clinerules_file = ws / ".clinerules"
                if clinerules_file.is_file():
                    txt = clinerules_file.read_text(encoding="utf-8", errors="replace")
                    if BMAD_SIGNATURE_RE.search(txt):
                        is_dis, _ = split_frontmatter(txt)
                        if is_dis:
                            warnings.append(f"工作区历史禁用残留: [workspace] {clinerules_file}")
                        else:
                            conflicts.append(f"[workspace] {clinerules_file}")
                c_rules, r_rules = self._scan_rules_dir(ws / ".cline/rules", set(), "workspace")
                conflicts.extend(c_rules)
                warnings.extend([f"工作区历史禁用残留: {x}" for x in r_rules])
            return {
                "state": "UNINSTALLED",
                "exit_code": 0,
                "runtime_load_status": "[UNKNOWN]",
                "broken_reasons": [],
                "conflicts": conflicts,
                "warnings": warnings,
                "router_enabled": None,
            }

        # 2. 受管完整性核验 (BROKEN 检查)
        if manifest_err:
            broken_reasons.append(manifest_err)
        elif manifest is None:
            broken_reasons.append(f"存在受管文件但缺失 manifest.json: {self.manifest_path}")
        else:
            for spec in MANAGED_SPECS:
                tgt = managed_targets[spec["id"]]
                owned = manifest.get("files", {}).get(spec["id"])
                if owned is None:
                    broken_reasons.append(f"manifest 缺失受管条目: {spec['id']}")
                    continue
                if tgt.is_symlink():
                    broken_reasons.append(f"受管目标被替换为符号链接: {tgt}")
                    continue
                if not tgt.is_file():
                    broken_reasons.append(f"受管文件缺失: {tgt}")
                    continue
                text = tgt.read_text(encoding="utf-8", errors="replace")
                is_disabled, cur_hash = body_sha256(text)
                if cur_hash != owned.get("body_sha256"):
                    broken_reasons.append(
                        f"正文 SHA-256 漂移（可能被外部或模型篡改）: {tgt}"
                    )
                if spec["id"] == "router":
                    router_disabled = is_disabled
                    if is_disabled:
                        warnings.append(f"Cline UI 开关当前为禁用态 (disabled: true): {tgt}")
                else:
                    file_mode = stat.S_IMODE(tgt.stat().st_mode)
                    if file_mode & 0o222:
                        broken_reasons.append(
                            f"只读技能文件权限漂移 (期望 0444，当前 {oct(file_mode)}): {tgt}"
                        )

        # 3. 冲突与隔离扫描 (CONFLICT / DEGRADED)
        skip_global = {managed_targets["router"].resolve()} if managed_targets["router"].exists() else set()
        g_conf, g_res = self._scan_rules_dir(self.cline_rules_dir, skip_global, "global")
        conflicts.extend(g_conf)
        warnings.extend([f"全局历史禁用残留: {x}" for x in g_res])
        conflicts.extend(self._scan_skills_dir(self.cline_skills_dir, "global"))
        conflicts.extend(self._scan_gemini_v5_leak())

        if workspace is not None:
            ws = workspace.resolve()
            clinerules_file = ws / ".clinerules"
            if clinerules_file.is_file():
                txt = clinerules_file.read_text(encoding="utf-8", errors="replace")
                if BMAD_SIGNATURE_RE.search(txt):
                    is_dis, _ = split_frontmatter(txt)
                    if is_dis:
                        warnings.append(f"工作区历史禁用残留: [workspace] {clinerules_file}")
                    else:
                        conflicts.append(f"[workspace] {clinerules_file}")
            w_conf, w_res = self._scan_rules_dir(ws / ".cline/rules", set(), "workspace")
            conflicts.extend(w_conf)
            warnings.extend([f"工作区历史禁用残留: {x}" for x in w_res])
            conflicts.extend(self._scan_skills_dir(ws / ".cline/skills", "workspace"))

        # 4. 严格优先级裁决：BROKEN(1) > CONFLICT(2) > DEGRADED(0) > HEALTHY(0)
        if broken_reasons:
            state, code = "BROKEN", 1
        elif conflicts:
            state, code = "CONFLICT", 2
        elif warnings:
            state, code = "DEGRADED", 0
        else:
            state, code = "HEALTHY", 0

        return {
            "state": state,
            "exit_code": code,
            "runtime_load_status": "[UNKNOWN]",
            "router_enabled": (not router_disabled) if router_disabled is not None else None,
            "broken_reasons": broken_reasons,
            "conflicts": conflicts,
            "warnings": warnings,
        }

    def cmd_doctor(self, workspace: Path | None = None, as_json: bool = False) -> int:
        report = self.evaluate_health(workspace=workspace)
        if as_json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return report["exit_code"]

        print("=" * 64)
        print("BMAD-Solo V5.1 Health Check Report (--doctor)")
        print("=" * 64)
        print(f"  - Health Verdict: {report['state']} (exit_code={report['exit_code']})")
        print(f"  - Core Root: {self.core_root}")
        print(f"  - Cline Thin Entry: {self.cline_rules_dir / 'bmad-v5-router.md'}")
        print(f"  - Router UI Enabled: {report['router_enabled']}")
        print(f"  - Runtime Client Load Status: {report['runtime_load_status']}")
        if workspace is not None:
            print(f"  - Scanned Workspace: {workspace.resolve()}")
        if report["broken_reasons"]:
            print("  - Broken Items:")
            for item in report["broken_reasons"]:
                print(f"      * {item}")
        if report["conflicts"]:
            print("  - Conflicts (Enabled Competing Rules / Auto-Skills / Leaks):")
            for item in report["conflicts"]:
                print(f"      * {item}")
        if report["warnings"]:
            print("  - Warnings / Legacy Disabled Residue:")
            for item in report["warnings"]:
                print(f"      * {item}")
        print("=" * 64)
        return report["exit_code"]

    def cmd_status(self, workspace: Path | None = None) -> int:
        return self.cmd_doctor(workspace=workspace, as_json=False)


def main() -> None:
    workspace_default = Path(sys.argv[1])
    raw_args = sys.argv[2:]

    parser = argparse.ArgumentParser(
        prog="scripts/dispatch_v5.sh",
        description="BMAD-Solo V5.1 独立受管生命周期管理器（支持隔离测试、精确卸载与四态健康检查）",
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--deploy", action="store_true", help="执行受管原子部署（默认模式）")
    mode_group.add_argument(
        "--test",
        action="store_true",
        help="执行预检与排他锁校验（会触碰 <HOME>/.local/share/bmad-solo/v5/deploy.lock，不覆写目标规则）",
    )
    mode_group.add_argument(
        "--doctor",
        action="store_true",
        help="执行健康与冲突体检，返回 HEALTHY(0)/DEGRADED(0)/UNINSTALLED(0)/BROKEN(1)/CONFLICT(2)",
    )
    mode_group.add_argument("--status", action="store_true", help="查看当前受管状态与健康度摘要")
    mode_group.add_argument("--rollback", action="store_true", help="从最近受管快照回滚")
    mode_group.add_argument("--uninstall", action="store_true", help="基于 manifest.json 精确卸载 V5.1 受管资产")

    parser.add_argument("--force", action="store_true", help="强制覆盖或强制卸载已被外部修改的受管文件")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出 --doctor 报告")
    parser.add_argument(
        "--home-dir",
        type=Path,
        default=Path.home(),
        help="目标家目录根路径（默认 $HOME；测试时可传入临时隔离目录）",
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=workspace_default / "dist/v5",
        help="编译源资产目录（默认 <repo>/dist/v5）",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="供 --doctor 额外扫描 V4/V5 规则冲突的目标业务工作区路径",
    )

    args = parser.parse_args(raw_args)
    try:
        mgr = V5Manager(home_dir=args.home_dir, source_dir=args.source_dir)
        if args.test:
            code = mgr.cmd_test()
        elif args.doctor:
            code = mgr.cmd_doctor(workspace=args.workspace, as_json=args.json)
        elif args.status:
            code = mgr.cmd_status(workspace=args.workspace)
        elif args.rollback:
            code = mgr.cmd_rollback()
        elif args.uninstall:
            code = mgr.cmd_uninstall(force=args.force)
        else:
            code = mgr.cmd_deploy(force=args.force)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    sys.exit(code)


if __name__ == "__main__":
    main()
PYEOF
