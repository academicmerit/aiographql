
### import

import asyncio

import aiographql

### test

def test_simple(schema, curl, unix_endpoint):

    servers = aiographql.serve(schema, listen=[unix_endpoint], run=False)
    loop = asyncio.get_event_loop()

    async def client():
        result = await curl(unix_endpoint, '''{
  me {
    id
    name
    friends {
      id
      name
    }
  }
}''')
        await servers.close()
        return result

    result = loop.run_until_complete(client())
    assert result == {'data': {'me': {'id': '42', 'name': 'John', 'friends': []}}}
