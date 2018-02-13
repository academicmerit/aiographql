"""
aiographql version 0.1.0
asyncio + graphql = fast and simple api
Docs: https://github.com/academicmerit/aiographql/blob/master/README.md
"""

### import

import asyncio
import os
import re

import ujson as json
import uvloop
from graphql.error import format_error
from graphql.execution.executors.asyncio import AsyncioExecutor

### const

UNIX_SOCK_ENV_VAR = 'UNIX_SOCK'
UNIX_SOCK_DEFAULT = '/tmp/worker0'

END_OF_HEADERS = b'\r\n\r\n'
CONTENT_LENGTH_RE = re.compile(br'\r\nContent-Length:\s*(\d+)', re.IGNORECASE)

### serve

def serve(schema, get_context=None, unix_sock=None, exception_handler=None, enable_uvloop=True, run=True):
    """
    Configure the stack and start serving requests

    @param schema: graphene.Schema - GraphQL schema to serve
    @param get_context: None or callable(headers: bytes, request: dict): mixed - callback to produce GraphQL context, for example auth
    @param unix_sock: str - path to unix socket to listen for requests, defaults to env var UNIX_SOCK or '/tmp/worker0'
    @param exception_handler: None or callable(loop, context: dict) - default or custom exception handler as defined in
        https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.AbstractEventLoop.set_exception_handler
    @param enable_uvloop: bool - enable uvloop for top performance, unless you have a better loop
    @param run: bool - if True, run the loop and the coroutine serving requests, else return this coroutine
    @return: coroutine or None - the coroutine serving requests, unless run=True
    """
    try:
        if enable_uvloop:
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

        loop = asyncio.get_event_loop()

        if exception_handler:
            loop.set_exception_handler(exception_handler)

        if not unix_sock:
            unix_sock = os.environ.get(UNIX_SOCK_ENV_VAR, UNIX_SOCK_DEFAULT)

        coro = _serve(loop, schema, get_context, unix_sock)
        if run:
            loop.run_until_complete(coro)
        else:
            return coro

    except Exception as e:
        asyncio.get_event_loop().call_exception_handler(dict(
            message=str(e),
            exception=e,
        ))

async def _serve(loop, schema, get_context, unix_sock):
    """
    The coroutine serving requests.
    Should be created by serve() only.

    @param loop: uvloop.Loop - or some other loop if you opted out of enable_uvloop=True
    @param schema: graphene.Schema - GraphQL schema to serve
    @param get_context: None or callable(headers: bytes, request: dict): mixed - callback to produce GraphQL context, for example auth
    @param unix_sock: str - path to unix socket to listen for requests
    """
    if os.path.exists(unix_sock):
        os.remove(unix_sock)

    server = await loop.create_unix_server(lambda: ConnectionFromClient(loop, schema, get_context), unix_sock)
    await server.wait_closed()

### ConnectionFromClient

class ConnectionFromClient(asyncio.Protocol):
    """
    Each connection from client is represented with a separate instance of this class.
    """

    def __init__(self, loop, schema, get_context):
        """
        @param loop: uvloop.Loop - or some other loop if you opted out of enable_uvloop=True
        @param schema: graphene.Schema - GraphQL schema to serve
        @param get_context: None or callable(headers: bytes, request: dict): mixed - callback to produce GraphQL context, for example auth
        """
        self.loop = loop
        self.schema = schema
        self.get_context = get_context

    ### connection_made

    def connection_made(self, transport):
        """
        Called by asyncio when connection from client is made.

        @param transport: uvloop.loop.UnixTransport which implements (but not inherits) asyncio.BaseTransport,ReadTransport,WriteTransport,
            or some other transport if you opted out of enable_uvloop=True
        """
        self.transport = transport
        self.prepare_for_new_request()

    ### prepare_for_new_request

    def prepare_for_new_request(self):
        """
        Should be called when we expect new request from this client connection:
        on connection_made() and on send_response()

        self.request: bytes, None - accumulated HTTP request before content length is known, after - accumulated content
        self.content_length: int, None - content length, if known
        self.headers: bytes, None - HTTP headers, if known and required by "get_context"
        """
        self.request = None
        self.content_length = None
        self.headers = None

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
                self.send_response({'errors': [{'message': '"Content-Length" header is not found'}]})
                return

            self.content_length = int(match.group(1))

            ### cut headers off

            if self.get_context:
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

        @param headers: bytes, None - HTTP headers, if required by "get_context"
        @param request: bytes - content of GraphQL request
        """
        json_error_message = None
        is_response_sent = False
        try:
            ### json parser

            try:
                request = json.loads(request)
                assert 'query' in request, '"query" key not found'

            except Exception as e:
                json_error_message = 'JSON: {}'.format(e)
                raise

            ### execute GraphQL

            result = await self.schema.execute(
                request_string=request['query'],
                context_value=self.get_context(headers, request) if self.get_context else None,
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
                        message=json.dumps(dict(
                            request=request,
                            message=error.message,
                        )),
                        exception=getattr(error, 'original_error', error),
                    ))

        except Exception as e:

            self.loop.call_exception_handler(dict(
                message=json.dumps(dict(
                    request=request,
                    message=str(e),
                )),
                exception=e,
            ))

            if not is_response_sent:
                self.send_response({'errors': [{'message': json_error_message or 'Internal Server Error'}]})

    ### send_response

    def send_response(self, response):
        """
        Send response to the client.

        HTTP status is always "200 OK". Good explanation why:
        https://github.com/graphql-python/graphene/issues/142#issuecomment-221290862

        @param response: dict - http://facebook.github.io/graphql/October2016/#sec-Response-Format
        """
        self.prepare_for_new_request()
        content = json.dumps(response)

        http_response = '''HTTP/1.1 200 OK
Access-Control-Allow-Origin: *
Content-Length: {content_length}
Content-Type: application/json
Expires: Wed, 21 Oct 2015 07:28:00 GMT

{content}'''.format(
            content_length=len(content),
            content=content,
        )

        self.transport.write(http_response.encode())
