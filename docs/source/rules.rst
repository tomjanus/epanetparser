Rules, Warnings, and Rule Sets
==============================

Overview
--------

Rule
    A function that ``asserts`` something about a component or about a model as
    a whole. If the assertion holds, the rule passes. If it fails, an issue is
    recorded against the model, and the model is reported invalid.

Warning
    A rule that reports at :attr:`Severity.WARNING` rather than
    :attr:`Severity.ERROR`. A model with warnings but no errors is still valid.
    Warnings identify something that is legal but questionable, such as a
    modelling convention that is easy to miss or a potential future
    incompatibility.

Rule set
    A module collecting rules and warnings, which may be applied to a model as
    a group. Custom rule sets let different collections of rules be applied to
    the same model depending on the context the caller operates in.

Rules are plain functions. They are not methods on the component classes, and
nothing subclasses them. Adding validation never requires modifying a model
class, which is what makes it possible to impose an application's constraints on
a model without redefining what a valid EPANET model is.

Adding a rule
-------------

Add a function to a rule set module. Nothing else changes: no registry entry, no
import elsewhere, no base class to subclass.

.. code-block:: python

    from epanetparser.core.validation import rule

    @rule("WNTREPANETLink", code="E_NO_CHECK_VALVES", attribute="check_valve")
    def rule_no_check_valves(link) -> None:
        """A check valve is not supported by our solver."""
        assert link.data.get("check_valve") in (False, None), "Check valves not supported"

The arguments to :func:`rule` are the rule's metadata:

``component_type``
    The component class the rule applies to, as a string such as
    ``"WNTREPANETLink"``. Required.

``code``
    A stable identifier reported as the issue's ``code``, such as
    ``"E_NO_CHECK_VALVES"``. Optional; one is derived from the function name if
    omitted. This is part of the public API, because downstream tooling matches
    on it. Change it only deliberately.

``attribute``
    The field the rule concerns, such as ``"check_valve"``. Reported with the
    finding and used to group issues. Optional.

Severity follows from the function name. A function named ``rule_*`` reports at
:attr:`Severity.ERROR`; one named ``warn_*`` reports at :attr:`Severity.WARNING`.
Only :attr:`Severity.ERROR` makes a report invalid.

.. code-block:: python

    from epanetparser.core.validation import rule

    @rule("WNTREPANETNetworkInfo", code="W_NETWORK_VERSION_MISSING", attribute="version")
    def warn_network_has_version(network_info) -> None:
        """A network should declare the EPANET version it was written for."""
        assert network_info.data.get("version"), "Network missing a version"

Use ``defined()`` to require a field to carry a value, rather than merely to be
present. The distinction matters because JSON producers routinely emit
``"elevation": null`` when they have nothing to put in it, and a junction with
a null elevation is no more simulable than one whose elevation is absent.

.. code-block:: python

    from epanetparser.core.validation import defined, rule

    @rule("WNTREPANETNode", code="E_NODE_ELEVATION_MISSING", attribute="elevation")
    def rule_junction_has_elevation(node) -> None:
        """A junction must have an elevation."""
        assert defined(node, "elevation"), "Junction does not define elevation"

Restricting a rule with ``match``
---------------------------------

Some rules apply to only one kind of component: a junction should not be asked
for a tank diameter. The :func:`match` decorator narrows a rule accordingly. It
is imported from :mod:`epanetparser.core.decorators`, and applied *below*
:func:`rule`:

.. code-block:: python

    from epanetparser.core.decorators import match
    from epanetparser.core.validation import rule

    @rule("WNTREPANETNode", code="E_NODE_ELEVATION_MISSING", attribute="elevation")
    @match("Junction")
    def rule_junction_has_elevation(node) -> None:
        """A junction must have an elevation."""
        assert defined(node, "elevation"), "Junction does not define elevation"

Without a :func:`match` decorator, a rule applies to *every* instance of its
component type.

The decorator also accepts ``fuzzy=True``, which matches any component whose
type *contains* the given string, compared case-insensitively. This is useful
where a type name varies in case or carries a suffix.

Network rules
-------------

Some questions cannot be answered by looking at one component. Does a referenced
name exist? Is a name used twice? For those, use :func:`network_rule`, which
receives the model as a whole.

.. code-block:: python

    from epanetparser.core.validation import network_rule

    @network_rule(code="E_DUPLICATE_COMPONENT_NAME", attribute="name")
    def rule_component_names_unique(network) -> None:
        """Component names must be unique within their collection."""
        duplicates = []
        for collection in ("nodes", "links", "curves"):
            duplicates.extend(f"{collection} <{name}>" for name in network.index.duplicates(collection))
        assert not duplicates, f"Duplicate component names: {', '.join(sorted(duplicates))}"

    @network_rule(code="E_NETWORK_HAS_NODES", attribute="nodes")
    def rule_network_has_nodes(network) -> None:
        """A network must contain at least one named node."""
        assert len(network.index.nodes) > 0, "Network defines no named nodes"

