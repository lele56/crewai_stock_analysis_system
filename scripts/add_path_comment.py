# scripts/add_path_comment.py
"""给项目中所有源文件第一行添加路径注释"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent


def get_comment_style(file_path: str) -> str:
    """根据文件扩展名返回注释语法"""
    ext = Path(file_path).suffix.lower()
    if ext in (".py", ".yaml", ".yml", ".txt", ".cfg", ".ini", ".toml", ".env", ".example"):
        return "#", ""
    elif ext in (".html", ".md"):
        return "<!--", " -->"
    else:
        return None, None


def add_path_comment(file_path: str, dry_run: bool = False) -> bool:
    """给文件第一行添加路径注释，返回是否修改"""
    prefix, suffix = get_comment_style(file_path)
    if prefix is None:
        return False

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return False

    if not content:
        return False

    rel_path = os.path.relpath(file_path, str(PROJECT_ROOT))
    path_comment = f"{prefix} {rel_path}{suffix}"

    # 检查第一行是否已经是正确的路径注释
    first_line = content.split("\n", 1)[0]
    if first_line == path_comment:
        return False

    # 如果第一行是旧的路径注释，替换为新路径
    if first_line.startswith(prefix) and str(PROJECT_ROOT) in first_line:
        lines = content.split("\n", 1)
        content = (lines[1] if len(lines) > 1 else "")

    # 如果第一行是 shebang，插入到第二行
    elif first_line.startswith("#!") or first_line.startswith("#!/"):
        lines = content.split("\n", 1)
        new_content = lines[0] + "\n" + path_comment + "\n" + (lines[1] if len(lines) > 1 else "")
    else:
        new_content = path_comment + "\n" + content

    if dry_run:
        print(f"  [DRY_RUN] {file_path}")
        return True

    try:
        with open(file_path, "w", encoding="utf-8", newline="") as f:
            f.write(new_content)
        return True
    except Exception as e:
        print(f"  [ERROR] {file_path}: {e}", file=sys.stderr)
        return False


def main():
    global project_root_str
    project_root_str = str(PROJECT_ROOT)

    dry_run = "--dry-run" in sys.argv
    action = "预览" if dry_run else "添加"

    skip_dirs = {"__pycache__", ".git", ".pytest_cache", ".claude", "node_modules"}

    modified = 0
    skipped = 0

    for root, dirs, files in os.walk(str(PROJECT_ROOT)):
        # 跳过不需要的目录
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        for filename in files:
            file_path = os.path.join(root, filename)
            if add_path_comment(file_path, dry_run=dry_run):
                modified += 1
            else:
                skipped += 1

    print(f"\n{action}完成: 修改 {modified} 个文件, 跳过 {skipped} 个文件")


if __name__ == "__main__":
    main()