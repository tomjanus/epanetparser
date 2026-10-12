"""Standalone INP file parser that produces a WNTR-compatible dictionary.

This module parses EPANET INP files directly into the dictionary format
used by WNTR's JSON representation, without building a WaterNetworkModel.
This separates parsing from model construction and validation.

The parser handles all standard INP sections and performs unit conversions
to SI units (matching WNTR's internal representation).
"""
from __future__ import annotations

import logging
import re
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .inp_errors import (
    InpParseError,
    InpSyntaxError,
    InpSemanticError,
    create_inp_error,
)
from .epanet.util import (
    FlowUnits,
    HydParam,
    MassUnits,
    MixType,
    QualParam,
    from_si,
    to_si,
)

logger = logging.getLogger(__name__)

# INP section headers in parsing order
_INP_SECTIONS = [
    "[TITLE]",
    "[OPTIONS]",
    "[JUNCTIONS]",
    "[RESERVOIRS]",
    "[TANKS]",
    "[PIPES]",
    "[PUMPS]",
    "[VALVES]",
    "[EMITTERS]",
    "[CURVES]",
    "[PATTERNS]",
    "[ENERGY]",
    "[STATUS]",
    "[CONTROLS]",
    "[RULES]",
    "[DEMANDS]",
    "[QUALITY]",
    "[REACTIONS]",
    "[SOURCES]",
    "[MIXING]",
    "[TIMES]",
    "[REPORT]",
    "[COORDINATES]",
    "[VERTICES]",
    "[LABELS]",
    "[BACKDROP]",
    "[TAGS]",
    "[END]",
]

# EPANET error codes for reference
EN_ERROR_CODES = {
    200: "one or more errors in input file",
    201: "syntax error",
    202: "illegal numeric value",
    203: "undefined node",
    204: "undefined link",
    205: "undefined time pattern",
    206: "undefined curve",
    207: "attempt to control a CV/GPV link",
    208: "illegal PDA pressure limits",
    209: "illegal node property value",
    211: "illegal link property value",
    212: "undefined trace node",
    213: "invalid option value",
    214: "too many characters in input line",
    215: "duplicate ID label",
    216: "reference to undefined pump",
    217: "pump has no head curve or power defined",
    219: "illegal valve connection to tank node",
    220: "illegal valve connection to another valve",
    221: "misplaced rule clause in rule-based control",
    222: "link assigned same start and end nodes",
}


