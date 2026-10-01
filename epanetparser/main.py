""" """
from dataclasses import asdict
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from epanetparser.core.logger_setup import LoggingConfig, configure_logging, get_logger, ENV_PREFIX


console = Console()
config = LoggingConfig()
yaml_config = yaml.safe_dump(asdict(config), sort_keys=False)
panel = Panel(Syntax(yaml_config, lexer="yaml"))
console.print(panel)