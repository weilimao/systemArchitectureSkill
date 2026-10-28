#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architecture Guardian CLI
A zero-dependency tooling script to maintain living architecture documentation,
module matrices, feature synchronization, and impact search in engineering projects.
"""

import argparse
import datetime
import json
import os
from pathlib import Path
import re
import sys
from typing import List, Optional

try:
    from searcher import format_search_results, search_docs
except ImportError:
    from .searcher import format_search_results, search_docs


def get_current_date() -> str:
    """Return ISO format date string."""
    return datetime.date.today().strftime("%Y-%m-%d")


def find_template_dir() -> Path:
    """Locate the templates directory relative to this script."""
    script_dir = Path(__file__).resolve().parent
    template_dir = script_dir.parent / "resources" / "templates"
    if template_dir.exists():
        return template_dir
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


CONFIG_FILENAME = ".arch-guardian.json"


def load_project_config(workspace: Path) -> dict:
    """Load configuration from .arch-guardian.json in workspace root if present."""
    cfg_file = workspace / CONFIG_FILENAME
    if cfg_file.exists():
        try:
            return json.loads(cfg_file.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[WARN] Failed to parse {cfg_file}: {e}")
    return {}


def get_architecture_root(workspace: Path, custom_arch_dir: Optional[str] = None) -> Path:
    """Resolve architecture docs directory: CLI override > config file > default."""
    target_path_str = custom_arch_dir
    if not target_path_str:
        cfg = load_project_config(workspace)
        target_path_str = cfg.get("arch_dir") or cfg.get("archDir")

    if target_path_str:
        raw_path = Path(target_path_str)
        if raw_path.is_absolute():
            return raw_path.resolve()
        return (workspace / raw_path).resolve()
    return (workspace / "docs" / "architecture").resolve()


def init_architecture(
    workspace: Path,
    project_name: Optional[str] = None,
    description: Optional[str] = None,
    force: bool = False,
    arch_dir: Optional[str] = None,
) -> int:
    """Initialize standard architecture directory skeleton."""
    arch_root = get_architecture_root(workspace, arch_dir)
    modules_dir = arch_root / "modules"
    decisions_dir = arch_root / "decisions"
    index_file = arch_root / "ARCHITECTURE.md"

    if arch_dir:
        cfg_file = workspace / CONFIG_FILENAME
        existing_cfg = load_project_config(workspace)
        existing_cfg["arch_dir"] = arch_dir
        cfg_file.write_text(json.dumps(existing_cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"[OK] Saved architecture pointer to: {cfg_file}")

    if index_file.exists() and not force:
        print(f"[WARN] Architecture blueprint already exists at: {index_file}\nUse --force to overwrite if needed.")
        return 0

    arch_root.mkdir(parents=True, exist_ok=True)
    modules_dir.mkdir(parents=True, exist_ok=True)
    decisions_dir.mkdir(parents=True, exist_ok=True)

    p_name = project_name or workspace.name or "Engineering Project"
    p_desc = description or "致力于构建高内聚、低耦合、可持续演进的工业级软件系统。"
    tpl = read_template("ARCHITECTURE.template.md")
    content = (
        tpl.replace("{{PROJECT_NAME}}", p_name)
        .replace("{{PROJECT_DESCRIPTION}}", p_desc)
        .replace("{{CURRENT_DATE}}", get_current_date())
        .replace("{{RUNTIME_ENV}}", "Standard Runtime")
        .replace("{{FRAMEWORK}}", "Enterprise Framework")
        .replace("{{DATABASE}}", "SQL / NoSQL Database")
        .replace("{{CACHE_MQ}}", "Redis / Message Queue")
    )
    index_file.write_text(content, encoding="utf-8")
    print(f"[OK] Initialized architecture documentation at: {arch_root}\n     Main Index: {index_file}")

    try:
        rel_arch = os.path.relpath(arch_root, workspace).replace("\\", "/")
    except ValueError:
        rel_arch = str(arch_root).replace("\\", "/")

    gemini_rule_file = workspace / "GEMINI.md"
    gemini_tpl = read_template("GEMINI.template.md").replace("{{ARCH_DIR_REL}}", rel_arch)
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
    arch_dir: Optional[str] = None,
) -> int:
    """Create a new business module documentation and register in the main index."""
    if not re.match(r"^[a-zA-Z0-9_\-]+$", name):
        print(f"[ERROR] Invalid module name '{name}'. Only alphanumeric, '_' and '-' allowed.")
        return 1

    arch_root = get_architecture_root(workspace, arch_dir)
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

    index_text = index_file.read_text(encoding="utf-8")
    table_pattern = rf"({re.escape('<!-- MODULE_TABLE_START -->')}.*?)(\n{re.escape('<!-- MODULE_TABLE_END -->')})"
    rel_link = f"[modules/{name}/README.md](modules/{name}/README.md)"
    new_row = f"| **{title}** (`{name}`) | {m_desc} | {rel_link} | {today} |"

    if re.search(table_pattern, index_text, re.DOTALL):
        updated_index = re.sub(table_pattern, rf"\1\n{new_row}\2", index_text, flags=re.DOTALL)
        log_start = "<!-- CHANGE_LOG_START -->"
        log_entry = f"- `{today}`: 新增业务模块 [**{title}** (`{name}`)](modules/{name}/README.md)。"
        updated_index = updated_index.replace(log_start, f"{log_start}\n{log_entry}")
        index_file.write_text(updated_index, encoding="utf-8")
        print(f"[OK] Registered module '{name}' in main index: {index_file}")
    else:
        print(f"[WARN] Table tags not found in ARCHITECTURE.md, unable to auto-register table row.")
    return 0


def sync_feature(
    workspace: Path,
    module: str,
    title: str,
    description: str,
    code_ref: Optional[str] = None,
    arch_dir: Optional[str] = None,
) -> int:
    """Append a business feature to the module documentation and update index log."""
    arch_root = get_architecture_root(workspace, arch_dir)
    index_file = arch_root / "ARCHITECTURE.md"
    module_readme = arch_root / "modules" / module / "README.md"

    if not module_readme.exists():
        print(f"[ERROR] Module '{module}' does not exist at {module_readme}")
        return 1

    today = get_current_date()
    mod_text = module_readme.read_text(encoding="utf-8")
    ref_info = f"- **核心入口/代码关联**: `{code_ref}`\n" if code_ref else ""
    feature_entry = f"### {title}\n- **实现时间**: {today}\n- **业务功能概述**: {description}\n{ref_info}"

    feat_pattern = rf"({re.escape('<!-- FEATURE_LIST_START -->')}.*?)(\n{re.escape('<!-- FEATURE_LIST_END -->')})"
    if re.search(feat_pattern, mod_text, re.DOTALL):
        mod_text = re.sub(feat_pattern, rf"\1\n{feature_entry}\2", mod_text, flags=re.DOTALL)
    else:
        mod_text += f"\n\n{feature_entry}\n"

    m_log_start = "<!-- MODULE_CHANGELOG_START -->"
    if m_log_start in mod_text:
        mod_text = mod_text.replace(m_log_start, f"{m_log_start}\n- `{today}`: 实现业务功能点【{title}】。")

    module_readme.write_text(mod_text, encoding="utf-8")
    print(f"[OK] Synchronized feature '{title}' to {module_readme}")

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


def add_adr(workspace: Path, adr_id: str, title: str, arch_dir: Optional[str] = None) -> int:
    """Create an Architecture Decision Record (ADR) and register in main index."""
    arch_root = get_architecture_root(workspace, arch_dir)
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
    content = tpl.replace("{{ADR_ID}}", adr_id).replace("{{ADR_TITLE}}", title).replace("{{CURRENT_DATE}}", today)
    target_file.write_text(content, encoding="utf-8")
    print(f"[OK] Created ADR file: {target_file}")

    idx_text = index_file.read_text(encoding="utf-8")
    adr_start = "<!-- ADR_LIST_START -->"
    rel_link = f"- [ADR-{adr_id}: {title}](decisions/{filename})"
    if adr_start in idx_text:
        idx_text = idx_text.replace("- [暂无决策记录]\n", "").replace("- [暂无决策记录]", "")
        idx_text = idx_text.replace(adr_start, f"{adr_start}\n{rel_link}")
        index_file.write_text(idx_text, encoding="utf-8")
        print(f"[OK] Registered ADR in {index_file}")
    return 0


def cmd_search_docs(
    workspace: Path,
    keywords: List[str],
    arch_dir: Optional[str] = None,
    context_lines: int = 1,
) -> int:
    """Search keywords across architecture documentation to identify impact before sync."""
    arch_root = get_architecture_root(workspace, arch_dir)
    results = search_docs(arch_root, keywords, context_lines=context_lines)
    print(format_search_results(results, keywords, arch_root))
    return 0


def verify_architecture(workspace: Path, arch_dir: Optional[str] = None) -> int:
    """Verify integrity of architecture documentation, broken links, and missing modules."""
    arch_root = get_architecture_root(workspace, arch_dir)
    index_file = arch_root / "ARCHITECTURE.md"
    modules_dir = arch_root / "modules"
    errors: List[str] = []
    warnings: List[str] = []

    if not index_file.exists():
        print(f"[ERROR] Missing master index file at {index_file}")
        return 1

    index_text = index_file.read_text(encoding="utf-8")
    actual_modules = set()
    if modules_dir.exists():
        for item in modules_dir.iterdir():
            if item.is_dir():
                actual_modules.add(item.name)
                if not (item / "README.md").exists():
                    errors.append(f"Module directory '{item.name}' lacks a README.md")

    registered_modules = set()
    matches = re.findall(r"\[modules/([a-zA-Z0-9_\-]+)/README\.md\]", index_text)
    for mod_name in matches:
        registered_modules.add(mod_name)
        if not (modules_dir / mod_name / "README.md").exists():
            errors.append(f"Broken link in ARCHITECTURE.md: module '{mod_name}' not found on disk")

    for u in (actual_modules - registered_modules):
        warnings.append(f"Module '{u}' exists on disk but is not registered in ARCHITECTURE.md")

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
    parser = argparse.ArgumentParser(description="Architecture Guardian: Living documentation and sync CLI.")
    parser.add_argument("--workspace", "-w", default=".", help="Target workspace root path (default: current dir).")
    parser.add_argument("--arch-dir", "-a", help="Custom architecture docs directory.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: init
    init_parser = subparsers.add_parser("init", help="Initialize architecture documentation.")
    init_parser.add_argument("--name", "-n", help="Project name.")
    init_parser.add_argument("--desc", "-d", help="Project description.")
    init_parser.add_argument("--force", "-f", action="store_true", help="Force overwrite index.")
    init_parser.add_argument("--arch-dir", "-a", help="Custom architecture docs directory.")

    # Subcommand: new-module
    mod_parser = subparsers.add_parser("new-module", help="Create and register a business module.")
    mod_parser.add_argument("name", help="Directory name for module.")
    mod_parser.add_argument("--title", "-t", required=True, help="Display title of the module.")
    mod_parser.add_argument("--domain", help="Business domain classification.")
    mod_parser.add_argument("--desc", "-d", help="Module scope description.")

    # Subcommand: sync-feature
    sync_parser = subparsers.add_parser("sync-feature", help="Append feature to module and index.")
    sync_parser.add_argument("module", help="Module directory name.")
    sync_parser.add_argument("--title", "-t", required=True, help="Feature name/title.")
    sync_parser.add_argument("--desc", "-d", required=True, help="Detailed feature description.")
    sync_parser.add_argument("--code-ref", "-c", help="Reference to main code class/function.")

    # Subcommand: search-docs
    search_parser = subparsers.add_parser("search-docs", help="Search keywords across architecture documents.")
    search_parser.add_argument("keywords", nargs="+", help="Keywords to search across docs.")
    search_parser.add_argument("--context", "-c", type=int, default=1, help="Context lines to show (default: 1).")

    # Subcommand: add-adr
    adr_parser = subparsers.add_parser("add-adr", help="Add an Architecture Decision Record.")
    adr_parser.add_argument("id", help="ADR identifier (e.g., 0001).")
    adr_parser.add_argument("--title", "-t", required=True, help="Decision title.")

    # Subcommand: verify
    subparsers.add_parser("verify", help="Verify links and documentation integrity.")
    return parser


def main() -> int:
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    arch_dir = getattr(args, "arch_dir", None)

    if args.command == "init":
        return init_architecture(
            workspace=workspace, project_name=args.name, description=args.desc, force=args.force, arch_dir=arch_dir
        )
    elif args.command == "new-module":
        return add_module(
            workspace=workspace, name=args.name, title=args.title, domain=args.domain, description=args.desc, arch_dir=arch_dir
        )
    elif args.command == "sync-feature":
        return sync_feature(
            workspace=workspace, module=args.module, title=args.title, description=args.desc, code_ref=args.code_ref, arch_dir=arch_dir
        )
    elif args.command == "search-docs":
        return cmd_search_docs(workspace=workspace, keywords=args.keywords, arch_dir=arch_dir, context_lines=args.context)
    elif args.command == "add-adr":
        return add_adr(workspace=workspace, adr_id=args.id, title=args.title, arch_dir=arch_dir)
    elif args.command == "verify":
        return verify_architecture(workspace=workspace, arch_dir=arch_dir)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