class InpParser:
    """Parses an EPANET INP file into a WNTR-compatible dictionary."""

    def __init__(self, filepath: Union[str, Path]) -> None:
        self.filepath = Path(filepath)
        self.lines: List[Tuple[int, str]] = []
        self.sections: Dict[str, List[Tuple[int, str]]] = OrderedDict()
        self.curves: Dict[str, List[Tuple[float, float]]] = OrderedDict()
        self.flow_units: Optional[FlowUnits] = None
        self.mass_units: MassUnits = MassUnits.mg
        self.line_number = 0
        self.current_section: Optional[str] = None

        # Data structures matching WNTR dict output
        self.result: Dict[str, Any] = {
            "version": "wntr-1.4.0",
            "comment": "WaterNetworkModel - all values given in SI units",
            "name": str(self.filepath),
            "references": [],
            "options": {
                "time": {},
                "hydraulic": {
                    "headloss": "H-W",
                    "hydraulics": None,
                    "hydraulics_filename": None,
                    "viscosity": 1.0,
                    "specific_gravity": 1.0,
                    "pattern": None,
                    "demand_multiplier": 1.0,
                    "demand_model": "DDA",
                    "minimum_pressure": 0.0,
                    "required_pressure": 0.07,
                    "pressure_exponent": 0.5,
                    "emitter_exponent": 0.5,
                    "trials": 50,
                    "accuracy": 0.01,
                    "unbalanced": "CONTINUE",
                    "unbalanced_value": 10,
                    "checkfreq": 2,
                    "maxcheck": 10,
                    "damplimit": 0.0,
                    "headerror": 0.0,
                    "flowchange": 0.0,
                    "inpfile_units": "CFS",
                    "inpfile_pressure_units": None,
                },
                "report": {},
                "quality": {},
                "reaction": {},
                "energy": {},
                "graphics": {},
                "user": {},
            },
            "curves": [],
            "patterns": [],
            "nodes": [],
            "links": [],
            "sources": [],
            "controls": [],
        }

        # Tracking for semantic validation
        self._defined_nodes: set = set()
        self._defined_links: set = set()
        self._defined_curves: set = set()
        self._defined_patterns: set = set()
        self._referenced_curves: Dict[str, int] = {}  # curve_name -> line_number
        self._referenced_patterns: Dict[str, int] = {}  # pattern_name -> line_number
        
        # Store TITLE content separately
        self._title_lines: List[str] = []

    def parse(self) -> Dict[str, Any]:
        """Parse the INP file and return the dictionary representation."""
        self._read_file()
        self._parse_sections()
        self._validate_references()
        return self.result

    def _read_file(self) -> None:
        """Read the INP file and organize lines by section."""
        if not self.filepath.exists():
            raise InpParseError(
                f"Input file not found: {self.filepath}",
                error_code="200",
                suggestions=["Check the file path", "Ensure the file exists"],
            )

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(self.filepath, "r", encoding="latin-1") as f:
                content = f.read()

        # Initialize sections
        for sec in _INP_SECTIONS:
            self.sections[sec] = []

        self.current_section = None
        self.line_number = 0

        for line in content.splitlines():
            self.line_number += 1
            stripped = line.strip()

            # Skip empty lines
            if not stripped:
                continue

            # Handle section headers
            if stripped.startswith("["):
                self._handle_section_header(stripped)
                continue

            # Handle comments before any section
            if self.current_section is None and stripped.startswith(";"):
                self._title_lines.append(stripped[1:].strip())
                continue

            # Handle comments within a section
            if stripped.startswith(";"):
                continue

            # Regular data line
            if self.current_section is not None:
                self.sections[self.current_section].append((self.line_number, stripped))
            else:
                logger.debug("Line outside any section at line %d: %s", self.line_number, stripped)

    def _handle_section_header(self, line: str) -> None:
        """Process a section header line."""
        # Extract section name (e.g., "[JUNCTIONS]" from "[JUNCTIONS] ; comment")
        match = re.match(r"(\[\w+\])", line.upper())
        if not match:
            raise InpSyntaxError(
                f"Invalid section header: {line}",
                line_number=self.line_number,
                error_code="201",
            )

        section = match.group(1)

        # Handle common variations (extra S, missing S)
        if section not in _INP_SECTIONS:
            # Try adding S
            if section.endswith("]"):
                base = section[:-1]
                if base + "S]" in _INP_SECTIONS:
                    section = base + "S]"
            # Try removing S
            if section.endswith("S]"):
                base = section[:-2]
                if base + "]" in _INP_SECTIONS:
                    section = base + "]"

        if section not in _INP_SECTIONS:
            raise InpSyntaxError(
                f"Unknown section: {section}",
                line_number=self.line_number,
                section=section,
                error_code="201",
                suggestions=[f"Valid sections: {', '.join(_INP_SECTIONS)}"],
            )

        if section == "[END]":
            self.current_section = None
        else:
            self.current_section = section

    def _parse_sections(self) -> None:
        """Parse each section in the correct order."""
        # Order matters: some sections depend on others
        parse_order = [
            "[TITLE]",
            "[OPTIONS]",
            "[TIMES]",
            "[REPORT]",
            "[CURVES]",
            "[PATTERNS]",
            "[JUNCTIONS]",
            "[RESERVOIRS]",
            "[TANKS]",
            "[PIPES]",
            "[PUMPS]",
            "[VALVES]",
            "[EMITTERS]",
            "[COORDINATES]",
            "[VERTICES]",
            "[ENERGY]",
            "[STATUS]",
            "[DEMANDS]",
            "[QUALITY]",
            "[REACTIONS]",
            "[SOURCES]",
            "[MIXING]",
            "[CONTROLS]",
            "[RULES]",
            "[LABELS]",
            "[BACKDROP]",
            "[TAGS]",
        ]

        for section in parse_order:
            if section in self.sections and self.sections[section]:
                self._parse_section(section)

        # Set metadata from TITLE section
        if self._title_lines:
            self.result["comment"] = "\n".join(self._title_lines)

    def _parse_section(self, section: str) -> None:
        """Dispatch to section-specific parser."""
        parser_method = getattr(self, f"_parse_{section[1:-1].lower()}", None)
        if parser_method:
            parser_method()
        else:
            logger.debug("No parser for section: %s", section)

    def _split_line(self, line: str) -> Tuple[List[str], Optional[str]]:
        """Split line into values and comment."""
        parts = line.split(";", 1)
        values = parts[0].split()
        comment = parts[1].strip() if len(parts) > 1 else None
        return values, comment

    def _to_float(self, value: str, line_num: int, context: str) -> float:
        """Convert string to float with error handling."""
        try:
            return float(value)
        except ValueError:
            raise InpSyntaxError(
                f"Invalid numeric value '{value}' for {context}",
                line_number=line_num,
                error_code="202",
                suggestions=["Check that the value is a valid number"],
            )

    # ==================== SECTION PARSERS ====================

    def _parse_title(self) -> None:
        """Parse TITLE section - already handled in _read_file."""
        pass

    def _parse_options(self) -> None:
        """Parse OPTIONS section."""
        options = self.result["options"]
        for line_num, line in self.sections["[OPTIONS]"]:
            values, _ = self._split_line(line)
            if len(values) < 2:
                continue
            key = values[0].lower()
            val = " ".join(values[1:])

            # Map EPANET option keys to WNTR structure
            if key in ["flow_units", "flowunits", "units"]:
                self.flow_units = FlowUnits[val.upper()]
                options.setdefault("hydraulic", {})["inpfile_units"] = val.upper()
            elif key in ["pressure_units", "pressureunits"]:
                options.setdefault("hydraulic", {})["inpfile_pressure_units"] = val
            elif key == "headloss":
                options.setdefault("hydraulic", {})["headloss"] = val
            elif key == "hydraulics":
                options.setdefault("hydraulic", {})["hydraulics"] = val
            elif key == "specific_gravity":
                options.setdefault("hydraulic", {})["specific_gravity"] = self._to_float(val, line_num, "specific_gravity")
            elif key == "viscosity":
                options.setdefault("hydraulic", {})["viscosity"] = self._to_float(val, line_num, "viscosity")
            elif key == "trials":
                options.setdefault("hydraulic", {})["trials"] = int(self._to_float(val, line_num, "trials"))
            elif key == "accuracy":
                options.setdefault("hydraulic", {})["accuracy"] = self._to_float(val, line_num, "accuracy")
            elif key == "unbalanced":
                # Format: CONTINUE <value> or STOP
                # Split into unbalanced and unbalanced_value
                parts = val.split()
                options.setdefault("hydraulic", {})["unbalanced"] = parts[0].upper()
                if len(parts) >= 2:
                    options.setdefault("hydraulic", {})["unbalanced_value"] = int(self._to_float(parts[1], line_num, "unbalanced_value"))
            elif key == "unbalanced_value":
                options.setdefault("hydraulic", {})["unbalanced_value"] = self._to_float(val, line_num, "unbalanced_value")
            elif key == "checkfreq":
                options.setdefault("hydraulic", {})["checkfreq"] = int(self._to_float(val, line_num, "checkfreq"))
            elif key == "maxcheck":
                options.setdefault("hydraulic", {})["maxcheck"] = int(self._to_float(val, line_num, "maxcheck"))
            elif key == "damplimit":
                options.setdefault("hydraulic", {})["damplimit"] = self._to_float(val, line_num, "damplimit")
            elif key == "headerror":
                options.setdefault("hydraulic", {})["headerror"] = self._to_float(val, line_num, "headerror")
            elif key == "flowchange":
                options.setdefault("hydraulic", {})["flowchange"] = self._to_float(val, line_num, "flowchange")
            elif key == "demand_model":
                options.setdefault("hydraulic", {})["demand_model"] = val
            elif key == "minimum_pressure":
                options.setdefault("hydraulic", {})["minimum_pressure"] = self._to_float(val, line_num, "minimum_pressure")
            elif key == "required_pressure":
                options.setdefault("hydraulic", {})["required_pressure"] = self._to_float(val, line_num, "required_pressure")
            elif key == "pressure_exponent":
                options.setdefault("hydraulic", {})["pressure_exponent"] = self._to_float(val, line_num, "pressure_exponent")
            elif key == "emitter_exponent":
                options.setdefault("hydraulic", {})["emitter_exponent"] = self._to_float(val, line_num, "emitter_exponent")
            elif key in ["demand_multiplier", "demandmult"]:
                options.setdefault("hydraulic", {})["demand_multiplier"] = self._to_float(val, line_num, "demand_multiplier")
            elif key == "pattern":
                options.setdefault("hydraulic", {})["pattern"] = val
            elif key == "quality":
                # Quality parameter can be: NONE, CHEMICAL, AGE, TRACE
                # If CHEMICAL, format is: CHEMICAL <name> <units>
                # Some INP files omit "CHEMICAL" and just give the chemical name
                quality_parts = val.split()
                valid_params = {"NONE", "CHEMICAL", "AGE", "TRACE"}
                first = quality_parts[0].upper()
                if first in valid_params:
                    options.setdefault("quality", {})["parameter"] = first
                    if first == "CHEMICAL" and len(quality_parts) >= 2:
                        options.setdefault("quality", {})["chemical_name"] = quality_parts[1]
                    if len(quality_parts) >= 3:
                        options.setdefault("quality", {})["inpfile_units"] = quality_parts[2]
                else:
                    # Assume CHEMICAL with omitted keyword
                    options.setdefault("quality", {})["parameter"] = "CHEMICAL"
                    options.setdefault("quality", {})["chemical_name"] = quality_parts[0]
                    if len(quality_parts) >= 2:
                        options.setdefault("quality", {})["inpfile_units"] = quality_parts[1]
            elif key == "trace_node":
                options.setdefault("quality", {})["trace_node"] = val
            elif key == "chemical_name":
                options.setdefault("quality", {})["chemical_name"] = val
            elif key == "diffusivity":
                options.setdefault("quality", {})["diffusivity"] = self._to_float(val, line_num, "diffusivity")
            elif key == "tolerance":
                options.setdefault("quality", {})["tolerance"] = self._to_float(val, line_num, "tolerance")
            elif key == "mass_units":
                self.mass_units = MassUnits[val.upper()]
                options.setdefault("quality", {})["inpfile_units"] = val.upper()
            elif key == "bulk_order":
                options.setdefault("reaction", {})["bulk_order"] = self._to_float(val, line_num, "bulk_order")
            elif key == "wall_order":
                options.setdefault("reaction", {})["wall_order"] = self._to_float(val, line_num, "wall_order")
            elif key == "tank_order":
                options.setdefault("reaction", {})["tank_order"] = self._to_float(val, line_num, "tank_order")
            elif key == "bulk_coeff":
                options.setdefault("reaction", {})["bulk_coeff"] = self._to_float(val, line_num, "bulk_coeff")
            elif key == "wall_coeff":
                options.setdefault("reaction", {})["wall_coeff"] = self._to_float(val, line_num, "wall_coeff")
            elif key == "limiting_potential":
                options.setdefault("reaction", {})["limiting_potential"] = self._to_float(val, line_num, "limiting_potential")
            elif key == "roughness_correl":
                options.setdefault("reaction", {})["roughness_correl"] = self._to_float(val, line_num, "roughness_correl")
            elif key == "global_price":
                options.setdefault("energy", {})["global_price"] = self._to_float(val, line_num, "global_price")
            elif key == "global_pattern":
                options.setdefault("energy", {})["global_pattern"] = val
            elif key == "global_efficiency":
                options.setdefault("energy", {})["global_efficiency"] = self._to_float(val, line_num, "global_efficiency")
            elif key == "demand_charge":
                options.setdefault("energy", {})["demand_charge"] = self._to_float(val, line_num, "demand_charge")

        self.result["options"] = options

    def _parse_times(self) -> None:
        """Parse TIMES section."""
        if not self.flow_units:
            self.flow_units = FlowUnits.CMH

        time_opts = self.result["options"].setdefault("time", {})
        for line_num, line in self.sections["[TIMES]"]:
            # Split line into words
            words = line.strip().split()
            if len(words) < 2:
                continue
            
            # Reconstruct key and value
            # Known multi-word keys:
            if len(words) >= 3 and words[0].lower() == "hydraulic" and words[1].lower() == "timestep":
                key = "hydraulic_timestep"
                val = words[2]
            elif len(words) >= 3 and words[0].lower() == "quality" and words[1].lower() == "timestep":
                key = "quality_timestep"
                val = words[2]
            elif len(words) >= 3 and words[0].lower() == "pattern" and words[1].lower() == "timestep":
                key = "pattern_timestep"
                val = words[2]
            elif len(words) >= 3 and words[0].lower() == "pattern" and words[1].lower() == "start":
                key = "pattern_start"
                val = words[2]
            elif len(words) >= 3 and words[0].lower() == "report" and words[1].lower() == "timestep":
                key = "report_timestep"
                val = words[2]
            elif len(words) >= 3 and words[0].lower() == "report" and words[1].lower() == "start":
                key = "report_start"
                val = words[2]
            elif len(words) >= 4 and words[0].lower() == "start" and words[1].lower() == "clocktime":
                key = "start_clocktime"
                # Value could be "12 am" or "12" "am"
                if len(words) >= 4 and words[3].upper() in ("AM", "PM"):
                    val = f"{words[2]} {words[3]}"
                else:
                    val = words[2]
            else:
                # Single-word key
                key = words[0].lower()
                val = words[1] if len(words) >= 2 else ""

            if key == "duration":
                time_opts["duration"] = self._parse_time(val, line_num)
            elif key == "hydraulic_timestep":
                time_opts["hydraulic_timestep"] = self._parse_time(val, line_num)
            elif key == "quality_timestep":
                time_opts["quality_timestep"] = self._parse_time(val, line_num)
            elif key == "pattern_timestep":
                time_opts["pattern_timestep"] = self._parse_time(val, line_num)
            elif key == "pattern_start":
                time_opts["pattern_start"] = self._parse_time(val, line_num)
            elif key == "report_timestep":
                time_opts["report_timestep"] = self._parse_time(val, line_num)
            elif key == "report_start":
                time_opts["report_start"] = self._parse_time(val, line_num)
            elif key == "start_clocktime":
                time_opts["start_clocktime"] = self._parse_time(val, line_num)
            elif key == "statistic":
                time_opts["statistic"] = val.upper()  # Normalize to uppercase
            elif key == "pattern_interpolation":
                time_opts["pattern_interpolation"] = val.upper() in ("TRUE", "YES", "1")

    def _parse_time(self, value: str, line_num: int) -> float:
        """Parse EPANET time format (HH:MM:SS, HH:MM, HH, HH:MM:SS AM/PM, or HH AM/PM) to seconds."""
        value = value.strip().upper()
        
        # Handle HH:MM:SS AM/PM format (e.g., "00:00:00 AM", "12:30:45 PM")
        clock_match = re.match(r"^(\d+):(\d+):(\d+)\s*(AM|PM)$", value)
        if clock_match:
            hour = int(clock_match.group(1))
            minute = int(clock_match.group(2))
            second = int(clock_match.group(3))
            am_pm = clock_match.group(4)
            if hour == 12:
                hour = 0 if am_pm == "AM" else 12
            elif am_pm == "PM":
                hour += 12
            return hour * 3600 + minute * 60 + second
        
        # Handle HH:MM AM/PM format (e.g., "12:30 AM", "1:45 PM")
        clock_match2 = re.match(r"^(\d+):(\d+)\s*(AM|PM)$", value)
        if clock_match2:
            hour = int(clock_match2.group(1))
            minute = int(clock_match2.group(2))
            am_pm = clock_match2.group(3)
            if hour == 12:
                hour = 0 if am_pm == "AM" else 12
            elif am_pm == "PM":
                hour += 12
            return hour * 3600 + minute * 60
        
        # Handle HH AM/PM format (e.g., "12 AM", "1 PM")
        am_pm_match = re.match(r"^(\d+)\s*(AM|PM)$", value)
        if am_pm_match:
            hour = int(am_pm_match.group(1))
            am_pm = am_pm_match.group(2)
            if hour == 12:
                hour = 0 if am_pm == "AM" else 12
            elif am_pm == "PM":
                hour += 12
            return hour * 3600
        
        from typing import Callable, Any, Tuple
        
        from typing import Callable, Any, Tuple, Union, List, Pattern
        
        TimeConverter = Callable[..., int]
        
        patterns: List[Tuple[Pattern, TimeConverter]] = [
            (re.compile(r"^(\d+):(\d+):(\d+)$"), lambda h, m, s: int(h) * 3600 + int(m) * 60 + int(s)),
            (re.compile(r"^(\d+):(\d+)$"), lambda h, m: int(h) * 3600 + int(m) * 60),
            (re.compile(r"^(\d+)$"), lambda h: int(h) * 3600),
        ]
        for pattern, converter in patterns:
            match = pattern.match(value.strip())
            if match:
                groups = match.groups()
                return converter(*groups)
        raise InpSyntaxError(
            f"Invalid time format: {value}",
            line_number=line_num,
            error_code="213",
            suggestions=["Use HH:MM:SS, HH:MM, HH, HH:MM:SS AM/PM, HH:MM AM/PM, or HH AM/PM format"],
        )

    def _parse_report(self) -> None:
        """Parse REPORT section."""
        report_opts = self.result["options"].setdefault("report", {})
        for line_num, line in self.sections["[REPORT]"]:
            values, _ = self._split_line(line)
            if not values:
                continue
            key = values[0].lower()
            if key == "status":
                report_opts["status"] = " ".join(values[1:]).upper()
            elif key == "summary":
                report_opts["summary"] = " ".join(values[1:]).upper()
            elif key == "energy":
                report_opts["energy"] = " ".join(values[1:]).upper()
            elif key in ["nodes", "links"]:
                report_opts[key] = values[1].upper() in ("ALL", "YES", "TRUE", "1") if len(values) > 1 else False
            elif key in ("page", "pagesize"):
                if len(values) >= 2:
                    report_opts["pagesize"] = self._to_float(values[1], line_num, "pagesize")

    def _parse_curves(self) -> None:
        """Parse CURVES section."""
        curve_name = None
        for line_num, line in self.sections["[CURVES]"]:
            values, _ = self._split_line(line)
            if not values:
                continue

            name = values[0]
            if name not in self.curves:
                self.curves[name] = []
                self._defined_curves.add(name)

            if len(values) >= 3:
                x = self._to_float(values[1], line_num, "curve x-value")
                y = self._to_float(values[2], line_num, "curve y-value")
                self.curves[name].append((x, y))

        # Convert curves to output format
        for name, points in self.curves.items():
            # Determine curve type from usage (default to HEAD)
            curve_type = "HEAD"
            self.result["curves"].append({
                "name": name,
                "curve_type": curve_type,
                "points": points,
            })

    def _parse_patterns(self) -> None:
        """Parse PATTERNS section."""
        pattern_data: OrderedDict[str, list[float]] = OrderedDict()
        for line_num, line in self.sections["[PATTERNS]"]:
            values, _ = self._split_line(line)
            if not values:
                continue

            name = values[0]
            if name not in pattern_data:
                pattern_data[name] = []
                self._defined_patterns.add(name)

            for v in values[1:]:
                pattern_data[name].append(self._to_float(v, line_num, "pattern multiplier"))

        for name, multipliers in pattern_data.items():
            self.result["patterns"].append({
                "name": name,
                "multipliers": multipliers,
            })

    def _parse_junctions(self) -> None:
        """Parse JUNCTIONS section."""
        if not self.flow_units:
            self.flow_units = FlowUnits.CMH

        default_pattern = self.result["options"].get("hydraulic", {}).get("pattern")

        for line_num, line in self.sections["[JUNCTIONS]"]:
            values, _ = self._split_line(line)
            if len(values) < 2:
                raise InpSyntaxError(
                    "Junction entry requires at least 2 values (name and elevation)",
                    line_number=line_num,
                    section="[JUNCTIONS]",
                    error_code="201",
                )

            name = values[0]
            self._defined_nodes.add(name)

            elevation = to_si(self.flow_units, self._to_float(values[1], line_num, "elevation"), HydParam.Elevation)

            base_demand = 0.0
            pattern_name = default_pattern
            if len(values) >= 3:
                base_demand = to_si(self.flow_units, self._to_float(values[2], line_num, "base_demand"), HydParam.Demand)
            if len(values) >= 4:
                pattern_name = values[3]
                self._referenced_patterns[pattern_name] = line_num

            node = {
                "name": name,
                "node_type": "Junction",
                "elevation": elevation,
                "base_demand": base_demand,
                "demand_pattern_name": pattern_name,
                "demand_category": None,
                "emitter_coefficient": None,
                "coordinates": [],
                "initial_quality": None,
                "minimum_pressure": None,
                "pressure_exponent": None,
                "required_pressure": None,
                "tag": None,
            }
            self.result["nodes"].append(node)

    def _parse_reservoirs(self) -> None:
        """Parse RESERVOIRS section."""
        if not self.flow_units:
            self.flow_units = FlowUnits.CMH

        for line_num, line in self.sections["[RESERVOIRS]"]:
            values, _ = self._split_line(line)
            if len(values) < 2:
                continue

            name = values[0]
            self._defined_nodes.add(name)

            head = to_si(self.flow_units, self._to_float(values[1], line_num, "head"), HydParam.HydraulicHead)
            pattern_name = values[2] if len(values) >= 3 else None
            if pattern_name:
                self._referenced_patterns[pattern_name] = line_num

            node = {
                "name": name,
                "node_type": "Reservoir",
                "elevation": 0.0,
                "base_head": head,
                "head_pattern_name": pattern_name,
                "coordinates": [],
                "initial_quality": None,
                "tag": None,
            }
            self.result["nodes"].append(node)

    def _parse_tanks(self) -> None:
        """Parse TANKS section."""
        if not self.flow_units:
            self.flow_units = FlowUnits.CMH

        for line_num, line in self.sections["[TANKS]"]:
            values, _ = self._split_line(line)
            if len(values) < 7:
                raise InpSyntaxError(
                    "Tank entry requires at least 7 values",
                    line_number=line_num,
                    section="[TANKS]",
                    error_code="201",
                )

            name = values[0]
            self._defined_nodes.add(name)

            elevation = to_si(self.flow_units, self._to_float(values[1], line_num, "elevation"), HydParam.Elevation)
            init_level = to_si(self.flow_units, self._to_float(values[2], line_num, "init_level"), HydParam.Length)
            min_level = to_si(self.flow_units, self._to_float(values[3], line_num, "min_level"), HydParam.Length)
            max_level = to_si(self.flow_units, self._to_float(values[4], line_num, "max_level"), HydParam.Length)
            diameter = to_si(self.flow_units, self._to_float(values[5], line_num, "diameter"), HydParam.TankDiameter)
            min_vol = to_si(self.flow_units, self._to_float(values[6], line_num, "min_vol"), HydParam.Volume)

            vol_curve_name = None
            overflow = False
            if len(values) >= 8:
                if values[7] != "*":
                    vol_curve_name = values[7]
                    self._referenced_curves[vol_curve_name] = line_num
            if len(values) >= 9:
                overflow = values[8].upper() in ("YES", "TRUE", "1")

            node = {
                "name": name,
                "node_type": "Tank",
                "elevation": elevation,
                "init_level": init_level,
                "min_level": min_level,
                "max_level": max_level,
                "diameter": diameter,
                "min_vol": min_vol,
                "vol_curve_name": vol_curve_name,
                "overflow": overflow,
                "coordinates": [],
                "initial_quality": None,
                "mixing_fraction": None,
                "mixing_model": None,
                "bulk_coeff": None,
                "tag": None,
            }
            self.result["nodes"].append(node)

    def _parse_pipes(self) -> None:
        """Parse PIPES section."""
        if not self.flow_units:
            self.flow_units = FlowUnits.CMH

        darcy_weisbach = self.result["options"].get("hydraulic", {}).get("headloss") == "D-W"

        for line_num, line in self.sections["[PIPES]"]:
            values, _ = self._split_line(line)
            if len(values) < 6:
                raise InpSyntaxError(
                    "Pipe entry requires at least 6 values",
                    line_number=line_num,
                    section="[PIPES]",
                    error_code="201",
                )

            name = values[0]
            self._defined_links.add(name)

            start_node = values[1]
            end_node = values[2]
            # Track references for semantic validation
            # (will validate after all sections parsed)

            length = to_si(self.flow_units, self._to_float(values[3], line_num, "length"), HydParam.Length)
            diameter = to_si(self.flow_units, self._to_float(values[4], line_num, "diameter"), HydParam.PipeDiameter)
            roughness = to_si(self.flow_units, self._to_float(values[5], line_num, "roughness"), HydParam.RoughnessCoeff, darcy_weisbach=darcy_weisbach)

            minor_loss = 0.0
            if len(values) >= 7:
                minor_loss = self._to_float(values[6], line_num, "minor_loss")

            status = "OPEN"
            check_valve = False
            if len(values) >= 8:
                status_val = values[7].upper()
                if status_val == "CV":
                    status = "OPEN"
                    check_valve = True
                else:
                    status = status_val

            link = {
                "name": name,
                "link_type": "Pipe",
                "start_node_name": start_node,
                "end_node_name": end_node,
                "length": length,
                "diameter": diameter,
                "roughness": roughness,
                "minor_loss": minor_loss,
                "initial_status": status,
                "check_valve": check_valve,
                "bulk_coeff": None,
                "wall_coeff": None,
                "vertices": [],
                "tag": None,
            }
            self.result["links"].append(link)

    def _parse_pumps(self) -> None:
        """Parse PUMPS section."""
        if not self.flow_units:
            self.flow_units = FlowUnits.CMH

        for line_num, line in self.sections["[PUMPS]"]:
            values, _ = self._split_line(line)
            if len(values) < 3:
                raise InpSyntaxError(
                    "Pump entry requires at least 3 values",
                    line_number=line_num,
                    section="[PUMPS]",
                    error_code="201",
                )

            name = values[0]
            self._defined_links.add(name)

            start_node = values[1]
            end_node = values[2]

            pump_type = None
            power = None
            pump_curve_name = None
            speed = 1.0
            speed_pattern_name = None

            i = 3
            while i < len(values) - 1:
                keyword = values[i].upper()
                val = values[i + 1]
                if keyword == "HEAD":
                    pump_type = "HEAD"
                    pump_curve_name = val
                    self._referenced_curves[pump_curve_name] = line_num
                elif keyword == "POWER":
                    pump_type = "POWER"
                    power = to_si(self.flow_units, self._to_float(val, line_num, "power"), HydParam.Power)
                elif keyword == "SPEED":
                    speed = self._to_float(val, line_num, "speed")
                elif keyword == "PATTERN":
                    speed_pattern_name = val
                    self._referenced_patterns[speed_pattern_name] = line_num
                i += 2

            if pump_type is None:
                raise InpSyntaxError(
                    "Pump must specify either HEAD or POWER",
                    line_number=line_num,
                    section="[PUMPS]",
                    error_code="217",
                )

            link: dict = {
                "name": name,
                "link_type": "Pump",
                "start_node_name": start_node,
                "end_node_name": end_node,
                "pump_type": pump_type,
                "power": power,
                "pump_curve_name": pump_curve_name,
                "base_speed": speed,
                "speed_pattern_name": speed_pattern_name,
                "initial_status": "OPEN",
                "efficiency_curve_name": None,
                "energy_pattern": None,
                "energy_price": None,
                "initial_setting": None,
                "vertices": [],
                "tag": None,
            }
            self.result["links"].append(link)

    def _parse_valves(self) -> None:
        """Parse VALVES section."""
        if not self.flow_units:
            self.flow_units = FlowUnits.CMH

        for line_num, line in self.sections["[VALVES]"]:
            values, _ = self._split_line(line)
            if len(values) < 6:
                raise InpSyntaxError(
                    "Valve entry requires at least 6 values",
                    line_number=line_num,
                    section="[VALVES]",
                    error_code="201",
                )

            name = values[0]
            self._defined_links.add(name)

            start_node = values[1]
            end_node = values[2]
            diameter = to_si(self.flow_units, self._to_float(values[3], line_num, "diameter"), HydParam.PipeDiameter)
            valve_type = values[4].upper()

            if valve_type in ("PRV", "PSV", "PBV"):
                setting = to_si(self.flow_units, self._to_float(values[5], line_num, "setting"), HydParam.Pressure)
            elif valve_type == "FCV":
                setting = to_si(self.flow_units, self._to_float(values[5], line_num, "setting"), HydParam.Flow)
            elif valve_type == "TCV":
                setting = self._to_float(values[5], line_num, "setting")
            elif valve_type == "GPV":
                setting = values[5]  # curve name
                self._referenced_curves[setting] = line_num
            else:
                raise InpSyntaxError(
                    f"Unknown valve type: {valve_type}",
                    line_number=line_num,
                    section="[VALVES]",
                    error_code="213",
                )

            minor_loss = 0.0
            if len(values) >= 7:
                minor_loss = self._to_float(values[6], line_num, "minor_loss")

            link = {
                "name": name,
                "link_type": "Valve",
                "start_node_name": start_node,
                "end_node_name": end_node,
                "diameter": diameter,
                "valve_type": valve_type,
                "minor_loss": minor_loss,
                "initial_setting": setting,
                "initial_status": "ACTIVE",
                "headloss_curve_name": setting if valve_type == "GPV" else None,
                "tag": None,
            }
            self.result["links"].append(link)

    def _parse_emitters(self) -> None:
        """Parse EMITTERS section."""
        if not self.flow_units:
            self.flow_units = FlowUnits.CMH

        for line_num, line in self.sections["[EMITTERS]"]:
            values, _ = self._split_line(line)
            if len(values) < 2:
                continue

            node_name = values[0]
            coeff = to_si(self.flow_units, self._to_float(values[1], line_num, "emitter_coefficient"), HydParam.EmitterCoeff)

            # Find node and add emitter
            for node in self.result["nodes"]:
                if node["name"] == node_name:
                    node["emitter_coefficient"] = coeff
                    break

    def _parse_coordinates(self) -> None:
        """Parse COORDINATES section."""
        for line_num, line in self.sections["[COORDINATES]"]:
            values, _ = self._split_line(line)
            if len(values) < 3:
                continue

            name = values[0]
            x = self._to_float(values[1], line_num, "x coordinate")
            y = self._to_float(values[2], line_num, "y coordinate")

            # Update node or link coordinates
            for node in self.result["nodes"]:
                if node["name"] == name:
                    node["coordinates"] = [x, y]
                    break
            for link in self.result["links"]:
                if link["name"] == name:
                    link["coordinates"] = [x, y]
                    break

    def _parse_vertices(self) -> None:
        """Parse VERTICES section."""
        for line_num, line in self.sections["[VERTICES]"]:
            values, _ = self._split_line(line)
            if len(values) < 3:
                continue

            link_name = values[0]
            x = self._to_float(values[1], line_num, "x coordinate")
            y = self._to_float(values[2], line_num, "y coordinate")

            for link in self.result["links"]:
                if link["name"] == link_name:
                    if "vertices" not in link:
                        link["vertices"] = []
                    link["vertices"].append([x, y])
                    break

    def _parse_energy(self) -> None:
        """Parse ENERGY section."""
        energy_opts = self.result["options"].setdefault("energy", {})
        for line_num, line in self.sections["[ENERGY]"]:
            values, _ = self._split_line(line)
            if len(values) < 2:
                continue

            keyword = values[0].upper()
            if keyword == "GLOBAL":
                if len(values) >= 3:
                    sub_key = values[1].upper()
                    val = values[2]
                    if sub_key == "PRICE":
                        energy_opts["global_price"] = to_si(self.flow_units or FlowUnits.CMH, self._to_float(val, line_num, "price"), HydParam.Energy)
                    elif sub_key == "PATTERN":
                        energy_opts["global_pattern"] = val
                    elif sub_key in ("EFFIC", "EFFICIENCY"):
                        energy_opts["global_efficiency"] = self._to_float(val, line_num, "efficiency")
            elif keyword == "DEMAND":
                if len(values) >= 3:
                    energy_opts["demand_charge"] = self._to_float(val, line_num, "demand_charge")
            elif keyword == "PUMP":
                if len(values) >= 4:
                    pump_name = values[1]
                    sub_key = values[2].upper()
                    val = values[3]
                    if sub_key in ("EFFIC", "EFFICIENCY"):
                        # Efficiency curve - store in pump object later
                        # For now, track the curve reference
                        self._referenced_curves[val] = line_num
                        # Store in a temporary place for later assignment to pump
                        if "pump_efficiency_curves" not in self.result:
                            self.result["pump_efficiency_curves"] = {}
                        self.result["pump_efficiency_curves"][pump_name] = val

    def _parse_status(self) -> None:
        """Parse STATUS section."""
        for line_num, line in self.sections["[STATUS]"]:
            values, _ = self._split_line(line)
            if len(values) < 2:
                continue

            name = values[0]
            setting_str = values[1].upper()

            # Find link and update status/setting
            for link in self.result["links"]:
                if link["name"] == name:
                    if setting_str in ("OPEN", "CLOSED"):
                        link["initial_status"] = setting_str
                    else:
                        # It's a numeric setting
                        try:
                            setting = self._to_float(setting_str, line_num, "setting")
                            link["initial_setting"] = setting
                            link["initial_status"] = "ACTIVE" if link["link_type"] == "Valve" else "OPEN"
                        except InpSyntaxError:
                            link["initial_status"] = setting_str
                    break

    def _parse_demands(self) -> None:
        """Parse DEMANDS section (additional demands for junctions)."""
        if not self.flow_units:
            self.flow_units = FlowUnits.CMH

        for line_num, line in self.sections["[DEMANDS]"]:
            values, _ = self._split_line(line)
            if len(values) < 3:
                continue

            node_name = values[0]
            base_demand = to_si(self.flow_units, self._to_float(values[1], line_num, "base_demand"), HydParam.Demand)
            pattern_name = values[2] if len(values) >= 3 else None
            category = values[3] if len(values) >= 4 else None

            if pattern_name:
                self._referenced_patterns[pattern_name] = line_num

            for node in self.result["nodes"]:
                if node["name"] == node_name and node["node_type"] == "Junction":
                    if "demand_timeseries_list" not in node:
                        node["demand_timeseries_list"] = []
                    node["demand_timeseries_list"].append({
                        "base_val": base_demand,
                        "pattern_name": pattern_name,
                        "category": category,
                    })
                    break

    def _parse_quality(self) -> None:
        """Parse QUALITY section (initial quality for nodes)."""
        for line_num, line in self.sections["[QUALITY]"]:
            values, _ = self._split_line(line)
            if len(values) < 2:
                continue

            node_name = values[0]
            quality = self._to_float(values[1], line_num, "initial_quality")

            for node in self.result["nodes"]:
                if node["name"] == node_name:
                    node["initial_quality"] = quality
                    break

    def _parse_reactions(self) -> None:
        """Parse REACTIONS section."""
        reaction_opts = self.result["options"].setdefault("reaction", {})
        for line_num, line in self.sections["[REACTIONS]"]:
            values, _ = self._split_line(line)
            if len(values) < 2:
                continue

            key = values[0].lower()

            if key == "order":
                # Format: Order Bulk 1.00, Order Tank 1.00, Order Wall 1
                if len(values) >= 3:
                    param = values[1].lower()
                    val = values[2]
                    reaction_opts[f"{param}_order"] = self._to_float(val, line_num, f"{param}_order")
            elif key == "global":
                # Format: Global Bulk 0.000000, Global Wall 0.000000
                # These need unit conversion based on flow units and reaction order
                if len(values) >= 3:
                    param = values[1].lower()
                    val_str = values[2]
                    val_global: float = self._to_float(val_str, line_num, f"{param}_coeff")
                    # Convert from EPANET units to SI (per second)
                    # For order 1 reactions:
                    # - Bulk: per day -> per second
                    # - Wall: traditional (ft/day) or metric (m/day) -> m/s
                    if param == "bulk":
                        reaction_opts[f"{param}_coeff"] = val_global / 86400.0
                    elif param == "wall":
                        # Wall coefficient conversion depends on flow units
                        if self.flow_units and self.flow_units.is_traditional:
                            # Traditional: ft/day -> m/s
                            reaction_opts[f"{param}_coeff"] = val_global * 0.3048 / 86400.0
                        else:
                            # Metric: m/day -> m/s
                            reaction_opts[f"{param}_coeff"] = val_global / 86400.0
                    else:
                        reaction_opts[f"{param}_coeff"] = val_global
            elif key == "limiting":
                # Format: Limiting Potential 0
                if len(values) >= 2:
                    val = values[1] if len(values) == 2 else values[2]
                    reaction_opts["limiting_potential"] = self._to_float(val, line_num, "limiting_potential")
            elif key == "roughness":
                # Format: Roughness Correlation 0
                if len(values) >= 2:
                    val = values[1] if len(values) == 2 else values[2]
                    reaction_opts["roughness_correl"] = self._to_float(val, line_num, "roughness_correl")


    def _parse_sources(self) -> None:
        """Parse SOURCES section."""
        for line_num, line in self.sections["[SOURCES]"]:
            values, _ = self._split_line(line)
            if len(values) < 4:
                continue

            # SOURCES section format: Node, Type, Quality, Pattern
            # No explicit name column - use node name as source name
            node_name = values[0]
            source_type = values[1]
            strength = self._to_float(values[2], line_num, "source strength")
            pattern = values[3] if len(values) >= 4 else None

            if pattern:
                self._referenced_patterns[pattern] = line_num

            source = {
                "name": node_name,  # Use node name as source name
                "node_name": node_name,
                "source_type": source_type,
                "strength": strength,
                "pattern": pattern,
            }
            self.result["sources"].append(source)

    def _parse_mixing(self) -> None:
        """Parse MIXING section (tank mixing models)."""
        for line_num, line in self.sections["[MIXING]"]:
            values, _ = self._split_line(line)
            if len(values) < 2:
                continue

            tank_name = values[0]
            model = values[1].upper()

            mix_model_map = {
                "MIX1": "MIX1",
                "MIX2": "MIX2",
                "FIFO": "FIFO",
                "LIFO": "LIFO",
            }

            for node in self.result["nodes"]:
                if node["name"] == tank_name and node["node_type"] == "Tank":
                    node["mixing_model"] = mix_model_map.get(model, "MIX1")
                    if len(values) >= 3:
                        node["mixing_fraction"] = self._to_float(values[2], line_num, "mixing_fraction")
                    break

    def _parse_controls(self) -> None:
        """Parse CONTROLS section (simple controls)."""
        for line_num, line in self.sections["[CONTROLS]"]:
            values, _ = self._split_line(line)
            if not values:
                continue

            # Parse simple control format:
            # LINK <name> <status/setting> IF NODE <name> <condition> <value>
            # LINK <name> <status/setting> AT <time>
            
            # Reconstruct the line for parsing
            ctrl_text = " ".join(values)
            
            # Try to parse as simple control
            parsed = self._parse_simple_control(ctrl_text, line_num)
            if parsed:
                self.result["controls"].append(parsed)

    def _parse_simple_control(self, ctrl_text: str, line_num: int) -> Optional[Dict[str, Any]]:
        """Parse a simple control line into structured format."""
        # Pattern: LINK <name> <action> IF NODE <name> <cond> <value>
        # Or: LINK <name> <action> AT <time>
        
        parts = ctrl_text.split()
        if len(parts) < 4:
            return None
            
        if parts[0].upper() != "LINK":
            return None
            
        link_name = parts[1]
        
        # Find IF or AT keyword
        if_keyword_idx = -1
        at_keyword_idx = -1
        for idx, part in enumerate(parts[2:], 2):
            if part.upper() == "IF":
                if_keyword_idx = idx
                break
            elif part.upper() == "AT":
                at_keyword_idx = idx
                break
        
        if if_keyword_idx > 0:
            # IF condition format
            action_parts = parts[2:if_keyword_idx]
            condition_parts = parts[if_keyword_idx+1:]
            
            # Parse action: should be like "CLOSED" or "OPEN" (the action after link name)
            # Convert to "PUMP PUMP_1 STATUS IS CLOSED"
            action_text = ""
            if len(action_parts) >= 1:
                link_type = "PUMP"  # Default, could be valve too
                action_type = action_parts[0].upper()
                if action_type in ("OPEN", "CLOSED"):
                    action_text = f"{link_type} {link_name} STATUS IS {action_type}"
                else:
                    action_text = f"{link_type} {link_name} SETTING IS {action_type}"
            else:
                # Fallback
                action_text = f"PUMP {link_name} STATUS IS OPEN"
            
            # Parse condition: IF NODE <name> <cond> <value>
            if len(condition_parts) >= 4 and condition_parts[0].upper() == "NODE":
                node_name = condition_parts[1]
                cond = condition_parts[2].upper()
                value = condition_parts[3]
                
                # Use format expected by _read_control_line: IF NODE <name> <cond> <value>
                cond_text = f"IF NODE {node_name} {cond} {value}"
                
                return {
                    "name": f"control_{len(self.result['controls']) + 1}",
                    "type": "simple",
                    "condition": cond_text,
                    "then_actions": [action_text],
                }
        elif at_keyword_idx > 0:
            # AT time format
            # Include link type and name in action
            link_type = parts[0]
            link_name = parts[1]
            action_parts = parts[2:at_keyword_idx]
            time_parts = parts[at_keyword_idx+1:]
            
            # Build action text with link type and name
            action_text = " ".join([link_type, link_name] + action_parts)
            time_text = " ".join(time_parts)
            
            return {
                "name": f"control_{len(self.result['controls']) + 1}",
                "type": "simple",
                "condition": f"AT {time_text}",
                "then_actions": [action_text],
            }
        
        # Fallback: store raw text
        return {
            "name": f"control_{len(self.result['controls']) + 1}",
            "type": "simple",
            "condition": "",
            "then_actions": [ctrl_text],
        }

    def _parse_rules(self) -> None:
        """Parse RULES section (rule-based controls)."""
        # Store raw rule text
        rule_lines = []
        for line_num, line in self.sections["[RULES]"]:
            rule_lines.append(line)

        if rule_lines:
            self.result["controls"].append({
                "name": "rule_control",
                "type": "rule",
                "condition": "",
                "then_actions": rule_lines,
            })

    def _parse_labels(self) -> None:
        """Parse LABELS section - store as metadata."""
        pass

    def _parse_backdrop(self) -> None:
        """Parse BACKDROP section - store in graphics options."""
        graphics = self.result["options"].setdefault("graphics", {})
        for line_num, line in self.sections["[BACKDROP]"]:
            values, _ = self._split_line(line)
            if not values:
                continue
            key = values[0].upper()
            if key == "DIMENSIONS":
                if len(values) >= 5:
                    graphics["dimensions"] = [values[1], values[2], values[3], values[4]]
            elif key == "UNITS":
                if len(values) >= 2:
                    graphics["units"] = values[1]
            elif key == "FILE":
                if len(values) >= 2:
                    graphics["image_filename"] = " ".join(values[1:])
            elif key == "OFFSET":
                if len(values) >= 3:
                    graphics["offset"] = [values[1], values[2]]

    def _parse_tags(self) -> None:
        """Parse TAGS section."""
        for line_num, line in self.sections["[TAGS]"]:
            values, _ = self._split_line(line)
            if len(values) < 2:
                continue

            name = values[0]
            tag = " ".join(values[1:])

            for node in self.result["nodes"]:
                if node["name"] == name:
                    node["tag"] = tag
                    break
            for link in self.result["links"]:
                if link["name"] == name:
                    link["tag"] = tag
                    break

    def _validate_references(self) -> None:
        """Validate cross-references after all sections parsed."""
        # Check curve references
        for curve_name, line_num in self._referenced_curves.items():
            if curve_name not in self._defined_curves:
                raise InpSemanticError(
                    f"Undefined curve referenced: {curve_name}",
                    line_number=line_num,
                    section="[CURVES]",
                    error_code="206",
                    suggestions=[f"Define curve '{curve_name}' in [CURVES] section"],
                )

        # Check pattern references
        for pattern_name, line_num in self._referenced_patterns.items():
            if pattern_name not in self._defined_patterns:
                raise InpSemanticError(
                    f"Undefined pattern referenced: {pattern_name}",
                    line_number=line_num,
                    section="[PATTERNS]",
                    error_code="205",
                    suggestions=[f"Define pattern '{pattern_name}' in [PATTERNS] section"],
                )

        # Check node references in links
        for link in self.result["links"]:
            for node_field in ("start_node_name", "end_node_name"):
                node_name = link.get(node_field)
                if node_name and node_name not in self._defined_nodes:
                    raise InpSemanticError(
                        f"Undefined node '{node_name}' referenced in link '{link['name']}'",
                        error_code="203",
                        suggestions=[f"Define node '{node_name}' in [JUNCTIONS], [RESERVOIRS], or [TANKS]"],
                    )

        # Check source node references
        for source in self.result["sources"]:
            node_name = source.get("node_name")
            if node_name and node_name not in self._defined_nodes:
                raise InpSemanticError(
                    f"Undefined node '{node_name}' referenced in source '{source['name']}'",
                    error_code="203",
                    suggestions=[f"Define node '{node_name}' in [JUNCTIONS], [RESERVOIRS], or [TANKS]"],
                )

        # Assign pump efficiency curves to pump objects
        if "pump_efficiency_curves" in self.result:
            for pump_name, curve_name in self.result["pump_efficiency_curves"].items():
                for link in self.result["links"]:
                    if link["name"] == pump_name and link["link_type"] == "Pump":
                        link["efficiency_curve_name"] = curve_name
                        break
            # Clean up temporary storage
            del self.result["pump_efficiency_curves"]


def read_inp_to_dict(filepath: Union[str, Path]) -> Dict[str, Any]:
    """Parse an EPANET INP file into a WNTR-compatible dictionary.

    This is the main entry point for the standalone INP parser.

    Parameters
    ----------
    filepath : str or Path
        Path to the EPANET INP file.

    Returns
    -------
    dict
        Dictionary representation of the network model in WNTR format.
        Contains keys: version, comment, name, references, options,
        curves, patterns, nodes, links, sources, controls.

    Raises
    ------
    InpParseError
        If the file cannot be read or parsed.
    InpSyntaxError
        If the INP file has syntax errors.
    InpSemanticError
        If the INP file has valid syntax but invalid references/values.

    Examples
    --------
    >>> from epanetparser.core.io import read_inp_to_dict
    >>> network_dict = read_inp_to_dict("network.inp")
    >>> print(network_dict.keys())
    dict_keys(['version', 'comment', 'name', 'references', 'options',
               'curves', 'patterns', 'nodes', 'links', 'sources', 'controls'])
    """
    parser = InpParser(filepath)
    return parser.parse()