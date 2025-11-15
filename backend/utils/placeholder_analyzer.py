"""
Placeholder Analyzer

Scans a Google Slides presentation to detect placeholders and returns
their names, inferred types, slide/element IDs, size, and transform
properties. Outputs a structured JSON report.
"""

import argparse
import json
import os
import re
import unicodedata
from typing import Any, Dict, List, Optional

from core.slides_client import SlidesClient


PLACEHOLDER_PATTERN = re.compile(r"\{\{([^}]+)\}\}")


def _clean_placeholder_name(name: str) -> str:
    """
    Clean and normalize placeholder names extracted from presentation text.
    Handles Unicode characters, quotes, special characters.
    """
    if not name:
        return ""
    
    # Remove leading/trailing whitespace
    name = name.strip()
    
    # Skip if name is too short (likely empty or just a special character)
    if len(name) < 1:
        return ""
    
    # Check for Unicode quote character \u0022 (regular double quote)
    # or if name is just a quote character
    if name in ['\u0022', '"', "'", '\u201c', '\u201d', '\u2018', '\u2019']:
        return ""
    
    # Replace common Unicode quotes with regular quotes first
    name = name.replace('\u201c', '"')  # Left double quotation mark
    name = name.replace('\u201d', '"')  # Right double quotation mark
    name = name.replace('\u2018', "'")  # Left single quotation mark
    name = name.replace('\u2019', "'")  # Right single quotation mark
    name = name.replace('\u201b', "'")  # Single high-reversed-9 quotation mark
    name = name.replace('\u2032', "'")  # Prime
    name = name.replace('\u2033', '"')   # Double prime
    name = name.replace('\u0022', '"')  # Unicode regular quote (explicit check)
    
    # Replace Unicode dashes with hyphens
    name = name.replace('\u2013', '-')  # En dash
    name = name.replace('\u2014', '-')   # Em dash
    name = name.replace('\u2015', '-')  # Horizontal bar
    
    # Strip quotes from the beginning/end (but keep them if they're part of the actual content)
    name = name.strip('"').strip()
    name = name.strip("'").strip()
    
    # Check if after stripping quotes, we're left with nothing or just special characters
    if len(name) < 1:
        return ""
    
    # Remove quotes if they appear to be surrounding the entire text (not part of content)
    if len(name) >= 2 and name[0] in ['"', "'"] and name[-1] in ['"', "'"]:
        name = name[1:-1].strip()
    
    # If after removing surrounding quotes we have nothing, skip it
    if len(name) < 1:
        return ""
    
    # Remove other special characters that might break matching
    # Keep alphanumeric, space, underscore, and hyphen
    cleaned = ''.join(c for c in name if c.isalnum() or c in ' _-')
    
    # If cleaned result is too short or empty, skip it
    if len(cleaned) < 1:
        return ""
    
    # Normalize spaces (replace multiple spaces with single space)
    cleaned = ' '.join(cleaned.split())
    
    return cleaned.strip()


