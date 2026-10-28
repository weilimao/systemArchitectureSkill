#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architecture Documentation Searcher
Searches across all markdown documentation files in the architecture repository
to detect keywords, symbol occurrences, and potential impact zones before sync.
"""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import List, Optional


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


def search_docs(
    arch_root: Path,
    keywords: List[str],
    context_lines: int = 1,
    case_sensitive: bool = False,
) -> List[FileSearchResult]:
    """Recursively search for keywords in all markdown files within arch_root."""
    if not arch_root.exists() or not keywords:
        return []

    results: List[FileSearchResult] = []
    # Compile regex pattern matching any of the keywords
    flags = 0 if case_sensitive else re.IGNORECASE
    escaped_keywords = [re.escape(k.strip()) for k in keywords if k.strip()]
    if not escaped_keywords:
        return []

    pattern = re.compile(r"(" + "|".join(escaped_keywords) + r")", flags)

    # Collect all markdown files
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
