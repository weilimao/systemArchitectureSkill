#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architecture Documentation Searcher & Locator
Searches across all markdown documentation files in the architecture repository
to detect keywords, symbol occurrences, locate specific sections, and assess impact.
"""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import List, Optional, Tuple


@dataclass
class MatchItem:
    line_number: int
    line_text: str
    context_before: List[str]
    context_after: List[str]


@dataclass
class FileSearchResult:
    file_path: Path
    rel_path: str
    matches: List[MatchItem]


@dataclass
class SectionLocateItem:
    line_number: int
    section_path: List[str]
    line_text: str
    matched_keyword: str


@dataclass
class FileLocateResult:
    file_path: Path
    rel_path: str
    module_name: Optional[str]
    matches: List[SectionLocateItem]


def _extract_module_name(rel_path: str) -> Optional[str]:
    """Extract module name if file is under modules/<name>/..."""
    parts = rel_path.replace("\\", "/").split("/")
    if len(parts) >= 2 and parts[0] == "modules":
        return parts[1]
    return None


def search_docs(
    arch_root: Path,
    keywords: List[str],
    context_lines: int = 1,
    case_sensitive: bool = False,
) -> List[FileSearchResult]:
    """Recursively search for keywords in all markdown files within arch_root."""
    if not arch_root.exists() or not keywords:
        return []

    flags = 0 if case_sensitive else re.IGNORECASE
    escaped_keywords = [re.escape(k.strip()) for k in keywords if k.strip()]
    if not escaped_keywords:
        return []

    pattern = re.compile(r"(" + "|".join(escaped_keywords) + r")", flags)
    results: List[FileSearchResult] = []
    md_files = sorted(arch_root.rglob("*.md"))

    for file_path in md_files:
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            continue

        lines = content.splitlines()
        file_matches: List[MatchItem] = []

        for idx, line in enumerate(lines):
            if pattern.search(line):
                start_before = max(0, idx - context_lines)
                end_after = min(len(lines), idx + context_lines + 1)
                before = lines[start_before:idx]
                after = lines[idx + 1:end_after]
                file_matches.append(
                    MatchItem(
                        line_number=idx + 1,
                        line_text=line,
                        context_before=before,
                        context_after=after,
                    )
                )

        if file_matches:
            try:
                rel = file_path.relative_to(arch_root).as_posix()
            except ValueError:
                rel = file_path.as_posix()
            results.append(
                FileSearchResult(
                    file_path=file_path,
                    rel_path=rel,
                    matches=file_matches,
                )
            )

    return results


def locate_docs(
    arch_root: Path,
    keywords: List[str],
    case_sensitive: bool = False,
) -> List[FileLocateResult]:
    """
    Locate specific sections across architecture docs matching keywords.
    Maintains a markdown heading stack to pinpoint exact section hierarchy.
    """
    if not arch_root.exists() or not keywords:
        return []

    flags = 0 if case_sensitive else re.IGNORECASE
    valid_kws = [k.strip() for k in keywords if k.strip()]
    if not valid_kws:
        return []

    # Compile regex pattern capturing which keyword matched
    pattern_str = r"(" + "|".join(re.escape(k) for k in valid_kws) + r")"
    pattern = re.compile(pattern_str, flags)
    header_pattern = re.compile(r"^(#{1,6})\s+(.*)$")

    results: List[FileLocateResult] = []
    md_files = sorted(arch_root.rglob("*.md"))

    for file_path in md_files:
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            continue

        lines = content.splitlines()
        header_stack: List[Tuple[int, str]] = []
        file_matches: List[SectionLocateItem] = []

        for idx, line in enumerate(lines):
            header_match = header_pattern.match(line.strip())
            if header_match:
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                # Pop headers of equal or deeper level
                while header_stack and header_stack[-1][0] >= level:
                    header_stack.pop()
                header_stack.append((level, title))

            search_match = pattern.search(line)
            if search_match:
                current_section = [h[1] for h in header_stack]
                matched_text = search_match.group(1)
                file_matches.append(
                    SectionLocateItem(
                        line_number=idx + 1,
                        section_path=current_section if current_section else ["(文档根部/未归类章节)"],
                        line_text=line.strip(),
                        matched_keyword=matched_text,
                    )
                )

        if file_matches:
            try:
                rel = file_path.relative_to(arch_root).as_posix()
            except ValueError:
                rel = file_path.as_posix()

            results.append(
                FileLocateResult(
                    file_path=file_path,
                    rel_path=rel,
                    module_name=_extract_module_name(rel),
                    matches=file_matches,
                )
            )

    return results


def format_search_results(
    results: List[FileSearchResult],
    keywords: List[str],
    arch_root: Path,
) -> str:
    """Format search results into human and LLM friendly text summary."""
    kw_str = ", ".join(keywords)
    total_matches = sum(len(r.matches) for r in results)
    sep = "=" * 80
    sub_sep = "-" * 80

    output: List[str] = [
        sep,
        f"[SEARCH] 架构文档全域检索结果 [关键词: {kw_str}] (共命中 {total_matches} 处，涉及 {len(results)} 个文档)",
        sep,
    ]

    if not results:
        output.append("（未检索到包含上述关键词的架构文档内容）")
        output.append(sep)
        return "\n".join(output)

    for item in results:
        output.append(f"[DOC] 文档: {item.rel_path} (文件路径: {item.file_path})")
        for match in item.matches:
            for b_line in match.context_before:
                output.append(f"     | {b_line}")
            output.append(f"   [L{match.line_number}] >> {match.line_text}")
            for a_line in match.context_after:
                output.append(f"     | {a_line}")
        output.append(sub_sep)

    output.append(
        "[TIP] 协同同步红线: 请仔细核对上述所有命中文件，确保本次修改的业务逻辑/签名在所有关联文档中均已同步更新！"
    )
    output.append(sep)
    return "\n".join(output)


def format_locate_results(
    results: List[FileLocateResult],
    keywords: List[str],
    arch_root: Path,
) -> str:
    """Format section-aware locate results into a compact tree view for fast navigation."""
    kw_str = ", ".join(keywords)
    total_matches = sum(len(r.matches) for r in results)
    sep = "=" * 80

    output: List[str] = [
        sep,
        f"[LOCATE] 架构说明快速定位导航 [关键词: {kw_str}]",
        f"统计: 命中 {len(results)} 个文档，共 {total_matches} 处相关章节说明",
        sep,
    ]

    if not results:
        output.append("（未在架构文档中检索到与该关键词直接相关的章节说明）")
        output.append(sep)
        return "\n".join(output)

    for item in results:
        mod_tag = f"【业务模块: {item.module_name}】" if item.module_name else "【系统全局/决策】"
        output.append(f"\n* {mod_tag} {item.rel_path}")
        output.append(f"  文件绝对路径: {item.file_path}")

        # Group matches by section path to present clean hierarchical navigation
        section_groups: dict = {}
        for m in item.matches:
            sec_key = " > ".join(m.section_path)
            section_groups.setdefault(sec_key, []).append(m)

        for sec_name, matches in section_groups.items():
            lines_str = ", ".join(f"L{m.line_number}" for m in matches)
            output.append(f"  └── 章节: {sec_name} [{lines_str}]")
            # Show up to 2 representative preview snippets per section
            for m in matches[:2]:
                snippet = m.line_text[:120] + ("..." if len(m.line_text) > 120 else "")
                output.append(f"      - [L{m.line_number}] {snippet}")
            if len(matches) > 2:
                output.append(f"      - ... (该章节另有 {len(matches) - 2} 处匹配)")

    output.append("\n" + sep)
    output.append(
        "[GUIDE] 靶向阅读建议: 无需通篇阅读所有文档！请优先针对上述标明的具体文档与章节行号，使用 read_file 精准阅读对应区间。"
    )
    output.append(sep)
    return "\n".join(output)
