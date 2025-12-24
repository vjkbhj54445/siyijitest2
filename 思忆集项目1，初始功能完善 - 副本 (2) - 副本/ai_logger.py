#!/usr/bin/env python3
"""对话记录器：追加对话并可记录指定文件的修改 diff（基于快照）。

用法示例：
python ai_logger.py "我的消息" --role 用户 --topic 测试 --files 思忆集test1.py other.py
"""

import argparse
from datetime import datetime
from pathlib import Path
import difflib
import os

DEFAULT_FILE = Path(__file__).parent / "编程AI对话记录.md"
DEFAULT_SNAP = Path(__file__).parent / ".ai_snapshots"

TEMPLATE = """
---
**时间**: {time}  
**角色**: {role}  
**主题**: {topic}  
**思路 / 意图**: {intent}  
**对话**:
- {speaker}: {message}
{file_section}
**结果 / 决策**: {result}
**TODO**: {todo}
"""


def ensure_snapshots_dir(snap_dir: Path):
    snap_dir.mkdir(parents=True, exist_ok=True)


def _snapshot_path_for(file_path: str, snapshots_dir: Path) -> Path:
    # 将文件路径映射为 snapshots 目录下的文件名（避免目录结构复杂性）
    p = Path(file_path)
    safe_name = str(p).replace(os.sep, "__").replace(":", "")
    return snapshots_dir / safe_name


def compute_file_diffs(file_paths, snapshots_dir: Path):
    ensure_snapshots_dir(snapshots_dir)
    diffs = []
    for fp in file_paths:
        try:
            cur_path = Path(fp)
            if not cur_path.exists():
                diffs.append((fp, f"(文件未找到: {fp})"))
                continue
            cur_text = cur_path.read_text(encoding='utf-8', errors='replace').splitlines()
        except Exception as e:
            diffs.append((fp, f"(读取失败: {e})"))
            continue

        snap_path = _snapshot_path_for(fp, snapshots_dir)
        if snap_path.exists():
            old_text = snap_path.read_text(encoding='utf-8', errors='replace').splitlines()
        else:
            old_text = []

        udiff = list(difflib.unified_diff(old_text, cur_text, fromfile=f"a/{fp}", tofile=f"b/{fp}", lineterm=""))
        if udiff:
            diffs.append((fp, "\n".join(udiff)))
        else:
            diffs.append((fp, "(无改动)"))

        # 更新快照为当前内容
        try:
            snap_path.parent.mkdir(parents=True, exist_ok=True)
            snap_path.write_text("\n".join(cur_text), encoding='utf-8')
        except Exception:
            pass

    return diffs


def build_file_section(diffs):
    if not diffs:
        return ""
    parts = ["**修改内容**:"]
    for fp, diff in diffs:
        parts.append(f"- `{fp}`:")
        if diff.startswith("(文件未找到") or diff.startswith("(读取失败") or diff == "(无改动)":
            parts.append(f"  - {diff}")
        else:
            parts.append("```diff")
            parts.append(diff)
            parts.append("```")
    return "\n" + "\n".join(parts) + "\n"


def append_entry(message, role, topic, tags, intent, result, todo, speaker, file_path, file_diffs):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_section = build_file_section(file_diffs) if file_diffs is not None else ""
    content = TEMPLATE.format(
        time=now,
        role=role,
        topic=topic or "",
        intent=intent or "",
        speaker=speaker,
        message=message,
        file_section=file_section,
        result=result or "",
        todo=todo or "",
    )
    if tags:
        content = f"<!-- tags: {tags} -->\n" + content
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(content + "\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Append a conversation entry and optionally record file diffs to 编程AI对话记录.md")
    p.add_argument("message", help="主要的对话内容（建议简短）")
    p.add_argument("--role", default="用户", choices=["用户", "AI"], help="谁发出的这条消息")
    p.add_argument("--topic", default="", help="简短主题")
    p.add_argument("--tags", default="", help="逗号分隔的标签，便于检索")
    p.add_argument("--intent", default="", help="你的意图或背景说明")
    p.add_argument("--result", default="", help="结果或决策说明")
    p.add_argument("--todo", default="", help="后续待办项")
    p.add_argument("--speaker", default=None, help="可选：对话中具体说话者（默认为 role）")
    p.add_argument("--file", default=str(DEFAULT_FILE), help="记录文件路径（默认为项目中的 编程AI对话记录.md）")
    p.add_argument("--files", nargs="*", help="要记录修改的文件路径（多个用空格分隔）")
    p.add_argument("--snapshots", default=str(DEFAULT_SNAP), help="快照目录路径（默认为 .ai_snapshots）")

    args = p.parse_args()
    speaker = args.speaker or args.role
    file_diffs = None
    if args.files:
        file_diffs = compute_file_diffs(args.files, Path(args.snapshots))

    append_entry(
        message=args.message,
        role=args.role,
        topic=args.topic,
        tags=args.tags,
        intent=args.intent,
        result=args.result,
        todo=args.todo,
        speaker=speaker,
        file_path=args.file,
        file_diffs=file_diffs,
    )
    print(f"已将条目追加到 {args.file}")
