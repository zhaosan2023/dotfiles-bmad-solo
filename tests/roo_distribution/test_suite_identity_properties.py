"""V4 身份边界的有界确定性属性测试；不部署、不联网、不替代宿主验收。

只使用标准库。固定种子控制输入，不声称操作系统或完整 CLI 确定性。
每个反例是单个身份故障，失败报告含种子、场景、故障和实际输入。
现有 test_suite*.py CI 收集范围覆盖本文件。
"""
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import random
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from asset_safety import AssetError, Snapshot
from deployment_identity import PLUGIN_PREFIX, manifest_suite
from managed_files import ownership_record
from suite_versions import suite_spec


class Fault(Enum):
    NONE = "none"
    WRONG_SUITE = "wrong_suite"
    WRONG_VERSION = "wrong_version"
    WRONG_PATH = "wrong_path"
    WRONG_DIRECTORY = "wrong_directory"
    MISSING_FIELD = "missing_field"
    WRONG_SCHEMA_TYPE = "wrong_schema_type"
    DUPLICATE_JSON_KEY = "duplicate_json_key"
    CORRUPT_BYTES = "corrupt_bytes"
    MISSING_OBSERVED = "missing_observed"
    STALE_MANAGED_RECORD = "stale_managed_record"
    MISSING_IDENTITY_SOURCE = "missing_identity_source"
    MISSING_IDENTITY_MANAGED = "missing_identity_managed"


@dataclass(frozen=True)
class IdentityCase:
    seed: int
    retired: bool
    fault: Fault


