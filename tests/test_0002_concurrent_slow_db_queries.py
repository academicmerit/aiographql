
### import

import asyncio
import time

import aiographql

### test

def test_concurrency(schema, curl, unix_endpoint):

    servers = aiographql.serve(schema, listen=[unix_endpoint], run=False)
    loop = asyncio.get_event_loop()

    async def clients():

        started_at = time.perf_counter()
        sloths = [
            curl(unix_endpoint, 'query Sloth($seconds: Float) { slowDb(seconds: $seconds) }', {"seconds": seconds})
            for seconds in [0.5, 0.7, 0.5, 0.7, 0.5]
        ]
        await asyncio.gather(*sloths)
        result = time.perf_counter() - started_at

        await servers.close()
        return result

    result = loop.run_until_complete(clients())
    assert 0.70 < result < 0.75
