"""检查生命周期验收矩阵的结构和覆盖范围，不模拟 Roo 运行时通过。"""
import unittest

from test_contracts import ROOT, contracts


class LifecycleCaseContracts(unittest.TestCase):
    def test_case_matrix_is_complete_and_explicitly_unverified(self):
        path = ROOT / "tests/roo_contracts/lifecycle-cases.yaml"
        data = contracts.load_yaml(path.read_text(encoding="utf-8"))
        self.assertEqual(data.get("schema_version"), 1)
        self.assertEqual(data.get("runtime_verification_status"), "NOT_VERIFIED")
        cases = data.get("cases")
        self.assertIsInstance(cases, list)
        required = {
            "explicit_over_unrelated_pending", "explicit_missing",
            "pending_missing_idle", "matching_active_plan",
            "unrelated_active_plan", "multiple_archives", "suspended_resume",
            "read_only_audit", "distinguish_input_errors", "analyst_permissions",
            "verification_failure", "plan_changed_externally",
            "archive_collision_or_failure", "project_mode_override",
        }
        identifiers = []
        for case in cases:
            self.assertIsInstance(case, dict)
            for field in ("id", "input", "evidence_required"):
                self.assertIsInstance(case.get(field), str)
                self.assertTrue(case[field].strip())
            identifiers.append(case["id"])
            with self.subTest(case=case["id"]):
                self.assertIsInstance(case.get("expected"), list)
                self.assertGreaterEqual(len(case["expected"]), 2)
                for assertion in case["expected"]:
                    self.assertIsInstance(assertion, str)
                    self.assertTrue(assertion.strip())
        self.assertEqual(len(identifiers), len(set(identifiers)))
        self.assertTrue(required.issubset(set(identifiers)))


if __name__ == "__main__":
    unittest.main()
