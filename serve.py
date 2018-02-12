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
