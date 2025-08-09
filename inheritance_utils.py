"""
Utilities for handling inheritance relationships and topological sorting.
"""
import re
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict, deque


SECTION_HEADER_RE = re.compile(r"^===\s*(.+?)\s*===\s*$")
INHERIT_RE = re.compile(
    r"\{\{\s*Metadata\s+inherit\|([^}|]+)(?:\|inherits=([^}]+))?\}\}", re.IGNORECASE
)


def collect_inheritance_relationships(lines: List[str]) -> tuple[List[str], Dict[str, Optional[str]]]:
    """
    Collect all inheritance relationships and section names from the source.
    Returns (section_names, inherit_map)
    """
    section_names = []
    inherit_map: Dict[str, Optional[str]] = {}
    
    for line in lines:
        stripped = line.strip()
        
        # Collect inheritance markers
        m_inh = INHERIT_RE.search(stripped)
        if m_inh:
            name, inherits = m_inh.group(1), m_inh.group(2) or None
            section_name = _normalize_whitespace(name)
            inherit_map[section_name] = _normalize_whitespace(inherits) if inherits else None
        
        # Find section headers
        m_sec = SECTION_HEADER_RE.match(stripped)
        if m_sec:
            section_name = _normalize_whitespace(m_sec.group(1))
            if section_name not in section_names:
                section_names.append(section_name)
    
    return section_names, inherit_map


def topological_sort(section_names: List[str], inherit_map: Dict[str, Optional[str]]) -> List[str]:
    """
    Topologically sort sections based on inheritance dependencies.
    Base classes (no parents) come first, then their children.
    """
    # Build dependency graph
    dependencies = defaultdict(set)  # section -> set of dependencies
    dependents = defaultdict(set)    # section -> set of sections that depend on it
    
    for section in section_names:
        parent = inherit_map.get(section)
        if parent and parent in section_names:
            dependencies[section].add(parent)
            dependents[parent].add(section)
    
    # Kahn's algorithm for topological sorting
    sorted_sections = []
    queue = deque()
    
    # Start with sections that have no dependencies (base classes)
    for section in section_names:
        if not dependencies[section]:
            queue.append(section)
    
    while queue:
        current = queue.popleft()
        sorted_sections.append(current)
        
        # Remove this section from dependencies of its dependents
        for dependent in dependents[current]:
            dependencies[dependent].discard(current)
            if not dependencies[dependent]:
                queue.append(dependent)
    
    # Handle any remaining sections (circular dependencies or missing parents)
    remaining = set(section_names) - set(sorted_sections)
    for section in remaining:
        sorted_sections.append(section)
    
    return sorted_sections


def calculate_base_index(section_name: str, inherit_map: Dict[str, Optional[str]], 
                        parsed_sections: Dict[str, Dict[str, Any]]) -> int:
    """
    Calculate the starting index for a section based on its inheritance chain.
    """
    base_index = 0
    current = inherit_map.get(section_name)
    
    # Build inheritance chain
    inheritance_chain = []
    visited = set()
    
    while current and current not in visited:
        visited.add(current)
        inheritance_chain.append(current)
        current = inherit_map.get(current)
    
    # Calculate base index by counting fields from all parents in inheritance chain
    for parent in reversed(inheritance_chain):  # Start from root
        if parent in parsed_sections:
            parent_fields = parsed_sections[parent].get("fields", [])
            base_index += len(parent_fields)
    
    return base_index


def _normalize_whitespace(text: str) -> str:
    """Normalize whitespace and remove extra spaces"""
    if not text:
        return ""
    # Replace multiple whitespace with single space
    text = re.sub(r"\s+", " ", text)
    return text.strip()
