"""Configuration is a merge, and the merge is the whole point.

``ConfigLoader`` reads two files: the ``default_config.yaml`` bundled with the
package, and an optional user file in the platform configuration directory. The
user file is merged over the defaults. Everything subtle about the package's
behaviour flows from that one sentence, and every part of it has been wrong at
some point:

- When the merge replaced whole sections instead of merging them, a user who
  wanted a different log level lost every other logging setting and the package
  fell back to its dataclass defaults.
- When ``ConfigLoader.__init__`` created the configuration directory, importing
  ``epanetparser`` on a read-only home directory raised ``PermissionError`` and
  the whole package became unimportable.
- When the user file was allowed to replace the rule set search paths outright, a
  user who listed only their own package silently lost the core rule set, and
  the CLI reported a perfectly valid EPANET model as invalid with exit status 2.

So the merge is asserted directly, here, against the real bundled defaults rather
than against a fixture. A partial user file that sets one nested key must keep
that key's siblings, must keep every other section, and must be enough on its
own.

The second concern of this file is the *schema*: ``rule_set_discovery`` and
``logging`` are read by name from this YAML file, with no constant, no type
checking and no import to fail. Renaming a key there would not raise; it would
silently disable rule discovery. The contract test near the end of the file
parses ``default_config.yaml`` directly and asserts those keys exist.

Isolation
---------
Every test here sets ``XDG_CONFIG_HOME`` to a temporary directory before a
:class:`ConfigLoader` is constructed, so no test can read or write the
developer's real ``~/.config/epanetparser/``. :mod:`tests.test_cli` runs the CLI
in a subprocess and inherits the real home directory, which makes its results
depend on the machine it runs on; that is a latent flakiness bug, and repeating
it here would make this file flaky for the same reason. Where a specific file is
needed, the manager is constructed with an explicit ``config_path`` inside
``tmp_path`` instead.

Notes
-----
The root logger's handlers and level are snapshotted and restored around every
test, because ``import epanetparser`` configures logging as a side effect and
this file asserts on captured stdout.
"""
import logging
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional

import pytest
import yaml

import epanetparser
from epanetparser.core.config import Config, ConfigError, ConfigLoader
from epanetparser.core.validation.discovery import default_packages

#: The rule set search paths the package must find even when a user replaces
#: them. ``epanetparser.core_rules`` carries the core rule set; without it every
#: model is reported invalid.
CORE_RULES_PACKAGE = "epanetparser.core_rules"

CUSTOM_RULES_PACKAGE = "epanetparser.custom_rules"

#: The rotation threshold the package documents, named once so that a change to
#: the default is one deliberate edit rather than a hunt through the file.
DEFAULT_MAX_BYTES = 5242880


class UserConfigFile:
    """A user configuration file on disk, and the manager bound to it.

    Parameters
    ----------
    path : pathlib.Path
        Where the user file lives. The file need not exist yet.

    Attributes
    ----------
    path : pathlib.Path
        The user file's location.
    manager : ConfigLoader
        A manager bound to ``path``, and to nothing else.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.manager = ConfigLoader(config_path=path)

    def write(self, text: str) -> ConfigLoader:
        """Replace the file's contents and return the manager.

        Parameters
        ----------
        text : str
            The complete YAML text of the user file.

        Returns:
            ConfigLoader: The same manager, so a test can write and load in one
            expression.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(text, encoding="utf8")
        return self.manager


@pytest.fixture(autouse=True)
def isolated_config_home(tmp_path_factory) -> Iterator[Path]:
    """Point the platform configuration directory at a temporary tree.

    Parameters
    ----------
    tmp_path_factory : pytest.TempPathFactory
        Session-scoped factory for temporary directories.

    Yields:
        pathlib.Path: The value given to ``XDG_CONFIG_HOME``. A test that needs
        the manager to fall back to the platform default can write its file at
        ``<this>/epanetparser/default_config.yaml``.

    Notes
    -----
    This fixture is autouse because the alternative is that a test which forgets
    it silently reads the developer's own configuration, and passes or fails
    depending on what happens to be on their machine. :class:`ConfigLoader` is
    constructed inside tests, so the environment variable is set before any
    ``platformdirs`` lookup happens.
    """
    monkeypatch = pytest.MonkeyPatch()
    home = tmp_path_factory.mktemp("cfg")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home))
    try:
        yield home
    finally:
        monkeypatch.undo()