class SuiteIdentityProperties(unittest.TestCase):
    @staticmethod
    def fixture(case):
        rng = random.Random(case.seed)
        version = "v5" if case.retired else "v4"
        directory = "bmralph-suite-v5" if case.retired else "bmad-suite-v4"
        identity = {
            "schema_version": 1, "suite_id": directory,
            "major_version": version, "source_path": directory,
        }
        entries = list(identity.items())
        rng.shuffle(entries)
        identity_bytes = json.dumps(dict(entries), ensure_ascii=False).encode()
        observed = {
            PLUGIN_PREFIX + "plugin.json": Snapshot(b'{"name":"bmad-suite"}', 0o600),
            PLUGIN_PREFIX + "suite.json": Snapshot(identity_bytes, 0o600),
        }
        sources = {
            relative: ownership_record(observed[PLUGIN_PREFIX + relative])
            for relative in ("plugin.json", "suite.json")
        }
        provenance = {
            "suite_id": directory, "major_version": version,
            "source_path": directory,
            "source_directory": "/fixture/" + directory,
            "source_kind": "worktree",
            "source_files": sources,
            "managed_files": {
                PLUGIN_PREFIX + relative: deepcopy(record)
                for relative, record in sources.items()
            },
        }
        fault = case.fault
        if fault == Fault.WRONG_SUITE:
            provenance["suite_id"] = "unknown-" + str(case.seed)
        elif fault == Fault.WRONG_VERSION:
            provenance["major_version"] = "v6"
        elif fault == Fault.WRONG_PATH:
            provenance["source_path"] = "other-suite"
        elif fault == Fault.WRONG_DIRECTORY:
            provenance["source_directory"] = "/fixture/other-suite"
        elif fault == Fault.MISSING_FIELD:
            del provenance[rng.choice(("suite_id", "major_version", "source_path"))]
        elif fault in (Fault.WRONG_SCHEMA_TYPE, Fault.DUPLICATE_JSON_KEY, Fault.CORRUPT_BYTES):
            if fault == Fault.WRONG_SCHEMA_TYPE:
                identity["schema_version"] = rng.choice((True, False, "1", 1.0, None, []))
                content = json.dumps(identity).encode()
            elif fault == Fault.DUPLICATE_JSON_KEY:
                content = identity_bytes[:-1] + b',"schema_version":1}'
            else:
                content = rng.choice((b"\xff", b"{", b"[]", b"null"))
            value = Snapshot(content, 0o600)
            observed[PLUGIN_PREFIX + "suite.json"] = value
            # 连摘要一起更新仍不能使非法身份合法；不是防篡改证明。
            record = ownership_record(value)
            provenance["source_files"]["suite.json"] = record
            provenance["managed_files"][PLUGIN_PREFIX + "suite.json"] = deepcopy(record)
        elif fault == Fault.MISSING_OBSERVED:
            del observed[PLUGIN_PREFIX + rng.choice(("plugin.json", "suite.json"))]
        elif fault == Fault.STALE_MANAGED_RECORD:
            provenance["managed_files"][PLUGIN_PREFIX + "suite.json"]["mode"] = 0o644
        elif fault == Fault.MISSING_IDENTITY_SOURCE:
            del provenance["source_files"]["suite.json"]
        elif fault == Fault.MISSING_IDENTITY_MANAGED:
            del provenance["managed_files"][PLUGIN_PREFIX + "suite.json"]
        return provenance, observed

    def check_case(self, case):
        provenance, observed = self.fixture(case)
        before = deepcopy((provenance, observed))
        try:
            if case.fault == Fault.NONE:
                result = manifest_suite(
                    provenance, observed, retired_from="v5" if case.retired else None,
                )
                expected = ("v5", "bmralph-suite-v5", "bmralph-suite-v5") if case.retired else (
                    "v4", "bmad-suite-v4", "bmad-suite-v4",
                )
                self.assertEqual((result.major_version, result.suite_id, result.source_path), expected)
            else:
                with self.assertRaises(AssetError):
                    manifest_suite(
                        provenance, observed, retired_from="v5" if case.retired else None,
                    )
            if case.retired:
                # 显式一次性退役的合法输入也绝不能通过普通 V4 入口。
                with self.assertRaises(AssetError):
                    manifest_suite(provenance, observed)
            self.assertEqual((provenance, observed), before, "身份解析修改了输入")
        except Exception as exc:
            self.fail(
                f"seed={case.seed} retired={case.retired} property=IDENTITY_FAIL_CLOSED "
                f"single_fault={case.fault.value} input={provenance!r} failure={exc!r}"
            )

    def test_generated_identity_faults_fail_closed_without_mutating_inputs(self):
        hits = {fault: 0 for fault in Fault}
        accepted = {False: 0, True: 0}
        for seed in range(1, 257):
            rng = random.Random(seed)
            # 每条固定种子都含合法分支，防止全部拒绝的虚真通过。
            for retired in (False, True):
                self.check_case(IdentityCase(seed, retired, Fault.NONE))
                accepted[retired] += 1
                hits[Fault.NONE] += 1
                fault = rng.choice(tuple(Fault)[1:])
                self.check_case(IdentityCase(seed, retired, fault))
                hits[fault] += 1
        self.assertTrue(all(count > 0 for count in hits.values()), hits)
        self.assertTrue(all(count > 0 for count in accepted.values()), accepted)
        print(f"IDENTITY_PROPERTIES seeds=256 cases=1024 fault_hits={hits!r} accepted={accepted!r}")

    def test_oracle_detects_accept_all_reject_all_and_input_mutation(self):
        def accept_all(provenance, observed, **kwargs):
            return suite_spec("v4")

        def reject_all(provenance, observed, **kwargs):
            raise AssetError("injected unconditional rejection")

        def mutate_input(provenance, observed, **kwargs):
            provenance["injected_mutation"] = True
            return suite_spec("v4")

        cases = (
            (accept_all, Fault.MISSING_IDENTITY_SOURCE, "AssetError not raised"),
            (reject_all, Fault.NONE, "injected unconditional rejection"),
            (mutate_input, Fault.NONE, "身份解析修改了输入"),
        )
        for mutant, fault, expected in cases:
            with self.subTest(mutant=mutant.__name__), mock.patch.object(
                sys.modules[__name__], "manifest_suite", side_effect=mutant,
            ), self.assertRaisesRegex(AssertionError, expected):
                self.check_case(IdentityCase(19, False, fault))

    def test_same_seed_replays_identical_inputs(self):
        for seed in range(1, 33):
            for retired in (False, True):
                for fault in Fault:
                    case = IdentityCase(seed, retired, fault)
                    self.assertEqual(self.fixture(case), self.fixture(case), case)

    def test_legacy_v4_and_explicit_retirement_are_not_interchangeable(self):
        provenance, observed = self.fixture(IdentityCase(1, False, Fault.NONE))
        for field in ("suite_id", "major_version", "source_path"):
            del provenance[field]
        del provenance["source_files"]["suite.json"]
        del provenance["managed_files"][PLUGIN_PREFIX + "suite.json"]
        del observed[PLUGIN_PREFIX + "suite.json"]
        before = deepcopy((provenance, observed))
        self.assertEqual(manifest_suite(provenance, observed).major_version, "v4")
        with self.assertRaises(AssetError):
            manifest_suite(provenance, observed, retired_from="v5")
        self.assertEqual((provenance, observed), before)

    def test_generated_commit_names_have_exact_hex_contract(self):
        spec = suite_spec("v4")
        valid_hits = invalid_hits = 0
        alphabet = "0123456789abcdefABCDEFxyz/._- \n\x00"
        for seed in range(1, 513):
            rng = random.Random(seed)
            valid = "".join(rng.choice("0123456789abcdef") for _ in range(rng.choice((40, 64))))
            self.assertEqual(spec.cache_name(valid), "commit-" + valid, f"seed={seed}")
            valid_hits += 1
            candidate = "".join(rng.choice(alphabet) for _ in range(rng.choice((0, 1, 39, 40, 41, 63, 64, 65))))
            expected = len(candidate) in (40, 64) and all(c in "0123456789abcdef" for c in candidate)
            if expected:
                self.assertEqual(spec.cache_name(candidate), "commit-" + candidate)
            else:
                with self.assertRaises(AssetError, msg=f"seed={seed} candidate={candidate!r}"):
                    spec.cache_name(candidate)
                invalid_hits += 1
        for candidate in (None, True, 1, [], {}, b"a" * 40):
            with self.assertRaises(AssetError):
                spec.cache_name(candidate)
        self.assertGreater(valid_hits, 0)
        self.assertGreater(invalid_hits, 0)


if __name__ == "__main__":
    unittest.main()
