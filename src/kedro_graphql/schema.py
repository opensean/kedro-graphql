from .config import PIPELINES, TYPE_PLUGINS
from .events import PipelineEventMonitor
import strawberry
from strawberry.tools import merge_types
from strawberry.types import Info
from typing import AsyncGenerator, List
from .celeryapp import app as APP_CELERY
from .tasks import run_pipeline
from .models import Parameter, DataSet, Pipeline, PipelineInput, PipelineEvent, PipelineLogMessage, PipelineTemplate, Tag
from .logs.logger import logger, PipelineLogStream

@strawberry.type
class Query:
    @strawberry.field
    def pipeline_templates(self) -> List[PipelineTemplate]:
        pipes = []
        for k,v in PIPELINES.items():
            pipes.append(PipelineTemplate(name = k))
        return pipes

    @strawberry.field
    def pipeline(self, id: str, info: Info) -> Pipeline:
        return info.context["request"].app.backend.load(id)


@strawberry.type
class Mutation:
    @strawberry.mutation
    def pipeline(self, pipeline: PipelineInput, info: Info) -> Pipeline:
        """
        - fill in missing values from default catalog?
        - is validation against template needed, e.g. check DataSet type or at least check the dataset names?
        """
        if pipeline.tags:
            tags = [Tag(**vars(t)) for t in pipeline.tags]
        else:
            tags = None

        ## check for credentials
        input_creds = []
        for i in pipeline.inputs:
            input_creds.append(i.serialize_credentials())
            delattr(i, "credentials")
            delattr(i, "credentials_nested")

        output_creds = []
        for o in pipeline.outputs:
            input_creds.append(o.serialize_credentials())
            delattr(o, "credentials")
            delattr(o, "credentials_nested")
                
        print(input_creds)
        print(output_creds)

        p = Pipeline(
            name = pipeline.name,
            inputs = [DataSet(**vars(i)) for i in pipeline.inputs],
            outputs = [DataSet(**vars(o)) for o in pipeline.outputs],
            parameters = [Parameter(**vars(p)) for p in pipeline.parameters],
            tags = tags,
            task_name = str(run_pipeline),
        )

        serial = p.serialize()

        ## merge any credentials with inputs and outputs
        ## credentials are intentionally not persisted

        result = run_pipeline.delay(
            name = serial["name"], 
            inputs = serial["inputs"], 
            outputs = serial["outputs"], 
            parameters = serial["parameters"]
        )  

        p.task_id = result.id
        p.status = result.status
        p.task_kwargs = str(
                {"name": serial["name"], 
                "inputs": serial["inputs"], 
                "outputs": serial["outputs"], 
                "parameters": serial["parameters"]}
        )
        
        ## PLACE HOLDER for future reolver plugins
        ## testing plugin_resolvers, 
        #RESOLVER_PLUGINS["text_in"].__input__("called text_in resolver")

        logger.info(f'Starting {p.name} pipeline with task_id: ' + str(p.task_id))

        p = info.context["request"].app.backend.create(p)

        return p


@strawberry.type
class Subscription:
    @strawberry.subscription
    async def pipeline(self, id: str, info: Info) -> AsyncGenerator[PipelineEvent, None]:
        p  = info.context["request"].app.backend.load(id=id)
        if p:
            async for e in PipelineEventMonitor(app = APP_CELERY, task_id = p.task_id).consume():
                e["id"] = id
                yield PipelineEvent(**e)

    @strawberry.subscription
    async def pipeline_logs(self, id: str, info: Info) -> AsyncGenerator[PipelineLogMessage, None]:
        p  = info.context["request"].app.backend.load(id=id)
        if p:
            async for e in PipelineLogStream(task_id = p.task_id ).consume():
                e["id"] = id
                yield PipelineLogMessage(**e)


def build_schema():
    ComboQuery = merge_types("Query", tuple([Query] + TYPE_PLUGINS["query"]))
    ComboMutation = merge_types("Mutation", tuple([Mutation] + TYPE_PLUGINS["mutation"]))
    ComboSubscription = merge_types("Subscription", tuple([Subscription] + TYPE_PLUGINS["subscription"]))
    
    return strawberry.Schema(query=ComboQuery, mutation=ComboMutation, subscription=ComboSubscription)