@pytest.fixture(autouse=True)
def preserved_root_logger() -> Iterator[None]:
    """Restore the root logger's handlers and level after each test.

    Yields:
        None: Control passes to the test with whatever logging state the test
        session happens to have.

    Notes
    -----
    ``import epanetparser`` installs a ``RichHandler`` on the root logger as a
    side effect. A test that added a handler and did not remove it would make
    the stdout assertions below fail for an unrelated reason, and would make
    every test after it in the session noisier.
    """
    root = logging.getLogger()
    handlers = root.handlers[:]
    level = root.level
    try:
        yield
    finally:
        for handler in list(root.handlers):
            if handler not in handlers:
                root.removeHandler(handler)
        root.handlers[:] = handlers
        root.setLevel(level)


@pytest.fixture
def user_config(tmp_path: Path) -> UserConfigFile:
    """A user configuration file under ``tmp_path``, bound to a manager.

    This is the primary seam: the path is named explicitly, so nothing about the
    test depends on where the platform would have looked.

    Returns:
        UserConfigFile: The file, holding no content yet, and the manager bound
        to it.
    """
    return UserConfigFile(tmp_path / "user_config.yaml")


@pytest.fixture
def xdg_user_config(isolated_config_home: Path) -> UserConfigFile:
    """A user file at the path :class:`ConfigLoader` finds with no argument.

    Returns:
        UserConfigFile: The file the *unbound* manager will read, so that code
        which constructs ``ConfigLoader()`` with no arguments, as
        :mod:`epanetparser.core.init` and
        :mod:`epanetparser.core.validation.discovery` both do, is exercised
        against this file rather than against the real home directory.
    """
    return UserConfigFile(isolated_config_home / "epanetparser" / "config.yaml")


def _bundled_defaults() -> Dict[str, Any]:
    """Return the packaged ``default_config.yaml`` as a mapping.

    Returns:
        dict: The parsed bundled defaults, read from the file rather than from a
        manager, so that a key removed from the file cannot be masked by the
        loader's own behaviour.
    """
    return yaml.safe_load(_bundled_defaults_text())


def _bundled_defaults_text() -> str:
    """Return the packaged ``default_config.yaml`` as text.

    Returns:
        str: The file's contents, via the Traversable the package ships.
    """
    return ConfigLoader().packaged_config_path.read_text(encoding="utf8")


class TestDeepMerge:
    """The merge primitive, pinned as a table.

    ``_deep_merge`` is where "user overrides defaults" is actually decided. These
    cases are its truth table; :class:`TestMerging` checks the same rules end to
    end through :meth:`ConfigLoader.load`, against the real defaults.
    """

    def test_a_nested_override_keeps_the_untouched_siblings(self) -> None:
        """Merging into a sub-dictionary leaves the keys it does not mention.

        This is the behaviour that lets a user set one logging option without
        restating the other twenty. Replacing the sub-dictionary instead would
        be a silent and total loss of settings, so it is worth its own test.
        """
        base = {"logging": {"level": "INFO", "max_bytes": 5242880, "backup_count": 5}}
        merged = ConfigLoader._deep_merge(base, {"logging": {"level": "DEBUG"}})
        assert merged["logging"] == {
            "level": "DEBUG",
            "max_bytes": 5242880,
            "backup_count": 5,
        }

    def test_the_recursion_reaches_deeply_nested_keys(self) -> None:
        """The merge continues past one level.

        A merge that stopped after one level would replace ``b`` wholesale here,
        dropping ``d`` for no stated reason.
        """
        merged = ConfigLoader._deep_merge(
            {"a": {"b": {"c": 1, "d": 2}}}, {"a": {"b": {"c": 99}}}
        )
        assert merged == {"a": {"b": {"c": 99, "d": 2}}}

    @pytest.mark.parametrize(
        "base, override",
        [
            pytest.param(
                {"logging": {"level": "INFO"}},
                {"logging": "disabled"},
                id="scalar_replaces_mapping",
            ),
            pytest.param(
                {"console": None},
                {"console": {"theme": "dark"}},
                id="mapping_replaces_scalar",
            ),
        ],
    )
    def test_a_non_mapping_on_either_side_replaces_wholesale(
        self, base: Dict[str, Any], override: Dict[str, Any]
    ) -> None:
        """When only one side is a mapping there is nothing to merge, so it wins.

        The two directions are separate branches of the condition in the
        implementation. A user who writes ``logging: null`` gets no logging
        section at all rather than a half-merged one, which is the only
        defensible reading: there is no meaningful merge of a scalar with a
        mapping.
        """
        assert ConfigLoader._deep_merge(base, override) == override

    def test_a_key_absent_from_the_defaults_is_added(self) -> None:
        """A user may introduce a section the defaults never mention.

        Without this, a third-party package could not ship its own configuration
        section through the user file.
        """
        assert ConfigLoader._deep_merge({"a": 1}, {"my_section": {"x": 1}}) == {
            "a": 1,
            "my_section": {"x": 1},
        }

    def test_the_defaults_are_not_mutated_by_a_merge(self) -> None:
        """The base mapping is left alone, so a merge cannot leak state.

        ``_load_defaults`` re-reads the file on every ``load``, so a merge that
        mutated its result would be invisible to a caller. The guarantee is
        asserted anyway because the failure would be very hard to trace.
        """
        base = {"logging": {"level": "INFO"}, "packages": ["a"]}
        ConfigLoader._deep_merge(base, {"logging": {"level": "DEBUG"}})
        assert base == {"logging": {"level": "INFO"}, "packages": ["a"]}


