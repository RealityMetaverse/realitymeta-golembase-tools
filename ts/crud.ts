import { createClient, AccountData, Tagged, GolemBaseCreate, Annotation, GolemBaseUpdate } from 'golem-base-sdk'
import { randomUUID } from 'crypto'

const key: AccountData = new Tagged(
    "privatekey", 
    Buffer.from('<YOUR_PRIVATE_KEY>', 'hex')
)  // TODO: replace with your private key, this variable will be used in the mutations operations
const chainId = 60138453025  // ID of the chain of our public testnet - Kaolin
const rpcUrl = "https://kaolin.holesky.golemdb.io/rpc"  // RPC URL of the chain
const wsUrl = "wss://kaolin.holesky.golemdb.io/rpc/ws"  // WebSocket URL of the chain

// TextEncoder and TextDecoder are used to encode and decode data from text into bytes and vice versa
const encoder = new TextEncoder()
const decoder = new TextDecoder()

// Create a client to interact with the GolemDB API
const client = await createClient(
    chainId,
    key,
    rpcUrl,
    wsUrl,
);

// Watch for logs on the chain
const unsubscribe = client.watchLogs({
    fromBlock: BigInt(await client.getRawClient().httpClient.getBlockNumber()),
    onCreated: (args) => {
        console.log("WATCH-> Create: ", args)
    },
    onUpdated: (args) => {
        console.log("WATCH-> Update: ", args)
    },
    onExtended: (args) => {
        console.log("WATCH-> Extend: ", args)
    },
    onDeleted: (args) => {
        console.log("WATCH-> Delete: ", args)
    },
    onError: (error) => {
        console.error("WATCH-> Error: ", error)
    },
    pollingInterval: 1000,
    transport: "websocket",
})

// Create a new entity with annotations
const id = randomUUID()
const creates = [
    {
      data: encoder.encode("Test entity"),
      btl: 600,
      stringAnnotations: [new Annotation("testTextAnnotation", "demo"), new Annotation("id", id)],
      numericAnnotations: [new Annotation("version", 1)]
    } as GolemBaseCreate]

const createReceipt = await client.createEntities(creates);
console.log('Receipt', createReceipt)

// Query the entity by annotations
let entities = await client.queryEntities(`id = "${id}" && version = 1`)
let entityKey: `0x${string}` | null = null
for (const entity of entities) {
    console.log('Entity value', decoder.decode(entity.storageValue))
    entityKey = entity.entityKey
}

// Update the entity
const updateReceipt = await client.updateEntities([{
    entityKey: createReceipt[0].entityKey,
    data: encoder.encode("Updated entity"),
    btl: 1200,
    stringAnnotations: [new Annotation("id", id)],
    numericAnnotations: [new Annotation("version", 2)]
} as GolemBaseUpdate])
console.log('Update', updateReceipt)

// Query the entity by annotations
entities = await client.queryEntities(`id = "${id}" && version = 2`)
console.log('Entities', entities)

// Delete the entity
const deleteReceipt = await client.deleteEntities([entityKey as `0x${string}`])
console.log('Delete', deleteReceipt)

unsubscribe()
process.exit(0)