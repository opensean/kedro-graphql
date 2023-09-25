import click
import uvicorn
from importlib import import_module
from .config import config, discover_plugins, init_kedro_session

@click.group(name="kedro-graphql")
def commands():
    pass


@commands.command()
@click.pass_obj
@click.option(
    "--app",
    "-a",
    default = config["KEDRO_GRAPHQL_APP"],
    help="Application import path"
)
@click.option(
    "--env",
    "-e",
    default = 'local',
    help="Kedro configuration environment name. Defaults to `local`."
)
@click.option(
    "--imports",
    "-i",
    default = config["KEDRO_GRAPHQL_IMPORTS"],
    help="Additional import paths"
)
@click.option(
    "--worker",
    "-w",
    is_flag=True,
    default=False,
    help="Start a celery worker."
)
@click.option(
    "--conf-source",
    default = None,
    help="Path of a directory where project configuration is stored."
)
def gql(metadata, app, env, imports, worker, conf_source):
    """Commands for working with kedro-graphql."""
    if worker:
        from .celeryapp import app
        worker = app.Worker()
        worker.start()
    else:
        config["KEDRO_GRAPHQL_IMPORTS"] = imports
        config["KEDRO_GRAPHQL_APP"] = app
        config["KEDRO_GRAPHQL_ENV"] = env
        config["KEDRO_GRAPHQL_CONF_SOURCE"] = conf_source

        init_kedro_session()
        discover_plugins()
                
        module, class_name = config["KEDRO_GRAPHQL_APP"].rsplit(".", 1)
        module = import_module(module)
        class_inst = getattr(module, class_name)
        a = class_inst() 
        uvicorn.run(a, host="0.0.0.0", port=5000, log_level="info")
