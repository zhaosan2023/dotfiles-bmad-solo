"""本轮授权的独立探针：不导入 FastCode、不安装、不修改生产配置。
控制器未证明覆盖本任务；JSON 回执不是任务账本或防篡改保证。
仅向现有网关发送无工具请求；CPU 预检仅访问获准 PyTorch CPU 索引。
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import http.client
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
from urllib.parse import urlsplit
import uuid

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT / "_bmad-output/scratch"
REPO = (ROOT / "../project/FastCode").resolve()
LIMIT = 2 * 1024 * 1024
SECRETS = []


class Blocked(Exception):
    pass


def alarm_handler(signum, frame):
    raise TimeoutError("deadline")


def sanitize(value):
    if isinstance(value, str):
        for secret in SECRETS:
            if secret:
                value = value.replace(secret, "[REDACTED]")
        value = re.sub(r"(?i)(bearer\s+)[^\s\"']+", r"\1[REDACTED]", value)
        return value
    if isinstance(value, dict):
        return {k: sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    return value


def gateway_config():
    directory = (ROOT / "../project/aurora2api/config").resolve()
    values, structure = {}, {}
    aliases = {
        "openai_api_key": "key", "api_key": "key", "apikey": "key",
        "gateway_api_key": "key", "auth_key": "key",
        "base_url": "base", "baseurl": "base", "openai_base_url": "base",
        "gateway_base_url": "base", "gateway_url": "base",
    }
    for path in sorted(directory.glob("*.json")):
        if path.is_symlink() or path.stat().st_size > 1024 * 1024:
            raise Blocked("gateway config symlink or size rejected")
        obj = json.loads(path.read_text(encoding="utf-8"))
        structure[path.name] = list(obj.keys()) if isinstance(obj, dict) else ["non-object"]
        def walk(node):
            if isinstance(node, dict):
                for name, value in node.items():
                    tag = aliases.get(name.lower())
                    if tag and isinstance(value, str) and value.strip():
                        values.setdefault(tag, set()).add(value.strip())
                        if tag == "key":
                            SECRETS.append(value.strip())
                    if isinstance(value, (dict, list)):
                        walk(value)
            elif isinstance(node, list):
                for item in node:
                    walk(item)
        walk(obj)
    return values, structure


def credentials():
    # 当前明确授权固定回环地址且不发送认证头；不读取或替换凭据。
    return None, urlsplit("http://127.0.0.1:8080/v1"), "/v1", "explicitly authorized loopback; no credentials loaded or sent"


def connection(parsed, seconds):
    cls = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    return cls(parsed.hostname, parsed.port, timeout=seconds)


def request(record, endpoint, payload=None, seconds=120, stream=False):
    key, parsed, prefix, source = credentials()
    record.update(credential_source=source, endpoint_path=prefix + endpoint, request_attempts=1,
                  timeout_seconds=seconds, redirects_followed=0, retries=0)
    started = time.monotonic()
    conn = connection(parsed, seconds)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        record["request_body_bytes"] = len(body or b"")
        record["authorization_header_sent"] = False
        conn.request("GET" if payload is None else "POST", prefix + endpoint, body=body, headers={
            "Content-Type": "application/json", "Accept": "text/event-stream" if stream else "application/json",
            "Connection": "close",
        })
        response = conn.getresponse()
        record.update(http_status=response.status, headers_seconds=round(time.monotonic()-started, 4),
                      content_type=response.getheader("Content-Type", ""), response_bytes=0)
        if response.status != 200:
            raw = response.read(8192)
            record["response_bytes"] = len(raw)
            record["http_error_body"] = raw.decode("utf-8", errors="replace")
            raise Blocked("authentication rejected" if response.status in {401, 403} else "HTTP non-200")
        if not stream:
            raw = response.read(LIMIT + 1)
            record["response_bytes"] = len(raw)
            if len(raw) > LIMIT:
                raise Blocked("response exceeds byte budget")
            return json.loads(raw)
        if response.getheader("Content-Type", "").split(";", 1)[0].strip().lower() != "text/event-stream":
            raw = response.read(8192)
            record["response_bytes"] = len(raw)
            record["unexpected_body"] = raw.decode("utf-8", errors="replace")
            raise Blocked("expected SSE")
        fragments, pending = [], []
        record.update(sse_events=0, done_received=False, finish_reason=None, ttft_seconds=None,
                      first_event_seconds=None, first_line_seconds=None, max_line_wait_seconds=0)
        stream_id = None
        last = time.monotonic()
        while True:
            line = response.readline(min(65537, LIMIT-record["response_bytes"]+1))
            now = time.monotonic()
            record["max_line_wait_seconds"] = max(record["max_line_wait_seconds"], round(now-last, 4))
            last = now
            record["response_bytes"] += len(line)
            if line and record["first_line_seconds"] is None:
                record["first_line_seconds"] = round(now-started, 4)
            if record["response_bytes"] > LIMIT:
                raise Blocked("SSE exceeds byte budget")
            if not line:
                record["premature_eof"] = True
                raise Blocked("EOF without DONE")
            if not line.endswith(b"\n"):
                raise Blocked("incomplete SSE line")
            line = line.rstrip(b"\r\n")
            if line:
                if line.startswith(b"data:"):
                    pending.append(line[5:].lstrip(b" "))
                continue
            if not pending:
                continue
            raw = b"\n".join(pending)
            pending.clear()
            record["sse_events"] += 1
            if record["first_event_seconds"] is None:
                record["first_event_seconds"] = round(now-started, 4)
            if raw == b"[DONE]":
                record["done_received"] = True
                text = "".join(fragments)
                record["answer"] = text
                record["answer_bytes"] = len(text.encode("utf-8"))
                if record["finish_reason"] != "stop" or not text.strip():
                    raise Blocked("DONE without nonempty normally-finished answer")
                return text
            event = json.loads(raw)
            if "error" in event:
                record["stream_error"] = event["error"]
                raise Blocked("SSE error event")
            current_id = event.get("id")
            if current_id:
                if stream_id and current_id != stream_id:
                    raise Blocked("stream identity changed")
                stream_id = current_id
            record["reported_model"] = event.get("model", record.get("reported_model"))
            if isinstance(event.get("usage"), dict):
                record["usage"] = event["usage"]
            for choice in event.get("choices", []):
                if choice.get("index", 0) != 0:
                    raise Blocked("multiple choices unexpected")
                delta = choice.get("delta", {})
                if delta.get("tool_calls") or delta.get("function_call"):
                    raise Blocked("unsolicited tool output; never execute")
                text = delta.get("content")
                if isinstance(text, str) and text:
                    if record["ttft_seconds"] is None:
                        record["ttft_seconds"] = round(now-started, 4)
                    fragments.append(text)
                    record["answer"] = "".join(fragments)
                reason = choice.get("finish_reason")
                if reason is not None:
                    record["finish_reason"] = reason
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        conn.close()
        record["elapsed_seconds"] = round(time.monotonic()-started, 4)
        record["connection_closed"] = True


def skeleton():
    started = time.monotonic()
    files = sorted(p for p in REPO.glob("*.py") if not p.is_symlink())
    skipped = []
    for directory in ("fastcode", "nanobot"):
        for parent, dirs, names in os.walk(REPO / directory, followlinks=False):
            dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in {"__pycache__", "node_modules"} and not (Path(parent)/d).is_symlink())
            for name in sorted(names):
                path = Path(parent)/name
                if name.endswith(".py"):
                    if path.is_symlink():
                        skipped.append(str(path.relative_to(REPO)))
                    else:
                        files.append(path)
    parts, modules, imported, source_hashes, symbol_count = [], {}, {}, {}, 0
    for path in sorted(files):
        rel = path.relative_to(REPO).as_posix()
        if path.stat().st_size > 1024*1024:
            skipped.append(rel+":size")
            continue
        raw = path.read_bytes()
        try:
            tree = ast.parse(raw, filename=rel)
        except (SyntaxError, UnicodeError):
            skipped.append(rel+":parse")
            continue
        source_hashes[rel] = hashlib.sha256(raw).hexdigest()
        module = rel[:-3].replace("/", ".")
        if module.endswith(".__init__"):
            module = module[:-9]
        modules[module] = rel
        imported[rel] = []
        parts.append("FILE " + rel)
        scope = []
        class Symbols(ast.NodeVisitor):
            def visit_ClassDef(self, node):
                nonlocal symbol_count
                bases = [ast.unparse(b) for b in node.bases if isinstance(b, (ast.Name, ast.Attribute))]
                parts.append(f"  L{node.lineno} class {'.'.join(scope+[node.name])}({','.join(bases)})")
                symbol_count += 1
                scope.append(node.name)
                self.generic_visit(node)
                scope.pop()
            def visit_FunctionDef(self, node):
                nonlocal symbol_count
                args = [a.arg for a in node.args.posonlyargs+node.args.args]
                if node.args.vararg:
                    args.append("*"+node.args.vararg.arg)
                args += [a.arg for a in node.args.kwonlyargs]
                if node.args.kwarg:
                    args.append("**"+node.args.kwarg.arg)
                parts.append(f"  L{node.lineno} def {'.'.join(scope+[node.name])}({','.join(args)})")
                symbol_count += 1
                scope.append(node.name)
                self.generic_visit(node)
                scope.pop()
            visit_AsyncFunctionDef = visit_FunctionDef
            def visit_Import(self, node):
                for alias in node.names:
                    parts.append(f"  L{node.lineno} import {alias.name}" + (" as "+alias.asname if alias.asname else ""))
                    imported[rel].append(alias.name)
            def visit_ImportFrom(self, node):
                names = ",".join(a.name+(" as "+a.asname if a.asname else "") for a in node.names)
                parts.append(f"  L{node.lineno} from {'.'*node.level}{node.module or ''} import {names}")
                if node.level:
                    package = module.split(".") if path.name == "__init__.py" else module.split(".")[:-1]
                    target = ".".join(package[:len(package)-node.level+1]+([node.module] if node.module else []))
                else:
                    target = node.module or ""
                imported[rel].append(target)
                if not node.module:
                    imported[rel].extend(target+"."+a.name for a in node.names)
        Symbols().visit(tree)
    edges = sorted({(rel, modules[target]) for rel, targets in imported.items() for target in targets if target in modules and modules[target] != rel})
    text = "\n".join(parts)
    if len(text.encode("utf-8")) > 240000:
        raise Blocked("skeleton exceeds input byte budget; no silent truncation")
    return text, {"files":len(source_hashes),"symbols":symbol_count,"skipped":skipped,
                  "utf8_bytes":len(text.encode("utf-8")),"characters":len(text),
                  "token_estimate_chars_div_4":round(len(text)/4),"token_estimate_not_actual":True,
                  "scan_seconds":round(time.monotonic()-started,4),"source_hashes":source_hashes,
                  "direct_import_edges":edges,"scope":"root *.py + fastcode/**/*.py + nanobot/**/*.py; no bodies/defaults/docs/config/credentials"}


def run_local(command, seconds):
    started = time.monotonic()
    env = dict(os.environ)
    for name in ("OPENAI_API_KEY", "BASE_URL", "OPENAI_BASE_URL"):
        env.pop(name, None)
    env.update(PIP_NO_INPUT="1", PIP_DISABLE_PIP_VERSION_CHECK="1")
    result = subprocess.run(["timeout", "--signal=TERM", "--kill-after=2s", str(seconds)+"s"]+command,
                            cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, env=env, timeout=seconds+5)
    return {"command":command,"cwd":".","exit_code":result.returncode,
            "elapsed_seconds":round(time.monotonic()-started,4),"output":result.stdout}


def inventory(record):
    record.update(cpu_count=os.cpu_count(), architecture=os.uname().machine,
                  credential_environment_present={k:bool(os.environ.get(k)) for k in ("OPENAI_API_KEY","BASE_URL")},
                  authorized_dotenv_exists=(REPO/".env").is_file())
    record["memory"] = [line for line in Path("/proc/meminfo").read_text().splitlines() if line.startswith(("MemTotal:","MemAvailable:"))]
    record["cpu_model"] = next((line.split(":",1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines() if line.startswith("model name")), "unknown")
    py = str(REPO/".venv/bin/python")
    record["venv"] = run_local([py,"-c","import sys,importlib.metadata as m; print(sys.version.split()[0]); x=sorted(d.metadata['Name'] for d in m.distributions()); print('distribution_count',len(x)); print(x)"], 5)
    record["venv_pip"] = run_local([py,"-m","pip","--version"],5)
    key, parsed, prefix, source = credentials()
    record["credential_source"] = source
    record["endpoint_validated_without_printing"] = True


def cpu_sizes(record, report):
    data = json.loads(report.read_text(encoding="utf-8"))
    sizes = []
    record["wheel_sizes"] = sizes
    started = time.monotonic()
    signal.setitimer(signal.ITIMER_REAL, 60)
    try:
        for item in data.get("install", []):
            url = urlsplit(item["download_info"]["url"])
            allowed = {"download.pytorch.org", "download-r2.pytorch.org", "files.pythonhosted.org"}
            if url.scheme != "https" or url.hostname not in allowed or url.username or url.password:
                raise Blocked("unrecognized report wheel host; no request sent")
            entry = {"name": item["metadata"]["name"], "version": item["metadata"]["version"], "wheel_bytes": None}
            sizes.append(entry)
            conn = connection(url, 5)
            try:
                conn.request("HEAD", url.path + ("?" + url.query if url.query else ""), headers={"Connection": "close"})
                response = conn.getresponse()
                entry["head_status"] = response.status
                length = response.getheader("Content-Length")
                if response.status == 200 and length and length.isdigit():
                    entry["wheel_bytes"] = int(length)
            except (OSError, http.client.HTTPException) as error:
                entry["error_type"] = type(error).__name__
            finally:
                conn.close()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        record["head_seconds"] = round(time.monotonic() - started, 4)
        record["known_total_wheel_bytes"] = sum(i["wheel_bytes"] or 0 for i in sizes)
        record["size_complete"] = bool(sizes) and all(i["wheel_bytes"] is not None for i in sizes)
        record["actual_install_performed"] = False
        record["pip_report"] = str(report.relative_to(ROOT))
        record["installation_time_estimate"] = "unknown; HEAD and dry-run do not measure installation or full FastCode footprint"
    if not record["size_complete"]:
        raise Blocked("wheel size evidence incomplete")


def cpu(record, receipt_stem):
    py = str(REPO/".venv/bin/python")
    pip = run_local([py,"-m","pip","--version"],5)
    record["venv_pip"] = pip
    runner = [py,"-m","pip","--isolated"]
    if pip["exit_code"] != 0:
        runner = [sys.executable,"-m","pip","--isolated","--python",py]
        record["pip_fallback"] = "existing system pip targets existing venv; no bootstrap or installation"
    report = SCRATCH/(receipt_stem+"-pip-report.json")
    args = runner + ["install","--dry-run","--ignore-installed","--no-cache-dir",
            "--disable-pip-version-check","--no-input","--progress-bar","off","--timeout","25","--retries","0",
            "--only-binary=:all:","--report",str(report),"torch","--index-url","https://download.pytorch.org/whl/cpu"]
    result = run_local(args,240)
    record["dry_run"] = result
    record["actual_install_performed"] = False
    if result["exit_code"] != 0:
        raise Blocked("CPU pip dry-run unsuccessful")
    cpu_sizes(record, report)


def gemini_audit(record, receipt, previous=None):
    if previous is None:
        previous = json.loads(receipt.read_text(encoding="utf-8"))
    meta = previous["skeleton"]
    changed, symbols = [], set()
    for rel, expected in meta["source_hashes"].items():
        path = REPO / rel
        if path.is_symlink() or not path.is_file():
            changed.append(rel)
            continue
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            changed.append(rel)
            continue
        scope = []
        class Definitions(ast.NodeVisitor):
            def visit_ClassDef(self, node):
                symbols.add(rel + ":" + ".".join(scope + [node.name]))
                scope.append(node.name)
                self.generic_visit(node)
                scope.pop()
            def visit_FunctionDef(self, node):
                symbols.add(rel + ":" + ".".join(scope + [node.name]))
                scope.append(node.name)
                self.generic_visit(node)
                scope.pop()
            visit_AsyncFunctionDef = visit_FunctionDef
        Definitions().visit(ast.parse(raw, filename=rel))
    record["source_versions_changed"] = changed
    if changed:
        raise Blocked("input source versions changed; no inherited quality score")
    clean = previous["answer"].strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
    answer = json.loads(clean)
    direct = set(tuple(edge) for edge in meta["direct_import_edges"])
    claims = answer.get("dependencies", [])
    imports = {(edge.get("from_file"), edge.get("to_file")) for edge in claims
               if isinstance(edge, dict) and str(edge.get("evidence", "")).strip().lower().startswith("import")}
    matched = imports & direct
    flow_symbols = {symbol for flow in answer.get("dataflows", []) for symbol in flow.get("symbols", []) if isinstance(symbol, str)}
    record["quality_audit"] = {
        "original_receipt": str(receipt.relative_to(ROOT)),
        "original_checker_issue": "exact equality with import missed evidence strings beginning import followed by explanation; original zero is not model accuracy",
        "dependency_items": len(claims), "claimed_import_edges": len(imports),
        "matched_direct_import_edges": len(matched), "unmatched_import_edges": sorted(imports - direct),
        "syntactic_import_precision": len(matched) / len(imports) if imports else None,
        "reference_direct_import_edges": len(direct),
        "reference_import_coverage": len(matched) / len(direct) if direct else None,
        "dataflow_items": len(answer.get("dataflows", [])),
        "unique_claimed_symbols": len(flow_symbols), "located_symbols": len(flow_symbols & symbols),
        "unlocated_symbols": sorted(flow_symbols - symbols),
        "unknowns_count": len(answer.get("unknowns", [])),
        "limitations": "one sample; subset import matching and symbol existence only; no measured dataflow/call-chain precision, runtime correctness, repeated latency or task-completion guarantee",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode",choices=["config","inventory","models","embedding","research","factcheck","skeleton","gemini","benchmark","gemini-audit","cpu","cpu-head"])
    parser.add_argument("--cpu-report")
    parser.add_argument("--gemini-receipt")
    parser.add_argument("--model", choices=["claude-sonnet-5.5", "gpt-6.1-sol", "gpt-6-sol", "deepseek-v4.1-flash", "qwen-3.8-max", "glm-5.3", "grok-4.7"])
    args = parser.parse_args()
    signal.signal(signal.SIGALRM,alarm_handler)
    signal.signal(signal.SIGTERM,alarm_handler)
    stem = "gateway_probe-"+args.mode+"-"+uuid.uuid4().hex
    record = {"probe":args.mode,"started_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
              "controller_coverage":"unproven; platform task record only","status":"BLOCKED",
              "production_changed":False,"automatic_retry":False}
    began = time.monotonic()
    try:
        if args.mode == "config":
            values, structure = gateway_config()
            record["config_top_level_keys"] = structure
            record["candidate_counts"] = {name: len(found) for name, found in values.items()}
            record["configured_credential_found"] = bool(values.get("key"))
            record["configured_endpoint_found"] = bool(values.get("base"))
        elif args.mode == "cpu-head":
            if not args.cpu_report:
                raise Blocked("existing CPU report path required")
            report = (ROOT / args.cpu_report).resolve()
            if report.parent != SCRATCH.resolve() or report.is_symlink() or not report.is_file():
                raise Blocked("CPU report must be existing scratch file")
            record["reused_existing_report"] = True
            cpu_sizes(record, report)
        elif args.mode == "gemini-audit":
            if not args.gemini_receipt:
                raise Blocked("existing Gemini receipt required")
            original = ROOT / args.gemini_receipt
            receipt = original.resolve()
            if original.is_symlink() or receipt.parent != SCRATCH.resolve() or not receipt.is_file():
                raise Blocked("Gemini receipt must be existing scratch file")
            gemini_audit(record, receipt)
        elif args.mode == "skeleton":
            text, meta = skeleton()
            record["skeleton"] = meta
        elif args.mode == "inventory":
            inventory(record)
        elif args.mode == "models":
            result = request(record,"/models")
            ids = [item["id"] for item in result.get("data",[]) if isinstance(item,dict) and isinstance(item.get("id"),str)]
            record["model_ids"] = ids
            record["targets_present"] = {k:k in ids for k in ("baseline:academic","baseline:factcheck","gemini-3.8-flash","text-embedding-3-small")}
            if not ids:
                raise Blocked("empty/invalid registry")
        elif args.mode == "embedding":
            result = request(record,"/embeddings",{"input":"def test(): pass","model":"text-embedding-3-small"})
            items = result.get("data",[])
            vector = items[0].get("embedding") if len(items)==1 and isinstance(items[0],dict) else None
            valid = isinstance(vector,list) and len(vector)>0 and all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in vector)
            record.update(vector_valid=valid,vector_dimension=len(vector) if isinstance(vector,list) else None,usage=result.get("usage"),reported_model=result.get("model"))
            if not valid:
                raise Blocked("no finite embedding vector")
        elif args.mode in {"research", "factcheck"}:
            model = "gpt-6-astra:academic" if args.mode == "research" else "baseline:factcheck"
            record["requested_model"] = model
            prompt = "请对开源项目 https://github.com/pallets/click 进行尽职架构拆解：检视其核心源码文件树，梳理命令解析入口到执行的函数跳转链，并给出具体文件与符号定位。请明确所查看的版本/提交与原始源码来源；区分实际查看源码、已有知识和推断，不得把 README 当作调用链证据。仅研究，不请求或输出可执行工具调用。"
            if args.mode == "factcheck":
                prompt = "请依据 https://github.com/pallets/click 当前可查看的具体源码版本核验这些待验证命题：Command.main 创建上下文后调用 invoke；Group.invoke 解析并选择子命令；Context.invoke 最终调用用户 callback。逐项判断并给出 src/click/core.py 的具体符号、源码证据与版本。无法访问源码请直说，不能用 README 或搜索摘要冒充已读源码。仅研究，不输出工具调用。"
            request(record,"/chat/completions",{"model":model,"messages":[{"role":"user","content":prompt}],"stream":True,"max_tokens":6000},280,True)
        elif args.mode in {"gemini", "benchmark"}:
            text, meta = skeleton()
            model = "gemini-3.8-flash"
            if args.mode == "benchmark":
                if not args.model:
                    raise Blocked("explicit authorized benchmark model required")
                model = args.model
                baseline_path = SCRATCH / "gateway_probe-gemini-8ba12d0609034815912f401b909636b0.json"
                baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
                if meta["source_hashes"] != baseline["skeleton"]["source_hashes"] or meta["utf8_bytes"] != baseline["skeleton"]["utf8_bytes"]:
                    raise Blocked("FastCode input changed from Gemini baseline; no request sent")
                record["benchmark_contract"] = {
                    "baseline_receipt": str(baseline_path.relative_to(ROOT)),
                    "input_source_versions_match": True,
                    "skeleton_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    "max_tokens": 6000, "stream": True, "deadline_seconds": 180,
                    "samples_per_model": 1, "execution": "serial; no automatic retries",
                    "comparison_limit": "Gemini is a historical single sample; no randomized order or provider-identity verification",
                }
            record["skeleton"] = meta
            record["requested_model"] = model
            prompt = "根据以下提取的代码符号骨架，梳理整个项目的模块依赖关系图与核心数据流向。输入只有文件、import、类和函数签名，不含函数体；不能声称已核验运行时调用或副作用。返回一个 JSON 对象：summary（中文），dependencies（至多40条，元素含from_file、to_file、evidence，文件用原样项目相对路径，evidence区分import或inference），dataflows（含symbols、description、certainty），unknowns。优先覆盖FastCode引擎、MCP、解析、索引、嵌入、向量库、检索、生成与缓存；不要输出工具调用。\n\n"+text
            record["prompt_sha256"] = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
            answer = request(record,"/chat/completions",{"model":model,"messages":[{"role":"user","content":prompt}],"stream":True,"max_tokens":6000},180,True)
            try:
                clean = answer.strip()
                if clean.startswith("```"):
                    clean = clean.split("\n",1)[1].rsplit("```",1)[0]
                obj = json.loads(clean)
                direct = set(tuple(e) for e in meta["direct_import_edges"])
                claimed = {(e.get("from_file"),e.get("to_file")) for e in obj.get("dependencies",[]) if isinstance(e, dict) and str(e.get("evidence", "")).strip().lower().startswith("import")}
                record["dependency_check"] = {"claimed_import_edges":len(claimed),"matched":len(claimed & direct),"unmatched":sorted(claimed-direct),
                                              "reference_direct_import_edges":len(direct),"reference_coverage":len(claimed & direct)/len(direct) if direct else None,
                                              "scope":"syntactic direct imports only; unmatched is not automatically false, dynamic/submodule resolution excluded; dataflow needs human source check"}
            except (ValueError,TypeError,AttributeError):
                record["dependency_check"] = {"status":"unstructured answer; manual source check required"}
            if args.mode == "benchmark":
                try:
                    gemini_audit(record, SCRATCH / (stem + ".json"), previous=record)
                    record["quality_status"] = "STRUCTURED_AUDIT_OBSERVED; semantic source review still required"
                except (ValueError, TypeError, AttributeError, KeyError, Blocked) as error:
                    record["quality_status"] = "BLOCKED"
                    record["quality_error_type"] = type(error).__name__
                    record["quality_error"] = str(error) if isinstance(error, Blocked) else "invalid structure; inspect saved answer"
        else:
            cpu(record,stem)
        record["status"] = "OBSERVED_OK"
    except Exception as error:
        record["error_type"] = type(error).__name__
        record["error"] = str(error) if isinstance(error,Blocked) else "details suppressed; inspect protocol/status/exit metrics"
        if isinstance(error,http.client.IncompleteRead):
            record["incomplete_read_partial_bytes"] = len(error.partial)
        record["status"] = "BLOCKED"
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        record["total_seconds"] = round(time.monotonic()-began,4)
        record["probe_exit_code"] = 0 if record["status"]=="OBSERVED_OK" else 2
        record = sanitize(record)
        path = SCRATCH/(stem+".json")
        fd = os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        with os.fdopen(fd,"w",encoding="utf-8") as file:
            json.dump(record,file,ensure_ascii=False,indent=2)
            file.write("\n")
        preview = {k:v for k,v in record.items() if k not in {"answer","http_error_body","unexpected_body","skeleton","dry_run","venv","venv_pip","model_ids"}}
        if "model_ids" in record:
            preview["model_count"] = len(record["model_ids"])
            preview["related_model_ids"] = [m for m in record["model_ids"] if any(s in m.lower() for s in ("baseline","academic","factcheck","gemini","embed"))][:60]
        if "skeleton" in record:
            preview["skeleton_summary"] = {k:v for k,v in record["skeleton"].items() if k not in {"source_hashes","direct_import_edges"}}
        for name in ("venv","venv_pip"):
            if name in record:
                preview[name] = record[name]
        if "dry_run" in record:
            preview["dry_run_summary"] = {k:v for k,v in record["dry_run"].items() if k!="output"}
            preview["dry_run_tail"] = record["dry_run"]["output"].splitlines()[-18:]
        preview["receipt"] = str(path.relative_to(ROOT))
        print(json.dumps(preview,ensure_ascii=False,indent=2))
    return record["probe_exit_code"]


if __name__ == "__main__":
    sys.exit(main())