class TestMerging:
    """What a user file does to the packaged defaults, end to end."""

    def test_one_nested_override_changes_exactly_one_value(
        self, user_config: UserConfigFile
    ) -> None:
        """The headline case: set one nested key, keep everything else.

        ``logging: {level: DEBUG}`` must not cost the user ``max_bytes``,
        ``backup_count``, the formatter strings, or the sixteen other keys in
        that section. Comparing the whole section against the bundled file
        catches a key invented or lost as well as a value changed, and it does so
        without a copied snapshot to fall out of date. This is the defect that
        motivated the file.
        """
        defaults = _bundled_defaults()["logging"]
        merged = user_config.write("logging:\n  level: DEBUG\n").load()["logging"]
        assert merged["level"] == "DEBUG"
        assert merged["max_bytes"] == DEFAULT_MAX_BYTES
        assert set(merged) == set(defaults)
        assert {k for k in defaults if merged[k] != defaults[k]} == {"level"}

    def test_a_scalar_override_replaces_the_default(
        self, user_config: UserConfigFile
    ) -> None:
        """``INFO`` becomes ``DEBUG``; the default is not combined with it."""
        config = user_config.write("logging:\n  level: DEBUG\n").load()
        assert _bundled_defaults()["logging"]["level"] == "INFO"
        assert config["logging"]["level"] == "DEBUG"

    def test_a_false_default_can_be_turned_on(self, user_config: UserConfigFile) -> None:
        """A ``false`` default is overridable by ``true``.

        Several bundled defaults are ``false`` or ``null``, and a merge that
        tested truthiness rather than key presence would make those settings
        impossible to switch on. The user file's ``true`` has to survive.
        """
        assert _bundled_defaults()["logging"]["show_path"] is False
        config = user_config.write("logging:\n  show_path: true\n").load()
        assert config["logging"]["show_path"] is True

    def test_the_rule_set_search_path_list_is_replaced_not_extended(
        self, user_config: UserConfigFile
    ) -> None:
        """``packages`` ends up naming exactly what the user wrote.

        Documented behaviour, and load-bearing: the additive form is
        ``extra_packages``. A future change that concatenated the lists would
        make it impossible to drop a default search path, so the test names that
        to force the change to be deliberate.
        """
        config = user_config.write(
            "rule_set_discovery:\n  packages:\n    - my_own_pkg\n"
        ).load()
        assert config["rule_set_discovery"]["packages"] == ["my_own_pkg"]

    def test_a_partial_user_file_is_complete_and_valid(
        self, user_config: UserConfigFile
    ) -> None:
        """A one-key file overrides only that key; other sections stay whole.

        A user should not have to copy the packaged file to change one setting,
        and a section the file says nothing about must arrive untouched.
        """
        config = user_config.write("logging:\n  level: DEBUG\n").load()
        assert config["rule_set_discovery"] == _bundled_defaults()["rule_set_discovery"]

    def test_a_missing_user_file_yields_the_defaults_without_error(
        self, user_config: UserConfigFile
    ) -> None:
        """Absent is not an error.

        The overwhelming majority of users have no configuration file. Failing
        here would make the package unusable for them, and it is why nothing in
        the loading path creates the file.
        """
        assert not user_config.path.exists()
        assert user_config.manager.load()["logging"]["level"] == "INFO"

    def test_an_empty_user_file_yields_the_defaults(
        self, user_config: UserConfigFile
    ) -> None:
        """An empty file parses to nothing and is treated as no overrides."""
        config = user_config.write("").load()
        assert config["logging"] == _bundled_defaults()["logging"]

    def test_a_comment_only_user_file_yields_the_defaults(
        self, user_config: UserConfigFile
    ) -> None:
        """A file emptied of settings but not of prose still loads.

        Commenting out every setting is the usual way to get back to the
        defaults, so it should behave exactly like an empty file.
        """
        config = user_config.write(
            "# everything is commented out\n# level: DEBUG\n"
        ).load()
        assert config["logging"]["level"] == "INFO"

    def test_malformed_yaml_raises_config_error_naming_the_file(
        self, user_config: UserConfigFile
    ) -> None:
        """A syntax error is reported against the user's file, by path.

        The message has to say which file, because the two inputs are a bundled
        file the user cannot edit and a file they can. Without the path the only
        way to find the offending one is to guess.
        """
        manager = user_config.write("logging: [unclosed\n")
        with pytest.raises(ConfigError) as excinfo:
            manager.load()
        assert "Invalid YAML" in str(excinfo.value)
        assert str(user_config.path) in str(excinfo.value)

    @pytest.mark.parametrize(
        "text, expected_type",
        [
            pytest.param("- one\n- two\n", "list", id="list"),
            pytest.param("just a string\n", "str", id="str"),
            pytest.param("42\n", "int", id="int"),
        ],
    )
    def test_a_non_mapping_root_raises_config_error_not_attribute_error(
        self, user_config: UserConfigFile, text: str, expected_type: str
    ) -> None:
        """A user file that is not a mapping is a configuration error.

        Before this was a type check, merging a list root called ``.items()`` on
        it and the user saw an ``AttributeError`` traceback from inside the
        library. :class:`ConfigError` names the file and the type it found.
        """
        manager = user_config.write(text)
        with pytest.raises(ConfigError) as excinfo:
            manager.load()
        message = str(excinfo.value)
        assert f"must be a mapping, got {expected_type}" in message
        assert str(user_config.path) in message

    def test_a_directory_where_the_user_file_should_be_is_ignored(
        self, tmp_path: Path
    ) -> None:
        """A directory at the user config path is not treated as a file.

        ``exists()`` alone does not identify a file, and opening a directory
        raises ``IsADirectoryError``, which is neither a configuration error nor
        a user's mistake worth reporting.
        """
        as_dir = tmp_path / "user_config.yaml"
        as_dir.mkdir()
        manager = ConfigLoader(config_path=as_dir)
        assert manager.load()["logging"]["level"] == "INFO"

    def test_loading_twice_returns_the_same_result(
        self, user_config: UserConfigFile
    ) -> None:
        """Overrides do not accumulate across calls, and do not leak sideways.

        A manager that merged into its own previous result would double-apply
        list overrides and drift on repeated calls. The second manager checks the
        other direction: the packaged defaults are re-read from the file, so one
        manager's overrides cannot become another's defaults for the rest of the
        process.
        """
        manager = user_config.write("rule_set_discovery:\n  packages:\n    - p\n")
        first = manager.load()["rule_set_discovery"]["packages"]
        assert manager.load()["rule_set_discovery"]["packages"] == first == ["p"]
        elsewhere = ConfigLoader(
            config_path=user_config.path.with_name("elsewhere.yaml")
        )
        assert elsewhere.load()["logging"]["level"] == "INFO"


