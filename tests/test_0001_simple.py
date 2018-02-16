
### import

import asyncio

import aiographql

### test

def test_simple(schema, curl, unix_endpoint):

    server_coro = aiographql.serve(schema, listen=[unix_endpoint], run=False)
    loop = asyncio.get_event_loop()
    server_task = loop.create_task(server_coro)

    async def client():
        result = await curl(unix_endpoint, '''{
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
