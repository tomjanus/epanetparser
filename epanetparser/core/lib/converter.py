"""Bidirectional converter between EPANET INP files and WNTR JSON format.

This module provides functionality to convert EPANET network models between the
traditional INP text format and WNTR's JSON representation. The conversion is
bidirectional, supporting both INP-to-JSON and JSON-to-INP transformations.

The converter uses the WNTR (Water Network Tool for Resilience) library to parse
and generate network models, ensuring compatibility with WNTR's internal data
structures and validation.
"""
from pathlib import Path
import json
import wntr


class WNTRINPJSONConverter:
    """Bidirectional converter between EPANET INP files and WNTR JSON format.
    
    This class handles conversion between EPANET's native INP text format and
    WNTR's JSON representation. It uses WNTR's WaterNetworkModel to parse and
    generate network models.
    
    Args:
        preserve_order: If True, attempt to preserve element ordering during
                       conversion (currently unused, reserved for future use).
    """

    @staticmethod
    def inp_to_json_string(inp_path: str | Path, indent: int = 2) -> str:
        """Convert an EPANET INP file to a JSON string in WNTR format.
        
        Args:
            inp_path: Path to the input .inp file.
            indent: Number of spaces for JSON indentation (default: 2).
                   Set to None for compact output.
        
        Returns:
            A JSON string representing the network model in WNTR format.
        
        Raises:
            ValueError: If the input file does not have a .inp extension.
            FileNotFoundError: If the input file does not exist.
            Exception: If WNTR fails to parse the INP file.
        """
        inp_path = Path(inp_path)
        if inp_path.suffix.lower() != ".inp":
            raise ValueError("Input must be a .inp file")
        _network = wntr.network.WaterNetworkModel(str(inp_path.as_posix()))
        return json.dumps(_network.to_dict(), indent=indent, ensure_ascii=False)
    
    
    @staticmethod
    def replace_file_suffix(file_path: str | Path, new_suffix: str) -> Path:
        """Replace the suffix of a file path with a new suffix.
        
        Args:
            file_path: Original file path.
            new_suffix: New suffix to replace the original (e.g., '.json').
        
        Returns:
            A new Path object with the updated suffix.
        """
        return Path(file_path).with_suffix(new_suffix)
    
    # -------------------------
    # INP -> JSON
    # -------------------------
    @staticmethod
    def inp_to_json(
            inp_path: str | Path,
            json_path: str | Path = None,
            indent: int = 2) -> str:
        """Convert an EPANET INP file to WNTR JSON format.
        
        Reads an EPANET network model from an INP file, converts it to WNTR's
        dictionary representation, and writes it as a well-formatted JSON file
        with the same base name but .json extension.
        
        Args:
            inp_path: Path to the input .inp file.
            json_path: Optional path for the output .json file. If not provided,
                       the output will be saved in the same directory with the same 
                       base name as the input but with a .json extension.
            indent: Number of spaces for JSON indentation (default: 2).
                   Set to None for compact output.
        
        Returns:
            Path to the generated JSON file as a string.
        
        Raises:
            ValueError: If the input file does not have a .inp extension.
            FileNotFoundError: If the input file does not exist.
        """
        inp_path = Path(inp_path)
        if inp_path.suffix.lower() != ".inp":
            raise ValueError("Input must be a .inp file")
        if not inp_path.exists():
            raise FileNotFoundError(f"Input file not found: {inp_path}")
        json_str = WNTRINPJSONConverter.inp_to_json_string(inp_path, indent=indent)
        if json_path is None:
            json_path = Path(inp_path).with_suffix(".json")
        else:
            json_path = Path(json_path)
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(json_str)
        return str(json_path)

    # -------------------------
    # JSON -> INP
    # -------------------------
    @staticmethod
    def json_to_inp(
            json_path: str | Path,
            inp_path: str | Path = None,
            version: float = 2.2) -> str:
        """Convert a WNTR JSON file to EPANET INP format.
        
        Reads a WNTR JSON network model, reconstructs the WaterNetworkModel,
        and writes it as an EPANET INP file with the same base name but .inp extension.
        
        Args:
            json_path: Path to the input .json file.
            inp_path: Optional path for the output .inp file. If not provided,
                      the output will be saved in the same directory with the same 
                      base name as the input but with a .inp extension.
            version: EPANET version to target for the output INP file (default 2.2).
        
        Returns:
            Path to the generated INP file as a string.
        
        Raises:
            ValueError: If the input file does not have a .json extension.
            FileNotFoundError: If the input file does not exist.
            json.JSONDecodeError: If the JSON file is malformed.
        """
        json_path = Path(json_path)
        if json_path.suffix.lower() != ".json":
            raise ValueError("Input file must have .json extension")
        if not json_path.exists():
            raise FileNotFoundError(f"Input file not found: {json_path}")
        # Read formatted JSON
        with open(json_path, "r", encoding="utf-8") as f:
            wn_dict = json.load(f)
        # Reconstruct network model
        wn = wntr.network.WaterNetworkModel()
        wn.from_dict(wn_dict)
        # Output path
        if inp_path is None:
            inp_path = json_path.with_suffix(".inp")
        else:
            inp_path = Path(inp_path)
        # Write INP
        wntr.network.write_inpfile(
            wn,
            str(inp_path),
            version=version
        )
        return str(inp_path)

