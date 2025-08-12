import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any

def load_version_data(output_dir: Path) -> Dict[str, Dict]:
    """加载所有版本的完整 JSON 数据"""
    version_data = {}
    json_files = sorted(output_dir.glob("*.json"))
    
    for json_file in json_files:
        version = json_file.stem
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            version_data[version] = data
    
    return version_data

def format_value(value, max_width=25):
    """格式化值，处理过长的文本"""
    if value is None or value == "-":
        return "-"
    
    value_str = str(value)
    if len(value_str) > max_width:
        if "normal:" in value_str or "marker:" in value_str or "small:" in value_str:
            parts = value_str.split()
            return " ".join(parts[:2]) + "..."
        return value_str[:max_width-3] + "..."
    return value_str

def analyze_entity_changes(version_data: Dict[str, Dict]) -> str:
    """分析实体基本属性变化（type_index, bounding_box）"""
    lines = []
    lines.append("=" * 150)
    lines.append(" " * 60 + "ENTITY PROPERTY CHANGES")
    lines.append("=" * 150)
    lines.append("\nShowing entities with changes in type_index or bounding box properties.\n")
    
    versions = sorted(version_data.keys())
    
    # 获取所有实体
    all_entities = set()
    for version_data_item in version_data.values():
        all_entities.update(version_data_item.get('entities', {}).keys())
    all_entities = sorted(all_entities)
    
    # 先收集所有有变化的实体
    entities_with_changes = []
    
    for entity in all_entities:
        entity_versions = {}
        has_changes = False
        
        for version in versions:
            entities = version_data[version].get('entities', {})
            if entity in entities:
                entity_versions[version] = entities[entity]
            else:
                entity_versions[version] = None
        
        # 检查是否有变化
        values_set = set()
        for v_data in entity_versions.values():
            if v_data is not None:
                values_set.add((
                    v_data.get('type_index'),
                    v_data.get('bounding_box_xz'),
                    v_data.get('bounding_box_y')
                ))
        
        # 检查是否新增或删除
        not_all_present = any(v is None for v in entity_versions.values())
        has_some = any(v is not None for v in entity_versions.values())
        
        if len(values_set) > 1 or (not_all_present and has_some):
            has_changes = True
            entities_with_changes.append((entity, entity_versions))
    
    # 为每个有变化的实体生成表格
    for entity, entity_versions in entities_with_changes:
        entity_display = entity.replace("minecraft:", "")
        lines.append(f"\n{'=' * 150}")
        lines.append(f"Entity: {entity_display}")
        lines.append(f"{'=' * 150}")
        
        # 属性表格 - 与 metadata 相似的格式
        lines.append("\nProperty Changes:")
        lines.append("| Property        | Version | Value                                    | Changes           |")
        lines.append("|-----------------|---------|------------------------------------------|-------------------|")
        
        # type_index
        prev_index = None
        for version in versions:
            if entity_versions[version] is not None:
                index_val = entity_versions[version].get('type_index', '-')
                changes = ""
                if prev_index is not None and prev_index != index_val:
                    changes = f"Changed: {prev_index}→{index_val}"
                
                # 只显示第一个版本和有变化的版本
                if prev_index is None or prev_index != index_val:
                    lines.append(f"| type_index      | {version:7} | {str(index_val):40} | {changes:17} |")
                
                prev_index = index_val
            else:
                if prev_index is not None:
                    lines.append(f"| type_index      | {version:7} | {'-':40} | {'REMOVED':17} |")
                    prev_index = None
        
        lines.append("|-----------------|---------|------------------------------------------|-------------------|")
        
        # bounding_box_xz
        prev_boxz = None
        for version in versions:
            if entity_versions[version] is not None:
                boxz_val = entity_versions[version].get('bounding_box_xz', '-')
                changes = ""
                if prev_boxz is not None and prev_boxz != boxz_val:
                    changes = "Changed"
                
                # 只显示第一个版本和有变化的版本
                if prev_boxz is None or prev_boxz != boxz_val:
                    boxz_display = str(boxz_val) if len(str(boxz_val)) <= 40 else str(boxz_val)[:37] + "..."
                    lines.append(f"| bounding_box_xz | {version:7} | {boxz_display:40} | {changes:17} |")
                
                prev_boxz = boxz_val
            else:
                if prev_boxz is not None:
                    lines.append(f"| bounding_box_xz | {version:7} | {'-':40} | {'REMOVED':17} |")
                    prev_boxz = None
        
        lines.append("|-----------------|---------|------------------------------------------|-------------------|")
        
        # bounding_box_y
        prev_boxy = None
        for version in versions:
            if entity_versions[version] is not None:
                boxy_val = entity_versions[version].get('bounding_box_y', '-')
                changes = ""
                if prev_boxy is not None and prev_boxy != boxy_val:
                    changes = "Changed"
                
                # 只显示第一个版本和有变化的版本
                if prev_boxy is None or prev_boxy != boxy_val:
                    boxy_display = str(boxy_val) if len(str(boxy_val)) <= 40 else str(boxy_val)[:37] + "..."
                    lines.append(f"| bounding_box_y  | {version:7} | {boxy_display:40} | {changes:17} |")
                
                prev_boxy = boxy_val
            else:
                if prev_boxy is not None:
                    lines.append(f"| bounding_box_y  | {version:7} | {'-':40} | {'REMOVED':17} |")
                    prev_boxy = None
    
    lines.append(f"\n[!] = Changed from previous version")
    lines.append(f"Total entities with property changes: {len(entities_with_changes)}/{len(all_entities)}")
    
    return "\n".join(lines)

