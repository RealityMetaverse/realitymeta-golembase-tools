import { createClient, AccountData, Tagged } from "golem-base-sdk";

// Configuration - these would typically come from environment variables
const config = {
  CHAIN_ID: "60138453032",
  RPC_URL: "https://reality-games.hoodi.arkiv.network/rpc",
  WS_URL: "wss://reality-games.hoodi.arkiv.network/rpc/ws",
  TARGET_OWNER: "0x744A2Bb994246810450375a23251F5298764122e",
  // This is trash private key, can be exposed
  PRIVATE_KEY:
    "d4fa9b8ee991d792547ba95f779ee34780d1a705455200887c8721662f55e7ed",
};

/**
 * Create account data from configuration
 * @returns AccountData or null if configuration is invalid
 */
function createAccountDataFromConfig(): AccountData | null {
  try {
    return new Tagged(
      "privatekey",
      new Uint8Array(
        config.PRIVATE_KEY.match(/.{1,2}/g)!.map((byte) => parseInt(byte, 16))
      )
    );
  } catch (error) {
    console.error("Failed to create account data:", error);
    return null;
  }
}

export class RealityNFTService {
  private client: any = null;
  private cache: Map<string, any> = new Map();
  private isInitialized = false;
  private isServiceAvailable = false;

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
      // Check if all required config is available
      if (
        !config.CHAIN_ID ||
        !config.RPC_URL ||
        !config.WS_URL ||
        !config.TARGET_OWNER
      ) {
        throw new Error("Missing required Golem configuration");
      }

      const accountData = createAccountDataFromConfig();
      if (!accountData) {
        throw new Error("Failed to create account data from configuration");
      }

      const chainId = parseInt((config as any).CHAIN_ID);
      this.client = await createClient(
        chainId,
        accountData,
        (config as any).RPC_URL,
        (config as any).WS_URL
      );
      this.isInitialized = true;
      this.isServiceAvailable = true;
      console.log("✅ RealityNFTService initialized with environment config");
      console.log(`   Chain ID: ${config.CHAIN_ID}`);
      console.log(`   RPC URL: ${config.RPC_URL}`);
      console.log(`   Target Owner: ${(config as any).TARGET_OWNER}`);
    } catch (error) {
      console.error("❌ Failed to initialize RealityNFTService:", error);
      this.isServiceAvailable = false;
      this.isInitialized = true; // Mark as initialized even if failed to prevent retries
      throw new Error(`Service initialization failed: ${error}`);
    }
  }

  /**
   * Check if the service is available and configured properly
   * @returns Promise<boolean> - True if service is ready to use
   */
  async isAvailable(): Promise<boolean> {
    if (!this.isInitialized) {
      try {
        await this.initialize();
        return this.isServiceAvailable;
      } catch {
        return false;
      }
    }
    return this.isServiceAvailable;
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
      const query = this.buildQuery({
        tokenIds: [tokenId],
        sysCategory,
      });
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
      const query = this.buildQuery({
        tokenIds: uncachedTokenIds,
        sysCategory,
      });
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
   * @param skip - Number of elements to skip from the beginning (default: 0)
   * @param limit - Maximum number of elements to return after skip (default: null for no limit)
   * @returns Promise<{ data: Record<string, any>; totalCount: number }> - Dictionary mapping tokenId to data
   */
  async getAllData({
    sysCategory = "REALITY_NFT_METADATA",
    tokenCategory,
    tokenCountry,
    tokenKeyword,
    skip = 0,
    limit = null,
  }: {
    sysCategory: string;
    tokenCategory?: string;
    tokenCountry?: string;
    tokenKeyword?: string;
    skip: number;
    limit: number | null;
  }): Promise<{ data: Record<string, any>; totalCount: number }> {
    await this.initialize();
    const results: Record<string, any> = {};

    // CATEGORY
    // KEYWORD
    // COUNTRY

    try {
      const query = this.buildQuery({
        sysCategory,
        tokenCategory,
        tokenCountry,
        tokenKeyword,
      });

      const entities = await this.client.queryEntities(query);

      // Apply skip and limit to entities array
      let processedEntities = entities;

      // Apply skip: remove first x elements
      if (skip > 0) {
        processedEntities = entities.slice(skip);
      }

      // Apply limit: keep first x elements after skip
      if (limit !== null && limit > 0) {
        processedEntities = processedEntities.slice(0, limit);
      }

      // Process each entity
      for (const entity of processedEntities) {
        const result = await this.processEntityForMultiple(entity, sysCategory);
        if (result) {
          results[result.tokenId] = result.data;
        }
      }

      return {
        data: results,
        totalCount: entities.length,
      };
    } catch (error) {
      console.error("Error fetching all data:", error);
      return {
        data: {},
        totalCount: 0,
      };
    }
  }

  /**
   * Build query string for tokenIds
   * @param tokenIds - Array of tokenIds to query for
   * @param sysCategory - System category to filter by
   * @returns string - The constructed query
   */
  private buildQuery({
    tokenIds,
    sysCategory,
    tokenCategory,
    tokenCountry,
    tokenKeyword,
  }: {
    tokenIds?: string[];
    sysCategory: string;
    tokenCategory?: string;
    tokenCountry?: string;
    tokenKeyword?: string;
  }): string {
    let baseQuery = `_sys_version = 1 && (_sys_status = "both" || _sys_status = "prod") && _sys_file_type = "json"`;

    if (sysCategory) {
      baseQuery += ` && _sys_category = "${sysCategory}"`;
    }

    if (tokenIds) {
      if (tokenIds.length === 1) {
        baseQuery += ` && _sys_file_stem = "${tokenIds[0]}"`;
      } else {
        baseQuery += ` && (${tokenIds
          .map((tokenId) => `_sys_file_stem = "${tokenId}"`)
          .join(" || ")})`;
      }
    }

    // category filter
    if (tokenCategory) {
      baseQuery += ` && attr_category = "${tokenCategory}"`;
    }

    // country filter
    if (tokenCountry) {
      baseQuery += ` && attr_country_code = "${tokenCountry}"`;
    }

    // keyword filter
    if (tokenKeyword) {
      // Convert keyword to pattern: "*[<Ch1Capital><Ch1lower>][<Ch2Capital><Ch2lower>][<Ch3Capital><Ch3lower>]...*"
      const keywordPattern = tokenKeyword
        .split('')
        .map(char => {
          const upper = char.toUpperCase();
          const lower = char.toLowerCase();
          return `[${upper}${lower}]`;
        })
        .join('');
      baseQuery += ` && name ~ "*${keywordPattern}*"`;
    }

    return baseQuery;
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
      if (
        this.hasOwnerInEntityMetadata(
          entityMetadata,
          config.TARGET_OWNER as string
        )
      ) {
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
      if (
        this.hasOwnerInEntityMetadata(
          entityMetadata,
          config.TARGET_OWNER as string
        )
      ) {
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

console.log(
  await realityNFTService.getAllData({
    sysCategory: "REALITY_NFT_METADATA",
    tokenKeyword: "main",
    skip: 0,
    limit: 30,
  })
);
