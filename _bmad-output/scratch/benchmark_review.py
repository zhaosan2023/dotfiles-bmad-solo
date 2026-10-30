"""离线复核本轮七模型回执；不联网、不修改生产代码、不修补模型 JSON。"""
import ast
import hashlib
import json
from pathlib import Path
import re
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gateway_probe as probe

RECEIPTS = [
    "gateway_probe-benchmark-c472d7d58f644c6da260524aa6cda07a.json",
    "gateway_probe-benchmark-91723da59f9f4fe598c6f1a54a27713f.json",
    "gateway_probe-benchmark-afda21005d4a44d58192cb110dad8705.json",
    "gateway_probe-benchmark-7978d7842b8b4cbab734469827b5c72e.json",
    "gateway_probe-benchmark-67240fcf98534151a8986f091619b879.json",
    "gateway_probe-benchmark-b5e446a7e8b04155a60766f3f2b77340.json",
    "gateway_probe-benchmark-c7049d4ccd1c46dd9ba133171fa6b19f.json",
    "gateway_probe-gemini-8ba12d0609034815912f401b909636b0.json",
]


def parse_answer(text):
    stripped = text.strip()
    errors = []
    # 仅剥离完整匹配的展示围栏，不改变 JSON 正文或修补字段。
    outer = re.fullmatch(r"(`{3,})(?:json|markdown)?[ \t]*\r?\n(.*?)\r?\n\1[ \t]*", stripped, flags=re.S)
    outer_removed = bool(outer)
    if outer:
        stripped = outer.group(2).strip()
    try:
        obj = json.loads(stripped)
        if isinstance(obj, dict):
            return obj, "outer_fence_json_without_repair" if outer_removed else "whole_response_json", errors
    except json.JSONDecodeError as error:
        errors.append({"method": "whole_response", "line": error.lineno, "column": error.colno,
                       "message": error.msg, "near_error": stripped[max(0, error.pos - 80):error.pos + 160]})
    fenced = re.findall(r"```(?:json)?\s*\n(.*?)```", stripped, flags=re.S)
    for body in fenced:
        try:
            obj = json.loads(body.strip())
            if isinstance(obj, dict):
                return obj, "single_json_fence" if len(fenced) == 1 else "multiple_fences_first_matching_object", errors
        except json.JSONDecodeError as error:
            errors.append({"method": "fence", "line": error.lineno, "column": error.colno,
                           "message": error.msg, "near_error": body[max(0, error.pos - 80):error.pos + 160]})
    return None, "unparseable_without_repair", errors[:3]


def normalize_symbols(items, definitions):
    normalized, unsupported = set(), []
    for item in items:
        if not isinstance(item, str):
            unsupported.append(str(item))
            continue
        if ":" not in item:
            candidates = {s for s in definitions if s.split(":", 1)[1] == item.strip()}
            if len(candidates) == 1:
                normalized.update(candidates)
            else:
                unsupported.append(item)
            continue
        path, names = item.split(":", 1)
        names = names.lstrip(":").strip()
        segments = [segment.strip() for segment in names.split(" / ")]
        owner = segments[0].rsplit(".", 1)[0] if "." in segments[0] else ""
        for index, segment in enumerate(segments):
            if index and owner and "." not in segment:
                segment = owner + "." + segment
            if not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", segment):
                unsupported.append(item)
            else:
                normalized.add(path.strip() + ":" + segment)
    return normalized, sorted(set(unsupported))