class TestSuppliedPathIsHonoured:
    """An explicit ``config_path`` is taken literally.

    A regression here is the worst kind this file guards. If the manager
    redirected an explicit path to the platform directory, a test that asked for
    an isolated file would silently read the developer's real configuration, and
    would then behave differently on different machines.
    """

    @pytest.mark.parametrize(
        "make_file",
        [
            pytest.param(lambda p: False, id="missing"),
            pytest.param(
                lambda p: p.write_text("a: [1,\n", encoding="utf8") or True,
                id="malformed",
            ),
        ],
    )
    def test_a_supplied_path_is_stored_verbatim(
        self, make_file: Callable[[Path], bool], tmp_path: Path
    ) -> None:
        """The path given is the path kept, whatever state the file is in.

        Checked for both a missing file and a broken one, because the two fail at
        different points and a redirect on either one would silently un-isolate
        the tests that depend on it.
        """
        path = tmp_path / "somewhere" / "else.yaml"
        path.parent.mkdir()
        if make_file(path):
            with pytest.raises(ConfigError, match=str(path)):
                ConfigLoader(config_path=path).load()
        assert ConfigLoader(config_path=path).config_path == path

    def test_the_default_path_is_the_platform_config_directory(
        self, isolated_config_home: Path
    ) -> None:
        """With no argument, the manager looks in ``$XDG_CONFIG_HOME``.

        Pinned so that the isolation fixture is known to be the thing redirecting
        it, rather than the explicit-path tests passing by accident.
        """
        expected = isolated_config_home / ConfigLoader.APP_NAME / "config.yaml"
        assert ConfigLoader().config_path == expected

    def test_a_user_file_at_the_default_path_is_read(
        self, xdg_user_config: UserConfigFile
    ) -> None:
        """The no-argument manager really does pick the file up.

        :mod:`epanetparser.core.init` and
        :mod:`epanetparser.core.validation.discovery` both construct
        ``ConfigLoader()`` with no arguments, so this is the path they take, and
        it is the path that the isolation fixture exists to redirect.
        """
        xdg_user_config.write("logging:\n  level: DEBUG\n")
        assert ConfigLoader().load()["logging"]["level"] == "DEBUG"