def analyze_metadata_changes(version_data: Dict[str, Dict]) -> str:
    """分析真正的 metadata 字段变化"""
    lines = []
    lines.append("=" * 150)
    lines.append(" " * 60 + "METADATA FIELD CHANGES")
    lines.append("=" * 150)
    lines.append("\nShowing changes in entity metadata field definitions across versions.\n")
    
    versions = sorted(version_data.keys())
    
    # 获取所有 metadata 类型
    all_metadata_types = set()
    for version_data_item in version_data.values():
        all_metadata_types.update(version_data_item.get('metadata', {}).keys())
    all_metadata_types = sorted(all_metadata_types)
    
    # 收集有变化的 metadata 类型
    metadata_with_changes = []
    
    for metadata_type in all_metadata_types:
        type_versions = {}
        
        # 按字段名分组
        fields_by_name = {}  # {field_name: {version: field_data}}
        
        for version in versions:
            metadata = version_data[version].get('metadata', {})
            if metadata_type in metadata:
                type_versions[version] = metadata[metadata_type]
                # 收集字段，按名称分组
                for field in metadata[metadata_type].get('fields', []):
                    # 如果字段有 bitmask，展开为单独的字段
                    if 'bitmask' in field and field.get('bitmask'):
                        for bit_field in field['bitmask']:
                            bit_name = bit_field.get('name', f"bit_{field['index']}_{bit_field.get('mask', '')}")
                            if bit_name not in fields_by_name:
                                fields_by_name[bit_name] = {}
                            # 创建一个扩展的字段数据
                            expanded_field = {
                                'index': field['index'],
                                'type': f"Byte[{bit_field.get('mask', '')}]",
                                'default': field.get('default', '0'),
                                'meaning': bit_field.get('meaning', ''),
                                'is_bitmask': True,
                                'mask': bit_field.get('mask', '')
                            }
                            fields_by_name[bit_name][version] = expanded_field
                    else:
                        # 普通字段
                        field_name = field.get('name', f"field_{field['index']}")
                        if field_name not in fields_by_name:
                            fields_by_name[field_name] = {}
                        fields_by_name[field_name][version] = field
            else:
                type_versions[version] = None
        
        # 检查是否有变化
        has_changes = False
        
        # 检查存在性变化
        not_all_present = any(v is None for v in type_versions.values())
        has_some = any(v is not None for v in type_versions.values())
        if not_all_present and has_some:
            has_changes = True
        
        # 检查继承变化
        inherits_values = set()
        for v_data in type_versions.values():
            if v_data is not None:
                inherits_values.add(v_data.get('inherits'))
        if len(inherits_values) > 1:
            has_changes = True
        
        # 检查字段变化
        for field_name, field_versions in fields_by_name.items():
            # 检查索引变化
            indices = set()
            types = set()
            defaults = set()
            
            for v in versions:
                if v in field_versions:
                    f = field_versions[v]
                    indices.add(f.get('index'))
                    types.add(f.get('type'))
                    defaults.add(str(f.get('default')))
            
            if len(indices) > 1 or len(types) > 1 or len(defaults) > 1:
                has_changes = True
            
            # 检查字段是否在所有版本都存在
            if len(field_versions) != len([v for v in type_versions.values() if v is not None]):
                has_changes = True
        
        if has_changes:
            metadata_with_changes.append((metadata_type, type_versions, fields_by_name))
    
    # 生成表格
    for metadata_type, type_versions, fields_by_name in metadata_with_changes:
        lines.append(f"\n{'=' * 150}")
        lines.append(f"Metadata Type: {metadata_type}")
        lines.append(f"{'=' * 150}")
        
        # 继承关系表
        lines.append("\nInheritance:")
        inherit_line = "| Version |"
        sep_line = "|---------|"
        for version in versions:
            inherit_line += f" {version:^20} |"
            sep_line += "-" * 22 + "|"
        lines.append(inherit_line)
        lines.append(sep_line)
        
        inherit_row = "| Inherits|"
        prev_inherit = None
        for version in versions:
            if type_versions[version] is not None:
                inherit_val = type_versions[version].get('inherits', 'None')
                if inherit_val is None:
                    inherit_val = "None"
                # 移除 minecraft: 前缀以节省空间
                inherit_val_display = str(inherit_val).replace('minecraft:', '')
                # 如果还是太长，截断
                if len(inherit_val_display) > 18:
                    inherit_val_display = inherit_val_display[:15] + "..."
                if prev_inherit is not None and prev_inherit != inherit_val:
                    if len(inherit_val_display) <= 15:
                        inherit_val_display = f"{inherit_val_display}[!]"
                inherit_row += f" {inherit_val_display:^20} |"
                prev_inherit = inherit_val
            else:
                inherit_row += f" {'-':^20} |"
        lines.append(inherit_row)
        
        # 字段变化表 - 新格式，按字段名分组
        if fields_by_name:
            lines.append("\nField Changes:")
            lines.append("| Field Name                | Version |Index| Type                 | Default             | Meaning                      | Changes           |")
            lines.append("|---------------------------|---------|-----|----------------------|---------------------|------------------------------|-------------------|")
            
            # 排序字段名
            sorted_field_names = sorted(fields_by_name.keys())
            
            for field_name in sorted_field_names:
                field_versions = fields_by_name[field_name]
                
                # 收集所有版本的数据
                version_data_list = []
                prev_index = None
                prev_type = None
                prev_default = None
                
                for version in versions:
                    if version in field_versions:
                        field = field_versions[version]
                        index = field.get('index')
                        ftype = field.get('type', '-')
                        default = str(field.get('default', '-'))
                        
                        # 对于 bitmask 字段，添加意义说明
                        if field.get('is_bitmask'):
                            meaning = field.get('meaning', '')
                            if meaning:
                                ftype = f"{ftype}"
                        
                        # 检测变化
                        changes = []
                        if prev_index is not None and prev_index != index:
                            changes.append(f"Index:{prev_index}→{index}")
                        if prev_type is not None and prev_type != ftype:
                            changes.append(f"Type changed")
                        if prev_default is not None and prev_default != default:
                            changes.append(f"Default changed")
                        
                        version_data_list.append({
                            'version': version,
                            'index': index,
                            'type': ftype,
                            'default': default,
                            'changes': ', '.join(changes) if changes else '',
                            'meaning': field.get('meaning', '')
                        })
                        
                        prev_index = index
                        prev_type = ftype
                        prev_default = default
                    else:
                        # 字段在该版本不存在
                        if prev_index is not None:
                            # 字段被删除
                            version_data_list.append({
                                'version': version,
                                'index': '-',
                                'type': '-',
                                'default': '-',
                                'changes': 'REMOVED'
                            })
                            prev_index = None
                            prev_type = None
                            prev_default = None
                
                # 输出该字段的所有版本
                first_row = True
                for vdata in version_data_list:
                    if first_row:
                        display_name = field_name if len(field_name) <= 25 else field_name[:22] + "..."
                        field_col = f"{display_name:25}"
                        first_row = False
                    else:
                        field_col = " " * 25
                    
                    type_display = vdata['type'] if len(vdata['type']) <= 20 else vdata['type'][:17] + "..."
                    default_display = vdata['default'] if len(vdata['default']) <= 19 else vdata['default'][:16] + "..."
                    meaning_display = vdata.get('meaning', '') if len(vdata.get('meaning', '')) <= 28 else vdata.get('meaning', '')[:25] + "..."
                    changes_display = vdata['changes'] if len(vdata['changes']) <= 17 else vdata['changes'][:14] + "..."
                    
                    # 确保 index 对齐
                    index_str = str(vdata['index']) if vdata['index'] != '-' else '-'
                    
                    lines.append(f"| {field_col} | {vdata['version']:7} | {index_str:^3} | {type_display:20} | {default_display:19} | {meaning_display:28} | {changes_display:17} |")
                
                # 字段间的分隔线
                if field_name != sorted_field_names[-1]:
                    lines.append("|---------------------------|---------|-----|----------------------|---------------------|------------------------------|-------------------|")
    
    lines.append(f"\n[!] = Changed from previous version")
    lines.append(f"Total metadata types with changes: {len(metadata_with_changes)}/{len(all_metadata_types)}")
    
    return "\n".join(lines)

def main():
    # 设置路径
    output_dir = Path("output")
    
    # 加载数据
    print("Loading version data...")
    version_data = load_version_data(output_dir)
    versions = sorted(version_data.keys())
    
    print(f"Found versions: {', '.join(versions)}")
    
    # 分析实体属性变化
    print("\nAnalyzing entity property changes...")
    entity_changes = analyze_entity_changes(version_data)
    with open("entity_changes.txt", 'w', encoding='utf-8') as f:
        f.write(entity_changes)
    print("Entity changes saved to: entity_changes.txt")
    
    # 分析 metadata 字段变化
    print("\nAnalyzing metadata field changes...")
    metadata_changes = analyze_metadata_changes(version_data)
    with open("metadata_changes.txt", 'w', encoding='utf-8') as f:
        f.write(metadata_changes)
    print("Metadata changes saved to: metadata_changes.txt")
    
    print("\nAnalysis complete!")

if __name__ == "__main__":
    main()