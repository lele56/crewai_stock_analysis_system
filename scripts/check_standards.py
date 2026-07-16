#!/usr/bin/env python3
# scripts/check_standards.py
"""通用代码规范检查工具 — 补充 Ruff 未覆盖的项目特有规则
适配任意 Python 项目，通过命令行参数控制检查行为
"""

import argparse
import os
from pathlib import Path
import re
import sys


class StandardsChecker:
    """通用代码规范检查器"""

    def __init__(
        self,
        root_dir: str = ".",
        line_limit: int = 300,
        main_line_limit: int = 400,
        exclude_dirs: tuple[str, ...] = (),
        exclude_files: tuple[str, ...] = (),
        skip_rules: tuple[str, ...] = (),
    ) -> None:
        self.root = Path(root_dir).resolve()
        self.line_limit = line_limit
        self.main_line_limit = main_line_limit
        self.exclude_dirs = set(exclude_dirs) | {
            ".git",
            "__pycache__",
            ".pytest_cache",
            "venv",
            ".venv",
            "env",
            ".trae",
        }
        self.exclude_files = set(exclude_files) | {"check_standards.py"}
        self.skip_rules = set(skip_rules)
        self.violations: dict[str, list[tuple[str, str, int]]] = {}
        self.files_checked = 0

    def _walk_py_files(self) -> list[Path]:
        """收集所有 .py 文件"""
        files = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in self.exclude_dirs]
            for f in filenames:
                if f.endswith(".py") and f not in self.exclude_files:
                    files.append(Path(dirpath) / f)
        return sorted(files)

    def _add_violation(self, rule: str, filepath: Path, line: int, detail: str) -> None:
        """记录一条违规"""
        rel = filepath.relative_to(self.root).as_posix()
        if rule not in self.violations:
            self.violations[rule] = []
        self.violations[rule].append((rel, detail, line))

    # ── 规则 1: 文件头部路径注释 ────────────────
    def check_path_comment(self, filepath: Path):
        if "R01" in self.skip_rules:
            return
        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception:
            return
        lines = content.split("\n")
        rel = filepath.relative_to(self.root).as_posix()
        expected = f"# {rel}"
        found = False
        for line in lines[:5]:
            stripped = line.strip()
            if stripped.startswith(f"# {rel}") or stripped == expected:
                found = True
                break
        if not found:
            self._add_violation("R01", filepath, 1, f"缺少路径注释，期望: {expected}")

    # ── 规则 2: 文件行数限制 ────────────────────
    def check_line_count(self, filepath: Path):
        if "R02" in self.skip_rules:
            return
        try:
            n = sum(1 for _ in open(filepath, encoding="utf-8"))
        except Exception:
            return
        rel = filepath.relative_to(self.root).as_posix()
        limit = self.main_line_limit if rel == "main.py" else self.line_limit
        if n > limit:
            self._add_violation("R02", filepath, n, f"{n} 行，超过 {limit} 行限制")

    # ── 规则 3: Import 规范 ──────────────────────
    def check_imports(self, filepath: Path):
        if "R03" in self.skip_rules:
            return
        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception:
            return
        rel = filepath.relative_to(self.root).as_posix()
        # 3c: 禁止 sys.path hack（main.py / scripts / tests 允许）
        if rel in ("main.py",) or rel.startswith("scripts/") or rel.startswith("tests/"):
            return
        if re.search(r"sys\.path\.(append|insert)\(", content):
            self._add_violation("R03c", filepath, 1, "禁止使用 sys.path.append/insert")

    # ── 规则 4: 日志规范 ─────────────────────────
    def check_logging(self, filepath: Path):
        if "R04" in self.skip_rules:
            return
        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception:
            return
        # 4a: 禁止散落的 basicConfig（main.py / scripts 入口文件允许）
        rel = filepath.relative_to(self.root).as_posix()
        if rel in ("main.py",) or rel.startswith("scripts/"):
            return
        if re.search(r"logging\.basicConfig\(", content):
            self._add_violation("R04a", filepath, 1, "禁止使用 logging.basicConfig()，请使用 Config.LOG_LEVEL")

    # ── 规则 5: Config 统一使用 ──────────────────
    def check_hardcoded_config(self, filepath: Path):
        if "R05" in self.skip_rules:
            return
        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception:
            return
        # 5b: 禁止直接调用 os.getenv（应通过 Config 类）
        for m in re.finditer(r"os\.getenv\(['\"](\w+)['\"]", content):
            var_name = m.group(1)
            # 允许 Config 类内部使用 os.getenv
            if "class Config" not in content:
                self._add_violation(
                    "R05b", filepath, m.start() // 80 + 1, f"直接调用 os.getenv('{var_name}')，应通过 Config 类"
                )

    # ── 规则 6: 无绝对路径 ───────────────────────
    def check_absolute_paths(self, filepath: Path):
        if "R06" in self.skip_rules:
            return
        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception:
            return
        # 匹配 Windows 绝对路径 C:\... 或 D:\... 等
        for m in re.finditer(r'["\']([A-Za-z]:\\(?:Users|home|root|opt|var|etc|tmp|mnt)\\[^"\']+)["\']', content):
            self._add_violation("R06", filepath, m.start() // 80 + 1, f"硬编码绝对路径: {m.group(1)[:60]}...")

    # ── 规则 7: 模块化结构 ───────────────────────
    def check_module_structure(self, filepath: Path):
        if "R07" in self.skip_rules:
            return
        parent = filepath.parent
        rel_parent = parent.relative_to(self.root).as_posix()
        # scripts/ 和 tests/ 不是 Python 包，不需要 __init__.py
        if rel_parent in ("scripts", "tests") or rel_parent.startswith("scripts/") or rel_parent.startswith("tests/"):
            return
        # 7a: 检查包目录是否有 __init__.py
        init_file = parent / "__init__.py"
        if filepath.name != "__init__.py" and parent != self.root and not init_file.exists():
            self._add_violation("R07a", filepath, 1, f"包目录缺少 __init__.py: {rel_parent}")

    # ── 规则 10: 异常处理 ────────────────────────
    def check_exception_handling(self, filepath: Path):
        if "R10" in self.skip_rules:
            return
        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception:
            return
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # 10a: 裸 except
            if re.match(r"except\s*:", stripped):
                self._add_violation("R10a", filepath, i, "禁止裸 except:，请指定异常类型")
            # 10b: except + pass（吞异常）— 跳过 ImportError（标准可选依赖模式）
            if re.match(r"except\s+\w+", stripped):
                if re.match(r"except\s+ImportError", stripped):
                    continue
                # 检查下一行或同一行是否为 pass
                next_line = lines[i].strip() if i < len(lines) else ""
                if stripped.endswith(": pass") or next_line == "pass":
                    # 检查是否在 pass 前有日志记录
                    prev_line = lines[i - 2].strip() if i >= 2 else ""
                    if "logger" not in prev_line and "logging" not in prev_line and "print" not in prev_line:
                        self._add_violation("R10b", filepath, i, "except 块吞异常无日志，请至少记录日志")

    # ── 执行所有检查 ─────────────────────────────
    def run(self) -> dict[str, list[tuple[str, str, int]]]:
        files = self._walk_py_files()
        self.files_checked = len(files)

        for fp in files:
            self.check_path_comment(fp)
            self.check_line_count(fp)
            self.check_imports(fp)
            self.check_logging(fp)
            self.check_hardcoded_config(fp)
            self.check_absolute_paths(fp)
            self.check_module_structure(fp)
            self.check_exception_handling(fp)

        return self.violations

    # ── 格式化报告 ───────────────────────────────
    def report(self, violations: dict[str, list[tuple[str, str, int]]]) -> str:
        severity_map = {
            "R01": "🔴 严重",
            "R03c": "🔴 严重",
            "R04a": "🔴 严重",
            "R06": "🔴 严重",
            "R07a": "🔴 严重",
            "R10a": "🔴 严重",
            "R02": "🟡 警告",
            "R05b": "🟡 警告",
            "R10b": "🟡 警告",
            "R03": "🟢 建议",
        }

        total = sum(len(v) for v in violations.values())
        n_files = len({f for v_list in violations.values() for f, _, _ in v_list})

        lines = []
        lines.append("╔══════════════════════════════════════════════════════╗")
        lines.append("║           自定义代码规范审查报告                     ║")
        lines.append("╠══════════════════════════════════════════════════════╣")
        lines.append(f"║  扫描文件: {self.files_checked:4d}  违规文件: {n_files:4d}  违规总数: {total:4d}     ║")
        lines.append("╚══════════════════════════════════════════════════════╝")
        lines.append("")

        rule_names = {
            "R01": "路径注释缺失",
            "R02": "文件行数超限",
            "R03": "Import 规范",
            "R03c": "sys.path 禁止",
            "R04a": "散落 basicConfig",
            "R05b": "直接 os.getenv",
            "R06": "硬编码绝对路径",
            "R07a": "缺少 __init__.py",
            "R10a": "裸 except",
            "R10b": "吞异常无日志",
        }

        order = ["R01", "R03c", "R04a", "R06", "R07a", "R10a", "R02", "R05b", "R10b", "R03"]
        for rule in order:
            if rule not in violations:
                continue
            sev = severity_map.get(rule, "  ")
            name = rule_names.get(rule, rule)
            lines.append(f"{sev} 规则 {rule} — {name} ({len(violations[rule])} 条):")
            for fpath, detail, lineno in violations[rule]:
                lines.append(f"     {fpath}:{lineno}  → {detail}")
            lines.append("")

        if total == 0:
            lines.append("✅ 所有自定义规则检查通过！")

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="通用 Python 代码规范检查工具（补充 Ruff 未覆盖规则）")
    parser.add_argument("--root", "-r", default=".", help="项目根目录 (默认: .)")
    parser.add_argument("--line-limit", "-l", type=int, default=300, help="单文件行数限制 (默认: 300)")
    parser.add_argument("--main-limit", "-m", type=int, default=400, help="main.py 行数限制 (默认: 400)")
    parser.add_argument("--exclude-dir", "-d", action="append", default=[], help="排除目录 (可多次指定)")
    parser.add_argument("--exclude-file", "-f", action="append", default=[], help="排除文件 (可多次指定)")
    parser.add_argument("--skip", "-s", action="append", default=[], help="跳过规则 (如 R01,R02, 可多次指定)")
    parser.add_argument("--json", "-j", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()

    skip_rules = []
    for s in args.skip:
        skip_rules.extend(r.strip() for r in s.split(","))

    checker = StandardsChecker(
        root_dir=args.root,
        line_limit=args.line_limit,
        main_line_limit=args.main_limit,
        exclude_dirs=tuple(args.exclude_dir),
        exclude_files=tuple(args.exclude_file),
        skip_rules=tuple(skip_rules),
    )
    violations = checker.run()

    if args.json:
        import json

        result = {
            "files_checked": checker.files_checked,
            "violations": {
                rule: [{"file": f, "detail": d, "line": l} for f, d, l in items] for rule, items in violations.items()
            },
            "total": sum(len(v) for v in violations.values()),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(checker.report(violations))

    # 返回码: 有严重违规返回 1
    severe = {"R01", "R03c", "R04a", "R06", "R07a", "R10a"}
    has_severe = any(rule in severe for rule in violations)
    return 1 if has_severe else 0


if __name__ == "__main__":
    sys.exit(main())
