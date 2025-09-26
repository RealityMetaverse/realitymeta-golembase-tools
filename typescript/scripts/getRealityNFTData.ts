import { createClient, AccountData, Tagged } from "golem-base-sdk";

// This is trash private key, can be exposed
const key: AccountData = new Tagged(
  "privatekey",
  new Uint8Array(
    "d119c5449177dd9755d5d5ad2c91218aec0e7e26a8183b502d87f1ca582a74b9"
      .match(/.{1,2}/g)!
      .map((byte) => parseInt(byte, 16))
  )
);

const chainId = 60138453032;
const rpcUrl = "https://reality-games.holesky.golemdb.io/rpc";
const wsUrl = "wss://reality-games.holesky.golemdb.io/rpc/ws";

// Target owner address for filtering
const TARGET_OWNER = "0x77AE0e97d8073AD7b529D5B67f389a2Ed6Cdf14f";

export class RealityNFTService {
  private client: any = null;
  private cache: Map<string, any> = new Map();
  private isInitialized = false;

  /**
   * Generate a composite cache key from category and tokenId
   * @param category - The system category
   * @param tokenId - The token ID
   * @returns string - The composite cache key
   */
  private getCacheKey(category: string, tokenId: string): string {
    return `${category}:${tokenId}`;
  }

  /**
   * Initialize the GolemDB client
   */
  private async initialize(): Promise<void> {
    if (this.isInitialized) return;

    try {
      this.client = await createClient(chainId, key, rpcUrl, wsUrl);
      this.isInitialized = true;
      console.log("✅ RealityNFTService initialized");
    } catch (error) {
      console.error("❌ Failed to initialize RealityNFTService:", error);
      throw new Error(`Service initialization failed: ${error}`);
    }
  }

  /**
   * Get metadata for a single tokenId
   * @param tokenId - The file stem (tokenId) to fetch
   * @returns Promise<any | null> - The converted JSON data or null if not found
   */
  async getData(
    tokenId: string,
    sysCategory: string = "REALITY_NFT_METADATA"
  ): Promise<any | null> {
    // Check cache first using composite key
    const cacheKey = this.getCacheKey(sysCategory, tokenId);
    if (this.cache.has(cacheKey)) {
      return this.cache.get(cacheKey);
    }

    await this.initialize();

    try {
      const query = this.buildQuery([tokenId], sysCategory);
      const entities = await this.client.queryEntities(query);

      if (entities.length === 0) {
        return null;
      }

      // Process entities to find one that belongs to the target owner
      for (const entity of entities) {
        const result = await this.processEntity(entity, tokenId, sysCategory);
        if (result) {
          return result;
        }
      }

      return null;
    } catch (error) {
      return null;
    }
  }

  /**
   * Get metadata for multiple tokenIds
   * @param tokenIds - Array of tokenIds to fetch
   * @returns Promise<Record<string, any>> - Dictionary mapping tokenId to data
   */
  async getMultipleData(
    tokenIds: string[],
    sysCategory: string = "REALITY_NFT_METADATA"
  ): Promise<Record<string, any>> {
    if (tokenIds.length === 0) return {};

    await this.initialize();

    const results: Record<string, any> = {};
    const uncachedTokenIds: string[] = [];

    // Check cache first using composite keys
    for (const tokenId of tokenIds) {
      const cacheKey = this.getCacheKey(sysCategory, tokenId);
      if (this.cache.has(cacheKey)) {
        const cachedData = this.cache.get(cacheKey);
        // For cached data, we can't check owner without re-fetching entity metadata
        // So we'll include it and let the user verify ownership separately
        results[tokenId] = cachedData;
      } else {
        uncachedTokenIds.push(tokenId);
      }
    }

    // If all are cached, return results
    if (uncachedTokenIds.length === 0) {
      return results;
    }

    try {
      const query = this.buildQuery(uncachedTokenIds, sysCategory);
      const entities = await this.client.queryEntities(query);

      // Process each entity
      for (const entity of entities) {
        const result = await this.processEntityForMultiple(entity, sysCategory);
        if (result) {
          results[result.tokenId] = result.data;
        }
      }

      return results;
    } catch (error) {
      return {};
    }
  }

