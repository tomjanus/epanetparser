"""How a broken rule is reported, and how rules are declared.

A rule is a plain function that signals a finding with ``assert``. That is a
deliberate design: the rule body reads as a statement about the model, and the
engine decides what a failure means. It has one consequence worth testing
directly, and it is the reason this file exists.

A rule that raises something other than ``AssertionError`` is a bug in the rule,
not a finding about the model. ``TypeError`` from a misspelled attribute, a
``KeyError`` from a field WNTR sometimes omits, a division by zero from a
malformed value: none of these say anything about the water network, and
reporting them as validation findings would put defects in the toolchain into
the user's report. They are re-raised as
:class:`~epanetparser.core.validation.rules.RuleExecutionError`, naming the rule
and the rule set, so the fault is attributed rather than swallowed.

That behaviour was exported, documented in two docstrings, and never exercised.
The rest of this file covers the declaration forms, which are cheap to state and
easy to regress.
"""
import pytest

from epanetparser.core.epanettypes.network import WNTREPANETNetwork
from epanetparser.core.validation import (
    RuleExecutionError,
    RuleSetRegistry,
    RuleSet,
    ValidationContext,
    network_rule,
    rule,
)

MINIMAL = (
    '{"network_info": {"title": "t", "version": "2.2"},'
    ' "options": {"energy": {"demand_charge": 0}, "hydraulic": {}, "quality": {},'
    ' "time": {"duration": 86400, "hydraulic_timestep": 3600, "quality_timestep": 3600, "pattern_timestep": 3600, "report_timestep": 3600, "rule_timestep": 3600}},'
    ' "nodes": [{"name": "J1", "node_type": "Junction", "elevation": 0}],'
    ' "links": [], "patterns": [], "curves": [], "sources": [], "controls": []}'
)


@pytest.fixture
def minimal():
    """Return the minimal model the broken rules are run against.

    Returns:
        WNTREPANETNetwork: A model with one junction and no links.
    """
    network, errors, _ = WNTREPANETNetwork.from_json(MINIMAL)
    assert network is not None, f"the fixture model did not parse: {errors}"
    return network


def registry_with(module) -> RuleSetRegistry:
    """Return a registry over the real core ruleset plus ``module`` as custom.

    Parameters
    ----------
    module : ModuleType
        A rule set module built by :func:`build_ruleset_module`.

    Returns:
        RuleSetRegistry: A registry that will resolve both rule sets.
    """
    ruleset = RuleSet.from_module(module)
    real = RuleSetRegistry()
    return RuleSetRegistry(rulesets=[real.get("epanet_core"), ruleset])


def build_ruleset_module(source: str):
    """Create a rule set module from source, without touching the filesystem.

    Parameters
    ----------
    source : str
        Python source for the module, including its rule set metadata.

    Returns:
        ModuleType: The executed module.
    """
    import textwrap
    from types import ModuleType

    module = ModuleType("broken_test_ruleset")
    exec(
        compile(textwrap.dedent(source), "<broken_test_ruleset>", "exec"),
        module.__dict__,
    )
    return module


#: A component rule that fails with something that is not an assertion.
BROKEN_COMPONENT_RULE = '''
    """A rule set whose component rule is broken on purpose."""
    __key__ = "broken"
    __ruleset_name__ = "Broken Ruleset"
    __version__ = "0.1"

    from epanetparser.core.validation import rule as _rule

    @_rule("WNTREPANETNode", code="X_TYPE_ERROR")
    def rule_raises_type_error(node):
        """Raise something that is not an assertion."""
        raise TypeError("deliberate failure inside a rule")
    rule_raises_type_error.__module__ = "broken_test_ruleset"
'''

#: A network rule that fails with something that is not an assertion.
BROKEN_NETWORK_RULE = '''
    """A rule set whose network rule is broken on purpose."""
    __key__ = "broken"
    __ruleset_name__ = "Broken Ruleset"
    __version__ = "0.1"

    from epanetparser.core.validation import network_rule as _network_rule

    @_network_rule(code="X_NETWORK_ERROR")
    def network_rule_raises(network):
        """Raise something that is not an assertion."""
        raise RuntimeError("deliberate network rule failure")
'''


