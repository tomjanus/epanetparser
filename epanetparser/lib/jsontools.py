"""JSON encoding utilities for EPANET parser types.

This module provides custom JSON encoders for serializing EPANET network components
and complete network models. The encoders extend Python's standard json.JSONEncoder
to handle EPANET-specific types that are not natively JSON-serializable.

The module includes:
- WNTREPANETTypeJSONEncoder: Encoder for individual EPANET component types
- WNTREPANETNetworkJSONEncoder: Encoder for complete EPANET network models
"""
import json
from typing import Any
from epanetparser.epanet_types.base import WNTREPANETType
from epanetparser.epanet_types.network import WNTREPANETNetwork


class WNTREPANETTypeJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for EPANET component types.
    
    This encoder handles serialization of individual EPANET component instances
    (nodes, links, patterns, etc.) by extracting their validated data dictionary.
    It extends the standard JSONEncoder to recognize WNTREPANETType instances
    and serialize them appropriately.
    
    Example:
        >>> encoder = WNTREPANETTypeJSONEncoder()
        >>> json_str = encoder.encode(node_instance)
    """
    def default(self, o: Any) -> Any:
        """Serialize EPANET component types to JSON-compatible format.
        
        Override of JSONEncoder.default() to handle WNTREPANETType instances.
        For WNTREPANETType objects, returns their data dictionary. For all other
        types, delegates to the parent class's default behavior.
        
        Args:
            o: Object to serialize.
        
        Returns:
            JSON-serializable representation of the object.
        
        Raises:
            TypeError: If the object is not JSON-serializable and not a WNTREPANETType.
        """
        if isinstance(o, WNTREPANETType):
            return o.data
        return json.JSONEncoder.default(self, o)


class WNTREPANETNetworkJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for EPANET network models.
    
    This encoder handles serialization of complete EPANET network model instances
    by converting them to dictionary format. It extends the standard JSONEncoder
    to recognize WNTREPANETNetwork instances and serialize them appropriately.
    
    Example:
        >>> encoder = WNTREPANETNetworkJSONEncoder()
        >>> json_str = encoder.encode(network_instance)
        >>> # Or use with json.dumps()
        >>> json_str = json.dumps(network, cls=WNTREPANETNetworkJSONEncoder)
    """
    def default(self, o: Any) -> Any:
        """Serialize EPANET network models to JSON-compatible format.
        
        Override of JSONEncoder.default() to handle WNTREPANETNetwork instances.
        For WNTREPANETNetwork objects, returns their dictionary representation.
        For all other types, delegates to the parent class's default behavior.
        
        Args:
            o: Object to serialize.
        
        Returns:
            JSON-serializable representation of the object.
        
        Raises:
            TypeError: If the object is not JSON-serializable and not a WNTREPANETNetwork.
        """
        if isinstance(o, WNTREPANETNetwork):
            return o.as_dict()
        return json.JSONEncoder.default(self, o)
