"""
aiographql version 0.2.1
asyncio + graphql = fast and simple api
Docs: https://github.com/academicmerit/aiographql/blob/master/README.md
"""

__version__ = '0.2.1'

### import

import asyncio
import datetime
import os
import re

import ujson as json
import uvloop
from graphql.error import format_error
from graphql.execution.executors.asyncio import AsyncioExecutor

### const

END_OF_HEADERS = b'\r\n\r\n'
CONTENT_LENGTH_RE = re.compile(br'\r\nContent-Length:\s*(\d+)', re.IGNORECASE)

HTTP_RESPONSE = '''HTTP/1.1 200 OK
Access-Control-Allow-Origin: *
Content-Length: {content_length}
Content-Type: application/json
Date: {date} GMT
Expires: Wed, 21 Oct 2015 07:28:00 GMT
Server: aiographql/{version}

{content}'''.replace('\n', '\r\n').replace('{version}', __version__)
# HTTP status is always "200 OK".
# Good explanation why: https://github.com/graphql-python/graphene/issues/142#issuecomment-221290862

### serve

def serve(schema, listen, get_context=None, exception_handler=None, enable_uvloop=True, run=True):
    """
    Configure the stack and start serving requests

    @param schema: graphene.Schema - GraphQL schema to serve

    @param listen: list - one or more endpoints to listen for connections:
        dict(protocol='tcp', port=25100, ...) - https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.AbstractEventLoop.create_server
        dict(protocol='unix', path='/tmp/worker0', ...) - https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.AbstractEventLoop.create_unix_server

    @param get_context: None or [async] callable(loop, context: dict): mixed - to produce GraphQL context like auth from input unified with exception_handler()

    @param exception_handler: None or callable(loop, context: dict) - default or custom exception handler as defined in
        https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.AbstractEventLoop.set_exception_handler +
        headers: bytes or None - HTTP headers, if known
        request: dict or bytes or None - accumulated HTTP request before content length is known, then accumulated content, then GraphQL request

    @param enable_uvloop: bool - enable uvloop for top performance, unless you have a better loop
    @param run: bool - if True, run the loop; False is good for tests
    @return servers: Servers - await servers.close() to close listening sockets - good for tests
    """
    try:
        if enable_uvloop:
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

        loop = asyncio.get_event_loop()

        if exception_handler:
            loop.set_exception_handler(exception_handler)

        servers = Servers()

        coro = _serve(schema, listen, get_context, loop, servers)
        if run:
            loop.run_until_complete(coro)
        else:
            loop.create_task(coro)

        return servers

    except Exception as e:
        asyncio.get_event_loop().call_exception_handler(dict(
            message=str(e),
            exception=e,
        ))

async def _serve(schema, listen, get_context, loop, servers):
    """
    The coroutine serving requests.
    Should be created by serve() only.

    @param schema: graphene.Schema - GraphQL schema to serve
    @param listen: list - one or more endpoints to listen for connections, as defined in serve()
    @param get_context: None or [async] callable(loop, context: dict): mixed - to produce GraphQL context like auth as defined in serve()
    @param loop: uvloop.Loop - or some other loop if you opted out of enable_uvloop=True
    @param servers: Servers - list that will be populated with asyncio.Server instances here
    """
    def protocol_factory():
        return ConnectionFromClient(schema, get_context, loop)

    assert listen, 'At least one endpoint should be specified in "listen"'
    for endpoint in listen:
        kwargs = endpoint.copy()  # to allow reuse of "listen" configuration
        protocol = kwargs.pop('protocol')

        if protocol == 'tcp':
            servers.append(await loop.create_server(protocol_factory, **kwargs))

        elif protocol == 'unix':
            if os.path.exists(kwargs['path']):
                os.remove(kwargs['path'])
            servers.append(await loop.create_unix_server(protocol_factory, **kwargs))

        else:
            raise ValueError('Unsupported protocol={}'.format(repr(protocol)))

    await asyncio.gather(*[server.wait_closed() for server in servers])

### Servers

class Servers(list):
    """
    A list of servers created by serve()
    """

    async def close(self):
        """
        Сlose listening sockets - good for tests
        """
        for server in self:
            server.close()

        await asyncio.gather(*[server.wait_closed() for server in self])

### ConnectionFromClient

