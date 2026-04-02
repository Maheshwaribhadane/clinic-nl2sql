import asyncio
from vanna_setup import get_agent
from vanna.core.user import User, RequestContext

async def test():
    agent, memory = get_agent()
    user = User(id="default_user", name="Clinic User")
    rc = RequestContext(user=user, params={}, metadata={})
    print("Sending message...")
    async for comp in agent.send_message(request_context=rc, message="How many patients do we have?", conversation_id="test-001"):
        rich = getattr(comp, "rich_component", None)
        if rich:
            rtype = type(rich).__name__
            attrs = [a for a in dir(rich) if not a.startswith("_")]
            print(f"TYPE: {rtype}")
            for attr in attrs:
                try:
                    val = getattr(rich, attr)
                    if not callable(val) and val is not None:
                        print(f"  {attr} = {str(val)[:150]}")
                except:
                    pass
            print("---")

asyncio.run(test())
