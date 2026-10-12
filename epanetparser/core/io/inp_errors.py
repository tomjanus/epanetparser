"""Structured error classes for INP parsing.

These exceptions provide detailed, machine-readable information about
parsing failures, including line numbers, section context, EPANET-compatible
error codes, and actionable suggestions for AI agents and users.
"""
from __future__ import annotations
from typing import List, Optional
from dataclasses import dataclass, field


class InpParseError(Exception):
    """Base exception for INP parsing errors.
    
    Attributes:
        message: Human-readable error description.
        line_number: Line number in the INP file where error occurred (1-indexed).
        section: INP section name where error occurred (e.g., "[JUNCTIONS]").
        error_code: EPANET-compatible error code (e.g., "201", "209", "213").
        suggestions: List of actionable fix suggestions.
    """
    
    def __init__(
        self,
        message: str,
        line_number: Optional[int] = None,
        section: Optional[str] = None,
        error_code: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.line_number = line_number
        self.section = section
        self.error_code = error_code
        self.suggestions = suggestions or []
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.line_number is not None:
            parts.append(f"Line {self.line_number}")
        if self.section:
            parts.append(f"Section {self.section}")
        if self.error_code:
            parts.append(f"Error {self.error_code}")
        return " | ".join(parts)
    
    def to_dict(self) -> dict:
        """Return a dictionary representation for JSON serialization."""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "line_number": self.line_number,
            "section": self.section,
            "error_code": self.error_code,
            "suggestions": self.suggestions,
        }


class InpSyntaxError(InpParseError):
    """Syntax errors in the INP file structure.
    
    EPANET Error Codes:
    - 201: Invalid section header or unrecognized keyword
    - 202: Invalid data format (wrong number of fields, etc.)
    - 213: Invalid value for a parameter
    """
    
    def __init__(
        self,
        message: str,
        line_number: Optional[int] = None,
        section: Optional[str] = None,
        error_code: str = "201",
        suggestions: Optional[List[str]] = None,
    ) -> None:
        default_suggestions = [
            "Check section header spelling (e.g., [JUNCTIONS] not [JUNCTION])",
            "Verify data lines have correct number of fields",
            "Ensure semicolon comments are not inside data values",
        ]
        super().__init__(
            message=message,
            line_number=line_number,
            section=section,
            error_code=error_code,
            suggestions=suggestions or default_suggestions,
        )


class InpSemanticError(InpParseError):
    """Semantic errors: valid syntax but invalid references or values.
    
    EPANET Error Codes:
    - 203: Undefined object reference (curve, pattern, node, link)
    - 205: Invalid default pattern
    - 209: Invalid numeric value
    - 211: Invalid link connection (node not found)
    - 213: Invalid parameter value
    - 217: Missing required pump curve
    - 225: Invalid tank parameters
    """
    
    def __init__(
        self,
        message: str,
        line_number: Optional[int] = None,
        section: Optional[str] = None,
        error_code: str = "203",
        suggestions: Optional[List[str]] = None,
    ) -> None:
        default_suggestions = [
            "Define the referenced object before using it",
            "Check spelling of object names (case-sensitive)",
            "Ensure all CURVES and PATTERNS are defined before use",
        ]
        super().__init__(
            message=message,
            line_number=line_number,
            section=section,
            error_code=error_code,
            suggestions=suggestions or default_suggestions,
        )


class InpStructuralError(InpParseError):
    """Structural errors: missing required sections or fundamental issues.
    
    EPANET Error Codes:
    - 200: General file read error
    - 204: Missing required section
    """
    
    def __init__(
        self,
        message: str,
        line_number: Optional[int] = None,
        section: Optional[str] = None,
        error_code: str = "204",
        suggestions: Optional[List[str]] = None,
    ) -> None:
        default_suggestions = [
            "Ensure all required sections are present: [TITLE], [JUNCTIONS], [RESERVOIRS], [TANKS], [PIPES], [PUMPS], [VALVES], [PATTERNS]",
            "Check that the file is a valid EPANET INP file",
        ]
        super().__init__(
            message=message,
            line_number=line_number,
            section=section,
            error_code=error_code,
            suggestions=suggestions or default_suggestions,
        )


# Error code to exception mapping for common EPANET errors
EPANET_ERROR_MAP = {
    "200": InpStructuralError,
    "201": InpSyntaxError,
    "202": InpSyntaxError,
    "203": InpSemanticError,
    "204": InpStructuralError,
    "205": InpSemanticError,
    "209": InpSemanticError,
    "211": InpSemanticError,
    "213": InpSyntaxError,
    "217": InpSemanticError,
    "225": InpSemanticError,
}


def create_inp_error(
    error_code: str,
    message: str,
    line_number: Optional[int] = None,
    section: Optional[str] = None,
    suggestions: Optional[List[str]] = None,
) -> InpParseError:
    """Factory function to create appropriate error from EPANET error code."""
    error_class = EPANET_ERROR_MAP.get(error_code, InpParseError)
    return error_class(
        message=message,
        line_number=line_number,
        section=section,
        error_code=error_code,
        suggestions=suggestions,
    )