class TestBrokenRules:
    """A rule that is itself broken must not be reported as a model defect."""

    def test_a_component_rule_failure_is_wrapped(self, minimal):
        """The error names the rule, so the author can find it.

        Reporting ``TypeError`` as a validation finding would be worse than
        useless: it would appear in the user's report as though the model were
        at fault, and would not say which rule produced it.
        """
        module = build_ruleset_module(BROKEN_COMPONENT_RULE)
        context = ValidationContext(
            core="epanet_core", custom=["broken"], registry=registry_with(module)
        )
        with pytest.raises(RuleExecutionError) as excinfo:
            minimal.validate(context)
        message = str(excinfo.value)
        assert "rule_raises_type_error" in message
        assert "broken" in message

    def test_a_network_rule_failure_is_wrapped(self, minimal):
        """The same holds for a rule applied to the whole network."""
        module = build_ruleset_module(BROKEN_NETWORK_RULE)
        context = ValidationContext(
            core="epanet_core", custom=["broken"], registry=registry_with(module)
        )
        with pytest.raises(RuleExecutionError) as excinfo:
            minimal.validate(context)
        assert "network_rule_raises" in str(excinfo.value)

    def test_the_original_exception_is_preserved(self, minimal):
        """The cause is attached, so the traceback points at the rule."""
        module = build_ruleset_module(BROKEN_COMPONENT_RULE)
        context = ValidationContext(
            core="epanet_core", custom=["broken"], registry=registry_with(module)
        )
        with pytest.raises(RuleExecutionError) as excinfo:
            minimal.validate(context)
        assert isinstance(excinfo.value.__cause__, TypeError)

    def test_an_assertion_is_still_just_a_finding(self, minimal):
        """The distinction is the exception type, not that it is an exception."""
        module = build_ruleset_module(
            '''
            """A rule set that reports a genuine finding."""
            __key__ = "asserting"
            __ruleset_name__ = "Asserting Ruleset"
            __version__ = "0.1"

            from epanetparser.core.validation import rule as _rule

            @_rule("WNTREPANETNode", code="X_ALWAYS")
            def rule_always(node):
                """Always fail, as a rule reporting a real defect would."""
                assert False, "the node is wrong"
            '''
        )
        context = ValidationContext(
            core="epanet_core", custom=["asserting"], registry=registry_with(module)
        )
        report = minimal.validate(context)
        assert "X_ALWAYS" in report.codes()


