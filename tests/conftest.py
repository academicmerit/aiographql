
### import

import asyncio

import graphene
import pytest
import ujson as json

### schema

@pytest.fixture
def schema():
    return graphene.Schema(query=Query, mutation=None)

class User(graphene.ObjectType):
    id = graphene.ID(required=True)
    name = graphene.String()
    friends = graphene.List(lambda: User)

    def resolve_friends(self, info):
        return []

class Query(graphene.ObjectType):
    me = graphene.Field(User)
    slow_db = graphene.Field(graphene.Boolean, seconds=graphene.Float())

    # NOTE this resolver is not async - because it does not need to await.
    def resolve_me(self, info):
        user_id = info.context and info.context['jwt'] and info.context['jwt']['id'] or 42
        return User(id=user_id, name='John')

    async def resolve_slow_db(self, info, seconds):
        await asyncio.sleep(seconds)
        return True

### endpoints

@pytest.fixture
def tcp_endpoint():
    return dict(protocol='tcp', port=25100)

@pytest.fixture
def unix_endpoint():
    return dict(protocol='unix', path='/tmp/aiographql-tests')

### curl

@pytest.fixture
def curl():
    return _curl

async def _curl(endpoint, query, variables=None, operation_name=None, extra_headers=None):

    ### format endpoint

    protocol = endpoint['protocol']

    if protocol == 'tcp':
        host = endpoint.get('host', 'localhost')
        assert isinstance(host, str), 'Test curl() supports single host only'
        endpoint = 'http://{}:{}/'.format(host, endpoint['port'])

    elif protocol == 'unix':
        endpoint = '--unix-socket {} http:/'.format(endpoint['path'])

    else:
        raise ValueError('Unsupported protocol={}'.format(repr(protocol)))

    ### format command

    # Produced by GraphiQL in Chrome - Dev tools - Network - Copy as cURL
    # plus --silent progress meter, custom endpoint and extra_headers:
    command = '''curl --silent {endpoint} \\
-H 'Origin: null' \\
-H 'Accept-Encoding: gzip, deflate, br' \\
-H 'Accept-Language: en-US,en;q=0.9,ru;q=0.8' \\
-H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36' \\
-H 'Content-Type: application/json' \\
-H 'Accept: application/json' \\
-H 'Connection: keep-alive' \\
{extra_headers} --data-binary '{content}' \\
--compressed'''.format(
        endpoint=endpoint,
        extra_headers=''.join("-H '{}' \\\n".format(header) for header in extra_headers) if extra_headers else '',
        content=json.dumps(dict(
            query=query,
            variables=variables,
            operationName=operation_name,
        )),
    )

    ### get response

    process = await asyncio.create_subprocess_shell(command,
        stdin=asyncio.subprocess.DEVNULL,  # Somewhy default "None" conflicts with "pytest" default capture mode.
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    assert stderr == b''
    return json.loads(stdout) if stdout else None