class TestConfigConstruction:
    """Building a :class:`Config` and getting it back out again."""

    def test_from_dict_preserves_the_data(self) -> None:
        """A mapping in gives the same mapping out."""
        data = {"a": 1, "b": {"c": "x"}}
        assert dict(Config.from_dict(data)) == data

    @pytest.mark.parametrize(
        "root",
        [
            pytest.param([1, 2], id="list"),
            pytest.param("s", id="str"),
            pytest.param(7, id="int"),
        ],
    )
    def test_from_dict_rejects_a_non_mapping_root(self, root: Any) -> None:
        """A non-mapping root is rejected at construction.

        Rejecting it here rather than at first access is what lets every later
        method assume a mapping, and so makes ``section()`` and ``instantiate()``
        total.
        """
        with pytest.raises(ConfigError, match="must be a dictionary/mapping"):
            Config.from_dict(root)

    def test_to_yaml_round_trips_through_from_dict(self) -> None:
        """Dump then load is the identity.

        ``to_yaml`` is how a user is shown the configuration they are editing,
        so a value that does not survive the round trip is a value the user
        cannot set by hand.
        """
        config = Config.from_dict({"logging": {"level": "DEBUG"}, "n": 3})
        assert Config.from_dict(yaml.safe_load(config.to_yaml())) == config


class TestMappingProtocol:
    """``Config`` behaves as a read-only mapping.

    The read-only part is not a promise about immutability of nested values,
    which is explicitly documented as absent; it is a promise that code holding a
    ``Config`` cannot corrupt it by assigning to it.
    """

    def test_len_counts_the_top_level_keys(self) -> None:
        """``len`` counts sections, not leaves."""
        assert len(Config.from_dict({"a": {"x": 1, "y": 2}, "b": 1})) == 2

    def test_the_views_describe_the_top_level(self) -> None:
        """``iter``, ``keys`` and ``items`` all report the sections, in order.

        Split across three methods these would assert the same delegation three
        times; what matters is that none of them descends into the nested values.
        """
        config = Config.from_dict({"a": 1, "b": {"c": 2}})
        assert list(config) == ["a", "b"]
        assert list(config.keys()) == ["a", "b"]
        assert list(config.items()) == [("a", 1), ("b", {"c": 2})]

    def test_membership_reports_whether_a_section_exists(self) -> None:
        """``in`` is answered by key presence, not by truthiness of the value."""
        config = Config.from_dict({"present": None, "absent": 1})
        assert "present" in config
        assert "absent" in config
        assert "missing" not in config

    def test_get_returns_the_default_for_a_missing_key(self) -> None:
        """``get`` with a default is the way callers avoid ``KeyError``.

        ``init.py`` and ``discovery.py`` both read sections this way, so the
        default argument is load-bearing rather than a convenience.
        """
        config = Config.from_dict({"a": 1})
        assert config.get("a") == 1
        assert config.get("b") is None
        assert config.get("b", "fallback") == "fallback"

    def test_a_missing_key_raises_key_error(self) -> None:
        """Indexing an absent key is a ``KeyError``, as the mapping protocol says."""
        with pytest.raises(KeyError):
            Config.from_dict({"a": 1})["b"]

    def test_assigning_a_top_level_key_raises_type_error(self) -> None:
        """A ``Config`` handed to a caller cannot be modified by that caller.

        The manager hands one object to logging setup and another to rule
        discovery. If either could write to it, the sections would drift apart
        within a single validation run.
        """
        config = Config.from_dict({"a": 1})
        with pytest.raises(TypeError):
            config["a"] = 2


