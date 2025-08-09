import json
import re
from typing import Dict, List, Optional, Tuple, Any
from text_utils import (
    strip_code_tags, strip_wikilinks, strip_templates, 
    normalize_whitespace, cleanup_cell_text, meaning_to_camel_case
)
from inheritance_utils import (
    collect_inheritance_relationships, topological_sort, 
    calculate_base_index, SECTION_HEADER_RE, INHERIT_RE
)


WIKITABLE_START_PATTERN = re.compile(r"^\{\|\s*class=\"wikitable\"", re.IGNORECASE)
WIKITABLE_END_PATTERN = re.compile(r"^\|\}")
ROW_SEPARATOR_PATTERN = re.compile(r"^\|-")
HEADER_CELL_PATTERN = re.compile(r"^!\s*(.*)")
DATA_CELL_PATTERN = re.compile(r"^\|\s*(.*)")


def to_snake_case(name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9]+", "_", name.strip())
    name = re.sub(r"_+", "_", name)
    return name.lower().strip("_")


def parse_wikitable(lines: List[str], start_index: int) -> Tuple[int, Dict[str, Any]]:
    """Parse a MediaWiki wikitable and return the next line index and table data"""
    i = start_index
    headers = []
    rows = []
    current_row = []
    
    # Skip the opening table tag
    i += 1
    
    while i < len(lines):
        line = lines[i].rstrip("\n")
        stripped = line.strip()
        
        if WIKITABLE_END_PATTERN.match(stripped):
            if current_row:
                rows.append(current_row)
            break
        
        if ROW_SEPARATOR_PATTERN.match(stripped):
            if current_row:
                rows.append(current_row)
                current_row = []
        elif HEADER_CELL_PATTERN.match(stripped):
            m = HEADER_CELL_PATTERN.match(stripped)
            if m:
                headers.append(cleanup_cell_text(m.group(1)))
        elif DATA_CELL_PATTERN.match(stripped):
            m = DATA_CELL_PATTERN.match(stripped)
            if m:
                cell_content = cleanup_cell_text(m.group(1))
                current_row.append(cell_content)
        elif stripped and not stripped.startswith("|"):
            # Multi-line cell content continuation
            if current_row:
                current_row[-1] += " " + cleanup_cell_text(stripped)
        
        i += 1
    
    return i + 1, {"headers": headers, "rows": rows}


def parse_entities_table(lines: List[str]) -> Dict[str, Dict[str, Any]]:
    """Parse the main entities table"""
    entities = {}
    i = 0
    
    while i < len(lines):
        line = lines[i].rstrip("\n")
        stripped = line.strip()
        
        if WIKITABLE_START_PATTERN.match(stripped):
            end_i, table = parse_wikitable(lines, i)
            
            for row in table["rows"]:
                if len(row) >= 5:
                    type_text = row[0]
                    name = row[1]
                    bbox_xz = row[2]
                    bbox_y = row[3]
                    entity_id = row[4]
                    
                    # Extract minecraft ID
                    entity_id = re.sub(r"</?code>", "", entity_id)
                    
                    # Try to parse type as integer
                    type_index = None
                    if type_text and type_text.strip().isdigit():
                        type_index = int(type_text.strip())
                    
                    entities[entity_id] = {
                        "type_index": type_index if type_index is not None else type_text,
                        "name": name,
                        "bounding_box_xz": bbox_xz,
                        "bounding_box_y": bbox_y,
                    }
            
            i = end_i
            continue
        
        i += 1
    
    return entities


def _find_section_lines(lines: List[str], section_name: str) -> Tuple[int, int]:
    """Find the start and end line indices for a specific section"""
    start_line = -1
    end_line = len(lines)
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        m_sec = SECTION_HEADER_RE.match(stripped)
        if m_sec:
            current_section = normalize_whitespace(m_sec.group(1))
            if current_section == section_name:
                start_line = i
            elif start_line != -1:
                # Found next section, end current one
                end_line = i
                break
    
    return start_line, end_line


