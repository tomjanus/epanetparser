"""Parser for EPANET network models in WNTR's JSON format.

This parser builds a model and nothing else. It does not validate: assigning a
field never runs a rule, and a model that EPANET could not simulate still
parses successfully here. That separation is deliberate, so that the same
parser serves users who only want a model, users who want the core ruleset,
and users who want their own rulesets as well.

What the parser does report is *structural*: a document that is not JSON, or
one that omits a required top-level key, cannot be turned into a model at all.
Those problems are raised as
:class:`~epanetparser.core.epanettypes.exceptions.WNTREPANETParserException`.
Everything else a model might get wrong, from a missing field to a reference
that points at nothing, is a validation concern and is found by
:meth:`epanetparser.core.epanettypes.network.WNTREPANETNetwork.validate`.

Duplicate-name detection used to live here. It is now a network rule in
:mod:`epanetparser.core_rules.epanet_core.network`, because a duplicate name is
a defect in the model rather than in its encoding.

# TODO: the component inventory below is restated in several other modules, so
#       adding a component means editing all of them. See
#       docs/TODO_MODEL_LAYER_DUPLICATION.md, section 1.

Component groups
----------------
============  ==========================================================
Key           Contents
============  ==========================================================
metadata      ``name``, ``comment``, ``version``, ``references``
``options``   Simulation options, by option group
``curves``    Pump, head, efficiency and volume curves
``patterns``  Time patterns
``nodes``     Junctions, reservoirs and tanks
``links``     Pipes, pumps and valves
``sources``   Water quality sources
``controls``  Simple and rule-based controls
============  ==========================================================

Required keys are ``options``, ``nodes`` and ``links``. A model with no curves,
patterns, sources or controls is normal and those keys may be absent.
"""
from typing import Any, Dict, List, Optional, Tuple
import json

from epanetparser.core.epanettypes import (
    WNTREPANETControl,
    WNTREPANETCurve,
    WNTREPANETLink,
    WNTREPANETNetworkInfo,
    WNTREPANETNode,
    WNTREPANETOptions,
    WNTREPANETPattern,
    WNTREPANETSource,
)
from epanetparser.core.epanettypes.exceptions import WNTREPANETParserException

#: Top-level keys that must be present for a document to be a model.
REQUIRED_KEYS: Tuple[str, ...] = ("options", "nodes", "links")

#: Optional top-level keys, and the attribute each is parsed into.
OPTIONAL_KEYS: Tuple[str, ...] = (
    "curves",
    "patterns",
    "sources",
    "controls",
)

#: Metadata fields taken from the top level of the document.
METADATA_KEYS: Tuple[str, ...] = ("version", "comment", "name", "references")

#: Prefix used to flag duplicate JSON object keys so that none is silently lost.
DUP_KEY_BASE = "__WNTREPANETParser_Duplicate_Key_{pattern}__"
DUP_KEY_FLAG = DUP_KEY_BASE.format(pattern="{idx:03d}")


