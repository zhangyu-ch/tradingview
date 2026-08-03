#!/usr/bin/env python3
"""从 pristine 原版与当前生效文件的差异中提取锚点补丁，生成/更新 patches.json。

用法（在仓库任意位置执行）：
    python charting_library_patches/extract_patches.py

工作流：手工调试修改 charting_library 下的产物文件后，运行本脚本把改动
固化为补丁；已有补丁的 note 字段按 (file, find) 匹配自动保留。
"""

import difflib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE_DIR = HERE.parent / "web/tradingview_zy_chart/cl_app/static/charting_library"
PRISTINE_DIR = HERE / "pristine"
PATCHES_JSON = HERE / "patches.json"

# 锚点前后保留的上下文长度；不足以唯一定位时按此步长扩展
CONTEXT = 60


def char_ranges(old: str, new: str):
    """行级 diff 定位变更块，返回 (old_start, old_end, new_start, new_end) 字符区间列表。"""
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    old_offsets = [0]
    for line in old_lines:
        old_offsets.append(old_offsets[-1] + len(line))
    new_offsets = [0]
    for line in new_lines:
        new_offsets.append(new_offsets[-1] + len(line))

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False)
    ranges = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            ranges.append((old_offsets[i1], old_offsets[i2], new_offsets[j1], new_offsets[j2]))
    return ranges


def trim_common(old_seg: str, new_seg: str):
    """去掉变更块首尾相同的部分，把补丁缩到最小。"""
    prefix = 0
    limit = min(len(old_seg), len(new_seg))
    while prefix < limit and old_seg[prefix] == new_seg[prefix]:
        prefix += 1
    suffix = 0
    while suffix < limit - prefix and old_seg[-1 - suffix] == new_seg[-1 - suffix]:
        suffix += 1
    return prefix, suffix


def make_patch(old: str, o1: int, o2: int, new: str, n1: int, n2: int):
    """生成一条 find/replace 补丁，扩展上下文直到 find 在原文中唯一。"""
    prefix, suffix = trim_common(old[o1:o2], new[n1:n2])
    o1, o2 = o1 + prefix, o2 - suffix
    n1, n2 = n1 + prefix, n2 - suffix

    ctx = CONTEXT
    while True:
        left = max(0, o1 - ctx)
        right = min(len(old), o2 + ctx)
        find = old[left:o1] + old[o1:o2] + old[o2:right]
        if old.count(find) == 1:
            replace = old[left:o1] + new[n1:n2] + old[o2:right]
            return {"find": find, "replace": replace}
        if left == 0 and right == len(old):
            raise RuntimeError("无法生成唯一锚点（整文件都不唯一？）")
        ctx *= 2


def main():
    old_notes = {}
    if PATCHES_JSON.exists():
        for entry in json.loads(PATCHES_JSON.read_text(encoding="utf-8")):
            for p in entry["patches"]:
                old_notes[(entry["file"], p["find"])] = p.get("note", "")

    result = []
    for pristine_path in sorted(PRISTINE_DIR.rglob("*")):
        if not pristine_path.is_file():
            continue
        rel = pristine_path.relative_to(PRISTINE_DIR).as_posix()
        live_path = LIVE_DIR / rel
        old = pristine_path.read_bytes().decode("utf-8")
        new = live_path.read_bytes().decode("utf-8")
        if old == new:
            print(f"无差异: {rel}")
            continue

        patches = []
        for o1, o2, n1, n2 in char_ranges(old, new):
            patch = make_patch(old, o1, o2, new, n1, n2)
            patch["note"] = old_notes.get((rel, patch["find"]), "")
            patches.append(patch)
        result.append({"file": rel, "patches": patches})
        print(f"{rel}: {len(patches)} 处补丁")

    PATCHES_JSON.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"已写入 {PATCHES_JSON}")


if __name__ == "__main__":
    main()
