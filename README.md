# aiographql

asyncio + graphql = fast and simple api

* `asyncio` - explicit concurrency to reduce race conditions  
  https://docs.python.org/3/library/asyncio.html  
  https://glyph.twistedmatrix.com/2014/02/unyielding.html
* `graphql` - all you need and nothing more in one request +auto docs of your api  
  http://graphql.org/  
  http://graphene-python.org/
* `uvloop`, `protocol` - top performance  
  https://magic.io/blog/uvloop-blazing-fast-python-networking/  
  https://github.com/MagicStack/uvloop#performance
* minimal http - unlike REST frameworks that are waste of time for `/graphql` endpoint
* pluggable context - for auth, logging, etc
* exception handling - at all levels, with default or custom handler

## Usage

    pip install aiographql

    cat <<'END' >serve.py
    import asyncio, aiographql, graphene

    class User(graphene.ObjectType):
        id = graphene.ID(required=True)
        name = graphene.String()

    class Query(graphene.ObjectType):
        me = graphene.Field(User)

        async def resolve_me(self, info):
            await asyncio.sleep(1)  # DB
            return User(id=42, name='John')

    schema = graphene.Schema(query=Query, mutation=None)

    aiographql.serve(schema, listen=[
        dict(protocol='tcp', port=25100),
        dict(protocol='unix', path='/tmp/worker0'),
    ])
    END

    python3 serve.py

    curl http://localhost:25100/ --data-binary \
    '{"query": "{
        me {
            id
            name
        }
    }", "variables": null}'

    # OR:
    curl --unix-socket /tmp/worker0 http:/ --data-binary ...

    # Result:
    # 1 second async await for DB and then:
    {"data":{"me":{"id":"42","name":"John"}}}

See more examples and tests about JWT auth, concurrent slow DB queries, remote_addr, etc:  
https://github.com/academicmerit/aiographql/tree/master/tests

## Config

    import aiographql; help(aiographql.serve)

    serve(schema, listen, get_context=None, exception_handler=None, enable_uvloop=True, run=True)
        Configure the stack and start serving requests

* `schema`: `graphene.Schema` - GraphQL schema to serve
* `listen`: `list` - one or more endpoints to listen for connections:
    * `dict(protocol='tcp', port=25100, ...)` - https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.AbstractEventLoop.create_server
    * `dict(protocol='unix', path='/tmp/worker0', ...)` - https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.AbstractEventLoop.create_unix_server
* `get_context`: `None` or `[async] callable(loop, context: dict): mixed` - to produce GraphQL context like auth from input unified with `exception_handler()`
* `exception_handler`: `None` or `callable(loop, context: dict)` - default or custom exception handler as defined in  
   https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.AbstractEventLoop.set_exception_handler +
    * `headers`: `bytes` or `None` - HTTP headers, if known
    * `request`: `dict` or `bytes` or `None` - accumulated HTTP request before content length is known, then accumulated content, then GraphQL request
* `enable_uvloop`: `bool` - enable uvloop for top performance, unless you have a better loop
* `run`: `bool` - if `True`, run the loop; `False` is good for tests
* return `servers`: `Servers` - `await servers.close()` to close listening sockets - good for tests

## TODO

* Support `GET` and `Content-Type: application/graphql`  
  http://graphql.org/learn/serving-over-http/#get-request  
  http://graphql.org/learn/serving-over-http/#post-request
* Support `GZIP`  
  http://graphql.org/learn/best-practices/#json-with-gzip  
  http://nginx.org/en/docs/http/ngx_http_gzip_module.html
* Support backpressure protection, etc  
  https://vorpus.org/blog/some-thoughts-on-asynchronous-api-design-in-a-post-asyncawait-world/
* Meet high quality standards and join https://github.com/aio-libs

## License

aiographql version 0.2.0  
Created and maintained by [Denis Ryzhkov](https://github.com/denis-ryzhkov/) \<denisr@denisr.com\> and other [aiographql authors](AUTHORS.md)  
Copyright (C) 2018 by AcademicMerit LLC (dba [FineTune](https://www.finetunelearning.com/))  
MIT License, see https://opensource.org/licenses/MIT
