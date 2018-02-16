
### import

import asyncio

import aiographql

### test

def test_multiple_chunks(schema, curl, unix_endpoint):

    state = dict(chunks=0)
    old_data_received = aiographql.ConnectionFromClient.data_received

    def new_data_received(self, chunk):
        state['chunks'] += 1
        old_data_received(self, chunk)

    aiographql.ConnectionFromClient.data_received = new_data_received

    try:
        servers = aiographql.serve(schema, listen=[unix_endpoint], run=False)
        loop = asyncio.get_event_loop()

        async def client():
            result = await curl(unix_endpoint, '''{
  me {
    # {comment}
    id
  }
}'''.replace('{comment}', 's' * 10 * 1024))  # enough to produce multiple chunks
            await servers.close()
            return result

        result = loop.run_until_complete(client())
        assert result == {'data': {'me': {'id': '42'}}}
        assert state['chunks'] >= 2

    finally:
        aiographql.ConnectionFromClient.data_received = old_data_received
