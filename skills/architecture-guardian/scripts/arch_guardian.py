#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architecture Guardian CLI
A zero-dependency tooling script to maintain living architecture documentation,
module matrices, and feature synchronization in engineering projects.
"""

import argparse
import datetime
import os
from pathlib import Path
import re
import sys
from typing import List, Optional, Tuple


def get_current_date() -> str:
    """Return ISO format date string."""
    return datetime.date.today().strftime("%Y-%m-%d")


def find_template_dir() -> Path:
    """Locate the templates directory relative to this script."""
    script_dir = Path(__file__).resolve().parent
    template_dir = script_dir.parent / "resources" / "templates"
    if template_dir.exists():
        return template_dir
    # Fallback to local workspace relative path if moved
    cwd_tpl = Path.cwd() / "skills" / "architecture-guardian" / "resources" / "templates"
    if cwd_tpl.exists():
        return cwd_tpl
    raise FileNotFoundError(f"Template directory not found at {template_dir}")


def read_template(filename: str) -> str:
    """Read template content by filename."""
    tpl_path = find_template_dir() / filename
    if not tpl_path.exists():
        raise FileNotFoundError(f"Required template not found: {tpl_path}")
    return tpl_path.read_text(encoding="utf-8")


def get_architecture_root(workspace: Path) -> Path:
    """Resolve the architecture docs directory."""
    return workspace / "docs" / "architecture"


def init_architecture(
    workspace: Path,
    project_name: Optional[str] = None,
    description: Optional[str] = None,
    force: bool = False,
) -> int:
    """Initialize standard architecture directory skeleton."""
    arch_root = get_architecture_root(workspace)
    modules_dir = arch_root / "modules"
    decisions_dir = arch_root / "decisions"
    index_file = arch_root / "ARCHITECTURE.md"

    if index_file.exists() and not force:
        print(f"[WARN] Architecture blueprint already exists at: {index_file}")
        print("Use --force to overwrite index file if necessary.")
        return 0

    arch_root.mkdir(parents=True, exist_ok=True)
    modules_dir.mkdir(parents=True, exist_ok=True)
    decisions_dir.mkdir(parents=True, exist_ok=True)

    p_name = project_name or workspace.name or "Engineering Project"
    p_desc = description or "致力于构建高内聚、低耦合、可持续演进的工业级软件系统。"

    template_content = read_template("ARCHITECTURE.template.md")
    content = (
        template_content.replace("{{PROJECT_NAME}}", p_name)
        .replace("{{PROJECT_DESCRIPTION}}", p_desc)
        .replace("{{CURRENT_DATE}}", get_current_date())
        .replace("{{RUNTIME_ENV}}", "Standard Runtime")
        .replace("{{FRAMEWORK}}", "Enterprise Framework")
        .replace("{{DATABASE}}", "SQL / NoSQL Database")
        .replace("{{CACHE_MQ}}", "Redis / Message Queue")
    )

    index_file.write_text(content, encoding="utf-8")
    print(f"[OK] Initialized architecture documentation at: {arch_root}")
    print(f"     Main Index: {index_file}")
    print(f"     Modules Directory: {modules_dir}")
    print(f"     Decisions Directory: {decisions_dir}")

    # Ensure GEMINI.md living architecture guardrail rule in workspace root
    gemini_rule_file = workspace / "GEMINI.md"
    gemini_tpl = read_template("GEMINI.template.md")
    if not gemini_rule_file.exists():
        gemini_rule_file.write_text(gemini_tpl, encoding="utf-8")
        print(f"     Project Guardrail Rule: {gemini_rule_file}")
    else:
        existing_text = gemini_rule_file.read_text(encoding="utf-8")
        if "Living Architecture Guardrail" not in existing_text:
            gemini_rule_file.write_text(existing_text.rstrip() + "\n\n" + gemini_tpl, encoding="utf-8")
            print(f"     Appended Living Architecture Guardrail to existing {gemini_rule_file}")

    return 0


def add_module(
    workspace: Path,
    name: str,
    title: str,
    domain: Optional[str] = None,
    description: Optional[str] = None,
) -> int:
    """Create a new business module documentation and register in the main index."""
    if not re.match(r"^[a-zA-Z0-9_\-]+$", name):
        print(f"[ERROR] Invalid module name '{name}'. Only alphanumeric, '_' and '-' allowed.")
        return 1

    arch_root = get_architecture_root(workspace)
    index_file = arch_root / "ARCHITECTURE.md"
    if not index_file.exists():
        print(f"[ERROR] ARCHITECTURE.md not found. Please run 'init' first.")
        return 1

    module_dir = arch_root / "modules" / name
    module_readme = module_dir / "README.md"
    if module_readme.exists():
        print(f"[ERROR] Module '{name}' already exists at {module_readme}")
        return 1

    module_dir.mkdir(parents=True, exist_ok=True)
    m_domain = domain or "核心业务域"
    m_desc = description or f"负责 {title} 相关的业务规则、流程流转及对外接口服务。"
    today = get_current_date()

    tpl = read_template("MODULE.template.md")
    content = (
        tpl.replace("{{MODULE_NAME}}", name)
        .replace("{{MODULE_TITLE}}", title)
        .replace("{{MODULE_DOMAIN}}", m_domain)
        .replace("{{MODULE_DESCRIPTION}}", m_desc)
        .replace("{{CURRENT_DATE}}", today)
    )

    module_readme.write_text(content, encoding="utf-8")
    print(f"[OK] Created module documentation: {module_readme}")

    # Register in ARCHITECTURE.md table
    index_text = index_file.read_text(encoding="utf-8")
    start_tag = "<!-- MODULE_TABLE_START -->"
    end_tag = "<!-- MODULE_TABLE_END -->"
    table_pattern = rf"({re.escape(start_tag)}.*?)(\n{re.escape(end_tag)})"

    rel_link = f"[modules/{name}/README.md](modules/{name}/README.md)"
    new_row = f"| **{title}** (`{name}`) | {m_desc} | {rel_link} | {today} |"

    if re.search(table_pattern, index_text, re.DOTALL):
        updated_index = re.sub(
            table_pattern,
            rf"\1\n{new_row}\2",
            index_text,
            flags=re.DOTALL,
        )
        # Update change stream
        log_start = "<!-- CHANGE_LOG_START -->"
        log_entry = f"- `{today}`: 新增业务模块 [**{title}** (`{name}`)](modules/{name}/README.md)。"
        updated_index = updated_index.replace(log_start, f"{log_start}\n{log_entry}")

        index_file.write_text(updated_index, encoding="utf-8")
        print(f"[OK] Registered module '{name}' in main index: {index_file}")
        return 0
    else:
        print(f"[WARN] Table tags not found in ARCHITECTURE.md, unable to auto-register table row.")
        return 0


def sync_feature(
    workspace: Path,
    module: str,
    title: str,
    description: str,
    code_ref: Optional[str] = None,
) -> int:
    """Append a business feature to the module documentation and update index log."""
    arch_root = get_architecture_root(workspace)
    index_file = arch_root / "ARCHITECTURE.md"
    module_readme = arch_root / "modules" / module / "README.md"

    if not module_readme.exists():
        print(f"[ERROR] Module '{module}' does not exist at {module_readme}")
        return 1

    today = get_current_date()
    mod_text = module_readme.read_text(encoding="utf-8")

    # Format feature entry
    ref_info = f"- **核心入口/代码关联**: `{code_ref}`\n" if code_ref else ""
    feature_entry = (
        f"### {title}\n"
        f"- **实现时间**: {today}\n"
        f"- **业务功能概述**: {description}\n"
        f"{ref_info}"
    )

    feat_start = "<!-- FEATURE_LIST_START -->"
    feat_end = "<!-- FEATURE_LIST_END -->"
    feat_pattern = rf"({re.escape(feat_start)}.*?)(\n{re.escape(feat_end)})"

    if re.search(feat_pattern, mod_text, re.DOTALL):
        mod_text = re.sub(
            feat_pattern,
            rf"\1\n{feature_entry}\2",
            mod_text,
            flags=re.DOTALL,
        )
    else:
        # Fallback append to section 3
        mod_text += f"\n\n{feature_entry}\n"

    # Append to module changelog
    m_log_start = "<!-- MODULE_CHANGELOG_START -->"
    m_log_entry = f"- `{today}`: 实现业务功能点【{title}】。"
    if m_log_start in mod_text:
        mod_text = mod_text.replace(m_log_start, f"{m_log_start}\n{m_log_entry}")

    module_readme.write_text(mod_text, encoding="utf-8")
    print(f"[OK] Synchronized feature '{title}' to {module_readme}")

    # Synchronize to main index changelog
    if index_file.exists():
        idx_text = index_file.read_text(encoding="utf-8")
        idx_log_start = "<!-- CHANGE_LOG_START -->"
        idx_log_entry = (
            f"- `{today}`: 业务模块 [`{module}`](modules/{module}/README.md) "
            f"新增功能特性【**{title}**】: {description}"
        )
        if idx_log_start in idx_text:
            idx_text = idx_text.replace(idx_log_start, f"{idx_log_start}\n{idx_log_entry}")
            index_file.write_text(idx_text, encoding="utf-8")
            print(f"[OK] Synchronized change stream to {index_file}")

    return 0


def add_adr(
    workspace: Path,
    adr_id: str,
    title: str,
) -> int:
    """Create an Architecture Decision Record (ADR) and register in main index."""
    arch_root = get_architecture_root(workspace)
    index_file = arch_root / "ARCHITECTURE.md"
    decisions_dir = arch_root / "decisions"

    if not index_file.exists():
        print(f"[ERROR] ARCHITECTURE.md not found. Please run 'init' first.")
        return 1

    decisions_dir.mkdir(parents=True, exist_ok=True)
    safe_slug = re.sub(r"[^a-zA-Z0-9_\-]+", "-", title.lower()).strip("-")
    filename = f"{adr_id}-{safe_slug}.md"
    target_file = decisions_dir / filename

    if target_file.exists():
        print(f"[ERROR] ADR file already exists: {target_file}")
        return 1

    today = get_current_date()
    tpl = read_template("ADR.template.md")
    content = (
        tpl.replace("{{ADR_ID}}", adr_id)
        .replace("{{ADR_TITLE}}", title)
        .replace("{{CURRENT_DATE}}", today)
    )

    target_file.write_text(content, encoding="utf-8")
    print(f"[OK] Created ADR file: {target_file}")

    # Register in ARCHITECTURE.md
    idx_text = index_file.read_text(encoding="utf-8")
    adr_start = "<!-- ADR_LIST_START -->"
    rel_link = f"- [ADR-{adr_id}: {title}](decisions/{filename})"

    if adr_start in idx_text:
        idx_text = idx_text.replace("- [暂无决策记录]\n", "")
        idx_text = idx_text.replace("- [暂无决策记录]", "")
        idx_text = idx_text.replace(adr_start, f"{adr_start}\n{rel_link}")
        index_file.write_text(idx_text, encoding="utf-8")
        print(f"[OK] Registered ADR in {index_file}")

    return 0


def verify_architecture(workspace: Path) -> int:
    """Verify integrity of architecture documentation, broken links, and missing modules."""
    arch_root = get_architecture_root(workspace)
    index_file = arch_root / "ARCHITECTURE.md"
    modules_dir = arch_root / "modules"

    errors: List[str] = []
    warnings: List[str] = []

    if not index_file.exists():
        errors.append(f"Missing master index file at {index_file}")
        print("\n".join(f"[ERROR] {e}" for e in errors))
        return 1

    index_text = index_file.read_text(encoding="utf-8")

    # 1. Check all modules on disk are registered
    actual_modules = set()
    if modules_dir.exists():
        for item in modules_dir.iterdir():
            if item.is_dir():
                actual_modules.add(item.name)
                readme = item / "README.md"
                if not readme.exists():
                    errors.append(f"Module directory '{item.name}' lacks a README.md")

    # 2. Check registered module links in index
    registered_modules = set()
    link_pattern = r"\[modules/([a-zA-Z0-9_\-]+)/README\.md\]"
    matches = re.findall(link_pattern, index_text)
    for mod_name in matches:
        registered_modules.add(mod_name)
        target_readme = modules_dir / mod_name / "README.md"
        if not target_readme.exists():
            errors.append(f"Broken link in ARCHITECTURE.md: module '{mod_name}' not found on disk")

    unregistered = actual_modules - registered_modules
    for u in unregistered:
        warnings.append(f"Module '{u}' exists on disk but is not registered in ARCHITECTURE.md")

    # 3. Report findings
    if warnings:
        for w in warnings:
            print(f"[WARN] {w}")
    if errors:
        for e in errors:
            print(f"[ERROR] {e}")
        print(f"\nVerification FAILED with {len(errors)} error(s).")
        return 1

    print(f"[OK] Verification PASSED. {len(actual_modules)} module(s) verified with 0 broken links.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build command line interface parser."""
    parser = argparse.ArgumentParser(
        description="Architecture Guardian: Living documentation and feature sync CLI."
    )
    parser.add_argument(
        "--workspace",
        "-w",
        default=".",
        help="Target workspace root path (default: current directory).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: init
    init_parser = subparsers.add_parser("init", help="Initialize architecture documentation.")
    init_parser.add_argument("--name", "-n", help="Project name.")
    init_parser.add_argument("--desc", "-d", help="Project description.")
    init_parser.add_argument("--force", "-f", action="store_true", help="Force overwrite index.")

    # Subcommand: new-module
    mod_parser = subparsers.add_parser("new-module", help="Create and register a business module.")
    mod_parser.add_argument("name", help="Directory name for the module (e.g., auth, order).")
    mod_parser.add_argument("--title", "-t", required=True, help="Display title of the module.")
    mod_parser.add_argument("--domain", help="Business domain classification.")
    mod_parser.add_argument("--desc", "-d", help="Module scope description.")

    # Subcommand: sync-feature
    sync_parser = subparsers.add_parser("sync-feature", help="Append feature to module and index.")
    sync_parser.add_argument("module", help="Module directory name.")
    sync_parser.add_argument("--title", "-t", required=True, help="Feature name/title.")
    sync_parser.add_argument("--desc", "-d", required=True, help="Detailed feature description.")
    sync_parser.add_argument("--code-ref", "-c", help="Reference to main code class/function.")

    # Subcommand: add-adr
    adr_parser = subparsers.add_parser("add-adr", help="Add an Architecture Decision Record.")
    adr_parser.add_argument("id", help="ADR identifier (e.g., 0001, 0002).")
    adr_parser.add_argument("--title", "-t", required=True, help="Decision title.")

    # Subcommand: verify
    subparsers.add_parser("verify", help="Verify links and documentation integrity.")

    return parser


def main() -> int:
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()

    if args.command == "init":
        return init_architecture(
            workspace=workspace,
            project_name=args.name,
            description=args.desc,
            force=args.force,
        )
    elif args.command == "new-module":
        return add_module(
            workspace=workspace,
            name=args.name,
            title=args.title,
            domain=args.domain,
            description=args.desc,
        )
    elif args.command == "sync-feature":
        return sync_feature(
            workspace=workspace,
            module=args.module,
            title=args.title,
            description=args.desc,
            code_ref=args.code_ref,
        )
    elif args.command == "add-adr":
        return add_adr(
            workspace=workspace,
            adr_id=args.id,
            title=args.title,
        )
    elif args.command == "verify":
        return verify_architecture(workspace=workspace)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
