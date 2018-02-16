
### import

import asyncio

import aiographql

### test_listen_tcp

def test_listen_tcp(schema, curl, tcp_endpoint):

    servers = aiographql.serve(schema, listen=[tcp_endpoint], run=False)
    loop = asyncio.get_event_loop()

    async def client():
        result = await curl(tcp_endpoint, '{me {id}}')
        await servers.close()
        return result

    result = loop.run_until_complete(client())
    assert result == {'data': {'me': {'id': '42'}}}

### test_listen_unix

def test_listen_unix(schema, curl, unix_endpoint):

    servers = aiographql.serve(schema, listen=[unix_endpoint], run=False)
    loop = asyncio.get_event_loop()

    async def client():
        result = await curl(unix_endpoint, '{me {id}}')
        await servers.close()
        return result

    result = loop.run_until_complete(client())
    assert result == {'data': {'me': {'id': '42'}}}

### test_listen_unsupported

def test_listen_unsupported(schema, curl, tcp_endpoint):

    contexts = []

    def exception_handler(loop, context):
        contexts.append(context)

    unsupported_endpoint = tcp_endpoint.copy()
    unsupported_endpoint['protocol'] = 'udp'

    servers = aiographql.serve(schema, listen=[unsupported_endpoint], exception_handler=exception_handler, run=False)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(servers.close())

    assert len(contexts) == 1
    assert str(contexts[0]['exception']) == "Unsupported protocol='udp'"