def _parse_section_by_name(
    lines: List[str], 
    section_name: str, 
    by_name_result: Dict[str, Dict[str, Any]], 
    inherit_map: Dict[str, Optional[str]]
) -> None:
    """Parse a specific section by name"""
    start_line, end_line = _find_section_lines(lines, section_name)
    
    if start_line == -1:
        return
    
    # Initialize section
    by_name_result.setdefault(section_name, {"inherits": None, "fields": []})
    
    # Calculate starting index
    base_index = calculate_base_index(section_name, inherit_map, by_name_result)
    
    i = start_line + 1  # Skip header line
    last_main_row = None
    index_counter = base_index - 1
    
    while i < end_line:
        line = lines[i].rstrip("\n")
        stripped = line.strip()
        
        # Short-circuit: "No additional metadata."
        if stripped.lower().startswith("no additional metadata"):
            i += 1
            continue
        
        # Parse wikitable if present
        if WIKITABLE_START_PATTERN.match(stripped):
            table_end_i, table = parse_wikitable(lines, i)
            
            fields = by_name_result[section_name].setdefault("fields", [])
            
            for raw_row in table["rows"]:
                cells = raw_row
                
                # Detect bitmask rows
                if (
                    len(cells) == 2
                    and re.match(r"^0x[0-9A-Fa-f]+$", cells[0] or "")
                    and last_main_row is not None
                ):
                    # Remove meaning and name from parent field (bitmask fields don't have these)
                    if "meaning" in last_main_row:
                        del last_main_row["meaning"]
                    if "name" in last_main_row:
                        del last_main_row["name"]
                    
                    # Add bitmask item
                    bitmask_meaning = cells[1]
                    bitmask_item = {
                        "mask": cells[0],
                        "meaning": bitmask_meaning,
                        "name": meaning_to_camel_case(bitmask_meaning)
                    }
                    last_main_row.setdefault("bitmask", []).append(bitmask_item)
                    continue
                
                # Parse regular field
                index_counter += 1
                
                row_obj = {
                    "index": index_counter,
                    "type": cells[1] if len(cells) > 1 else "Unknown",
                    "default": cells[4] if len(cells) > 4 else cells[-1] if cells else "",
                    "meaning": cells[2] if len(cells) > 2 else "",
                    "name": meaning_to_camel_case(cells[2]) if len(cells) > 2 and cells[2] else f"field{index_counter}"
                }
                
                fields.append(row_obj)
                last_main_row = row_obj
            
            i = table_end_i
            continue
        
        i += 1


def parse_metadata_sections(
    lines: List[str], name_to_entity_id: Optional[Dict[str, str]] = None
) -> Dict[str, Dict[str, Any]]:
    """Parse metadata sections using topological sorting"""
    name_to_entity_id = name_to_entity_id or {}
    by_name_result: Dict[str, Dict[str, Any]] = {}
    
    # Collect inheritance relationships and section names
    section_names, inherit_map = collect_inheritance_relationships(lines)
    
    # Topologically sort sections by inheritance dependencies
    sorted_sections = topological_sort(section_names, inherit_map)
    
    # Parse sections in dependency order
    for section_name in sorted_sections:
        _parse_section_by_name(lines, section_name, by_name_result, inherit_map)
    
    # Set inheritance info and convert keys
    for section_name in by_name_result:
        parent = inherit_map.get(section_name)
        if parent:
            # Convert to minecraft: format
            if section_name in name_to_entity_id:
                by_name_result[section_name]["inherits"] = name_to_entity_id[section_name]
            else:
                by_name_result[section_name]["inherits"] = f"minecraft:{to_snake_case(parent)}"
    
    # Convert result keys to minecraft: format
    converted_result = {}
    for section_name, data in by_name_result.items():
        if section_name in name_to_entity_id:
            key = name_to_entity_id[section_name]
        else:
            key = f"minecraft:{to_snake_case(section_name)}"
        converted_result[key] = data
    
    return converted_result


def extract(text: str) -> Dict[str, Any]:
    """Main extraction function"""
    lines = text.split("\n")
    
    # Extract entities table
    entities = parse_entities_table(lines)
    
    # Create name to entity ID mapping
    name_to_entity_id = {}
    for entity_id, entity_data in entities.items():
        name = entity_data["name"]
        name_to_entity_id[name] = entity_id
    
    # Find Entity Metadata section and extract only from there
    metadata_start = -1
    for i, line in enumerate(lines):
        if re.match(r"^==\s*Entity Metadata\s*==\s*$", line.strip()):
            metadata_start = i
            break
    
    if metadata_start == -1:
        metadata = {}
    else:
        # Extract metadata sections only from Entity Metadata section onward
        metadata_lines = lines[metadata_start:]
        metadata = parse_metadata_sections(metadata_lines, name_to_entity_id)
    
    # Extract version
    version = "unknown"
    for line in lines[:10]:
        if "1.21" in line:
            # Extract version number
            version_match = re.search(r"1\.21\.[\d]+", line)
            if version_match:
                version = version_match.group(0)
                break
    
    return {
        "version": version,
        "entities": entities,
        "metadata": metadata
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="source.txt")
    parser.add_argument("--output", default="output.json")
    args = parser.parse_args()
    
    with open(args.input, "r", encoding="utf-8") as f:
        text = f.read()
    data = extract(text)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
