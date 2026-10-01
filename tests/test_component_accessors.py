"""Component accessors read the field they claim to read.

An accessor is a promise that a named field of a WNTR document is reachable
under a particular Python attribute name. The promise is easy to break and
silent when broken: a rule that asks for ``source.param`` when WNTR writes
``source_type`` reads ``None``, and the rule either passes vacuously or reports
a defect that is not in the model.

That is not hypothetical. Two rules shipped in this package were wrong in
exactly this way. The source rules looked for ``param`` and ``pattern_name``
where WNTR writes ``source_type`` and ``pattern``, and the pump rule demanded a
pump curve from a model whose pump is defined by constant power. Both were
caught by :mod:`tests.test_core_networks`, which validates the bundled EPANET
reference networks; this file closes the gap at the other end, by checking each
accessor against the field the model actually carries.

Why real networks
-----------------
The assertions compare an accessor against the raw WNTR dictionary it came
from. A hand-written fixture only proves the accessor is consistent with the
fixture, which is the same claim made twice. Using the bundled EPANET reference
networks means the expected value comes from WNTR, not from the test.

Notes
-----
The networks are converted once per module because ``.inp`` files go through
WNTR, which is the slow part.
"""
from pathlib import Path

import pytest

from epanetparser.core.epanettypes.network import WNTREPANETNetwork

NETWORKS_DIR = Path(__file__).resolve().parent.parent / "epanetparser" / "networks" / "core"

#: A junction, tank and reservoir are all in Net1, which is a real EPANET example.
NET1 = NETWORKS_DIR / "Net1.inp"

#: Net2 is the bundled network that carries water quality sources.
NET2 = NETWORKS_DIR / "Net2.inp"


@pytest.fixture(scope="module")
def net1() -> dict:
    """Return Net1 as both a parsed model and its raw WNTR dictionary.

    Returns:
        dict: ``{"network": WNTREPANETNetwork, "raw": dict}``. The raw form is
        what WNTR produced, so an accessor can be compared with the field it
        claims to expose.
    """
    import wntr

    wn = wntr.network.WaterNetworkModel(str(NET1))
    raw = wntr.network.to_dict(wn)
    network, errors, _ = WNTREPANETNetwork.from_file(NET1)
    assert network is not None, f"Net1 did not parse: {errors}"
    return {"network": network, "raw": raw}


@pytest.fixture(scope="module")
def net2() -> dict:
    """Return Net2, the bundled network that carries sources.

    Returns:
        dict: ``{"network": WNTREPANETNetwork, "raw": dict}``.
    """
    import wntr

    wn = wntr.network.WaterNetworkModel(str(NET2))
    raw = wntr.network.to_dict(wn)
    network, errors, _ = WNTREPANETNetwork.from_file(NET2)
    assert network is not None, f"Net2 did not parse: {errors}"
    return {"network": network, "raw": raw}


def first_raw(raw: dict, key: str) -> dict:
    """Return the first record of a WNTR collection.

    Parameters
    ----------
    raw : dict
        A WNTR document.
    key : str
        Top-level collection name.

    Returns:
        dict: The first record, which must exist for the test to mean anything.
    """
    records = raw.get(key) or []
    assert records, f"the fixture has no {key}, so this test would be vacuous"
    return records[0]


class TestNetworkInfo:
    """Model metadata."""

    def test_the_metadata_fields_are_exposed(self, net1):
        """name, comment, version and references each read their own field."""
        info = net1["network"].network_info
        for field in ("name", "comment", "version"):
            assert getattr(info, field) == net1["raw"].get(field, "")

    def test_references_are_a_list(self, net1):
        """References come back as a list, never as None.

        WNTR omits the key entirely when a model records no references, so the
        accessor's empty-list default is the interesting case.
        """
        assert isinstance(net1["network"].network_info.references, list)

    def test_absent_metadata_is_empty_not_none(self):
        """A model with no metadata reads as empty strings and an empty list.

        Returning None here would push a ``None`` check onto every caller for a
        field the rules treat as optional.
        """
        from epanetparser.core.epanettypes.network_info import WNTREPANETNetworkInfo

        info = WNTREPANETNetworkInfo({})
        assert info.name == ""
        assert info.comment == ""
        assert info.version == ""
        assert info.references == []