  /**
   * Get all data for a specific category without filtering by tokenIds
   * @param sysCategory - The system category to fetch data for
   * @returns Promise<Record<string, any>> - Dictionary mapping tokenId to data
   */
  async getAllData(
    sysCategory: string = "REALITY_NFT_METADATA"
  ): Promise<Record<string, any>> {
    await this.initialize();

    const results: Record<string, any> = {};

    try {
      const query = this.buildAllDataQuery(sysCategory);
      const entities = await this.client.queryEntities(query);

      // Process each entity
      for (const entity of entities) {
        const result = await this.processEntityForMultiple(entity, sysCategory);
        if (result) {
          results[result.tokenId] = result.data;
        }
      }

      return results;
    } catch (error) {
      console.error("Error fetching all data:", error);
      return {};
    }
  }

  /**
   * Build query string for tokenIds
   * @param tokenIds - Array of tokenIds to query for
   * @param sysCategory - System category to filter by
   * @returns string - The constructed query
   */
  private buildQuery(tokenIds: string[], sysCategory: string): string {
    if (tokenIds.length === 1) {
      return `_sys_file_stem = "${tokenIds[0]}" && _sys_category = "${sysCategory}" && _sys_version = 1 && (_sys_status = "both" || _sys_status = "prod") && _sys_file_type = "json"`;
    }

    const tokenIdConditions = tokenIds
      .map((tokenId) => `_sys_file_stem = "${tokenId}"`)
      .join(" || ");

    return `(${tokenIdConditions}) && _sys_category = "${sysCategory}" && _sys_version = 1 && (_sys_status = "both" || _sys_status = "prod") && _sys_file_type = "json"`;
  }

  /**
   * Build query string for getAllData (no tokenId filtering)
   * @param sysCategory - System category to filter by
   * @returns string - The constructed query
   */
  private buildAllDataQuery(sysCategory: string): string {
    return `_sys_category = "${sysCategory}" && _sys_version = 1 && (_sys_status = "both" || _sys_status = "prod") && _sys_file_type = "json"`;
  }

  /**
   * Process a single entity for getData method
   * @param entity - The entity to process
   * @param expectedTokenId - The expected tokenId to match
   * @param sysCategory - The system category for cache key
   * @returns Promise<any | null> - The processed data or null
   */
  private async processEntity(
    entity: any,
    expectedTokenId: string,
    sysCategory: string
  ): Promise<any | null> {
    try {
      const entityMetadata = await this.client.getEntityMetaData(
        entity.entityKey
      );

      // Check if this entity belongs to the target owner
      if (this.hasOwnerInEntityMetadata(entityMetadata, TARGET_OWNER)) {
        // Get _sys_data from string annotations
        let base64Data = "";
        for (const annotation of entityMetadata.stringAnnotations) {
          if (annotation.key === "_sys_data") {
            base64Data = annotation.value;
            break;
          }
        }

        if (!base64Data) {
          return null;
        }

        // Decode base64 and parse JSON
        let data: any;
        try {
          const decodedData = atob(base64Data);
          data = JSON.parse(decodedData);
        } catch (parseError) {
          return null;
        }

        // Cache the result using composite key
        const cacheKey = this.getCacheKey(sysCategory, expectedTokenId);
        this.cache.set(cacheKey, data);
        return data;
      }
    } catch (entityError) {
      // Skip failed entities
    }
    return null;
  }

