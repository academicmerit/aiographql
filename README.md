# aiograpi

Micro framework for fast, correct and simple api - graphql, asyncio, uvloop, min http

* `graphql` - all you need and nothing more in one request +auto docs of your api  
  http://graphql.org/  
  http://graphene-python.org/
* `asyncio` - explicit concurrency to reduce race conditions  
  https://docs.python.org/3/library/asyncio.html  
  https://glyph.twistedmatrix.com/2014/02/unyielding.html
* `uvloop`, `protocol` - top performance  
  https://magic.io/blog/uvloop-blazing-fast-python-networking/  
  https://github.com/MagicStack/uvloop#performance
* minimal http - unlike REST frameworks that are waste of time for `/graphql` endpoint
* pluggable context - for auth, etc
* exception handling - at all levels, with default or custom handler

## Usage

    pip install aiograpi  # TODO: After switch to public.

    cat <<'END' >serve.py
    import asyncio, aiograpi, graphene

    class User(graphene.ObjectType):
        id = graphene.ID(required=True)
        name = graphene.String()

    class Query(graphene.ObjectType):
        me = graphene.Field(User)

        async def resolve_me(self, info):
            await asyncio.sleep(1)  # DB
            return User(id=42, name='John')

    schema = graphene.Schema(query=Query, mutation=None)
    aiograpi.serve(schema)
    END

    UNIX_SOCK=/tmp/worker0 python3 serve.py

    curl --unix-socket /tmp/worker0 http:/ --data-binary '{"query": "{
        me {
            id
            name
        }
    }", "variables": null}'

    # Result:
    # 1 second async await for DB and then:
    {"data":{"me":{"id":"42","name":"John"}}}

See more examples and tests about JWT auth, concurrent slow DB queries, etc:  
TODO:tests

## Config

    import aiograpi; help(aiograpi.serve)

    serve(schema, get_context=None, unix_sock=None, exception_handler=None, enable_uvloop=True, run=True)
        Configure the stack and start serving requests

* `schema`: `graphene.Schema` - GraphQL schema to serve
* `get_context`: `None` or `callable(headers: bytes, request: dict): mixed` - callback to produce GraphQL context, for example auth
* `unix_sock`: `str` - path to unix socket to listen for requests, defaults to env var `UNIX_SOCK` or `'/tmp/worker0'`
* `exception_handler`: `None` or `callable(loop, context: dict)` - default or custom exception handler as defined in  
  https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.AbstractEventLoop.set_exception_handler
* `enable_uvloop`: `bool` - enable uvloop for top performance, unless you have a better loop
* `run`: `bool` - if `True`, run the loop and the coroutine serving requests, else return this coroutine
* return: `coroutine` or `None` - the coroutine serving requests, unless `run=True`

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

aiograpi version 0.1.0  
Copyright (C) 2018 by Denis Ryzhkov <denisr@denisr.com>  
MIT License, see http://opensource.org/licenses/MIT
