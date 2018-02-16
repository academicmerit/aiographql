
### import

import asyncio

import aiographql

### test

def test_exception_handler(schema, curl, tcp_endpoint):

    state = dict(loop=None, context=None)

    def exception_handler(loop, context):
        state.update(loop=loop, context=context)

    servers = aiographql.serve(schema, listen=[tcp_endpoint], exception_handler=exception_handler, run=False)
    loop = asyncio.get_event_loop()

    async def client():
        result = await curl(tcp_endpoint, '''{
    me {
        password
    }
}''')
        await servers.close()
        return result

    result = loop.run_until_complete(client())

    assert result == {'errors': [{'locations': [{'line': 3, 'column': 9}], 'message': 'Cannot query field "password" on type "User".'}]}
    assert repr(state['loop']).startswith('<uvloop.Loop ')

    context = state['context']
    assert isinstance(context, dict)
    assert context['message'] == 'Cannot query field "password" on type "User".'
    assert repr(context['exception']) == '''GraphQLError('Cannot query field "password" on type "User".',)'''
    assert repr(context['protocol']).startswith('<aiographql.ConnectionFromClient object at 0x')

    remote_addr = context['transport'].get_extra_info('peername')
    assert isinstance(remote_addr, tuple)
    assert len(remote_addr) == 2
    host, port = remote_addr
    assert host == '127.0.0.1'
    assert isinstance(port, int)

    assert context['headers'] == b'''POST / HTTP/1.1
Host: localhost:25100
Origin: null
Accept-Encoding: gzip, deflate, br
Accept-Language: en-US,en;q=0.9,ru;q=0.8
User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36
Content-Type: application/json
Accept: application/json
Connection: keep-alive
Content-Length: 89'''.replace(b'\n', b'\r\n')

    assert context['request'] == {
        'variables': None,
        'operationName': None,
        'query': '''{
    me {
        password
    }
}'''}