class WNTRJSONParser:
    """Builds an EPANET model from a WNTR JSON document.

    Parameters
    ----------
    json_src : str
        JSON-encoded text of an EPANET model in WNTR's format.

    Attributes
    ----------
    src : Dict[str, Any]
        The decoded document, with duplicate object keys flagged rather than
        dropped.
    errors : Dict[str, List[WNTREPANETParserException]]
        Structural problems that prevented a model from being built, grouped
        by component collection. Kept for compatibility; empty after a
        successful parse.
    warnings : Dict[str, List[Any]]
        Structural warnings. Kept for compatibility; the parser produces none,
        because non-fatal findings belong to validation.
    network_info : WNTREPANETNetworkInfo
        Model metadata.
    options : WNTREPANETOptions
        Simulation options.
    curves : List[WNTREPANETCurve]
        Curves, in document order.
    patterns : List[WNTREPANETPattern]
        Patterns, in document order.
    nodes : List[WNTREPANETNode]
        Nodes, in document order. Duplicates are kept, not silently merged.
    links : List[WNTREPANETLink]
        Links, in document order. Duplicates are kept, not silently merged.
    sources : List[WNTREPANETSource]
        Water quality sources, in document order.
    controls : List[WNTREPANETControl]
        Controls, in document order.

    Raises
    ------
    WNTREPANETParserException
        If the text is not valid JSON.

    Notes
    -----
    The parser takes no ruleset argument. Validation is a separate, explicit
    step, so there is nothing for the parser to be configured with.

    Examples
    --------
    >>> parser = WNTRJSONParser(json_src)   # doctest: +SKIP
    >>> parser.parse()                      # doctest: +SKIP
    >>> network = WNTREPANETNetwork(parser) # doctest: +SKIP
    >>> network.validate().is_valid         # doctest: +SKIP
    False
    """

    def __init__(self, json_src: str) -> None:
        """Decode the document and prepare empty component stores.

        Parameters
        ----------
        json_src : str
            JSON-encoded text of an EPANET model in WNTR's format.

        Raises
        ------
        WNTREPANETParserException
            If ``json_src`` is not valid JSON.
        """
        self.errors: Dict[str, List[WNTREPANETParserException]] = {}
        self.warnings: Dict[str, List[Any]] = {}
        self._raise_on_error = False

        try:
            self.src: Dict[str, Any] = json.loads(
                json_src, object_pairs_hook=self.enforce_unique
            )
        except json.JSONDecodeError as err:
            raise WNTREPANETParserException(
                f"Invalid JSON document: {err}"
            ) from None

        self.network_info: WNTREPANETNetworkInfo = WNTREPANETNetworkInfo({})
        self.options: WNTREPANETOptions = WNTREPANETOptions({})
        self.curves: List[WNTREPANETCurve] = []
        self.patterns: List[WNTREPANETPattern] = []
        self.nodes: List[WNTREPANETNode] = []
        self.links: List[WNTREPANETLink] = []
        self.sources: List[WNTREPANETSource] = []
        self.controls: List[WNTREPANETControl] = []

    @staticmethod
    def enforce_unique(ordered_pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
        """Decode a JSON object, flagging duplicate keys instead of dropping them.

        Parameters
        ----------
        ordered_pairs : List[Tuple[str, Any]]
            Key-value pairs as produced by the JSON decoder, in document
            order.

        Returns
        -------
        Dict[str, Any]
            The object, with any repeated key renamed to
            ``__WNTREPANETParser_Duplicate_Key_NNN__:<key>`` so that no value
            is lost.

        Notes
        -----
        Python's JSON decoder keeps the last value for a repeated key, which
        would hide a real defect in the source document. Flagging the duplicate
        keeps it visible for validation to report.
        """
        result: Dict[str, Any] = {}
        index = 1
        for key, value in ordered_pairs:
            if key in result:
                result[DUP_KEY_FLAG.format(idx=index) + ":" + key] = value
                index += 1
            else:
                result[key] = value
        return result

    def missing_keys(self) -> List[str]:
        """Return the required top-level keys the document does not define.

        Returns
        -------
        List[str]
            Names of the missing keys, in the order they are declared in
            :data:`REQUIRED_KEYS`. Empty when the document can be parsed.
        """
        return [key for key in REQUIRED_KEYS if key not in self.src]

    def parse(
        self,
        raise_on_error: bool = False,
        raise_on_warning: bool = False,
        ignore_warnings: bool = False,
    ) -> None:
        """Build the model from the decoded document.

        Parameters
        ----------
        raise_on_error : bool
            If True, raise the first structural problem instead of collecting
            it in :attr:`errors`.
        raise_on_warning : bool
            Accepted for compatibility. The parser produces no warnings, so
            this has no effect.
        ignore_warnings : bool
            Accepted for compatibility and has no effect, for the same
            reason.

        Raises
        ------
        WNTREPANETParserException
            If a required top-level key is missing, or if any collection is not
            a list of objects and ``raise_on_error`` is True.

        Notes
        -----
        Components are stored in document order and are not deduplicated or
        reordered. A component whose fields are unusable is still constructed:
        what counts as usable is a question for validation, and answering it
        here would make parsing and validation inseparable.
        """
        self._raise_on_error = raise_on_error
        absent = self.missing_keys()
        if absent:
            message = f"Missing required key(s) in network document: {', '.join(absent)}"
            if raise_on_error:
                raise WNTREPANETParserException(message) from None
            self.errors.setdefault("network", []).append(
                WNTREPANETParserException(message)
            )
            return

        self.network_info = WNTREPANETNetworkInfo(
            {key: self.src[key] for key in METADATA_KEYS if key in self.src}
        )
        self.options = WNTREPANETOptions(self.src["options"])
        self.curves = [
            WNTREPANETCurve(item) for item in self._records("curves", WNTREPANETCurve)
        ]
        self.patterns = [
            WNTREPANETPattern(item)
            for item in self._records("patterns", WNTREPANETPattern)
        ]
        self.nodes = [
            WNTREPANETNode(item) for item in self._records("nodes", WNTREPANETNode)
        ]
        self.links = [
            WNTREPANETLink(item) for item in self._records("links", WNTREPANETLink)
        ]
        self.sources = [
            WNTREPANETSource(item) for item in self._records("sources", WNTREPANETSource)
        ]
        self.controls = [
            WNTREPANETControl(item)
            for item in self._records("controls", WNTREPANETControl)
        ]

    def _structural_error(self, key: str, message: str) -> None:
        """Record a structural problem, or raise it, per ``raise_on_error``."""
        if self._raise_on_error:
            raise WNTREPANETParserException(message) from None
        self.errors.setdefault(key, []).append(WNTREPANETParserException(message))

    def _records(
        self,
        key: str,
        factory: type,
    ) -> List[Dict[str, Any]]:
        """Return the object records of a collection, or an empty list.

        Parameters
        ----------
        key : str
            Top-level key to read.
        factory : type
            Component class the records are for, used in the error message.

        Returns
        -------
        List[Dict[str, Any]]
            The collection's records, or an empty list when the key is absent
            or the collection is structurally wrong.
        """
        raw: Optional[Any] = self.src.get(key)
        if raw is None:
            return []
        if not isinstance(raw, list):
            self._structural_error(
                key,
                f"Key '{key}' must be a list of "
                f"{factory.__name__} objects, found {type(raw).__name__}",
            )
            return []
        records: List[Dict[str, Any]] = []
        for position, item in enumerate(raw):
            if not isinstance(item, dict):
                self._structural_error(
                    key,
                    f"Key '{key}' entry {position} must be an object, "
                    f"found {type(item).__name__}",
                )
                return []
            records.append(item)
        return records

    @property
    def has_errors(self) -> bool:
        """True if any structural problem was recorded."""
        return bool(self.errors)

    @property
    def has_warnings(self) -> bool:
        """True if any structural warning was recorded.

        Notes
        -----
        Always False: the parser produces no warnings. Non-fatal findings are
        validation issues, and are reported by
        :attr:`~epanetparser.core.validation.results.ValidationReport.warnings`.
        """
        return bool(self.warnings)