def _load_placeholder_mapping() -> Dict[str, Any]:
    mapping_path = os.path.join("templates", "placeholder_mapping.json")
    if not os.path.exists(mapping_path):
        return {}
    try:
        with open(mapping_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("placeholder_mappings", {}) or {}
    except Exception:
        return {}


def _infer_type(placeholder_name: str, mapping: Dict[str, Any]) -> str:
    entry = mapping.get(placeholder_name)
    if entry and isinstance(entry, dict) and entry.get("type"):
        return entry["type"]

    normalized = placeholder_name.strip().lower()
    if normalized in {"logo", "companylogo"}:
        return "IMAGE"
    if normalized in {"image_1", "image_2", "image_3", "backgroundimage", "chart_1"}:
        return "IMAGE"
    if normalized.startswith("scope_img") or normalized.startswith("d_i_image"):
        return "IMAGE"
    if "color" in normalized:
        return "COLOR"
    if "logo" in normalized and normalized != "companylogo":
        return "EMOJI"
    if "heading" in normalized or "head" in normalized:
        return "TITLE"
    if "para" in normalized or "paragraph" in normalized:
        return "PARAGRAPH"
    if "title" in normalized or normalized.endswith("name"):
        return "TITLE"
    if "subtitle" in normalized or "tagline" in normalized:
        return "SUBTITLE"
    return "TEXT"


def _extract_text_from_shape(shape: Dict[str, Any]) -> str:
    text_obj = shape.get("text")
    if not text_obj:
        return ""
    buffer: List[str] = []
    for te in text_obj.get("textElements", []) or []:
        if "textRun" in te and te["textRun"].get("content"):
            buffer.append(te["textRun"]["content"])
        elif "autoText" in te and te["autoText"].get("content"):
            buffer.append(te["autoText"]["content"])
    return "".join(buffer)


def _pick_size_transform(element: Dict[str, Any]) -> Dict[str, Any]:
    # Prefer top-level size/transform if present, else fall back to elementProperties
    element_props = element.get("elementProperties", {}) or {}
    size = element.get("size") or element_props.get("size")
    transform = element.get("transform") or element_props.get("transform")
    return {
        "size": size,
        "transform": transform,
        "element_properties": element_props,
    }


def _compute_bounding_box(size: Optional[Dict[str, Any]], transform: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not size or not transform:
        return None
    try:
        width_mag = ((size.get("width") or {}).get("magnitude"))
        height_mag = ((size.get("height") or {}).get("magnitude"))
        scale_x = transform.get("scaleX", 1.0)
        scale_y = transform.get("scaleY", 1.0)
        translate_x = transform.get("translateX", 0.0)
        translate_y = transform.get("translateY", 0.0)
        unit = (size.get("width") or {}).get("unit", "PT")
        if width_mag is None or height_mag is None:
            return None
        width = width_mag * scale_x
        height = height_mag * scale_y
        return {
            "x": translate_x,
            "y": translate_y,
            "width": width,
            "height": height,
            "unit": unit,
        }
    except Exception:
        return None


def analyze_presentation(presentation_id: str) -> Dict[str, Any]:
    client = SlidesClient()
    presentation = client.get_presentation(presentation_id)
    if not presentation:
        raise RuntimeError("Could not load presentation")

    mapping = _load_placeholder_mapping()

    report: Dict[str, Any] = {
        "presentationId": presentation_id,
        "title": presentation.get("title"),
        "placeholders": [],
    }

    for slide in presentation.get("slides", []) or []:
        slide_id = slide.get("objectId")
        for element in slide.get("pageElements", []) or []:
            element_id = element.get("objectId")

            # Shapes (text boxes) with placeholders
            if "shape" in element and element["shape"].get("text"):
                text_content = _extract_text_from_shape(element["shape"]) or ""
                details = _pick_size_transform(element)
                bbox = _compute_bounding_box(details.get("size"), details.get("transform"))
                
                for name in PLACEHOLDER_PATTERN.findall(text_content):
                    # Special handling for u0022 Unicode quote placeholder
                    if name.strip().lower() == 'u0022':
                        # Store as a special quote placeholder that will be replaced with the quote character
                        # For u0022 placeholder, replace with actual quote
                        replacement_char = '"'
                        placeholder_text = f"{{{{{name.strip()}}}}}"
                        
                        report["placeholders"].append({
                            "placeholder": placeholder_text,
                            "name": 'u0022',  # Use u0022 as the name for matching
                            "inferred_type": "TEXT",
                            "slide_id": slide_id,
                            "element_id": element_id,
                            "size": details.get("size"),
                            "transform": details.get("transform"),
                            "bounding_box": bbox,
                            "element_properties": details.get("element_properties"),
                            "source": "shape",
                            "text_snippet": text_content[:120],
                            "is_quote": True  # Flag to indicate this is a quote placeholder
                        })
                        continue
                    
                    # Clean the placeholder name to handle Unicode and special characters
                    cleaned_name = _clean_placeholder_name(name)
                    if not cleaned_name:
                        continue  # Skip empty placeholders
                    
                    report["placeholders"].append({
                        "placeholder": f"{{{{{cleaned_name}}}}}",
                        "name": cleaned_name,
                        "inferred_type": _infer_type(cleaned_name, mapping),
                        "slide_id": slide_id,
                        "element_id": element_id,
                        "size": details.get("size"),
                        "transform": details.get("transform"),
                        "bounding_box": bbox,
                        "element_properties": details.get("element_properties"),
                        "source": "shape",
                        "text_snippet": text_content[:120],
                    })

            # Tables that may contain placeholders inside cells
            if "table" in element:
                table = element.get("table") or {}
                rows = table.get("tableRows", []) or []
                for row in rows:
                    for cell in (row.get("tableCells", []) or []):
                        cell_text = cell.get("text") or {}
                        buffer: List[str] = []
                        for te in cell_text.get("textElements", []) or []:
                            if "textRun" in te and te["textRun"].get("content"):
                                buffer.append(te["textRun"]["content"])
                        text_content = "".join(buffer)
                        if not text_content:
                            continue
                        for name in PLACEHOLDER_PATTERN.findall(text_content):
                            # Special handling for u0022 Unicode quote placeholder in tables
                            if name.strip().lower() == 'u0022':
                                # Store as a special quote placeholder
                                replacement_char = '"'
                                placeholder_text = f"{{{{{name.strip()}}}}}"
                                
                                report["placeholders"].append({
                                    "placeholder": placeholder_text,
                                    "name": 'u0022',  # Use u0022 as the name for matching
                                    "inferred_type": "TEXT",
                                    "slide_id": slide_id,
                                    "element_id": element_id,
                                    "size": details.get("size"),
                                    "transform": details.get("transform"),
                                    "bounding_box": bbox,
                                    "element_properties": details.get("element_properties"),
                                    "source": "table",
                                    "text_snippet": text_content[:120],
                                    "is_quote": True
                                })
                                continue
                            
                            # Clean the placeholder name to handle Unicode and special characters
                            cleaned_name = _clean_placeholder_name(name)
                            if not cleaned_name:
                                continue  # Skip empty placeholders
                            
                            details = _pick_size_transform(element)
                            bbox = _compute_bounding_box(details.get("size"), details.get("transform"))
                            report["placeholders"].append({
                                "placeholder": f"{{{{{cleaned_name}}}}}",
                                "name": cleaned_name,
                                "inferred_type": _infer_type(cleaned_name, mapping),
                                "slide_id": slide_id,
                                "element_id": element_id,
                                "size": details.get("size"),
                                "transform": details.get("transform"),
                                "bounding_box": bbox,
                                "element_properties": details.get("element_properties"),
                                "source": "table",
                                "text_snippet": text_content[:120],
                            })

    return report


def _save_report(report: Dict[str, Any], out_path: Optional[str]) -> str:
    path = out_path or os.path.join("logs", "placeholder_report.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze placeholders in a Google Slides presentation")
    parser.add_argument("presentation_id", help="The Google Slides presentation ID")
    parser.add_argument("--out", dest="out", help="Output JSON file path", default=None)
    args = parser.parse_args()

    report = analyze_presentation(args.presentation_id)
    out_path = _save_report(report, args.out)
    print(f"Placeholder analysis saved to: {out_path}")


if __name__ == "__main__":
    main()


