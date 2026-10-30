"""有界读取获准的 Cline 安装程序长行；不导入、执行或修改扩展。

仅解决原生读取长行截断；不是宿主行为探针或验证门禁。
"""
import argparse
import json
from pathlib import Path
import sys


ASSET_ROOT = Path(__file__).resolve().parents[2].parent / (
    ".antigravity-ide-server/extensions/saoudrizwan.claude-dev-4.1.25-universal"
)
MAX_SOURCE_BYTES = 80 * 1024 * 1024
MAX_OUTPUT_BYTES = 16000


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--needle", action="append", default=[])
    parser.add_argument("--offset", type=int)
    parser.add_argument("--limit", type=int, default=1200)
    parser.add_argument("--matches", type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.limit <= 6000 or not 1 <= args.matches <= 8:
        parser.error("limit 必须为 1..6000，matches 必须为 1..8")
    if args.offset is not None and (args.offset < 0 or args.needle):
        parser.error("offset 必须非负，且不能与 needle 混用")
    if args.offset is None and not args.needle:
        parser.error("必须指定 needle 或 offset")
    if len(args.needle) > 6 or any(not n or len(n) > 100 for n in args.needle):
        parser.error("最多 6 个非空 needle，每个不超过 100 字符")
    package = ASSET_ROOT / "package.json"
    bundle = ASSET_ROOT / "dist/extension.js"
    for path in (ASSET_ROOT, ASSET_ROOT / "dist", package, bundle):
        if path.is_symlink():
            raise RuntimeError("安装资产路径包含链接，停止读取")
    metadata = json.loads(package.read_text(encoding="utf-8"))
    if metadata.get("version") != "4.1.25" or metadata.get("publisher") != "saoudrizwan":
        raise RuntimeError("安装资产身份与获准目标不符")
    before = bundle.stat()
    if before.st_size > MAX_SOURCE_BYTES:
        raise RuntimeError("程序资产超出读取预算")
    with bundle.open("rb") as stream:
        raw = stream.read(MAX_SOURCE_BYTES + 1)
    if len(raw) > MAX_SOURCE_BYTES:
        raise RuntimeError("读取期间程序资产超出预算")
    after = bundle.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_ino, after.st_size, after.st_mtime_ns
    ):
        raise RuntimeError("读取期间源版本变化，停止")
    text = raw.decode("utf-8")
    records = [f"静态程序片段；Cline {metadata['version']}；字符偏移非字节偏移；不证明宿主运行。"]
    if args.offset is not None:
        if args.offset >= len(text):
            raise RuntimeError("字符偏移超出程序资产")
        line = text.count("\n", 0, args.offset) + 1
        records.append(f"line={line} offset={args.offset}\n" + text[args.offset:args.offset + args.limit])
    else:
        for needle in args.needle:
            total = text.count(needle)
            records.append(f"needle={needle!r} total={total} 展示上限={args.matches}")
            if not total:
                raise RuntimeError(f"必要定位零命中：{needle!r}")
            cursor = 0
            for _ in range(min(total, args.matches)):
                position = text.find(needle, cursor)
                start = max(0, position - 160)
                line = text.count("\n", 0, position) + 1
                records.append(f"line={line} match_offset={position} excerpt_offset={start}\n" + text[start:start + args.limit])
                cursor = position + len(needle)
            if total > args.matches:
                records.append(f"未展示 {total - args.matches} 项；此调用不是完整入口覆盖证明。")
    output = "\n\n".join(records) + "\n"
    if len(output.encode("utf-8")) > MAX_OUTPUT_BYTES:
        raise RuntimeError("结果超出输出预算，须缩小定位范围；不截断必要结果")
    sys.stdout.write(output)


if __name__ == "__main__":
    main()
