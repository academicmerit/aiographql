import os
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'requirements.txt'), 'r') as f:
    requirements = [line.rstrip() for line in f]

with open(os.path.join(here, 'requirements-test.txt'), 'r') as f:
    requirements_test = [line.rstrip() for line in f]

setup(
    name='aiographql',
    version='0.2.1',
    description='asyncio + graphql = fast and simple api',
    keywords='asyncio graphql graphene uvloop',
    long_description='''
* `asyncio <https://docs.python.org/3/library/asyncio.html>`_ - explicit concurrency `to reduce race conditions <https://glyph.twistedmatrix.com/2014/02/unyielding.html>`_
* `graphql <http://graphql.org/>`_ - all you need and nothing more in one request +auto docs of your api
* `uvloop, protocol <https://github.com/MagicStack/uvloop#performance>`_ - `top performance <https://magic.io/blog/uvloop-blazing-fast-python-networking/>`_
* minimal http - unlike REST frameworks that are waste of time for ``/graphql`` endpoint
* pluggable context - for auth, logging, etc
* exception handling - at all levels, with default or custom handler

**Usage**::

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

    curl http://localhost:25100/ --data-binary \\
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

See `more examples and tests <https://github.com/academicmerit/aiographql/tree/master/tests>`_ about JWT auth, concurrent slow DB queries, etc.

**Config**::

    import aiographql; help(aiographql.serve)

    serve(schema, listen, get_context=None, exception_handler=None, enable_uvloop=True, run=True)
        Configure the stack and start serving requests

* ``schema``: ``graphene.Schema`` - GraphQL schema to serve
* ``listen``: ``list`` - one or more endpoints to listen for connections:

    * ``dict(protocol='tcp', port=25100, ...)`` - `create_server() docs <https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.AbstractEventLoop.create_server>`_
    * ``dict(protocol='unix', path='/tmp/worker0', ...)`` - `create_unix_server() docs <https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.AbstractEventLoop.create_unix_server>`_

* ``get_context``: ``None`` or ``[async] callable(loop, context: dict): mixed`` - to produce GraphQL context like auth from input unified with ``exception_handler()``
* ``exception_handler``: ``None`` or ``callable(loop, context: dict)`` - default or custom exception handler as defined in `the docs <https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.AbstractEventLoop.set_exception_handler>`_ +

   * ``headers``: ``bytes`` or ``None`` - HTTP headers, if known
   * ``request``: ``dict`` or ``bytes`` or ``None`` - accumulated HTTP request before content length is known, then accumulated content, then GraphQL request

* ``enable_uvloop``: ``bool`` - enable uvloop for top performance, unless you have a better loop
* ``run``: ``bool`` - if ``True``, run the loop; ``False`` is good for tests
* return ``servers``: ``Servers`` - ``await servers.close()`` to close listening sockets - good for tests
''',
    url='https://github.com/academicmerit/aiographql',
    author='Denis Ryzhkov',
    author_email='denisr@denisr.com',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Unix',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    py_modules=['aiographql'],
    python_requires='>=3.5',
    install_requires=requirements,
    tests_require=requirements_test,
)
