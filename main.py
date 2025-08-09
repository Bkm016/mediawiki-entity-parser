#!/usr/bin/env python3
"""
Main script to process all txt files in the source directory.
For each file, generates corresponding JSON, meanings, and types files.
"""

import os
import json
import glob
from pathlib import Path
from extract import extract
from text_utils import meaning_to_camel_case


def extract_meanings_and_types(input_file: str, version: str, output_dir: str) -> None:
    """Extract meanings and types from the JSON file"""
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    meanings = []
    types = []
    
    # Extract meanings and types from metadata
    metadata = data.get("metadata", {})
    for entity_id, entity_data in metadata.items():
        fields = entity_data.get("fields", [])
        for field in fields:
            # Extract type
            field_type = field.get("type", "")
            if field_type:
                types.append(field_type)
            
            # Extract meaning
            if "bitmask" in field:
                # Extract meanings from bitmask items
                bitmask_items = field.get("bitmask", [])
                for item in bitmask_items:
                    item_meaning = item.get("meaning", "")
                    if item_meaning:
                        meanings.append(item_meaning)
            else:
                # Regular field meaning
                meaning = field.get("meaning", "")
                if meaning:
                    meanings.append(meaning)
    
    # Write meanings files
    meanings_file = os.path.join(output_dir, f"{version}-meanings.txt")
    with open(meanings_file, "w", encoding="utf-8") as f:
        for meaning in meanings:
            f.write(meaning + "\n")
    
    # Write meaning to name mapping
    meaning_to_name_file = os.path.join(output_dir, f"{version}-meaning_to_name.txt")
    with open(meaning_to_name_file, "w", encoding="utf-8") as f:
        for meaning in meanings:
            name = meaning_to_camel_case(meaning)
            f.write(f"{name}\n")

    # Write meaning compare file (meaning vs name side by side)
    meaning_compare_file = os.path.join(output_dir, f"{version}-meaning_compare.txt")
    with open(meaning_compare_file, "w", encoding="utf-8") as f:
        for meaning in meanings:
            name = meaning_to_camel_case(meaning)
            f.write(f"{meaning}\n{name}\n")
    
    # Write types file
    types_file = os.path.join(output_dir, f"{version}-types.txt")
    with open(types_file, "w", encoding="utf-8") as f:
        for field_type in types:
            f.write(field_type + "\n")
    
    print(f"  - 提取了 {len(meanings)} 个 meaning 字段到 {meanings_file}")
    print(f"  - 生成了 meaning -> name 映射到 {meaning_to_name_file}")
    print(f"  - 生成了 meaning 对比文件到 {meaning_compare_file}")
    print(f"  - 提取了 {len(types)} 个 type 字段到 {types_file}")


def process_file(input_path: str, output_dir: str) -> None:
    """Process a single txt file"""
    input_file = Path(input_path)
    version = input_file.stem  # e.g., "1.21.8" from "1.21.8.txt"
    output_file = os.path.join(output_dir, f"{version}.json")
    
    print(f"处理文件: {input_path}")
    print(f"  -> {output_file}")
    
    # Extract data
    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()
    
    data = extract(text)
    
    # Write JSON output
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # Extract meanings and types
    extract_meanings_and_types(output_file, version, output_dir)
    
    print(f"完成处理: {version}")


def main():
    """Main function to process all txt files in source directory"""
    source_dir = "source"
    output_dir = "output"
    
    if not os.path.exists(source_dir):
        print(f"错误: {source_dir} 目录不存在")
        return
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录: {output_dir}")
    
    # Find all txt files in source directory
    txt_files = glob.glob(os.path.join(source_dir, "*.txt"))
    
    if not txt_files:
        print(f"在 {source_dir} 目录中没有找到 txt 文件")
        return
    
    print(f"找到 {len(txt_files)} 个文件:")
    for file in sorted(txt_files):
        print(f"  - {file}")
    
    print(f"\n输出目录: {output_dir}")
    print("开始处理...")
    
    for txt_file in sorted(txt_files):
        try:
            process_file(txt_file, output_dir)
            print()
        except Exception as e:
            print(f"处理 {txt_file} 时出错: {e}")
            print()
    
    print("所有文件处理完成!")


if __name__ == "__main__":
    main()
