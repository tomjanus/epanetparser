"""Token-Oriented Object Notation (TOON) encoder for epanetparser.

Implements a minimal TOON encoder per SPEC v4.1 for the JSON data model.
Supports four array forms and object form for nested structures.

TOON Forms:
- Inline: Primitive arrays on header line (e.g., tags[3]: a,b,c)
- List: Non-uniform arrays, one - item per element
- Tabular: Uniform object arrays, declare fields once then stream rows
- Keyed Tabular: Objects of uniform objects, rows carry their own key
- Object: Nested objects using indentation
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union


Primitive = Union[str, int, float, bool, None]
JSONValue = Union[Primitive, Dict[str, Any], List[Any]]


class TOONEncoder:
    """Encodes Python objects (JSON data model) to TOON format."""

    def __init__(
        self,
        indent: str = "  ",
        delimiter: str = ",",
        max_inline_items: int = 10,
        max_inline_width: int = 120,
    ) -> None:
        """
        Parameters
        ----------
        indent : str
            Indentation string (default: two spaces)
        delimiter : str
            Field delimiter: ",", "\t", or "|" (default: comma)
        max_inline_items : int
            Max items for inline array form (default: 10)
        max_inline_width : int
            Max character width for inline form (default: 120)
        """
        self.indent = indent
        self.delimiter = delimiter
        self.max_inline_items = max_inline_items
        self.max_inline_width = max_inline_width

    def encode(self, value: JSONValue) -> str:
        """Encode a JSON-compatible value to TOON string."""
        lines = self._encode_value(value, depth=0, key=None)
        return "\n".join(lines)

    def _encode_value(
        self,
        value: JSONValue,
        depth: int,
        key: Optional[str] = None,
    ) -> List[str]:
        """Encode a value, returning list of lines."""
        if value is None:
            return [self._format_primitive(None, depth, key)]
        if isinstance(value, bool):
            return [self._format_primitive(value, depth, key)]
        if isinstance(value, (int, float)):
            return [self._format_primitive(value, depth, key)]
        if isinstance(value, str):
            return [self._format_primitive(value, depth, key)]
        if isinstance(value, list):
            return self._encode_array(value, depth, key)
        if isinstance(value, dict):
            return self._encode_object(value, depth, key)
        raise TypeError(f"Unsupported type: {type(value)}")

    def _format_primitive(
        self,
        value: Primitive,
        depth: int,
        key: Optional[str] = None,
    ) -> str:
        """Format a primitive value with optional key prefix."""
        prefix = f"{self.indent * depth}"
        if key is not None:
            prefix += f"{key}: "
        if value is None:
            return prefix + "null"
        if isinstance(value, bool):
            return prefix + ("true" if value else "false")
        if isinstance(value, (int, float)):
            if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                return prefix + "null"
            return prefix + str(value)
        if isinstance(value, str):
            quoted = self._quote_string(value)
            return prefix + quoted
        return prefix + "null"

    def _quote_string(self, s: str) -> str:
        """Quote a string if it contains special characters."""
        if not s:
            return '""'
        special_chars = set(' \t\n\r,:[]{}#\'\"')
        if any(c in special_chars for c in s) or s.startswith("-"):
            escaped = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            return f'"{escaped}"'
        return s

    def _encode_array(
        self,
        arr: List[Any],
        depth: int,
        key: Optional[str] = None,
    ) -> List[str]:
        """Encode an array, choosing the best form."""
        # Check if uniform objects (tabular form eligible) - do this first
        # so empty arrays of objects also use tabular form
        if self._is_uniform_objects(arr):
            return self._encode_tabular(arr, depth, key)
        if not arr and key == "issues":
            # Empty issues array - use tabular form with known fields
            return self._encode_tabular(arr, depth, key)

        if not arr:
            prefix = f"{self.indent * depth}"
            if key is not None:
                prefix += f"{key}: "
            return [prefix + "[]"]

        # Check if primitive array (inline form eligible)
        if self._is_primitive_array(arr):
            return self._encode_inline_array(arr, depth, key)

        # Fallback to list form
        return self._encode_list_form(arr, depth, key)

    def _is_primitive_array(self, arr: List[Any]) -> bool:
        """Check if array contains only primitives."""
        return all(
            isinstance(item, (str, int, float, bool, type(None)))
            for item in arr
        )

    def _is_uniform_objects(self, arr: List[Any]) -> bool:
        """Check if array contains uniform objects (same keys)."""
        if not arr:
            return False
        if not all(isinstance(item, dict) for item in arr):
            return False
        first_keys = set(arr[0].keys())
        return all(set(item.keys()) == first_keys for item in arr)

    def _encode_inline_array(
        self,
        arr: List[Primitive],
        depth: int,
        key: Optional[str] = None,
    ) -> List[str]:
        """Encode primitive array in inline form: key[N]: item1,item2,..."""
        prefix = f"{self.indent * depth}"
        if key is not None:
            prefix += f"{key}: "
        header = f"{prefix}[{len(arr)}]"
        if len(arr) <= self.max_inline_items:
            items_str = self.delimiter.join(
                self._format_inline_item(item) for item in arr
            )
            if len(header + ": " + items_str) <= self.max_inline_width:
                return [header + ": " + items_str]
        # Fallback to list form if too many items or too wide
        return self._encode_list_form(arr, depth, key)

    def _format_inline_item(self, item: Primitive) -> str:
        """Format a single item for inline array."""
        if item is None:
            return "null"
        if isinstance(item, bool):
            return "true" if item else "false"
        if isinstance(item, (int, float)):
            if isinstance(item, float) and (math.isnan(item) or math.isinf(item)):
                return "null"
            return str(item)
        if isinstance(item, str):
            return self._quote_string(item)
        return "null"

    def _encode_list_form(
        self,
        arr: List[Any],
        depth: int,
        key: Optional[str] = None,
    ) -> List[str]:
        """Encode array in list form: one - item per line."""
        lines = []
        prefix = f"{self.indent * depth}"
        if key is not None:
            lines.append(f"{prefix}{key}:")
            depth += 1
        for item in arr:
            item_lines = self._encode_value(item, depth, key="-")
            if item_lines:
                first = item_lines[0]
                if first.startswith(self.indent * depth + "- "):
                    lines.append(first)
                else:
                    lines.append(f"{self.indent * depth}- {first.lstrip()}")
                lines.extend(item_lines[1:])
        return lines

    def _encode_tabular(
        self,
        arr: List[Dict[str, Any]],
        depth: int,
        key: Optional[str] = None,
        fields: Optional[List[str]] = None,
    ) -> List[str]:
        """Encode uniform object array in tabular form: key[N]{fields}: row1, row2, ..."""
        # Determine fields from first object or provided list
        if fields is None:
            if not arr:
                # Default fields for ValidationReport issues
                fields = [
                    "code", "message", "severity", "rule_id", "ruleset_key",
                    "component_type", "component_name", "attribute",
                    "component_data", "context"
                ]
            else:
                fields = list(arr[0].keys())

        field_list = self.delimiter.join(fields)
        prefix = f"{self.indent * depth}"
        if key is not None:
            prefix += f"{key}"
        header = f"{prefix}[{len(arr)}]{{{field_list}}}:"
        lines = [header]

        for obj in arr:
            row_values = []
            for field in fields:
                value = obj.get(field)
                row_values.append(self._format_tabular_cell(value))
            lines.append(f"{self.indent * (depth + 1)}{self.delimiter.join(row_values)}")
        return lines

    def _format_tabular_cell(self, value: Any) -> str:
        """Format a cell value for tabular form."""
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                return "null"
            return str(value)
        if isinstance(value, str):
            return self._quote_string(value)
        if isinstance(value, dict):
            return self._encode_nested_object_inline(value)
        if isinstance(value, list):
            return self._encode_nested_array_inline(value)
        return "null"

    def _encode_nested_object_inline(self, obj: Dict[str, Any]) -> str:
        """Encode nested object inline for tabular cell."""
        parts = []
        for k, v in obj.items():
            cell = self._format_tabular_cell(v)
            parts.append(f"{k}:{cell}")
        return "{" + self.delimiter.join(parts) + "}"

    def _encode_nested_array_inline(self, arr: List[Any]) -> str:
        """Encode nested array inline for tabular cell."""
        if not arr:
            return "[]"
        if self._is_primitive_array(arr):
            items = [self._format_inline_item(item) for item in arr]
            return "[" + self.delimiter.join(items) + "]"
        return "[...]"  # Complex nested array - placeholder

    def _encode_object(
        self,
        obj: Dict[str, Any],
        depth: int,
        key: Optional[str] = None,
    ) -> List[str]:
        """Encode an object using indentation."""
        lines = []
        prefix = f"{self.indent * depth}"
        if key is not None:
            lines.append(f"{prefix}{key}:")
            depth += 1
        elif depth == 0:
            pass  # Root object - no key prefix
        else:
            depth += 1

        for k, v in obj.items():
            child_lines = self._encode_value(v, depth, key=k)
            lines.extend(child_lines)
        return lines


def encode(value: JSONValue, **kwargs: Any) -> str:
    """Convenience function to encode a value to TOON."""
    encoder = TOONEncoder(**kwargs)
    return encoder.encode(value)


def encode_validation_report(report_dict: Dict[str, Any]) -> str:
    """Encode a ValidationReport dict to TOON with optimized structure.

    Uses tabular form for the issues array since issues are uniform objects.
    """
    # Reorder keys for consistent output
    ordered = {}
    if "is_valid" in report_dict:
        ordered["is_valid"] = report_dict["is_valid"]
    if "counts" in report_dict:
        ordered["counts"] = report_dict["counts"]
    if "issues" in report_dict:
        ordered["issues"] = report_dict["issues"]
    # Add any other keys
    for k, v in report_dict.items():
        if k not in ordered:
            ordered[k] = v

    encoder = TOONEncoder()
    return encoder.encode(ordered)