  /**
   * Process a single entity for getMultipleData method
   * @param entity - The entity to process
   * @param sysCategory - The system category for cache key
   * @returns Promise<{tokenId: string, data: any} | null> - The processed data with tokenId or null
   */
  private async processEntityForMultiple(
    entity: any,
    sysCategory: string
  ): Promise<{ tokenId: string; data: any } | null> {
    try {
      const entityMetadata = await this.client.getEntityMetaData(
        entity.entityKey
      );

      // Check if this entity belongs to the target owner
      if (this.hasOwnerInEntityMetadata(entityMetadata, TARGET_OWNER)) {
        // Extract tokenId and _sys_data from annotations
        let tokenId = "";
        let base64Data = "";

        for (const annotation of entityMetadata.stringAnnotations) {
          if (annotation.key === "_sys_file_stem") {
            tokenId = annotation.value;
          } else if (annotation.key === "_sys_data") {
            base64Data = annotation.value;
          }
        }

        if (!tokenId || !base64Data) {
          return null;
        }

        // Decode base64 and parse JSON
        let data: any;
        try {
          const decodedData = atob(base64Data);
          data = JSON.parse(decodedData);
        } catch (parseError) {
          return null;
        }

        // Cache and return result using composite key
        const cacheKey = this.getCacheKey(sysCategory, tokenId);
        this.cache.set(cacheKey, data);
        return { tokenId, data };
      }
    } catch (entityError) {
      // Skip failed entities
    }
    return null;
  }

  /**
   * Clear the cache
   */
  clearCache(): void {
    this.cache.clear();
    console.log("🗑️ Cache cleared");
  }

  /**
   * Clear cache for a specific category
   * @param sysCategory - The system category to clear
   */
  clearCacheForCategory(sysCategory: string): number {
    const keysToDelete: string[] = [];

    // Find all keys that belong to the specified category
    for (const key of this.cache.keys()) {
      if (key.startsWith(`${sysCategory}:`)) {
        keysToDelete.push(key);
      }
    }

    // Delete the keys
    for (const key of keysToDelete) {
      this.cache.delete(key);
    }

    console.log(
      `🗑️ Cleared ${keysToDelete.length} entries for category: ${sysCategory}`
    );
    return keysToDelete.length;
  }

  /**
   * Get cache statistics
   */
  getCacheStats(): {
    size: number;
    keys: string[];
    categories: Record<string, number>;
    categoryBreakdown: Record<string, string[]>;
  } {
    const keys = Array.from(this.cache.keys());
    const categories: Record<string, number> = {};
    const categoryBreakdown: Record<string, string[]> = {};

    // Analyze cache keys to extract category information
    for (const key of keys) {
      const [category, tokenId] = key.split(":");
      if (category) {
        categories[category] = (categories[category] || 0) + 1;
        if (!categoryBreakdown[category]) {
          categoryBreakdown[category] = [];
        }
        categoryBreakdown[category].push(tokenId);
      }
    }

    return {
      size: this.cache.size,
      keys,
      categories,
      categoryBreakdown,
    };
  }

  /**
   * Remove specific tokenId from cache for a specific category
   * @param tokenId - The tokenId to remove from cache
   * @param sysCategory - The system category (defaults to "REALITY_NFT_METADATA")
   */
  removeFromCache(
    tokenId: string,
    sysCategory: string = "REALITY_NFT_METADATA"
  ): boolean {
    const cacheKey = this.getCacheKey(sysCategory, tokenId);
    return this.cache.delete(cacheKey);
  }

  /**
   * Check if the entity metadata has the specified owner
   * @param entityMetadata - The entity metadata object to check
   * @param ownerAddress - The owner address to check for
   * @returns boolean - True if the entity belongs to the owner
   */
  private hasOwnerInEntityMetadata(
    entityMetadata: any,
    ownerAddress: string
  ): boolean {
    // Check if entityMetadata has owner property
    if (
      entityMetadata.owner &&
      entityMetadata.owner.toLowerCase() === ownerAddress.toLowerCase()
    ) {
      return true;
    }

    return false;
  }
}

// Export a singleton instance for easy use in React
export const realityNFTService = new RealityNFTService();

console.log("REALITY NFT METADATA");
console.log(await realityNFTService.getMultipleData(["613", "277"]));

console.log("\nREALITY NFT SPECIAL VENUES");
console.log(
  await realityNFTService.getMultipleData(
    ["613", "277"],
    "REALITY_NFT_SPECIAL_VENUES"
  )
);

console.log("\nALL REALITY NFT DATA (no tokenId filtering)");
console.log(await realityNFTService.getAllData("REALITY_NFT_SPECIAL_VENUES"));
