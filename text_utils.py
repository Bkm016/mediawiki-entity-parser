"""
Text processing utilities for MediaWiki content parsing.
"""
import re
from typing import List, Dict, Any, Optional

# Try to import the modern NLP-based solution
try:
    from nlp_utils import modern_meaning_to_camel_case
    MODERN_NLP_AVAILABLE = True
except ImportError:
    MODERN_NLP_AVAILABLE = False
    print("⚠️  警告: 现代 NLP 功能不可用，将使用基础模式。")
    print("   要获得更好的命名效果，请安装: pip install scikit-learn keybert yake nltk")


def strip_code_tags(text: str) -> str:
    """Remove <code>...</code> tags"""
    return re.sub(r"<code[^>]*>(.*?)</code>", r"\1", text)


def strip_wikilinks(text: str) -> str:
    """Convert [[target|label]] to label and [[target]] to target"""
    # [[target|label]] -> label
    text = re.sub(r"\[\[([^|\]]+)\|([^\]]+)\]\]", r"\2", text)
    # [[target]] -> target
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    return text


def strip_templates(text: str) -> str:
    """Extract content from specific templates and remove others"""
    # Extract content from specific templates
    text = re.sub(r"\{\{\s*Metadata\s+type\|([^}]+)\}\}", r"\1", text, flags=re.IGNORECASE)
    text = re.sub(r"\{\{\s*Metadata\s+id\|([^}]*)\}\}", r"\1", text, flags=re.IGNORECASE)
    text = re.sub(r"\{\{\s*Type\|([^}]+)\}\}", r"\1", text, flags=re.IGNORECASE)
    
    # Remove all other templates
    text = re.sub(r"\{\{[^}]*\}\}", "", text)
    
    return text


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace and remove extra spaces"""
    if not text:
        return ""
    # Replace multiple whitespace with single space
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def cleanup_cell_text(text: str) -> str:
    """Apply all text cleaning operations"""
    if not text:
        return ""
    text = strip_code_tags(text)
    text = strip_wikilinks(text)
    text = strip_templates(text)
    
    # Remove MediaWiki table cell attributes
    text = re.sub(r"^(?:rowspan|colspan)=\"?\d+\"?\|\s*", "", text)
    text = re.sub(r"^style=\"[^\"]*\"\|\s*", "", text, flags=re.IGNORECASE)
    
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    
    text = normalize_whitespace(text)
    return text


def meaning_to_camel_case(meaning: str) -> str:
    """Convert meaning text to camelCase field name using NLP or pattern-based approach"""
    if not meaning:
        return "field"
    
    # Try modern NLP-based conversion first
    if MODERN_NLP_AVAILABLE:
        try:
            return modern_meaning_to_camel_case(meaning)
        except Exception:
            # Fall back to pattern-based approach if NLP fails
            pass

    # Clean the text
    text = meaning.strip()

    # Remove quotes and extra punctuation
    text = re.sub(r"['\"`]", "", text)

    # Remove parenthetical explanations and extra info
    text = re.sub(r"\s*\([^)]*\)", "", text)
    text = re.sub(r"\s*\{[^}]*\}", "", text)
    text = re.sub(r"\s*\[[^\]]*\]", "", text)

    # Remove enumeration patterns and explanations after colons/semicolons
    text = re.sub(r"\s*\*[^*]*(?:\*|$)", "", text)
    text = re.sub(r"[;:]\s*.*$", "", text)  # Remove everything after : or ;
    text = re.sub(r"\?\s*.*$", "", text)    # Remove everything after ?
    text = re.sub(r"\.\s+.*$", "", text)    # Remove secondary sentences

    # Remove explanatory phrases and redundant words
    text = re.sub(r"\s*-\s*.*$", "", text)  # Remove everything after dash
    text = re.sub(r"^the\s+", "", text, flags=re.IGNORECASE)  # Remove leading "the"
    text = re.sub(r"^number\s+of\s+", "", text, flags=re.IGNORECASE)  # "Number of X" -> "X"
    text = re.sub(r"^total\s+", "", text, flags=re.IGNORECASE)  # "Total X" -> "X"
    
    text = text.strip()

    # Extract all words first
    all_words = re.findall(r"[A-Za-z]+", text)
    
    if not all_words:
        return "field"
    
    # Remove common filler words
    filler_words = {"a", "an", "the", "of", "in", "on", "at", "to", "for", "with", "by", "that", "which", "used"}
    words = [w for w in all_words if w.lower() not in filler_words]
    
    if not words:
        return "field"
    
    # Identify semantic patterns dynamically
    first_word = words[0].lower()
    
    # Boolean prefix pattern
    if first_word in ["is", "has", "can"]:
        content_words = words[1:]  # Skip the boolean prefix
        if content_words:
            # Use natural word order, just limit length
            limited_words = content_words[:4]  # Keep reasonable length
            return first_word + "".join(word.capitalize() for word in limited_words)
        return first_word
    
    # Time/measurement suffix pattern
    last_word = words[-1].lower()
    time_suffixes = {"timer", "time", "ticks", "duration", "delay", "level", "state", "type", "variant", "mode"}
    
    if last_word in time_suffixes:
        if len(words) > 1:
            # Take words before the suffix
            prefix_words = words[:-1]
            # Smart limit based on suffix type
            if last_word in ["timer", "time", "ticks"]:
                max_prefix = 3
            else:
                max_prefix = 2
            
            prefix_words = prefix_words[:max_prefix]
            
            if prefix_words:
                base = "".join(word.capitalize() if i > 0 else word.lower() 
                             for i, word in enumerate(prefix_words))
                
                # Preserve important suffixes
                if last_word in ["timer", "ticks"]:
                    return base + last_word.capitalize()
                elif last_word == "time":
                    return base + "Time"
                elif last_word in ["level", "state", "type", "variant", "mode"]:
                    return base + last_word.capitalize()
                else:
                    return base
        
        # If only one word (the suffix itself)
        return last_word
    
    # ID/Entity pattern
    if "id" in [w.lower() for w in words] or "entity" in [w.lower() for w in words]:
        # Find meaningful words (not id/entity and not filler)
        meaningful = [w for w in words if w.lower() not in {"id", "entity"}]
        
        if meaningful:
            # Take first 2-3 meaningful words
            base_words = meaningful[:3]
            base = "".join(word.capitalize() if i > 0 else word.lower() 
                         for i, word in enumerate(base_words))
            
            # Add appropriate suffix
            if "id" in [w.lower() for w in words]:
                return base + "Id" if base and not base.endswith("Id") else base or "id"
            else:
                return base + "Entity" if base and not base.endswith("Entity") else base or "entity"
    
    # Default: smart word selection based on semantic density
    total_chars = sum(len(w) for w in words)
    
    if total_chars <= 15:  # Short enough, keep all words
        max_words = len(words)
    elif total_chars <= 25:  # Medium length, limit to 4 words
        max_words = 4
    else:  # Long description, prioritize first 3 words
        max_words = 3
    
    final_words = words[:max_words]
    
    # Convert to camelCase
    if len(final_words) == 1:
        return final_words[0].lower()
    else:
        return final_words[0].lower() + "".join(word.capitalize() for word in final_words[1:])
