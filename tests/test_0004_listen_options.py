
### import

import asyncio

import aiographql
import pytest

### test_listen_tcp

def test_listen_tcp(schema, curl, tcp_endpoint):

    server_coro = aiographql.serve(schema, listen=[tcp_endpoint], run=False)
    loop = asyncio.get_event_loop()
    server_task = loop.create_task(server_coro)

    async def client():
        result = await curl(tcp_endpoint, '{me {id}}')
        server_task.cancel()
        return result

    result = loop.run_until_complete(client())
    assert result == {'data': {'me': {'id': '42'}}}

### test_listen_unix

def test_listen_unix(schema, curl, unix_endpoint):

    server_coro = aiographql.serve(schema, listen=[unix_endpoint], run=False)
    loop = asyncio.get_event_loop()
    server_task = loop.create_task(server_coro)

    async def client():
        result = await curl(unix_endpoint, '{me {id}}')
        server_task.cancel()
        return result

    result = loop.run_until_complete(client())
    assert result == {'data': {'me': {'id': '42'}}}

### test_listen_unsupported

def test_listen_unsupported(schema, curl, tcp_endpoint):

    unsupported_endpoint = tcp_endpoint.copy()
    unsupported_endpoint['protocol'] = 'udp'

    server_coro = aiographql.serve(schema, listen=[unsupported_endpoint], run=False)
    loop = asyncio.get_event_loop()

    with pytest.raises(ValueError) as e:
        loop.run_until_complete(server_coro)

    assert "Unsupported protocol='udp'" in str(e)