class TestDeclarationForms:
    """The ways a rule's subject and severity can be declared."""

    def test_a_component_type_may_be_taken_from_the_annotation(self):
        """Annotating the argument is enough to scope a rule.

        Writing the class name twice invites the two from drifting apart, so the
        annotation is accepted as an alternative.
        """
        from epanetparser.core.epanettypes.node import WNTREPANETNode

        @rule(code="X_ANNOTATED")
        def rule_annotated(node: WNTREPANETNode):
            pass

        assert rule_annotated.__epanetparser_rule__.component_type == "WNTREPANETNode"

    def test_an_optional_annotation_is_understood(self):
        """A rule may declare its argument as optional.

        ``Optional[Node]`` is what a type checker infers for a rule that does not
        use its argument, so it must not be mistaken for an unannotated one.
        """
        from typing import Optional

        from epanetparser.core.epanettypes.node import WNTREPANETNode

        @rule(code="X_OPTIONAL")
        def rule_optional(node: Optional[WNTREPANETNode]):
            pass

        assert rule_optional.__epanetparser_rule__.component_type == "WNTREPANETNode"

    def test_an_explicit_type_wins_over_the_annotation(self):
        """Naming the type explicitly overrides what the annotation says.

        Otherwise a rule that deliberately targets a superclass could not be
        written.
        """
        from epanetparser.core.epanettypes.node import WNTREPANETNode

        @rule("WNTREPANETType", code="X_EXPLICIT")
        def rule_explicit(node: WNTREPANETNode):
            pass

        assert rule_explicit.__epanetparser_rule__.component_type == "WNTREPANETType"

    def test_an_unannotated_rule_runs_everywhere(self):
        """With no subject named, the rule applies to every component."""
        @rule(code="X_EVERYWHERE")
        def rule_everywhere(node):
            pass

        assert rule_everywhere.__epanetparser_rule__.component_type is None

    def test_a_code_is_derived_when_none_is_given(self):
        """Omitting the code derives one from the rule function's name."""
        @rule("WNTREPANETNode")
        def rule_something_is_wrong(node):
            pass

        assert (
            rule_something_is_wrong.__epanetparser_rule__.code
            == "E_SOMETHING_IS_WRONG"
        )

    def test_severity_follows_the_function_name(self):
        """A ``warn_`` rule reports a warning; anything else an error.

        Only an error makes a report invalid, so this is the one place a rule
        author can accidentally change whether a model passes.
        """
        from epanetparser.core.validation import Severity

        @rule("WNTREPANETNode", code="X_ERROR")
        def rule_fails(node):
            pass

        @rule("WNTREPANETNode", code="X_WARNING")
        def warn_fails(node):
            pass

        assert rule_fails.__epanetparser_rule__.severity is Severity.ERROR
        assert warn_fails.__epanetparser_rule__.severity is Severity.WARNING

    def test_severity_can_be_stated_explicitly(self):
        """A rule that reports a warning without being named warn_ says so."""
        from epanetparser.core.validation import Severity

        @rule("WNTREPANETNode", code="X_EXPLICIT_SEVERITY", severity=Severity.WARNING)
        def rule_novel(node):
            pass

        assert rule_novel.__epanetparser_rule__.severity is Severity.WARNING

    def test_a_network_rule_names_the_network_as_its_subject(self):
        """A network rule's subject is the network, not a component type."""
        @network_rule(code="X_NET")
        def network_rule_novel(network):
            pass

        assert network_rule_novel.__epanetparser_network_rule__.is_network is True
        assert network_rule_novel.__epanetparser_network_rule__.component_type is None

    def test_a_rule_spec_reports_its_severity(self):
        """``RuleSpec`` answers whether it is an error or a warning.

        A rule set listing renders the severity, and it is read from here rather
        than re-derived from the function name.
        """
        @rule("WNTREPANETNode", code="E_SPEC")
        def rule_error(node):
            pass

        @rule("WNTREPANETNode", code="W_SPEC")
        def warn_warning(node):
            pass

        error_spec = rule_error.__epanetparser_rule__
        assert error_spec.is_error is True
        assert error_spec.is_warning is False
        warning_spec = warn_warning.__epanetparser_rule__
        assert warning_spec.is_warning is True
        assert warning_spec.is_error is False

    def test_a_rule_spec_describes_itself(self):
        """The description names the code, the rule and its subject."""
        @rule("WNTREPANETNode", code="E_X", attribute="diameter")
        def rule_x(node):
            pass

        text = str(rule_x.__epanetparser_rule__)
        assert "E_X" in text
        assert "rule_x" in text
        assert "WNTREPANETNode" in text


class TestResolveCoercion:
    """``resolve`` accepts anything a context can be built from."""

    def test_a_bare_key_is_accepted(self):
        """The registry coerces a loose selection rather than demanding a context."""
        selected = RuleSetRegistry().resolve("epanet_core")
        assert [ruleset.key for ruleset in selected] == ["epanet_core"]

    def test_a_list_of_keys_is_accepted(self):
        """A sequence of keys names a core rule set and its custom ones."""
        selected = RuleSetRegistry().resolve(["epanet_core", "milp"])
        assert [ruleset.key for ruleset in selected] == ["epanet_core", "milp"]

    def test_a_coerced_selection_is_validated_the_same_way(self):
        """Coercion does not bypass the exactly-one-core requirement."""
        from epanetparser.core.validation import RuleSetSelectionError

        with pytest.raises(RuleSetSelectionError):
            RuleSetRegistry().resolve(["milp"])
