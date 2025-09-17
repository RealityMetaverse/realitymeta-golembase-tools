import asyncio
import uuid
import dotenv
import os

from golem_base_sdk import GolemBaseClient, GolemBaseCreate, Annotation, GolemBaseUpdate, GolemBaseDelete, GenericBytes

dotenv.load_dotenv()

GOLEM_DB_RPC = "https://reality-games.holesky.golem-base.io/rpc"
GOLEM_DB_WSS = "wss://reality-games.holesky.golem-base.io/rpc/ws"
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

async def crud_example():
    # Create a client to interact with the GolemDB API
    golem_base_client = await GolemBaseClient.create(
        rpc_url=GOLEM_DB_RPC,
        ws_url=GOLEM_DB_WSS,
        private_key=PRIVATE_KEY,
    )
    print("Golem DB client initialized")

    await golem_base_client.watch_logs(
        label="",
        create_callback=lambda create: print(f"WATCH-> Create: {create}"),
        update_callback=lambda update: print(f"WATCH-> Update: {update}"),
        delete_callback=lambda delete: print(f"WATCH-> Delete: {delete}"),
        extend_callback=lambda extend: print(f"WATCH-> Extend: {extend}"),
    )

    # Create a new entity with annotations
    id = str(uuid.uuid4())
    receipt = await golem_base_client.create_entities([GolemBaseCreate(
        b'Test entity',
        600,
        [
            Annotation("testTextAnnotation", "demo"), 
            Annotation("id", id),
        ],
        [
            Annotation("version", 1)
        ]
    )])
    print(f"Receipt: {receipt}")

    # Query the entity by annotations
    entities = await golem_base_client.query_entities(f'id = "{id}" && version = 1')
    for entity in entities:
        print(f"Entity: {entity}")
    
    # Update the entity
    receipt = await golem_base_client.update_entities([GolemBaseUpdate(
        receipt[0].entity_key,
        b'Updated entity',
        1200,
        [
            Annotation("id", id)
        ],
        [
            Annotation("version", 2)
        ]
    )])
    print(f"Receipt: {receipt}")

    # Query updated entity by annotations
    entity_key = None
    entities = await golem_base_client.query_entities(f'id = "{id}" && version = 2')
    for entity in entities:
        print(f"Entity: {entity}")
        # we can also obtain the entity key from the entity object
        entity_key = entity.entity_key

    # Remove the entity
    receipt = await golem_base_client.delete_entities([GolemBaseDelete(
        GenericBytes.from_hex_string(entity_key),
    )])
    print(f"Receipt: {receipt}")

    await golem_base_client.disconnect()

asyncio.run(crud_example())