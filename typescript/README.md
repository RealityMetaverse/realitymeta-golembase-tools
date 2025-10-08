# Arkiv Reality NFT

A TypeScript service for interacting with Reality NFT data from the Arkiv network using the Golem Base SDK.

## Installation

```bash
npm install @realitymeta/arkiv-reality-nft
```

## Usage

### Basic Example

```typescript
import {
  RealityNFTService,
  SystemCategory,
} from "@realitymeta/arkiv-reality-nft";

// Create service with default configuration
const service = new RealityNFTService();

// Get all data for a specific category
const result = await service.getAllData({
  sysCategory: SystemCategory.REALITY_NFT_METADATA,
});

console.log("Total entities:", result.totalCount);
console.log("Data:", result.data);
```

### Custom Configuration

```typescript
import {
  RealityNFTService,
  RealityNFTConfig,
} from "@realitymeta/arkiv-reality-nft";

const config: RealityNFTConfig = {
  chainId: "CHAIN_ID",
  rpcUrl: "RPC_URL",
  wsUrl: "WS_URL",
  targetOwner: "TARGET_OWNER",
  privateKey: "YOUR_PRIVATE_KEY",
};

const service = new RealityNFTService(config);
```

### Advanced Querying

```typescript
import {
  RealityNFTService,
  SystemCategory,
  EntityType,
} from "@realitymeta/arkiv-reality-nft";

const service = new RealityNFTService();

// Query with filters and advanced search
const result = await service.getAllData({
  sysCategory: SystemCategory.REALITY_NFT_SPECIAL_VENUES,
  tokenKeywords: ["eiffel"],
  advancedSearch: true,
  skip: 0,
  limit: 10,
});

// Query by specific types
const buildings = await service.getAllData({
  sysCategory: SystemCategory.REALITY_NFT_METADATA,
  tokenTypes: [EntityType.BUILDING],
  tokenCountry: "France",
});

// Get single entity data
const tokenData = await service.getData("12345");

// Get multiple entities data
const multipleData = await service.getMultipleData(["12345", "67890"]);
```

## API

### RealityNFTService

Main service class for interacting with Reality NFT data.

#### Methods

- `isAvailable()`: Check if service is properly configured and available
- `getData(tokenId, sysCategory?)`: Get data for a single token ID
- `getMultipleData(tokenIds, sysCategory?)`: Get data for multiple token IDs
- `getAllData(options)`: Get all data with optional filtering and pagination
- `getCacheStats()`: Get cache statistics
- `clearCache()`: Clear all cached data
- `clearCacheForCategory(sysCategory)`: Clear cache for a specific category
- `removeFromCache(tokenId, sysCategory?)`: Remove specific token from cache

#### getAllData Options

```typescript
{
  sysCategory?: string;           // Default: REALITY_NFT_METADATA
  tokenTypes?: string[];          // Filter by entity types (building, city, country)
  tokenCountry?: string;          // Filter by country name
  tokenKeywords?: string[];       // Filter by keywords
  tokenSettlement?: string;       // Filter by settlement name
  advancedSearch?: boolean;       // Enable advanced search with type prioritization
  skip?: number;                  // Skip N results (pagination)
  limit?: number | null;          // Limit results (pagination)
}
```

### Types

The package exports all necessary TypeScript types:

- `RealityNFTConfig` - Service configuration
- `Entity` - Raw entity structure
- `ProcessedEntity` - Processed entity result
- `EntityMetadata` - Entity metadata structure
- `QueryParams` - Query parameters
- `AdvancedQueryParams` - Advanced query parameters
- `GetAllDataResult` - Result from getAllData
- `CacheStats` - Cache statistics
- `EntityInfo` - Entity information

### Enums

- `SystemCategory` - REALITY_NFT_METADATA, REALITY_NFT_SPECIAL_VENUES
- `EntityType` - BUILDING, CITY, COUNTRY

## Configuration

```typescript
interface RealityNFTConfig {
  chainId: string; // Blockchain chain ID
  rpcUrl: string; // RPC endpoint URL
  wsUrl: string; // WebSocket endpoint URL
  targetOwner: string; // Target owner address for filtering entities
  privateKey: string; // Private key for authentication
}
```

## License

BUSL-1.1
