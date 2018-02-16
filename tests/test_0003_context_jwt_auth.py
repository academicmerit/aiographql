
### import

import asyncio
import re

import aiographql
import jwt

### const

AUTH_RE = re.compile(br'\r\nAuthorization:\s*Bearer\s+(\S+)', re.IGNORECASE)

JWT_SECRET = 'secret'
JWT_ALG = 'HS256'
JWT_PAYLOAD = {"id": "1042"}
JWT = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjEwNDIifQ.2j3hDntx8lXrFAUgKg0XmKN1WeqMdIBGt_G8ZkRW5f0'
# Produced by https://jwt.io/

### get_context

def get_context(headers, request):
    match = AUTH_RE.search(headers)
    return dict(
        jwt=jwt.decode(match.group(1), JWT_SECRET, algorithms=[JWT_ALG]) if match else None,
    )

### test

def test_get_context(schema, curl, unix_endpoint):

    server_coro = aiographql.serve(schema, listen=[unix_endpoint], get_context=get_context, run=False)
    loop = asyncio.get_event_loop()
    server_task = loop.create_task(server_coro)

    async def client():
        result = await curl(unix_endpoint, '{me {id}}', extra_headers=['Authorization: Bearer {}'.format(JWT)])
        server_task.cancel()
        return result

    result = loop.run_until_complete(client())
    assert result == {'data': {'me': {'id': '1042'}}}
