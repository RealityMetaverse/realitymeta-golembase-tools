import { createClient, AccountData, Tagged, Hex } from "golem-base-sdk";

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
   * Initialize the Arkiv client
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
        throw new Error("Missing required Arkiv configuration");
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
   * @param tokenKeywords - Array of keywords to search for in the name field
   * @param tokenSettlement - Optional settlement filter
   * @param advancedSearch - Enable advanced search with recursive calls (default: false)
   * @returns Promise<{ data: Record<string, any>; totalCount: number }> - Dictionary mapping tokenId to data
   */
  async getAllData({
    sysCategory = "REALITY_NFT_METADATA",
    tokenCategory,
    tokenCountry,
    tokenKeywords,
    tokenSettlement,
    advancedSearch = false,
    skip = 0,
    limit = null,
  }: {
    sysCategory: string;
    tokenCategory?: string;
    tokenCountry?: string;
    tokenKeywords?: string[];
    tokenSettlement?: string;
    advancedSearch?: boolean;
    skip: number;
    limit: number | null;
  }): Promise<{ data: Record<string, any>; totalCount: number }> {
    await this.initialize();
    const results: Record<string, any> = {};

    try {
      // If advanced search is enabled, get the first element and determine search strategy
      if (advancedSearch) {
        const initialQuery = this.buildQuery({
          sysCategory,
          tokenCategory,
          tokenCountry,
          tokenKeywords,
          tokenSettlement,
        });

        const initialEntities = await this.client.queryEntities(initialQuery);

        if (initialEntities.length === 0) {
          return {
            data: {},
            totalCount: 0,
          };
        }

        // Get metadata for the first entity to determine attr_type
        const firstEntity = initialEntities[0];
        const firstEntityMetadata = await this.client.getEntityMetaData(
          firstEntity.entityKey
        );

        // Determine attribute prefix based on category
        const useAttrPrefix = sysCategory !== "REALITY_NFT_SPECIAL_VENUES";
        const typeKey = useAttrPrefix ? "attr_type" : "type";
        const settlementKey = useAttrPrefix ? "attr_settlement" : "settlement";
        const countryNameKey = useAttrPrefix
          ? "attr_country_name"
          : "country_name";

        // Extract token ID from first entity for exclusion
        let firstEntityTokenId: string | null = null;
        let attrType: string | null = null;
        let attrSettlement: string | undefined = undefined;
        let attrCountryName: string | undefined = undefined;

        for (const annotation of firstEntityMetadata.stringAnnotations) {
          if (annotation.key === "_sys_file_stem") {
            firstEntityTokenId = annotation.value;
          } else if (annotation.key === typeKey) {
            attrType = annotation.value;
          } else if (annotation.key === settlementKey) {
            attrSettlement = annotation.value;
          } else if (annotation.key === countryNameKey) {
            attrCountryName = annotation.value;
          }
        }

        // Create a single query to get all relevant data based on attrType
        let advancedQuery: string | null = null;

        if (attrType === "building") {
          // For building: use attrSettlement and attrCountryName as tokenKeywords
          const buildingKeywords = [attrSettlement, attrCountryName].filter(
            Boolean
          ) as string[];
          advancedQuery = this.advancedQueryBuilder({
            sysCategory,
            tokenKeywords: buildingKeywords,
            excludeTokenIds: firstEntityTokenId ? [firstEntityTokenId] : [],
          });
        } else if (attrType === "country") {
          // For country: use attrCountryName as is
          advancedQuery = this.advancedQueryBuilder({
            sysCategory,
            tokenKeywords,
            tokenCountry: attrCountryName,
            excludeTokenIds: firstEntityTokenId ? [firstEntityTokenId] : [],
          });
        } else if (attrType === "city") {
          // For city: use attrSettlement as OR condition, attrCountryName as tokenKeywords
          const cityKeywords = attrCountryName ? [attrCountryName] : [];
          advancedQuery = this.advancedQueryBuilder({
            sysCategory,
            tokenKeywords: cityKeywords,
            tokenSettlement: attrSettlement,
            excludeTokenIds: firstEntityTokenId ? [firstEntityTokenId] : [],
          });
        }

        let allEntities: {
          entityKey: Hex;
          storageValue: Uint8Array;
        }[] = [];

        if (advancedQuery) {
          allEntities = await this.client.queryEntities(advancedQuery);
        }

        // Process all entities and categorize them by attr_type
        const categorizedResults: { [key: string]: any } = {};
        const buildingResults: { [key: string]: any } = {};
        const cityResults: { [key: string]: any } = {};
        const countryResults: { [key: string]: any } = {};

        for (const entity of allEntities) {
          const result = await this.processEntityForMultiple(
            entity,
            sysCategory
          );
          if (result) {
            categorizedResults[result.tokenId] = result.data;

            // Get attr_type from the processed data to categorize
            let entityAttrType: string | undefined = undefined;
            if (sysCategory === "REALITY_NFT_SPECIAL_VENUES") {
              entityAttrType = result.data.type;
            } else {
              entityAttrType = result.data.attributes.find(
                (attribute: { trait_type: string; value: string }) =>
                  attribute.trait_type === "type"
              )?.value;
            }

            if (entityAttrType === "building") {
              buildingResults[result.tokenId] = result.data;
            } else if (entityAttrType === "city") {
              cityResults[result.tokenId] = result.data;
            } else if (entityAttrType === "country") {
              countryResults[result.tokenId] = result.data;
            }
          }
        }

        // Order results based on attr_type
        let orderedResults: { [key: string]: any } = {};

        const firstEntityData = await this.processEntityForMultiple(
          firstEntity,
          sysCategory
        );
        if (attrType === "building") {
          if (firstEntityTokenId && firstEntityData) {
            orderedResults[firstEntityTokenId] = firstEntityData.data;
          }

          // building -> city -> country order
          orderedResults = {
            ...orderedResults,
            ...buildingResults,
            ...cityResults,
            ...countryResults,
          };
        } else if (attrType === "country") {
          if (firstEntityTokenId && firstEntityData) {
            orderedResults[firstEntityTokenId] = firstEntityData.data;
          }

          // country -> city -> building order
          orderedResults = {
            ...orderedResults,
            ...countryResults,
            ...cityResults,
            ...buildingResults,
          };
        } else if (attrType === "city") {
          if (firstEntityTokenId && firstEntityData) {
            orderedResults[firstEntityTokenId] = firstEntityData.data;
          }

          // city -> building -> country order
          orderedResults = {
            ...orderedResults,
            ...cityResults,
            ...buildingResults,
            ...countryResults,
          };
        } else {
          // If attrType doesn't match any expected values, return empty results
          console.warn(
            `Unknown attr_type: "${attrType}". Returning empty results.`
          );
          return {
            data: {},
            totalCount: 0,
          };
        }

        // Apply skip and limit to the ordered results
        const resultKeys = Object.keys(orderedResults);
        let processedKeys = resultKeys;

        if (skip > 0) {
          processedKeys = resultKeys.slice(skip);
        }

        if (limit !== null && limit > 0) {
          processedKeys = processedKeys.slice(0, limit);
        }

        const finalResults: Record<string, any> = {};
        for (const key of processedKeys) {
          finalResults[key] = orderedResults[key];
        }

        return {
          data: finalResults,
          totalCount: resultKeys.length,
        };
      }

      // Regular search (non-advanced)
      const query = this.buildQuery({
        sysCategory,
        tokenCategory,
        tokenCountry,
        tokenKeywords,
        tokenSettlement,
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
   * @param tokenSettlement - Settlement filter
   * @returns string - The constructed query
   */
  private buildQuery({
    tokenIds,
    sysCategory,
    tokenCategory,
    tokenCountry,
    tokenKeywords,
    tokenSettlement,
  }: {
    tokenIds?: string[];
    sysCategory: string;
    tokenCategory?: string;
    tokenCountry?: string;
    tokenKeywords?: string[];
    tokenSettlement?: string;
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
      const categoryKey =
        sysCategory === "REALITY_NFT_SPECIAL_VENUES"
          ? "category"
          : "attr_category";
      baseQuery += ` && ${categoryKey} = "${tokenCategory}"`;
    }

    // country filter
    if (tokenCountry) {
      const countryKey =
        sysCategory === "REALITY_NFT_SPECIAL_VENUES"
          ? "country_code"
          : "attr_country_code";
      baseQuery += ` && ${countryKey} = "${tokenCountry}"`;
    }

    // keyword filter
    if (tokenKeywords && tokenKeywords.length > 0) {
      const keywordPatterns = tokenKeywords.map((keyword) =>
        this.createKeywordPattern(keyword)
      );
      if (keywordPatterns.length === 1) {
        baseQuery += ` && name ~ "*${keywordPatterns[0]}*"`;
      } else {
        const orConditions = keywordPatterns.map(
          (pattern) => `name ~ "*${pattern}*"`
        );
        baseQuery += ` && (${orConditions.join(" || ")})`;
      }
    }

    // settlement filter
    if (tokenSettlement) {
      const settlementKey =
        sysCategory === "REALITY_NFT_SPECIAL_VENUES"
          ? "settlement"
          : "attr_settlement";
      baseQuery += ` && ${settlementKey} = "${tokenSettlement}"`;
    }

    return baseQuery;
  }

  /**
   * Build advanced query string for advanced search scenarios
   * @param sysCategory - System category to filter by
   * @param tokenKeywords - Array of keywords to search for
   * @param tokenCountry - Country filter
   * @param tokenSettlement - Settlement filter (will be added as OR condition)
   * @param excludeTokenIds - Array of token IDs to exclude from results
   * @returns string - The constructed advanced query
   */
  private advancedQueryBuilder({
    sysCategory,
    tokenKeywords,
    tokenCountry,
    tokenSettlement,
    excludeTokenIds,
  }: {
    sysCategory: string;
    tokenKeywords?: string[];
    tokenCountry?: string;
    tokenSettlement?: string;
    excludeTokenIds?: string[];
  }): string {
    // Build base query with sysCategory, tokenKeywords, and tokenCountry
    let baseQuery = this.buildQuery({
      sysCategory,
      tokenKeywords,
      tokenCountry,
    });

    // Add settlement as OR condition if provided
    if (tokenSettlement) {
      const settlementKey =
        sysCategory === "REALITY_NFT_SPECIAL_VENUES"
          ? "settlement"
          : "attr_settlement";
      baseQuery += ` || ${settlementKey} = "${tokenSettlement}"`;
    }

    // Add exclusion conditions for token IDs if provided
    if (excludeTokenIds && excludeTokenIds.length > 0) {
      const exclusionConditions = excludeTokenIds.map(
        (tokenId) => `_sys_file_stem != "${tokenId}"`
      );
      if (exclusionConditions.length === 1) {
        baseQuery += ` && ${exclusionConditions[0]}`;
      } else {
        baseQuery += ` && (${exclusionConditions.join(" && ")})`;
      }
    }

    return baseQuery;
  }

  /**
   * Convert keyword to pattern for case-insensitive matching
   * @param keyword - The keyword to convert
   * @returns string - The pattern for case-insensitive matching
   */
  private createKeywordPattern(keyword: string): string {
    // Convert keyword to pattern: "*[<Ch1Capital><Ch1lower>][<Ch2Capital><Ch2lower>][<Ch3Capital><Ch3lower>]...*"
    return keyword
      .split("")
      .map((char) => {
        const upper = char.toUpperCase();
        const lower = char.toLowerCase();
        return `[${upper}${lower}]`;
      })
      .join("");
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
    tokenKeywords: ["main"],
    skip: 0,
    limit: 30,
  })
);

// Advanced search usage - automatically determines search strategy based on first result's attr_type
realityNFTService
  .getAllData({
    sysCategory: "REALITY_NFT_SPECIAL_VENUES",
    tokenKeywords: ["eif"],
    advancedSearch: true,
    skip: 0,
    limit: 30,
  })
  .then((result) => console.log(result));
