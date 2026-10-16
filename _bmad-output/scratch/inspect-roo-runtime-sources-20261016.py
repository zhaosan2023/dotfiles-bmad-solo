#!/usr/bin/env python3
"""只读定位已安装 Roo 源映射中的运行时接口，不加载扩展或读取认证资产。"""
from pathlib import Path
import hashlib
import json
import re
import sys


WORKSPACE = Path(__file__).resolve().parents[2]
EXTENSION = WORKSPACE.parent / ".antigravity-ide-server/extensions/rooveterinaryinc.roo-cline-3.54.0-universal"
MAX_MAP_BYTES = 256 * 1024 * 1024
MAX_OUTPUT_BYTES = 16384
MAX_NAMES = 80
PATTERN = re.compile(r"(?:^|/)(?:cli|ipc)/|RooCodeAPI|roo-code-api|(?:^|/)extension\.ts$|vscode-shim", re.I)


def main():
    path = EXTENSION / "dist/extension.js.map"
    if path.is_symlink() or not path.is_file():
        raise ValueError("源映射缺失或不是物理文件；不加载扩展、不回退其他来源")
    before = path.stat()
    if before.st_size > MAX_MAP_BYTES:
        raise ValueError("源映射超过只读探测预算")
    with path.open("rb") as stream:
        raw = stream.read(MAX_MAP_BYTES + 1)
    after = path.stat()
    identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    if len(raw) > MAX_MAP_BYTES or identity(before) != identity(after):
        raise ValueError("源映射超预算或读取期间变化；停止对账")
    data = json.loads(raw)
    sources = data.get("sources")
    contents = data.get("sourcesContent")
    if not isinstance(sources, list) or any(not isinstance(item, str) for item in sources):
        raise ValueError("源映射来源字段不完整")
    matches = [
        {"index": index, "source": name,
         "embedded_source": isinstance(contents, list) and index < len(contents) and isinstance(contents[index], str)}
        for index, name in enumerate(sources) if PATTERN.search(name)
    ]
    result = {
        "operation": "inspect-installed-roo-source-map",
        "status": "PASS" if len(matches) <= MAX_NAMES else "BLOCKED",
        "extension_version": "3.54.0",
        "source_map": str(path.relative_to(WORKSPACE.parent)),
        "source_map_bytes": len(raw),
        "source_map_sha256": hashlib.sha256(raw).hexdigest(),
        "sources_total": len(sources),
        "matching_sources_total": len(matches),
        "matching_sources": matches[:MAX_NAMES],
        "output_truncated": len(matches) > MAX_NAMES,
        "evidence_boundary": "仅已安装扩展内嵌源码定位；不证明独立 CLI 已安装、接口可运行、认证、宿主加载或取消能力",
    }
    if len(matches) > MAX_NAMES:
        result["reason"] = "来源定位超过输出预算；未将截断列表作为完整接口证据"
    output = json.dumps(result, ensure_ascii=False, sort_keys=True)
    if len(output.encode("utf-8")) + 1 > MAX_OUTPUT_BYTES:
        raise ValueError("必要定位元数据超过输出预算；未输出无界内容")
    print(output, flush=True)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)[:512],
                          "evidence_boundary": "只读探测失败；未启动 Agent 或读取凭据"}, ensure_ascii=False), flush=True)
        sys.exit(1)
