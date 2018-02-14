#!/usr/bin/env python3
'''
Intro to async/await in Python 3.5+

by Denis Ryzhkov <denisr@denisr.com>
'''

### 1. Define two functions:

def twice(x):
    return x * 2

async def atwice(x):
    return x * 2

### 2. They are just functions:

assert repr(twice).startswith('<function twice at 0x')
assert repr(atwice).startswith('<function atwice at 0x')

### 3. Call the functions:

result = twice(2)
aresult = atwice(2)

### 4. Compare the results:

assert repr(result).startswith('4') and result == 4
assert repr(aresult).startswith('<coroutine object atwice at 0x') and aresult != 4
#                                 ^^^^^^^^^

### 5. Schedule the coroutine via "run_until_complete":

import asyncio
loop = asyncio.get_event_loop()

aresult_value = loop.run_until_complete(aresult)
assert repr(aresult_value) == '4'

### 6. Suspend one coroutine to await another coroutine and then resume first one:

async def one():
    print(1)
    result = await another()
    print(result)
    print(4)

async def another():
    print(2)
    return 3

loop.run_until_complete(one())
# Prints: 1 2 3 4

### 7. Concurrent waiting for over 9000 sloth DB queries:

from time import perf_counter as now
start = now()

loop.run_until_complete(asyncio.gather(*
    [asyncio.sleep(3.0)] * 9001
))

seconds = now() - start
print(seconds)  # 3.0708202040004835
assert 3.0 < seconds < 3.1

### 8. Create some tasks and run forever:

loop.create_task(atwice(21))
# Once done, returns 42 to nowhere.
# Please avoid callback hell: task = loop.create_task(...); task.add_done_callback(hell)
# Need result? await it as in steps 5 or 6 above.

loop.create_task(another())  # Once done, prints: 2
loop.run_forever()

### Further reading:

'''
https://docs.python.org/3/library/asyncio.html - the reference
https://glyph.twistedmatrix.com/2014/02/unyielding.html - especially the "Ca(sh|che Coherent) Money" section
https://vorpus.org/blog/some-thoughts-on-asynchronous-api-design-in-a-post-asyncawait-world/
'''
