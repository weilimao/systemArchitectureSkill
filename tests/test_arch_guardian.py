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
import searcher  # noqa: E402


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

    def test_default_arch_root_when_no_config(self):
        """Verify default fallback to workspace/docs/architecture when no config exists."""
        expected = (self.workspace / "docs" / "architecture").resolve()
        self.assertEqual(arch_guardian.get_architecture_root(self.workspace), expected)

    def test_arch_root_from_config_file_relative_and_absolute(self):
        """Verify .arch-guardian.json relative and absolute path resolution."""
        # 1. Relative path
        cfg_file = self.workspace / ".arch-guardian.json"
        cfg_file.write_text('{"arch_dir": "../central-arch/docs/architecture"}', encoding="utf-8")
        expected_rel = (self.workspace / "../central-arch/docs/architecture").resolve()
        self.assertEqual(arch_guardian.get_architecture_root(self.workspace), expected_rel)

        # 2. Absolute path
        abs_target = (self.workspace / "custom_abs_arch").resolve()
        cfg_file.write_text(f'{{"arch_dir": "{str(abs_target).replace(chr(92), "/")}"}}', encoding="utf-8")
        self.assertEqual(arch_guardian.get_architecture_root(self.workspace), abs_target)

    def test_arch_root_cli_override(self):
        """Verify CLI --arch-dir overrides .arch-guardian.json."""
        cfg_file = self.workspace / ".arch-guardian.json"
        cfg_file.write_text('{"arch_dir": "docs/architecture/from_config"}', encoding="utf-8")
        cli_override = "docs/architecture/from_cli"
        expected = (self.workspace / cli_override).resolve()
        self.assertEqual(
            arch_guardian.get_architecture_root(self.workspace, custom_arch_dir=cli_override),
            expected,
        )

    def test_init_with_arch_dir_persists_config(self):
        """Verify 'init' with custom arch_dir persists config and initializes target."""
        shared_arch = self.workspace / "shared_central_arch"
        code = arch_guardian.init_architecture(
            workspace=self.workspace,
            project_name="SubService",
            arch_dir=str(shared_arch),
        )
        self.assertEqual(code, 0)

        # Verify config created in workspace
        cfg_file = self.workspace / ".arch-guardian.json"
        self.assertTrue(cfg_file.exists(), ".arch-guardian.json should be created")
        content = cfg_file.read_text(encoding="utf-8")
        self.assertIn("arch_dir", content)

        # Verify architecture initialized at shared_arch
        self.assertTrue((shared_arch / "ARCHITECTURE.md").exists())
        self.assertTrue((shared_arch / "modules").exists())

    def test_distributed_multi_project_sync_lifecycle(self):
        """Test distributed scenario: multiple microservices sharing one architecture repo."""
        shared_arch_dir = self.workspace / "central_arch_repo" / "docs" / "architecture"
        order_service_dir = self.workspace / "services" / "order-service"
        user_service_dir = self.workspace / "services" / "user-service"

        order_service_dir.mkdir(parents=True, exist_ok=True)
        user_service_dir.mkdir(parents=True, exist_ok=True)

        # 1. Initialize order-service pointing to shared_arch_dir
        code1 = arch_guardian.init_architecture(
            workspace=order_service_dir,
            project_name="CentralDistributedPlatform",
            arch_dir=str(shared_arch_dir),
        )
        self.assertEqual(code1, 0)
        self.assertTrue((order_service_dir / ".arch-guardian.json").exists())

        # 2. Initialize user-service pointing to the same shared_arch_dir
        code2 = arch_guardian.init_architecture(
            workspace=user_service_dir,
            project_name="CentralDistributedPlatform",
            arch_dir=str(shared_arch_dir),
        )
        self.assertEqual(code2, 0)
        self.assertTrue((user_service_dir / ".arch-guardian.json").exists())

        # 3. order-service adds module and feature
        self.assertEqual(
            arch_guardian.add_module(order_service_dir, name="order_mod", title="订单中心"),
            0,
        )
        self.assertEqual(
            arch_guardian.sync_feature(
                order_service_dir,
                module="order_mod",
                title="创建订单",
                description="订单创建与库存扣减",
            ),
            0,
        )

        # 4. user-service adds module and feature to the SAME central arch
        self.assertEqual(
            arch_guardian.add_module(user_service_dir, name="user_mod", title="用户中心"),
            0,
        )
        self.assertEqual(
            arch_guardian.sync_feature(
                user_service_dir,
                module="user_mod",
                title="JWT登录认证",
                description="支持多端Token验签",
            ),
            0,
        )

        # 5. Verify shared architecture index contains BOTH modules
        central_index = shared_arch_dir / "ARCHITECTURE.md"
        central_text = central_index.read_text(encoding="utf-8")
        self.assertIn("订单中心", central_text)
        self.assertIn("用户中心", central_text)
        self.assertIn("创建订单", central_text)
        self.assertIn("JWT登录认证", central_text)

        # 6. Verify integrity passes for both services
        self.assertEqual(arch_guardian.verify_architecture(order_service_dir), 0)
        self.assertEqual(arch_guardian.verify_architecture(user_service_dir), 0)

    def test_search_docs_finds_all_occurrences(self):
        """Verify search_docs finds all keyword occurrences across multiple docs."""
        arch_guardian.init_architecture(workspace=self.workspace, project_name="SearchApp")
        arch_guardian.add_module(self.workspace, name="order", title="订单中心")
        arch_guardian.add_module(self.workspace, name="payment", title="支付中心")

        arch_guardian.sync_feature(
            self.workspace,
            module="order",
            title="退款流转",
            description="调用 PaymentGateway.processRefund 执行资金原路退回",
            code_ref="OrderRefundService.java",
        )
        arch_guardian.add_adr(self.workspace, adr_id="0001", title="PaymentGateway 集成规范")

        arch_root = self.workspace / "docs" / "architecture"
        results = searcher.search_docs(arch_root, keywords=["PaymentGateway", "processRefund"])

        # Should match in ARCHITECTURE.md, modules/order/README.md, and decisions/0001-...
        matched_rel_paths = [r.rel_path for r in results]
        self.assertTrue(any("order" in p for p in matched_rel_paths), "Should find in order module")
        self.assertTrue(any("ARCHITECTURE.md" in p for p in matched_rel_paths), "Should find in ARCHITECTURE.md")
        self.assertTrue(any("decisions" in p for p in matched_rel_paths), "Should find in ADR")

        formatted_report = searcher.format_search_results(results, ["PaymentGateway"], arch_root)
        self.assertIn("架构文档全域检索结果", formatted_report)
        self.assertIn("PaymentGateway", formatted_report)

    def test_search_docs_distributed_pointer(self):
        """Verify search-docs correctly searches in shared central arch directory."""
        shared_arch = self.workspace / "central_docs"
        service_repo = self.workspace / "service_a"
        service_repo.mkdir(parents=True, exist_ok=True)

        arch_guardian.init_architecture(
            workspace=service_repo,
            project_name="CentralPlatform",
            arch_dir=str(shared_arch),
        )
        arch_guardian.add_module(service_repo, name="inventory", title="库存中心")

        # Command should route to shared_arch and return 0
        exit_code = arch_guardian.cmd_search_docs(
            workspace=service_repo,
            keywords=["库存中心"],
        )
        self.assertEqual(exit_code, 0)

    def test_search_docs_cli_parsing(self):
        """Verify search-docs subcommand parsing and execution."""
        arch_guardian.init_architecture(workspace=self.workspace, project_name="CliApp")
        parser = arch_guardian.build_parser()
        args = parser.parse_args(["--workspace", str(self.workspace), "search-docs", "CliApp", "--context", "2"])
        self.assertEqual(args.command, "search-docs")
        self.assertEqual(args.keywords, ["CliApp"])
        self.assertEqual(args.context, 2)
        code = arch_guardian.cmd_search_docs(self.workspace, keywords=args.keywords, context_lines=args.context)
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