class ConnectionFromClient(asyncio.Protocol):
    """
    Each connection from client is represented with a separate instance of this class.
    """

    def __init__(self, schema, get_context, loop):
        """
        @param schema: graphene.Schema - GraphQL schema to serve
        @param get_context: None or [async] callable(loop, context: dict): mixed - to produce GraphQL context like auth as defined in serve()
        @param loop: uvloop.Loop - or some other loop if you opted out of enable_uvloop=True
        """
        self.schema = schema
        self.get_context = get_context
        self.loop = loop

    ### connection_made

    def connection_made(self, transport):
        """
        Called by asyncio when connection from client is made.

        @param transport: uvloop.loop.TCPTransport or UnixTransport or some other transport if you opted out of enable_uvloop=True,
            but it should implement (may not inherit) asyncio.BaseTransport,ReadTransport,WriteTransport:
            https://docs.python.org/3/library/asyncio-protocol.html#transports
        """
        self.transport = transport
        self.prepare_for_new_request()

    ### prepare_for_new_request

    def prepare_for_new_request(self):
        """
        Should be called when we expect new request from this client connection:
        on connection_made() and on send_response()

        self.content_length: int, None - content length, if known
        self.headers: bytes or None - HTTP headers, if known
        self.request: bytes or None - accumulated HTTP request before content length is known, then accumulated content
        """
        self.content_length = None
        self.headers = None
        self.request = None

    ### data_received

    def data_received(self, chunk):
        """
        Called by asyncio when new chunk of data is received.

        This function is NOT async,
        and it is good both for correct order of chunks
        and for performance: no need to create_task() each time.

        Once all chunks are accumulated,
        GraphQL request is processed in async mode - to be able to await DB, etc.

        @param chunk: bytes
        """

        ### accumulate chunks

        if self.request is None:
            self.request = chunk
        else:
            self.request += chunk

        ### get content length

        if self.content_length is None:

            end_of_headers_index = self.request.find(END_OF_HEADERS)
            if end_of_headers_index == -1:
                return  # wait for the next chunk

            match = CONTENT_LENGTH_RE.search(self.request)
            if not match:
                message = '"Content-Length" header is not found'
                self.loop.call_exception_handler(dict(
                    message=message,
                    protocol=self,
                    transport=self.transport,
                    request=self.request,
                ))
                self.send_response({'errors': [{'message': message}]})
                return

            self.content_length = int(match.group(1))

            ### cut headers off

            self.headers = self.request[:end_of_headers_index]
            self.request = self.request[end_of_headers_index + len(END_OF_HEADERS):]

        ### get full request

        if len(self.request) < self.content_length:
            return  # wait for the next chunk

        ### process request

        self.loop.create_task(self.process_request(self.headers, self.request))
        # loop.create_task() is a bit faster than asyncio.ensure_future() when starting coroutines.

    ### process_request

    async def process_request(self, headers, request):
        """
        Execute GraphQL request in async mode and send response back to client.

        Resolvers that need to await DB, etc - should be async too.
        Other resolvers should NOT be async.

        @param headers: bytes or None - HTTP headers
        @param request: bytes - content of GraphQL request
        """
        json_error_message = None
        is_response_sent = False
        try:

            ### parse json

            try:
                request = json.loads(request)
                assert 'query' in request, '"query" key not found'

            except Exception as e:
                json_error_message = 'JSON: {}'.format(e)
                raise

            ### get context

            if self.get_context:
                context = self.get_context(self.loop, dict(
                    message=None,  # this field is required by format shared with exception_handler()
                    protocol=self,
                    transport=self.transport,
                    headers=headers,
                    request=request,
                ))
                if hasattr(context, '__await__'):
                    context = await context
            else:
                context = None

            ### execute GraphQL

            result = await self.schema.execute(
                request_string=request['query'],
                context_value=context,
                variable_values=request.get('variables'),
                operation_name=request.get('operationName'),
                executor=AsyncioExecutor(loop=self.loop),
                # AsyncioExecutor should not be reused - to avoid memory leak.
                # TODO: Check if my PR is released: https://github.com/graphql-python/graphql-core/pull/161
                # Then update "graphql-core==2.0" in requirements.txt and use shared AsyncioExecutor.
                return_promise=True,
            )

            ### format and send response to client

            response = {}
            if not result.invalid:
                response['data'] = result.data
            if result.errors:
                response['errors'] = [format_error(error) for error in result.errors]

            self.send_response(response)
            is_response_sent = True

            ### process errors at server side too

            if result.errors:
                for error in result.errors:
                    self.loop.call_exception_handler(dict(
                        message=error.message,
                        exception=getattr(error, 'original_error', error),
                        protocol=self,
                        transport=self.transport,
                        headers=headers,
                        request=request,
                    ))

        except Exception as e:

            self.loop.call_exception_handler(dict(
                message=str(e),
                exception=e,
                protocol=self,
                transport=self.transport,
                headers=headers,
                request=request,
            ))

            if not is_response_sent:
                self.send_response({'errors': [{'message': json_error_message or 'Internal Server Error'}]})

    ### send_response

    def send_response(self, response):
        """
        Send response to the client.

        @param response: dict - http://facebook.github.io/graphql/October2016/#sec-Response-Format
        """
        self.prepare_for_new_request()
        content = json.dumps(response)

        http_response = HTTP_RESPONSE.format(
            content_length=len(content),
            content=content,
            date=datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S'),
        )

        self.transport.write(http_response.encode())
