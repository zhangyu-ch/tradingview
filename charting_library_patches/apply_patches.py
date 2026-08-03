#!/usr/bin/env python3
"""把 patches.json 中的锚点补丁应用到 pristine 原版，生成打好补丁的产物文件。

用法（在仓库任意位置执行）：
    python charting_library_patches/apply_patches.py          # 生成并写入 charting_library
    python charting_library_patches/apply_patches.py --check  # 只校验，与当前文件逐字节比较

每个 find 锚点必须在文件中恰好出现一次，否则报错退出——通常意味着
charting_library 已升级到新版本，需要人工重新定位锚点。
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE_DIR = HERE.parent / "web/tradingview_zy_chart/cl_app/static/charting_library"
PRISTINE_DIR = HERE / "pristine"
PATCHES_JSON = HERE / "patches.json"


def apply_file(entry: dict) -> bytes:
    rel = entry["file"]
    content = (PRISTINE_DIR / rel).read_bytes().decode("utf-8")
    for i, patch in enumerate(entry["patches"], 1):
        find = patch["find"]
        count = content.count(find)
        if count != 1:
            note = patch.get("note", "")
            sys.exit(
                f"错误: {rel} 第 {i} 处补丁锚点出现 {count} 次（应为 1 次）。\n"
                f"  note: {note}\n"
                f"  锚点可能因库升级失效，请人工重新定位后更新 patches.json。"
            )
        content = content.replace(find, patch["replace"])
    return content.encode("utf-8")


def main():
    check_only = "--check" in sys.argv[1:]
    entries = json.loads(PATCHES_JSON.read_text(encoding="utf-8"))

    failed = False
    for entry in entries:
        rel = entry["file"]
        patched = apply_file(entry)
        live_path = LIVE_DIR / rel
        if check_only:
            if live_path.exists() and live_path.read_bytes() == patched:
                print(f"一致: {rel}")
            else:
                print(f"不一致: {rel}（当前文件与补丁产物不同）")
                failed = True
        else:
            live_path.write_bytes(patched)
            print(f"已写入: {rel}（{len(entry['patches'])} 处补丁）")

    if check_only and failed:
        sys.exit(1)
    print("校验通过" if check_only else "完成")


if __name__ == "__main__":
    main()