class TestNode:
    """Node accessors."""

    def test_coordinates_are_exposed(self, net1):
        """coordinates reads the node's coordinate pair."""
        raw = first_raw(net1["raw"], "nodes")
        node = net1["network"].component("nodes", raw["name"])
        assert node.coordinates == raw["coordinates"]

    def test_the_emitter_coefficient_is_exposed(self, net1):
        """emitter_coefficient reads the node's own field.

        The value is ``None`` when the model has no emitter, which is the case
        worth checking: the key is present but empty.
        """
        raw = first_raw(net1["raw"], "nodes")
        node = net1["network"].component("nodes", raw["name"])
        assert node.emitter_coefficient == raw["emitter_coefficient"]

    def test_the_name_and_type_are_exposed(self, net1):
        """name and node_type are what identify a node."""
        raw = first_raw(net1["raw"], "nodes")
        node = net1["network"].component("nodes", raw["name"])
        assert node.name == raw["name"]
        assert node.type == raw["node_type"]

    def test_attrs_exposes_the_underlying_fields(self, net1):
        """attrs is a view of the fields, so it cannot drift from data."""
        raw = first_raw(net1["raw"], "nodes")
        node = net1["network"].component("nodes", raw["name"])
        assert set(node.attrs) == set(raw)


class TestLink:
    """Link accessors."""

    def test_the_name_and_type_are_exposed(self, net1):
        """name and link_type are what identify a link."""
        raw = first_raw(net1["raw"], "links")
        link = net1["network"].component("links", raw["name"])
        assert link.name == raw["name"]
        assert link.type == raw["link_type"]


class TestCurve:
    """Curve accessors."""

    def test_points_are_pairs(self, net1):
        """points reads the curve's coordinates as tuples.

        The conversion to tuples is deliberate, so that a caller cannot mutate a
        curve by mutating what the accessor returned.
        """
        raw = first_raw(net1["raw"], "curves")
        curve = net1["network"].component("curves", raw["name"])
        assert [tuple(p) for p in raw["points"]] == curve.points
        assert all(isinstance(point, tuple) for point in curve.points)

    def test_an_absent_curve_has_no_points(self):
        """A curve with no points reads as an empty list, not None."""
        from epanetparser.core.epanettypes.curve import WNTREPANETCurve

        assert WNTREPANETCurve({"name": "C1"}).points == []


class TestPattern:
    """Pattern accessors."""

    def test_multipliers_are_exposed(self, net1):
        """multipliers reads the pattern's values."""
        raw = first_raw(net1["raw"], "patterns")
        pattern = net1["network"].component("patterns", raw["name"])
        assert pattern.multipliers == raw["multipliers"]

    def test_an_absent_pattern_has_no_multipliers(self):
        """A pattern with no multipliers reads as an empty list, not None."""
        from epanetparser.core.epanettypes.pattern import WNTREPANETPattern

        assert WNTREPANETPattern({"name": "P1"}).multipliers == []


class TestOptions:
    """Option groups."""

    @pytest.mark.parametrize(
        ("group", "wntr_key"),
        [
            ("time_options", "time"),
            ("hydraulic_options", "hydraulic"),
            ("report_options", "report"),
            ("quality_options", "quality"),
            ("reaction_options", "reaction"),
            ("energy_options", "energy"),
            ("graphics_options", "graphics"),
        ],
    )
    def test_each_group_reads_its_own_field(self, net1, group, wntr_key):
        """Every option group accessor reads the WNTR key it names.

        WNTR stores each option group under a short name (``time``, ``report``)
        while the accessors are named after the group. If one of these were
        mapped to the wrong key, it would read a different group's values and
        nothing would complain.
        """
        raw = net1["raw"]["options"]
        assert getattr(net1["network"].options, group) == raw.get(wntr_key)

    def test_user_options_reads_the_user_key(self, net1):
        """user_options is the one group WNTR already calls 'user'."""
        raw = net1["raw"]["options"]
        assert net1["network"].options.user_options == raw.get("user")

    def test_attrs_exposes_the_option_fields(self, net1):
        """attrs is a view of the fields, so it cannot drift from data."""
        assert set(net1["network"].options.attrs) == set(net1["raw"]["options"])


