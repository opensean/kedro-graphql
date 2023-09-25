from kedro.framework.startup import bootstrap_project
from kedro.framework.session import KedroSession
from kedro.framework.project import pipelines as PIPELINES
from pathlib import Path
from dotenv import dotenv_values
import os
from importlib import import_module
import logging
logger = logging.getLogger("kedro-graphql")

## pyproject.toml located in parent directory, required for project config
##project_path = Path.cwd()
##metadata = bootstrap_project(project_path)
#### pass env and conf source here
##session = KedroSession.create(metadata.package_name, project_path=project_path)
##context = session.load_context()
##
##conf_catalog = context.config_loader["catalog"]
##conf_parameters = context.config_loader["parameters"]

## define defaults
config = {
    "MONGO_URI": "mongodb://root:example@localhost:27017/",
    "MONGO_DB_NAME": "pipelines",
    "KEDRO_GRAPHQL_IMPORTS": "kedro_graphql.plugins.plugins,",
    "KEDRO_GRAPHQL_APP": "kedro_graphql.asgi.KedroGraphQL",
    "KEDRO_GRAPHQL_BACKEND": "kedro_graphql.backends.mongodb.MongoBackend",
    "KEDRO_GRAPHQL_BROKER": "redis://localhost",
    "KEDRO_GRAPHQL_CELERY_RESULT_BACKEND": "redis://localhost",
    "KEDRO_GRAPHQL_RUNNER": "kedro.runner.SequentialRunner",
    "KEDRO_GRAPHQL_ENV": "local",
    "KEDRO_GRAPHQL_CONF_SOURCE": None,
    #"KEDRO_GRAPHQL_RUNNER": "kedro_graphql.runner.argo.ArgoWorkflowsRunner",
    }

load_config = {
    **dotenv_values(".env"),  # load 
    **os.environ,  # override loaded values with environment variables
}

## override defaults
config.update(load_config)


RESOLVER_PLUGINS = {}
TYPE_PLUGINS = {"query":[],
                "mutation":[],
                "subscription":[]}

CONF_CATALOG = {}
CONF_PARAMETERS = {}

def discover_plugins():
    ## discover plugins e.g. decorated functions e.g @gql_query, etc...
    imports = [i.strip() for i in config["KEDRO_GRAPHQL_IMPORTS"].split(",") if len(i.strip()) > 0]
    for i in imports:
        import_module(i)   


def init_kedro_session(env = None, conf_source = None):
    ## pyproject.toml located in parent directory, required for project config
    project_path = Path.cwd()
    metadata = bootstrap_project(project_path)
    ## pass env and conf source here
    session = KedroSession.create(metadata.package_name, 
                                  project_path=project_path,
                                  env = config["KEDRO_GRAPHQL_ENV"],
                                  conf_source = config["KEDRO_GRAPHQL_CONF_SOURCE"])
    context = session.load_context()
    logger.info("initialized kedro session")
    CONF_CATALOG = context.config_loader["catalog"]
    CONF_PARAMETERS = context.config_loader["parameters"]

##module, class_name = config["KEDRO_GRAPHQL_RUNNER"].rsplit(".", 1)
##module = import_module(module)
##RUNNER = getattr(module, class_name)