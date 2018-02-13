import os
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'requirements.txt'), 'r') as f:
    requirements = [line.rstrip() for line in f]

with open(os.path.join(here, 'requirements-test.txt'), 'r') as f:
    requirements_test = [line.rstrip() for line in f]

setup(
    name='aiograpi',
    version='0.1.0',
    description='Micro framework for fast, correct and simple api - graphql, asyncio, uvloop, min http',
    keywords='graphql asyncio uvloop',
    long_description='''
* `graphql <http://graphql.org/>`_ - all you need and nothing more in one request +auto docs of your api
* `asyncio <https://docs.python.org/3/library/asyncio.html>`_ - explicit concurrency `to reduce race conditions <https://glyph.twistedmatrix.com/2014/02/unyielding.html>`_
* `uvloop, protocol <https://github.com/MagicStack/uvloop#performance>`_ - `top performance <https://magic.io/blog/uvloop-blazing-fast-python-networking/>`_
* minimal http - unlike REST frameworks that are waste of time for ``/graphql`` endpoint
* pluggable context - for auth, etc
* exception handling - at all levels, with default or custom handler

Usage::

    pip install aiograpi

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

See `more examples and tests <https://github.com/academicmerit/aiograpi/tree/master/tests>`_ about JWT auth, concurrent slow DB queries, etc.

Config::

    import aiograpi; help(aiograpi.serve)

    serve(schema, get_context=None, unix_sock=None, exception_handler=None, enable_uvloop=True, run=True)
        Configure the stack and start serving requests

* ``schema``: ``graphene.Schema`` - GraphQL schema to serve
* ``get_context``: ``None`` or ``callable(headers: bytes, request: dict): mixed`` - callback to produce GraphQL context, for example auth
* ``unix_sock``: ``str`` - path to unix socket to listen for requests, defaults to env var ``UNIX_SOCK`` or ``'/tmp/worker0'``
* ``exception_handler``: ``None`` or ``callable(loop, context: dict)`` - default or custom exception handler as defined `here <https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.AbstractEventLoop.set_exception_handler>`_
* ``enable_uvloop``: ``bool`` - enable uvloop for top performance, unless you have a better loop
* ``run``: ``bool`` - if ``True``, run the loop and the coroutine serving requests, else return this coroutine
* return: ``coroutine`` or ``None`` - the coroutine serving requests, unless ``run=True``
''',
    url='https://github.com/academicmerit/aiograpi',
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
    py_modules=['aiograpi'],
    python_requires='>=3.5',
    install_requires=requirements,
    tests_require=requirements_test,
)
