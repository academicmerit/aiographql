
### import

import asyncio

import aiographql

### test

def test_simple(schema, curl):

    server_coro = aiographql.serve(schema, run=False)
    loop = asyncio.get_event_loop()
    server_task = loop.create_task(server_coro)

    async def client():
        result = await curl('''{
  me {
    id
    name
    friends {
      id
      name
    }
    # comment
  }
}''')
        server_task.cancel()
        return result

    result = loop.run_until_complete(client())
    assert result == {'data': {'me': {'id': '42', 'name': 'John', 'friends': []}}}