class TestSection:
    """``section`` navigates nested mappings and refuses everything else."""

    def test_a_section_returns_its_nested_mapping(self) -> None:
        """The happy path: traverse one or several levels and read."""
        config = Config.from_dict({"a": {"b": {"c": 1}}})
        assert config.section("a", "b")["c"] == 1

    def test_a_missing_key_raises_config_error_naming_the_path(self) -> None:
        """An absent section is a configuration error, not a ``KeyError``.

        The caller is looking up a section by a name it believes in; a
        ``KeyError`` would read as a bug in the caller rather than as a missing
        setting.
        """
        config = Config.from_dict({"a": {"b": 1}})
        with pytest.raises(ConfigError, match="a.missing"):
            config.section("a", "missing")

    def test_traversing_through_a_non_mapping_raises_config_error(self) -> None:
        """Descending into a scalar is reported, not attempted.

        The check happens before the next lookup, so the message says the path is
        not a section rather than complaining about a key that was never there.
        """
        with pytest.raises(ConfigError, match="not a configuration section"):
            Config.from_dict({"a": 3}).section("a", "deeper")

    def test_a_section_that_is_not_a_mapping_raises_config_error(self) -> None:
        """A scalar leaf is not a section."""
        with pytest.raises(ConfigError, match="must be a mapping"):
            Config.from_dict({"a": {"b": 3}}).section("a", "b")

    def test_a_section_is_read_only(self) -> None:
        """The returned mapping cannot be written to either.

        Same reason as the top level: ``section()`` is how callers reach nested
        values, so it has to offer the same guarantee one level down.
        """
        section = Config.from_dict({"a": {"b": 1}}).section("a")
        with pytest.raises(TypeError):
            section["b"] = 2


class TestInstantiate:
    """``instantiate`` hands a section to a ``from_dict`` constructor."""

    def test_instantiate_calls_from_dict_with_the_section(self) -> None:
        """The class receives the section, and its return value is passed through.

        This is the seam that keeps the configuration package free of domain
        objects: the loader does not know what a ``LoggingConfig`` is, it only
        knows the ``FromDict`` protocol.
        """
        received: List[Any] = []

        class Consumer:
            """Records the section it was handed."""

            @classmethod
            def from_dict(cls, data: Any) -> "Consumer":
                received.append(dict(data))
                return cls()

        result = Config.from_dict({"thing": {"x": 1}}).instantiate("thing", Consumer)
        assert received == [{"x": 1}]
        assert isinstance(result, Consumer)

    def test_instantiate_of_a_missing_section_raises_config_error(self) -> None:
        """A missing section is caught before the class is ever asked."""

        class Consumer:
            """Should never be constructed."""

            @classmethod
            def from_dict(cls, data: Any) -> "Consumer":  # pragma: no cover
                raise AssertionError("from_dict must not be called")

        with pytest.raises(ConfigError):
            Config.from_dict({"a": 1}).instantiate("absent", Consumer)


class TestRepr:
    """The representation has to be useful in a failure message."""

    def test_repr_names_the_class_and_shows_the_data(self) -> None:
        """``Config({...})`` with the keys visible, not a bare object address."""
        text = repr(Config.from_dict({"logging": {"level": "DEBUG"}}))
        assert text.startswith("Config(")
        assert "logging" in text
        assert "DEBUG" in text


