
### import

import asyncio
import time

import aiographql

### test

def test_concurrency(schema, curl):

    server_coro = aiographql.serve(schema, run=False)
    loop = asyncio.get_event_loop()
    server_task = loop.create_task(server_coro)

    async def clients():

        started_at = time.perf_counter()
        sloths = [
            curl('query Sloth($seconds: Float) { slowDb(seconds: $seconds) }', {"seconds": seconds})
            for seconds in [0.5, 0.7, 0.5, 0.7, 0.5]
        ]
        await asyncio.gather(*sloths)
        result = time.perf_counter() - started_at

        server_task.cancel()
        return result

    result = loop.run_until_complete(clients())
    assert 0.70 < result < 0.75
