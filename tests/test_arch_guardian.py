#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automated Test Suite for Architecture Guardian
Covers unit tests, business integration workflows, and CLI execution.
Features strict teardown isolation to ensure zero test pollution.
"""

from pathlib import Path
import shutil
import sys
import tempfile
import unittest

# Ensure script under test can be imported
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "skills" / "architecture-guardian" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import arch_guardian  # noqa: E402


class TestArchitectureGuardian(unittest.TestCase):
    """Test suite for Architecture Guardian core functionality."""

    def setUp(self):
        """Create an isolated sandbox directory for each test."""
        self.test_dir = tempfile.mkdtemp(prefix="test_arch_guardian_")
        self.workspace = Path(self.test_dir).resolve()

    def tearDown(self):
        """Strict Teardown: Completely remove sandbox workspace and all artifacts."""
        if self.workspace.exists():
            shutil.rmtree(self.workspace, ignore_errors=True)

    def test_init_creates_skeleton(self):
        """Verify 'init' creates standard directories and valid main index."""
        exit_code = arch_guardian.init_architecture(
            workspace=self.workspace,
            project_name="DemoApp",
            description="Testing living architecture.",
        )
        self.assertEqual(exit_code, 0)

        arch_root = self.workspace / "docs" / "architecture"
        index_file = arch_root / "ARCHITECTURE.md"
        modules_dir = arch_root / "modules"
        decisions_dir = arch_root / "decisions"

        self.assertTrue(arch_root.exists(), "docs/architecture should exist")
        self.assertTrue(index_file.exists(), "ARCHITECTURE.md should exist")
        self.assertTrue(modules_dir.exists(), "modules directory should exist")
        self.assertTrue(decisions_dir.exists(), "decisions directory should exist")

        content = index_file.read_text(encoding="utf-8")
        self.assertIn("DemoApp", content)
        self.assertIn("Testing living architecture.", content)

        # Verify GEMINI.md project rule was created
        gemini_rule = self.workspace / "GEMINI.md"
        self.assertTrue(gemini_rule.exists(), "GEMINI.md rule should be created in workspace root")
        self.assertIn("Living Architecture Guardrail", gemini_rule.read_text(encoding="utf-8"))

    def test_init_gemini_rule_merge(self):
        """Verify 'init' safely appends to existing GEMINI.md without overwriting."""
        gemini_rule = self.workspace / "GEMINI.md"
        gemini_rule.write_text("# My Existing Custom Rules\nDo not delete me.", encoding="utf-8")

        code = arch_guardian.init_architecture(workspace=self.workspace, project_name="MergedApp")
        self.assertEqual(code, 0)

        rule_content = gemini_rule.read_text(encoding="utf-8")
        self.assertIn("# My Existing Custom Rules", rule_content)
        self.assertIn("Do not delete me.", rule_content)
        self.assertIn("Living Architecture Guardrail", rule_content)

    def test_init_idempotency(self):
        """Verify 'init' without --force does not overwrite existing file."""
        arch_guardian.init_architecture(workspace=self.workspace, project_name="InitialApp")
        index_file = self.workspace / "docs" / "architecture" / "ARCHITECTURE.md"
        index_file.write_text("CUSTOM_MODIFIED_CONTENT", encoding="utf-8")

        # Second init without force
        code = arch_guardian.init_architecture(workspace=self.workspace, project_name="NewApp")
        self.assertEqual(code, 0)
        self.assertEqual(index_file.read_text(encoding="utf-8"), "CUSTOM_MODIFIED_CONTENT")

    def test_new_module_and_index_registration(self):
        """Verify module creation and automatic table injection in main index."""
        arch_guardian.init_architecture(workspace=self.workspace, project_name="DemoApp")

        code = arch_guardian.add_module(
            workspace=self.workspace,
            name="auth",
            title="认证授权中心",
            domain="用户安全域",
            description="管理用户登录、Token签发与权限校验",
        )
        self.assertEqual(code, 0)

        module_readme = self.workspace / "docs" / "architecture" / "modules" / "auth" / "README.md"
        self.assertTrue(module_readme.exists())
        mod_content = module_readme.read_text(encoding="utf-8")
        self.assertIn("认证授权中心", mod_content)
        self.assertIn("auth", mod_content)
        self.assertIn("用户安全域", mod_content)

        # Check registration in main index
        index_file = self.workspace / "docs" / "architecture" / "ARCHITECTURE.md"
        idx_content = index_file.read_text(encoding="utf-8")
        self.assertIn("[modules/auth/README.md](modules/auth/README.md)", idx_content)
        self.assertIn("认证授权中心", idx_content)

    def test_invalid_module_name(self):
        """Verify rejection of invalid module names."""
        arch_guardian.init_architecture(workspace=self.workspace)
        code = arch_guardian.add_module(
            workspace=self.workspace,
            name="invalid name with spaces!@#",
            title="Bad Module",
        )
        self.assertEqual(code, 1)

    def test_sync_feature_lifecycle(self):
        """Verify feature synchronization into module doc and main index changelog."""
        arch_guardian.init_architecture(workspace=self.workspace)
        arch_guardian.add_module(
            workspace=self.workspace,
            name="order",
            title="订单结算中心",
        )

        code = arch_guardian.sync_feature(
            workspace=self.workspace,
            module="order",
            title="新增超时自动取消功能",
            description="基于延迟队列实现30分钟未支付订单自动关单并释放库存",
            code_ref="src/order/OrderAutoCancelService.java",
        )
        self.assertEqual(code, 0)

        # Inspect module doc
        module_readme = self.workspace / "docs" / "architecture" / "modules" / "order" / "README.md"
        mod_text = module_readme.read_text(encoding="utf-8")
        self.assertIn("新增超时自动取消功能", mod_text)
        self.assertIn("OrderAutoCancelService.java", mod_text)

        # Inspect master index changelog
        index_file = self.workspace / "docs" / "architecture" / "ARCHITECTURE.md"
        idx_text = index_file.read_text(encoding="utf-8")
        self.assertIn("新增功能特性【**新增超时自动取消功能**】", idx_text)

    def test_add_adr(self):
        """Verify ADR creation and linking."""
        arch_guardian.init_architecture(workspace=self.workspace)
        code = arch_guardian.add_adr(
            workspace=self.workspace,
            adr_id="0001",
            title="Use Redis Distributed Lock",
        )
        self.assertEqual(code, 0)

        adr_file = self.workspace / "docs" / "architecture" / "decisions" / "0001-use-redis-distributed-lock.md"
        self.assertTrue(adr_file.exists())
        self.assertIn("Use Redis Distributed Lock", adr_file.read_text(encoding="utf-8"))

        index_file = self.workspace / "docs" / "architecture" / "ARCHITECTURE.md"
        self.assertIn("ADR-0001", index_file.read_text(encoding="utf-8"))

    def test_verify_integrity(self):
        """Verify verification passes on valid state and fails on broken links."""
        arch_guardian.init_architecture(workspace=self.workspace)
        arch_guardian.add_module(workspace=self.workspace, name="payment", title="支付网关")

        # Clean state passes
        self.assertEqual(arch_guardian.verify_architecture(self.workspace), 0)

        # Introduce broken link: delete directory but keep index link
        payment_dir = self.workspace / "docs" / "architecture" / "modules" / "payment"
        shutil.rmtree(payment_dir)

        # Should fail with code 1
        self.assertEqual(arch_guardian.verify_architecture(self.workspace), 1)


if __name__ == "__main__":
    unittest.main()
