import click
import uvicorn
from importlib import import_module
from .config import config, discover_plugins
#init_kedro_session
from kedro.framework.session import KedroSession
from .logs.logger import logger


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
    "--backend",
    default = config["KEDRO_GRAPHQL_BACKEND"],
    help="The only supported value for this option is 'kedro_graphql.backends.mongodb.MongoBackend'"
)
@click.option(
    "--broker",
    default = config["KEDRO_GRAPHQL_BROKER"],
    help="URI to broker e.g. 'redis://localhost'"
)
@click.option(
    "--celery-result-backend",
    default = config["KEDRO_GRAPHQL_CELERY_RESULT_BACKEND"],
    help="URI to backend for celery results e.g. 'redis://localhost'"
)
@click.option(
    "--conf-source",
    default = config["KEDRO_GRAPHQL_CONF_SOURCE"],
    help="Path of a directory where project configuration is stored."
)
@click.option(
    "--env",
    "-e",
    default = config["KEDRO_GRAPHQL_ENV"],
    help="Kedro configuration environment name. Defaults to `local`."
)
@click.option(
    "--imports",
    "-i",
    default = config["KEDRO_GRAPHQL_IMPORTS"],
    help="Additional import paths"
)
@click.option(
    "--mongo-uri",
    default = config["MONGO_URI"],
    help="URI to mongodb e.g. 'mongodb://root:example@localhost:27017/'"
)
@click.option(
    "--mongo-db-name",
    default = config["MONGO_DB_NAME"],
    help="Name to use for collection in mongo e.g. 'pipelines'"
)
@click.option(
    "--worker",
    "-w",
    is_flag=True,
    default=False,
    help="Start a celery worker."
)

def gql(metadata, app, backend, broker, celery_result_backend, conf_source, 
        env, imports, mongo_uri, mongo_db_name, worker):
    """Commands for working with kedro-graphql."""
    with KedroSession.create(metadata.package_name, project_path=metadata.project_path, env = env, conf_source = conf_source) as session:
        context = session.load_context()
        logger.info("initialized kedro session")
        
        ## capture cli config
        cli_config = {"KEDRO_GRAPHQL_APP": app,
                      "KEDRO_GRAPHQL_BACKEND": backend,
                      "KEDRO_GRAPHQL_BROKER": broker,
                      "KEDRO_GRAPHQL_CELERY_RESULT_BACKEND": celery_result_backend,
                      "KEDRO_GRAPHQL_CONF_SOURCE": conf_source,
                      "KEDRO_GRAPHQL_ENV": env,
                      "KEDRO_GRAPHQL_IMPORTS": imports,
                      "KEDRO_GRAPHQL_MONGO_URI": mongo_uri,
                      "KEDRO_GRAPHQL_MONGO_DB_NAME": mongo_db_name,
                      "KEDRO_GRAPHQL_WORKER": worker}

        cli_config["CONF_CATALOG"] = context.config_loader["catalog"]
        cli_config["CONF_PARAMETERS"] = context.config_loader["parameters"]

        ## update global config
        config.update(cli_config)
        discover_plugins()

        if worker:
            from .celeryapp import app
            worker = app.Worker()
            worker.start()

        else:
            module, class_name = app.rsplit(".", 1)
            module = import_module(module)
            class_inst = getattr(module, class_name)
            a = class_inst() 
            uvicorn.run(a, host="0.0.0.0", port=5000, log_level="info")
