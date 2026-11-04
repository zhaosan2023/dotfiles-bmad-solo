"""新单焦点入口与旧计划兼容的静态回归；不执行任务命令或认证门禁。"""
import copy
import unittest

import test_contracts as fixtures

contracts = fixtures.contracts


class ActiveTaskContracts(unittest.TestCase):
    setUp = fixtures.RepositoryContracts.setUp
    write_plan = fixtures.RepositoryContracts.write_plan
    run_cli = fixtures.RepositoryContracts.run_cli

    def pointer(self, identifier=None, **changes):
        data = {
            "schema_version": "1.0-draft",
            "active_task_id": identifier,
            "instance_id": None,
            "task_ref": f"specs/tasks/TU-{identifier}.md" if identifier else None,
            "contract_version": "1" if identifier else None,
            "authority_ref": None,
        }
        data.update(changes)
        return self.write_plan(contracts.ACTIVE_TASK, data)

    def task_data(self):
        return {
            "task_id": "DEMO-001", "instance_id": None,
            "contract_version": "1", "status": "BLOCKED", "session_id": None,
            "parent_objective": {"objective_id": "CUSTOMER-001"},
            "inputs": [],
            "cs_specification": {"scope": "仅隔离夹具"},
            "kcp_verification": {"checks": [{
                "check_id": "KCP-01", "required": True,
                "command_status": "UNAVAILABLE", "command": None,
            }]},
            "sod_review": {"supervisor_actor": None},
            "gate_status": {"cs": "UNKNOWN", "sr": "UNKNOWN", "accepted": False},
            "authorization": {"source_ref": None, "allowed_operations": []},
        }

    def task(self, **changes):
        data = self.task_data()
        data.update(changes)
        return self.write_plan("specs/tasks/TU-DEMO-001.md", data)

    def test_idle_new_pointer_does_not_read_corrupt_legacy_plan(self):
        legacy = self.write_plan(contracts.DEFAULT_PLAN)
        legacy.write_bytes(b"corrupt legacy plan\n")
        pointer = self.pointer()
        before = (legacy.read_bytes(), pointer.read_bytes())
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("明确空闲", result.stdout)
        self.assertIn("未读取旧默认计划", result.stdout)
        self.assertEqual((legacy.read_bytes(), pointer.read_bytes()), before)

    def test_explicit_plan_skips_corrupt_new_pointer(self):
        pointer = self.pointer()
        pointer.write_bytes(b"corrupt pointer\n")
        self.write_plan("selected.md")
        result = self.run_cli("--plan", "selected.md")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(pointer.read_bytes(), b"corrupt pointer\n")

    def test_missing_explicit_does_not_select_valid_active_task(self):
        self.task()
        self.pointer("DEMO-001")
        result = self.run_cli("--plan", "missing.md")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Task Unit 静态形状检查完成", result.stdout)

    def test_matching_active_task_is_checked_without_running_commands(self):
        marker = self.root / "must-not-exist"
        data = self.task_data()
        data["kcp_verification"]["checks"][0].update(
            command_status="AVAILABLE", command=f"touch {marker}",
        )
        task = self.write_plan("specs/tasks/TU-DEMO-001.md", data)
        self.pointer("DEMO-001")
        before = task.read_bytes()
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("未认证授权、CS/SR", result.stdout)
        self.assertFalse(marker.exists())
        self.assertEqual(task.read_bytes(), before)

    def test_explicit_task_skips_unrelated_pointer(self):
        self.task()
        pointer = self.pointer("OTHER")
        before = pointer.read_bytes()
        result = self.run_cli("--plan", "specs/tasks/TU-DEMO-001.md")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(pointer.read_bytes(), before)

    def test_new_pointer_missing_task_does_not_fall_back(self):
        self.write_plan(contracts.DEFAULT_PLAN)
        self.pointer("DEMO-001")
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("仅兼容检查旧默认计划", result.stdout)

    def test_idle_pointer_with_residual_binding_is_rejected(self):
        self.pointer(task_ref="specs/tasks/TU-DEMO-001.md")
        self.assertNotEqual(self.run_cli().returncode, 0)

    def test_identity_version_reference_and_instance_mismatch_are_rejected(self):
        self.task()
        for changes in (
            {"contract_version": "2"}, {"instance_id": "different-instance"},
            {"task_ref": "specs/tasks/TU-OTHER.md"},
            {"task_ref": "../outside.md"}, {"active_task_id": "../outside"},
        ):
            self.pointer("DEMO-001", **changes)
            with self.subTest(changes=changes):
                self.assertNotEqual(self.run_cli().returncode, 0)

    def test_pointer_and_task_symlinks_are_rejected_without_legacy_fallback(self):
        self.write_plan(contracts.DEFAULT_PLAN)
        pointer = self.pointer()
        target = self.write_plan("idle-copy.md", {
            "active_task_id": None, "instance_id": None, "task_ref": None,
            "contract_version": None, "authority_ref": None,
        })
        pointer.unlink()
        pointer.symlink_to(target)
        self.assertNotEqual(self.run_cli().returncode, 0)
        pointer.unlink()
        self.pointer("DEMO-001")
        task = self.task()
        copy_path = self.write_plan("task-copy.md", self.task_data())
        task.unlink()
        task.symlink_to(copy_path)
        self.assertNotEqual(self.run_cli().returncode, 0)

    def test_mixed_identity_and_contradictory_gate_declarations_are_rejected(self):
        self.task(plan_id="mixed-plan")
        result = self.run_cli("--plan", "specs/tasks/TU-DEMO-001.md")
        self.assertNotEqual(result.returncode, 0)
        data = self.task_data()
        data["gate_status"]["accepted"] = True
        with self.assertRaises(contracts.ContractError):
            contracts.validate_task(data)

    def test_missing_fields_and_invalid_verification_shapes_are_rejected(self):
        for field in self.task_data():
            data = self.task_data()
            del data[field]
            with self.subTest(field=field), self.assertRaises(contracts.ContractError):
                contracts.validate_task(data)
        for checks in ([], [None], [{"check_id": "KCP-01", "required": "true"}],
                       [{"check_id": "KCP-01", "required": True,
                         "command_status": "AVAILABLE", "command": None}]):
            data = self.task_data()
            data["kcp_verification"]["checks"] = checks
            with self.subTest(checks=checks), self.assertRaises(contracts.ContractError):
                contracts.validate_task(data)
        data = self.task_data()
        data["kcp_verification"]["checks"].append(copy.deepcopy(
            data["kcp_verification"]["checks"][0],
        ))
        with self.assertRaises(contracts.ContractError):
            contracts.validate_task(data)

    def test_unhashable_enum_values_fail_closed_without_tracebacks(self):
        for value in ([], {}, ["UNKNOWN"]):
            for field in ("status", "command_status", "cs", "sr"):
                data = self.task_data()
                if field == "status":
                    data[field] = value
                elif field == "command_status":
                    data["kcp_verification"]["checks"][0][field] = value
                else:
                    data["gate_status"][field] = value
                with self.subTest(field=field, value=value):
                    with self.assertRaises(contracts.ContractError):
                        contracts.validate_task(data)
                    self.write_plan("specs/tasks/TU-DEMO-001.md", data)
                    result = self.run_cli("--plan", "specs/tasks/TU-DEMO-001.md")
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("FAIL", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertNotIn("PASS", result.stdout)

    def test_task_template_is_checked_but_cannot_be_selected_as_instantiated_task(self):
        path = self.root / contracts.TASK_TEMPLATE_PATH
        before = path.read_bytes()
        data = contracts.frontmatter(path.read_text(encoding="utf-8"))
        contracts.validate_task(data, template=True)
        with self.assertRaises(contracts.ContractError):
            contracts.validate_task(data)
        result = self.run_cli("--plan", contracts.TASK_TEMPLATE_PATH)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("任务标识未实例化", result.stderr)
        self.assertNotIn("PASS", result.stdout)
        self.assertEqual(path.read_bytes(), before)

    def test_task_template_cannot_claim_acceptance_or_available_commands(self):
        path = self.root / contracts.TASK_TEMPLATE_PATH
        original = contracts.frontmatter(path.read_text(encoding="utf-8"))
        variants = []
        data = copy.deepcopy(original)
        data["status"] = "READY"
        variants.append(data)
        data = copy.deepcopy(original)
        data["gate_status"].update(cs="PASS", sr="APPROVED", accepted=True)
        variants.append(data)
        data = copy.deepcopy(original)
        data["kcp_verification"]["checks"][0].update(
            command_status="AVAILABLE", command="must-not-run",
        )
        variants.append(data)
        for data in variants:
            with self.subTest(data=data), self.assertRaises(contracts.ContractError):
                contracts.validate_task(data, template=True)

    def test_missing_or_corrupt_task_template_blocks_static_repository_check(self):
        path = self.root / contracts.TASK_TEMPLATE_PATH
        before = path.read_bytes()
        path.unlink()
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("PASS", result.stdout)
        path.write_bytes(b"corrupt template\n")
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("PASS", result.stdout)
        self.assertEqual(path.read_bytes(), b"corrupt template\n")
        path.write_bytes(before)

    def test_direct_task_validation_rejects_mixed_identity(self):
        data = self.task_data()
        data["plan_id"] = "legacy-plan"
        with self.assertRaises(contracts.ContractError):
            contracts.validate_task(data)

    def test_absent_new_pointer_still_supports_explicit_legacy_compatibility(self):
        self.write_plan(contracts.DEFAULT_PLAN)
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("仅兼容检查旧默认计划", result.stdout)


if __name__ == "__main__":
    unittest.main()