class TestBundledDefaultConfigContract:
    """The bundled YAML file is an interface the package reads by name.

    ``rule_set_discovery`` and ``logging`` are looked up as string keys in
    :mod:`epanetparser.core.init` and
    :mod:`epanetparser.core.validation.discovery`. There is no constant, no
    schema and no import that would fail on a rename: the lookup would simply
    return an empty section, logging would fall back to its dataclass defaults,
    and rule discovery would fall back to the built-in list. Nothing would raise.
    This class parses the file directly so that a rename fails a test instead.
    """

    @pytest.mark.parametrize(
        "section, key",
        [
            pytest.param("rule_set_discovery", "packages", id="search_paths"),
            pytest.param("rule_set_discovery", "extra_packages", id="additive_paths"),
            pytest.param("logging", None, id="logging"),
        ],
    )
    def test_the_keys_the_package_reads_are_present(
        self, section: str, key: Optional[str]
    ) -> None:
        """Each key the package reads exists in the bundled file."""
        data = _bundled_defaults()
        assert section in data
        if key is not None:
            assert key in data[section]

    def test_the_default_search_paths_are_the_two_builtin_packages(self) -> None:
        """The file ships the same list ``discovery._BUILTIN_PACKAGES`` names.

        Read from the file rather than from the constant, so that the constant
        and the file cannot drift apart unnoticed.
        """
        assert _bundled_defaults()["rule_set_discovery"]["packages"] == [
            CORE_RULES_PACKAGE,
            CUSTOM_RULES_PACKAGE,
        ]

    def test_the_additive_search_path_list_is_empty_by_default(self) -> None:
        """``extra_packages`` exists and is a list.

        Its presence is the contract: the additive form is only usable because
        the key is documented, and an absent key is indistinguishable from "no
        user additions" to anything reading it with ``get``.
        """
        extra = _bundled_defaults()["rule_set_discovery"]["extra_packages"]
        assert isinstance(extra, list)
        assert extra == []

    def test_the_logging_defaults_match_the_documented_values(self) -> None:
        """Two defaults the rest of the package and its docs rely on."""
        logging_section = _bundled_defaults()["logging"]
        assert logging_section["level"] == "INFO"
        assert logging_section["max_bytes"] == DEFAULT_MAX_BYTES

    def test_the_resource_is_readable_as_text_and_as_a_stream(self) -> None:
        """The bundled resource supports both ``read_text`` and ``open``.

        ``packaged_config_path`` is an ``importlib.resources`` Traversable,
        not necessarily a filesystem path, so this pair of operations is the
        interface :meth:`ConfigLoader._load_defaults` and this file's contract
        tests both depend on.
        """
        resource = ConfigLoader().packaged_config_path
        assert resource.read_text(encoding="utf8") == _bundled_defaults_text()
        with resource.open("r", encoding="utf8") as handle:
            assert yaml.safe_load(handle) == _bundled_defaults()

    def test_loading_with_no_user_file_reproduces_the_bundled_file(
        self, tmp_path: Path
    ) -> None:
        """``load()`` with nothing to merge returns the file, unchanged.

        Ties the two halves of the class together: if a future change filtered
        or defaulted a key on the way through the loader, the packaged file would
        no longer describe what the package actually runs with.
        """
        manager = ConfigLoader(config_path=tmp_path / "absent.yaml")
        assert dict(manager.load()) == _bundled_defaults()