def main():
    began = time.monotonic()
    text, meta = probe.skeleton()
    symbols = set()
    file = None
    for line in text.splitlines():
        if line.startswith("FILE "):
            file = line[5:]
        else:
            match = re.match(r"  L\d+ (?:class|def) ([A-Za-z_][\w.]*)\(", line)
            if match:
                symbols.add(file + ":" + match.group(1))
    reference = {tuple(edge) for edge in meta["direct_import_edges"]}
    # 前轮原生源码复读已确认的两条嵌套包导入；不把参考解析器漏项当作模型错误。
    confirmed = {
        ("nanobot/nanobot/agent/loop.py", "nanobot/nanobot/agent/context.py"),
        ("nanobot/nanobot/agent/loop.py", "nanobot/nanobot/agent/tools/fastcode.py"),
    }
    reference |= confirmed
    # 将仓库内嵌套 nanobot 项目根计入模块别名；只收 AST 中的直接导入。
    modules = {}
    for rel in meta["source_hashes"]:
        module = rel[:-3].replace("/", ".")
        if module.endswith(".__init__"):
            module = module[:-9]
        modules[module] = rel
        if module.startswith("nanobot.nanobot"):
            modules[module[len("nanobot."):]] = rel
    for rel in meta["source_hashes"]:
        module = rel[:-3].replace("/", ".")
        package = module.split(".")[:-1]
        if rel.endswith("/__init__.py"):
            package = module.split(".")[:-1]
        tree = ast.parse((probe.REPO / rel).read_bytes(), filename=rel)
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.Import):
                targets = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                target = (".".join(package[:len(package) - node.level + 1] + ([node.module] if node.module else []))
                          if node.level else node.module or "")
                targets = [target]
                if not node.module:
                    targets.extend(target + "." + a.name for a in node.names)
            for target in targets:
                if target in modules and modules[target] != rel:
                    reference.add((rel, modules[target]))
    results = []
    for name in RECEIPTS:
        path = probe.SCRATCH / name
        data = json.loads(path.read_text(encoding="utf-8"))
        if data["skeleton"]["source_hashes"] != meta["source_hashes"]:
            raise RuntimeError("input source changed; no inherited quality evidence")
        result = {"model": data["requested_model"], "receipt": str(path.relative_to(probe.ROOT)),
                  "http_status": data.get("http_status"), "exit_code": data["probe_exit_code"],
                  "total_seconds": data["total_seconds"], "request_seconds": data.get("elapsed_seconds"),
                  "ttft_seconds": data.get("ttft_seconds"), "done": data.get("done_received"),
                  "finish_reason": data.get("finish_reason"), "answer_bytes": data.get("answer_bytes", 0),
                  "stream_error": data.get("stream_error"), "prompt_sha256": data.get("prompt_sha256")}
        obj, method, errors = parse_answer(data.get("answer", ""))
        result.update(parse_method=method, parse_errors=errors)
        if obj is not None:
            dependencies, flows, unknowns = obj.get("dependencies"), obj.get("dataflows"), obj.get("unknowns")
            valid = (isinstance(obj.get("summary"), str) and isinstance(dependencies, list)
                     and isinstance(flows, list) and isinstance(unknowns, list)
                     and all(isinstance(edge, dict) and all(isinstance(edge.get(k), str) for k in ("from_file", "to_file"))
                             and isinstance(edge.get("evidence"), (str, dict)) for edge in dependencies)
                     and all(isinstance(flow, dict) and isinstance(flow.get("symbols"), list)
                             and all(isinstance(s, str) for s in flow["symbols"])
                             and isinstance(flow.get("description"), str) and isinstance(flow.get("certainty"), (str, dict)) for flow in flows)
                     and all(isinstance(u, str) for u in unknowns))
            result["field_types"] = {key: type(obj.get(key)).__name__ for key in ("summary", "dependencies", "dataflows", "unknowns")}
            result["evidence_object_count"] = sum(isinstance(e.get("evidence"), dict) for e in dependencies if isinstance(e, dict)) if isinstance(dependencies, list) else None
            result["required_structure_valid"] = valid
            if valid:
                def evidence_tag(edge):
                    value = edge["evidence"]
                    return str(value.get("type", "")) if isinstance(value, dict) else value
                imports = {(edge["from_file"], edge["to_file"]) for edge in dependencies if evidence_tag(edge).strip().lower().startswith("import")}
                matched = imports & reference
                raw_symbols = [s for flow in flows for s in flow["symbols"]]
                refs, unsupported = normalize_symbols(raw_symbols, symbols)
                qualified_lookup = {}
                for ref in refs - symbols:
                    path_name, symbol_name = ref.split(":", 1)
                    candidates = sorted(s for s in symbols if s.startswith(path_name + ":")
                                        and s.split(":", 1)[1].endswith("." + symbol_name))
                    if len(candidates) == 1:
                        qualified_lookup[ref] = candidates[0]
                result["quality"] = {
                    "dependency_items": len(dependencies), "within_dependency_budget": len(dependencies) <= 40,
                    "import_claims": len(imports), "confirmed_imports": len(matched),
                    "unconfirmed_imports": sorted(imports - reference),
                    "import_match_fraction": len(matched) / len(imports) if imports else None,
                    "reference_edges": len(reference), "reference_coverage": len(matched) / len(reference),
                    "flow_items": len(flows), "normalized_symbol_refs": len(refs),
                    "located_definition_refs": len(refs & symbols), "unlocated_definition_refs": sorted(refs - symbols),
                    "unsupported_symbol_notation": unsupported,
                    "unique_class_qualification_lookup": qualified_lookup,
                    "limitations": "definition existence and import matching are not semantic call-chain accuracy; grouped symbols normalized without JSON repair; field references need separate review",
                }
                result["summary_excerpt"] = obj["summary"][:1100]
                result["flow_review"] = [{"symbols": flow["symbols"], "description": flow["description"][:850], "certainty": flow["certainty"] if isinstance(flow["certainty"], dict) else flow["certainty"][:350]} for flow in flows]
                result["unknowns_review"] = [u[:350] for u in unknowns]
        else:
            answer = data.get("answer", "")
            result["answer_head"] = answer[:1500]
            result["answer_tail"] = answer[-1000:]
        if "--summary" in sys.argv:
            result.pop("flow_review", None)
            result.pop("unknowns_review", None)
        results.append(result)
    print(json.dumps({"offline_only": True, "sources_match": True,
                      "normalization": "strip path/symbol whitespace and split slash-grouped symbols; no invented definitions, JSON repair or network calls",
                      "review_seconds": round(time.monotonic() - began, 4), "models": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
