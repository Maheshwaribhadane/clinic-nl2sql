import os
from dotenv import load_dotenv
load_dotenv()

from vanna import Agent, AgentConfig
from vanna.core.user import UserResolver, User, RequestContext
from vanna.core.registry import ToolRegistry
from vanna.tools import RunSqlTool, VisualizeDataTool
from vanna.tools.agent_memory import SaveQuestionToolArgsTool, SearchSavedCorrectToolUsesTool
from vanna.integrations.sqlite import SqliteRunner
from vanna.integrations.local.agent_memory import DemoAgentMemory
from vanna.integrations.google import GeminiLlmService

DB_PATH = "clinic.db"
GOOGLE_API_KEY = "AIzaSyCExx42FHtQ5_t1_fNcQLHisdN0f-qCNdw"

_agent = None
_memory = None

class DefaultUserResolver(UserResolver):
    async def resolve_user(self, context: RequestContext) -> User:
        return User(id="default_user", name="Clinic User")

def get_agent():
    global _agent, _memory
    if _agent is None:
        llm = GeminiLlmService(
            api_key=GOOGLE_API_KEY,
            model="gemini-2.5-flash"
        )
        db_runner = SqliteRunner(DB_PATH)

        tool_registry = ToolRegistry()
        tool_registry.register_local_tool(
            RunSqlTool(sql_runner=db_runner), access_groups=["admin"]
        )
        tool_registry.register_local_tool(
            VisualizeDataTool(), access_groups=["admin"]
        )
        tool_registry.register_local_tool(
            SaveQuestionToolArgsTool(), access_groups=["admin"]
        )
        tool_registry.register_local_tool(
            SearchSavedCorrectToolUsesTool(), access_groups=["admin"]
        )

        _memory = DemoAgentMemory()


        _agent = Agent(
            llm_service=llm,
            tool_registry=tool_registry,
            agent_memory=_memory,
            user_resolver=DefaultUserResolver(),
            config=AgentConfig()
        )

    

    return _agent, _memory