class TestControl:
    """Control accessors."""

    def test_condition_and_actions_are_exposed(self, net1):
        """condition and then_actions read the control's own fields."""
        raw = first_raw(net1["raw"], "controls")
        control = next(
            c for c in net1["network"].controls if c.data.get("condition") == raw["condition"]
        )
        assert control.condition == raw["condition"]
        assert control.then_actions == raw["then_actions"]

    def test_then_actions_is_always_a_list(self):
        """A control with no actions reads as an empty list, not None."""
        from epanetparser.core.epanettypes.control import WNTREPANETControl

        assert WNTREPANETControl({"condition": "TANK 1 LEVEL BELOW 1"}).then_actions == []

    def test_then_actions_is_copied(self, net1):
        """The returned list is a copy, so mutating it cannot corrupt the model."""
        raw = first_raw(net1["raw"], "controls")
        control = next(
            c for c in net1["network"].controls if c.data.get("condition") == raw["condition"]
        )
        actions = control.then_actions
        actions.append("MUTATED")
        assert "MUTATED" not in control.then_actions


class TestSource:
    """Source accessors.

    These are the fields that two rules in this package originally got wrong, so
    they are asserted against Net2, which carries real sources.
    """

    @pytest.fixture
    def source(self, net2):
        """Return the first source of Net2 with the record it came from.

        Returns:
            tuple: ``(WNTREPANETSource, dict)``.
        """
        raw = first_raw(net2["raw"], "sources")
        source = net2["network"].sources[0]
        assert source.data["node_name"] == raw["node_name"], (
            "the parsed source is not the fixture's, so comparing them proves nothing"
        )
        return source, raw

    def test_source_type_is_exposed(self, source):
        """source_type reads WNTR's ``source_type``, not ``param``."""
        component, raw = source
        assert component.source_type == raw["source_type"]
        assert raw["source_type"], "the fixture carries no constituent to read"

    def test_the_node_name_is_exposed(self, source):
        """node_name names the node the constituent is injected into."""
        component, raw = source
        assert component.node_name == raw["node_name"]

    def test_the_strength_is_exposed(self, source):
        """strength is how much of the constituent is injected."""
        component, raw = source
        assert component.strength == raw["strength"]

    def test_the_pattern_is_exposed(self, source):
        """pattern reads WNTR's ``pattern``, not ``pattern_name``."""
        component, raw = source
        assert component.pattern == raw.get("pattern")

    def test_no_accessor_reads_a_field_wntr_does_not_write(self, source):
        """No accessor may fall back to a name WNTR never produces.

        This is the direct guard against the defect that was fixed: an accessor
        returning ``data.get("param")`` would still be consistent with itself,
        but would be wrong about WNTR's schema.
        """
        component, raw = source
        for accessor, wntr_key in (
            ("source_type", "source_type"),
            ("node_name", "node_name"),
            ("strength", "strength"),
            ("pattern", "pattern"),
        ):
            value = getattr(component, accessor)
            if value is None:
                continue
            assert wntr_key in raw, (
                f"{accessor} returned {value!r} but WNTR wrote no {wntr_key!r}"
            )


class TestNameCoercion:
    """A component's name is stored as a string even when it is not one.

    EPANET allows numeric identifiers, and WNTR sometimes hands them over as
    integers. A rule that compares a component's name against a string would
    otherwise miss every such component, and the model would appear to have
    duplicate names rather than one.

    Only the component kinds that are keyed by name coerce it. Sources and
    controls are identified by the node and condition they refer to, and do not
    carry a name of their own.
    """

    @pytest.mark.parametrize(
        "cls", ["WNTREPANETCurve", "WNTREPANETPattern", "WNTREPANETNode"]
    )
    def test_a_numeric_name_becomes_a_string(self, cls):
        """The coercion happens in the constructor, so it applies to every kind."""
        import epanetparser.core.epanettypes as types

        component = getattr(types, cls)({"name": 10})
        assert component.name == "10"

    def test_a_string_name_is_left_alone(self):
        """The common case is untouched."""
        from epanetparser.core.epanettypes.node import WNTREPANETNode

        assert WNTREPANETNode({"name": "J1"}).name == "J1"

    def test_an_absent_name_is_not_invented(self):
        """A component with no name has none; the rules report that."""
        from epanetparser.core.epanettypes.node import WNTREPANETNode

        assert WNTREPANETNode({}).name is None
