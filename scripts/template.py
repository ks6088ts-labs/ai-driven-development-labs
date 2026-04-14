import logging
from typing import Annotated

import typer
from dotenv import load_dotenv

from ai_driven_development_labs.core import hello_world
from ai_driven_development_labs.loggers import get_logger
from ai_driven_development_labs.settings import get_project_settings

app = typer.Typer(
    add_completion=False,
    help="ai-driven-development-labs CLI",
)

logger = get_logger(__name__)


def set_verbose_logging(
    verbose: bool,
):
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
        logger.setLevel(logging.DEBUG)


@app.command()
def hello(
    name: Annotated[
        str,
        typer.Option(
            "--name",
            "-n",
            help="Name of the person to greet",
        ),
    ] = "World",
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose output"),
    ] = False,
):
    set_verbose_logging(verbose)

    hello_world(verbose=verbose)
    logger.debug(f"This is a debug message with name: {name}")
    logger.info(f"Settings from .env: {get_project_settings().model_dump_json(indent=2)}")


if __name__ == "__main__":
    if not load_dotenv(override=True, verbose=True):
        logging.warning("No .env file found; using defaults")
    app()