class TestNoFilesystemSideEffects:
    """Constructing and loading a manager must not touch the filesystem.

    ``epanetparser/__init__.py`` calls ``initialize()`` at import, which builds a
    :class:`ConfigLoader` and loads it. So any filesystem work on this path runs
    on every ``import epanetparser`` in the world. That is what made a read-only
    home directory a fatal import error, back when the constructor created its
    directory.
    """

    def test_construction_creates_no_directory(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A home directory that does not exist stays non-existent.

        Asserting absence and not merely the absence of an exception matters: a
        ``mkdir`` inside a ``try`` would satisfy an exception check while still
        littering the user's home directory.
        """
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        home = tmp_path / "no_such_home"
        monkeypatch.setenv("HOME", str(home))
        manager = ConfigLoader()
        assert not home.exists()
        assert not manager.config_dir.exists()

    def test_construction_succeeds_with_a_read_only_home(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A read-only home raises nothing, and the defaults still load.

        ``mkdir`` under a directory without write permission raises
        ``PermissionError``; this is the exact failure that made the package
        unimportable for users with a read-only home.
        """
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        read_only = tmp_path / "read_only_home"
        read_only.mkdir(mode=0o500)
        monkeypatch.setenv("HOME", str(read_only))
        manager = ConfigLoader()
        assert manager.load()["logging"]["level"] == "INFO"

    def test_loading_creates_no_directory_either(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Nor does ``load``, which is the other entry point.

        Loading happens on every import through :mod:`epanetparser.core.init`, so
        a ``mkdir`` here would be just as fatal as one in the constructor.
        """
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        home = tmp_path / "absent_home"
        monkeypatch.setenv("HOME", str(home))
        manager = ConfigLoader()
        assert manager.load()["logging"]["level"] == "INFO"
        assert not home.exists()


class TestPackageInitialisation:
    """Importing the package must complete, and must complete its setup.

    :mod:`epanetparser.core.init` builds a :class:`ConfigLoader` on import. A
    change to the configuration API therefore breaks ``import epanetparser`` for
    everyone, and it did: ``init`` once called a ``create_user_config()`` that no
    longer existed, and the failure surfaced as an ``AttributeError`` during
    import rather than as anything recognisable about configuration.
    """

    def test_importing_the_package_initialises_it(self) -> None:
        """``import epanetparser`` leaves the package initialised.

        ``is_initialized`` lives in :mod:`epanetparser.core.init`; the package
        namespace re-exports ``initialize`` but not ``is_initialized``, so it is
        reached through the module.
        """
        from epanetparser.core.init import is_initialized

        assert epanetparser.initialize is not None
        assert is_initialized() is True


class TestRuleSetDiscoveryReadsConfiguration:
    """Rule discovery must not be able to lose the core rule set.

    :func:`default_packages` is what the CLI uses to decide which rule sets
    exist. It reads this configuration file, so a mistake here does not raise: it
    silently changes what "valid" means. One such mistake shipped, and the CLI
    reported a valid EPANET model as invalid with exit status 2.
    """

    def test_extra_packages_are_appended_after_the_builtins(
        self, xdg_user_config: UserConfigFile
    ) -> None:
        """The additive form puts the user's package last.

        Order matters: the core rule set must be the first hit for its key, so a
        third-party package cannot shadow it by being listed first.
        """
        xdg_user_config.write("rule_set_discovery:\n  extra_packages: [my_own_pkg]\n")
        assert default_packages() == [
            CORE_RULES_PACKAGE,
            CUSTOM_RULES_PACKAGE,
            "my_own_pkg",
        ]

    def test_a_replacing_packages_list_still_keeps_the_core_rule_set(
        self, xdg_user_config: UserConfigFile
    ) -> None:
        """``packages: [my_own_pkg]`` must not drop the built-ins.

        The documented merge replaces ``packages``, so this file is exactly what
        a user writes when they mean to search one extra package. Before the
        built-ins were seeded in :mod:`discovery`, that user got a search list
        with no core rule set, and every model came back invalid.
        """
        xdg_user_config.write("rule_set_discovery:\n  packages: [my_own_pkg]\n")
        packages = default_packages()
        assert CORE_RULES_PACKAGE in packages
        assert "my_own_pkg" in packages

    def test_a_package_declared_twice_is_searched_once(
        self, xdg_user_config: UserConfigFile
    ) -> None:
        """Redeclaring a built-in does not search it twice.

        ``extra_packages`` is additive and the default ``packages`` already names
        the built-ins, so a user who listed the core package in both would
        otherwise import it twice and see duplicate-key warnings.
        """
        xdg_user_config.write(
            f"rule_set_discovery:\n  extra_packages: [{CORE_RULES_PACKAGE}, zzz]\n"
        )
        assert default_packages() == [
            CORE_RULES_PACKAGE,
            CUSTOM_RULES_PACKAGE,
            "zzz",
        ]

    def test_with_no_user_file_the_builtins_are_searched(
        self, isolated_config_home: Path
    ) -> None:
        """The unpackaged case, and the baseline the three above are read against.

        The directory is asserted absent, not just unused, so this cannot pass by
        picking up a file left behind by another test in the session.
        """
        assert not (isolated_config_home / ConfigLoader.APP_NAME).exists()
        assert default_packages() == [CORE_RULES_PACKAGE, CUSTOM_RULES_PACKAGE]


class TestLoadedConfigurationIsQuiet:
    """Loading configuration must not write to stdout.

    ``epanetparser validate`` is consumed as a machine-readable exit status, and
    other consumers parse its output. Any stray print from configuration loading
    would corrupt that stream. The one message ``load`` emits is a
    ``logger.debug``, so at the packaged ``INFO`` verbosity nothing is expected.
    """

    def test_a_merged_load_writes_nothing_to_stdout(
        self, user_config: UserConfigFile, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Neither stream is touched, on either the merged or the default path."""
        user_config.write("logging:\n  level: DEBUG\n").load()
        user_config.manager.load()
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""
