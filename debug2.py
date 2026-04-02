import asyncio
from vanna_setup import get_agent
from vanna.core.user import User, RequestContext

async def test():
    agent, memory = get_agent()
    user = User(id="default_user", name="Clinic User")
    rc = RequestContext(user=user, params={}, metadata={})
    async for comp in agent.send_message(request_context=rc, message="How many patients do we have?", conversation_id="test-002"):
        rich = getattr(comp, "rich_component", None)
        if rich:
            comp_type = str(getattr(rich, "type", "")).lower()
            if "text" in comp_type:
                content = getattr(rich, "content", "") or ""
                print("=== FULL CONTENT ===")
                print(repr(content))
                print("=== END ===")

asyncio.run(test())