A network rule resolves names through the model's ``index``, which the engine
builds and caches before any network rule runs. That is what lets a rule ask
whether ``pump_curve_name`` names a curve that exists:

.. code-block:: python

    @network_rule(code="E_UNKNOWN_CURVE", attribute="pump_curve_name")
    def rule_pump_curves_exist(network) -> None:
        """Every pump must reference a curve that exists."""
        for pump in network.links:
            curve = pump.data.get("pump_curve_name")
            assert not curve or curve in network.index.curves, "Unknown pump curve"

How a rule fails
----------------

A rule signals failure by raising, conventionally with ``assert``. Any exception
a rule raises is recorded as an issue against the model; that is the whole
contract.

An exception that is *not* :exc:`AssertionError` indicates a defect in the rule
rather than a finding about the model. Those raise :exc:`RuleExecutionError`
instead of being reported, because a broken rule silently reporting nothing
would let an invalid model pass.

Defining a rule set
-------------------

A rule set is a module declaring its identity, containing rule functions:

.. code-block:: python

    from epanetparser.core.validation import network_rule, rule

    __key__ = "my_project"
    __ruleset_name__ = "My project's rules"
    __version__ = "1.0.0"
    __description__ = "Constraints imposed by the tool this project builds."
    __is_core__ = False

    @rule("WNTREPANETLink", code="E_NO_CHECK_VALVES", attribute="check_valve")
    def rule_no_check_valves(link) -> None:
        """A check valve is not supported by our solver."""
        assert link.data.get("check_valve") in (False, None), "Check valves not supported"

__key__
    A short string identifying the rule set, e.g. ``"my_project"``. This is what
    ``--ruleset`` and :exc:`RuleSetSelectionError` refer to.

__ruleset_name__
    The full human-readable name, e.g. ``"My project's rules"``.

__version__
    A version string for the rule set, e.g. ``"1.0.0"``.

__description__
    A string describing what the rule set checks.

__is_core__
    ``True`` for a core rule set, ``False`` or absent for a custom one. Exactly
    one core rule set may be selected per validation run; any number of custom
    ones may be added alongside it.

Discovery
---------

Core and custom rule sets are found by the same pass over the packages named in
the ``rule_set_discovery`` section of the configuration file:

.. code-block:: yaml

    rule_set_discovery:
      packages:
        - epanetparser.core_rules
        - epanetparser.custom_rules

That configuration file is the single source of truth. It is written to a
platform-specific location on first import, and your settings are merged with
the package defaults, with yours taking precedence. The ``[tool.epanetparser]``
section of ``pyproject.toml`` is not read by the code.

A rule set published as a separate distribution can also register itself through
the ``epanetparser.rulesets`` entry point group, which is scanned alongside the
configured packages:

.. code-block:: toml

    [project.entry-points."epanetparser.rulesets"]
    my_project = "my_project.rulesets"

Nothing needs to be imported or listed by hand either way. If two rule sets
claim the same key, the configured packages win.

The rule set will then appear in the output of ``epanetparser info
--list-rulesets``:

.. code-block:: console

    $ epanetparser info --list-rulesets
    Available rule sets:
      epanet_core (core) - EPANET core rules v1.0.0
          module: epanetparser.core_rules.epanet_core
          rules: 35 component, 9 network
          Simulator-agnostic checks that a model is a well-formed EPANET model.
      milp (custom) - Mixed Integer Linear Programming ruleset v0.2.0
          module: epanetparser.custom_rules.milp
          rules: 17 component, 0 network
          Constraints imposed by an example MILP optimal pump scheduling tool.

...and may be applied to a model with the repeatable ``--ruleset`` option:

.. code-block:: console

    $ epanetparser validate -f model.json --ruleset milp --ruleset my_project

The core rule set
-----------------

``epanet_core`` checks that a model is a well-formed EPANET model: required
component fields, valid component types, well-formed curves, unique component
names, and references between components that resolve. It is simulator-agnostic,
like a compiler's static checks, and it makes no claim about whether a given
tool can simulate the result.

Constraints that belong to one application, such as the linearisation limits of
an MILP pump scheduling formulation, belong in a custom rule set. That
distinction is what the architecture exists to express: a model can be a valid
EPANET model and still be unusable by a particular tool, and both statements can
be true of the same object at the same time.

