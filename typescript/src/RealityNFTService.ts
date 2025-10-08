import { createClient } from "golem-base-sdk";
import {
  RealityNFTConfig,
  Entity,
  EntityMetadata,
  ProcessedEntity,
  GetAllDataResult,
  CacheStats,
  EntityInfo,
  EntityType,
  SystemCategory,
} from "./types";
import { DEFAULT_CONFIG } from "./config";
import { InitializationError, ConfigurationError } from "./errors";
import {
  validateConfig,
  createAccountDataFromConfig,
  normalizeAddress,
} from "./utils";
import { QueryBuilder } from "./QueryBuilder";
import { DataProcessor } from "./DataProcessor";
import {
  SYSTEM_ANNOTATION_KEYS,
  ATTRIBUTE_KEYS,
  ENTITY_TYPE_PRIORITY,
} from "./constants";

/**
 * Service for interacting with Reality NFT data from Arkiv network
 */
export class RealityNFTService {
  private client: any = null;
  private readonly cache = new Map<string, unknown>();
  private isInitialized = false;
  private isServiceAvailable = false;
  private readonly config: RealityNFTConfig;
  private readonly queryBuilder = new QueryBuilder();
  private readonly dataProcessor = new DataProcessor();

  constructor(config: RealityNFTConfig = DEFAULT_CONFIG) {
    this.config = config;
  }

  /**
   * Generate a composite cache key from category and tokenId
   */
  private getCacheKey(category: string, tokenId: string): string {
    return `${category}:${tokenId}`;
  }

  /**
   * Get the correct attribute key based on system category
   */
  private getAttributeKey(sysCategory: string, baseKey: string): string {
    const useAttrPrefix =
      sysCategory !== SystemCategory.REALITY_NFT_SPECIAL_VENUES;
    return useAttrPrefix ? `attr_${baseKey}` : baseKey;
  }

  /**
   * Initialize the Arkiv client
   */
  private async initialize(): Promise<void> {
    if (this.isInitialized) return;

    try {
      validateConfig(this.config);

      const accountData = createAccountDataFromConfig(this.config.privateKey);
      const chainId = parseInt(this.config.chainId, 10);

      if (isNaN(chainId)) {
        throw new ConfigurationError(
          `Invalid chain ID: ${this.config.chainId}`
        );
      }

      this.client = await createClient(
        chainId,
        accountData,
        this.config.rpcUrl,
        this.config.wsUrl
      );

      this.isInitialized = true;
      this.isServiceAvailable = true;

      console.log("✅ RealityNFTService initialized");
      console.log(`   Chain ID: ${this.config.chainId}`);
      console.log(`   RPC URL: ${this.config.rpcUrl}`);
      console.log(`   Target Owner: ${this.config.targetOwner}`);
    } catch (error) {
      this.isServiceAvailable = false;
      this.isInitialized = true; // Prevent retry loops

      const message = error instanceof Error ? error.message : "Unknown error";
      console.error("❌ Failed to initialize RealityNFTService:", message);

      throw new InitializationError(
        `Service initialization failed: ${message}`
      );
    }
  }

  /**
   * Check if the service is available and configured properly
   */
  async isAvailable(): Promise<boolean> {
    if (!this.isInitialized) {
      try {
        await this.initialize();
      } catch {
        return false;
      }
    }
    return this.isServiceAvailable;
  }

  /**
   * Get metadata for a single tokenId
   */
  async getData(
    tokenId: string,
    sysCategory: string = SystemCategory.REALITY_NFT_METADATA
  ): Promise<unknown | null> {
    const cacheKey = this.getCacheKey(sysCategory, tokenId);
    const cachedData = this.cache.get(cacheKey);

    if (cachedData !== undefined) {
      return cachedData;
    }

    await this.initialize();

    try {
      const query = this.queryBuilder.buildQuery({
        tokenIds: [tokenId],
        sysCategory,
      });

      const entities: Entity[] = await this.client.queryEntities(query);

      if (entities.length === 0) {
        return null;
      }

      const results = await Promise.all(
        entities.map((entity) =>
          this.processEntity(entity, tokenId, sysCategory)
        )
      );

      return results.find((result) => result !== null) ?? null;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      console.error(`Failed to get data for tokenId ${tokenId}:`, message);
      return null;
    }
  }

  /**
   * Get metadata for multiple tokenIds
   */
  async getMultipleData(
    tokenIds: string[],
    sysCategory: string = SystemCategory.REALITY_NFT_METADATA
  ): Promise<Record<string, unknown>> {
    if (tokenIds.length === 0) {
      return {};
    }

    await this.initialize();

    const results: Record<string, unknown> = {};
    const uncachedTokenIds: string[] = [];

    // Retrieve cached data
    for (const tokenId of tokenIds) {
      const cacheKey = this.getCacheKey(sysCategory, tokenId);
      const cachedData = this.cache.get(cacheKey);

      if (cachedData !== undefined) {
        results[tokenId] = cachedData;
      } else {
        uncachedTokenIds.push(tokenId);
      }
    }

    if (uncachedTokenIds.length === 0) {
      return results;
    }

    try {
      const query = this.queryBuilder.buildQuery({
        tokenIds: uncachedTokenIds,
        sysCategory,
      });

      const entities: Entity[] = await this.client.queryEntities(query);

      const entityResults = await Promise.all(
        entities.map((entity) =>
          this.processEntityForMultiple(entity, sysCategory)
        )
      );

      for (const result of entityResults) {
        if (result) {
          results[result.tokenId] = result.data;
        }
      }

      return results;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      console.error("Failed to get multiple data:", message);
      return results; // Return partial results
    }
  }

  /**
   * Get all data for a specific category with optional filtering
   */
  async getAllData(options: {
    sysCategory?: string;
    tokenTypes?: string[];
    tokenCategories?: string[];
    tokenCountry?: string;
    tokenKeywords?: string[];
    tokenSettlement?: string;
    advancedSearch?: boolean;
    skip?: number;
    limit?: number | null;
  }): Promise<GetAllDataResult> {
    const {
      sysCategory = SystemCategory.REALITY_NFT_METADATA,
      tokenTypes,
      tokenCategories,
      tokenCountry,
      tokenKeywords,
      tokenSettlement,
      advancedSearch = false,
      skip = 0,
      limit = null,
    } = options;
    await this.initialize();

    try {
      if (advancedSearch) {
        return await this.performAdvancedSearch({
          sysCategory,
          tokenTypes,
          tokenCategories,
          tokenCountry,
          tokenKeywords,
          tokenSettlement,
          skip,
          limit,
        });
      }

      return await this.performStandardSearch({
        sysCategory,
        tokenTypes,
        tokenCategories,
        tokenCountry,
        tokenKeywords,
        tokenSettlement,
        skip,
        limit,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      console.error("Error fetching all data:", message);
      return {
        data: {},
        totalCount: 0,
      };
    }
  }

  /**
   * Perform standard search without advanced features
   */
  private async performStandardSearch(params: {
    sysCategory: string;
    tokenTypes?: string[];
    tokenCategories?: string[];
    tokenCountry?: string;
    tokenKeywords?: string[];
    tokenSettlement?: string;
    skip: number;
    limit: number | null;
  }): Promise<GetAllDataResult> {
    const {
      sysCategory,
      tokenTypes,
      tokenCategories,
      tokenCountry,
      tokenKeywords,
      tokenSettlement,
      skip,
      limit,
    } = params;

    const query = this.queryBuilder.buildQuery({
      sysCategory,
      tokenTypes,
      tokenCategories,
      tokenCountry,
      tokenKeywords,
      tokenSettlement,
    });

    const entities: Entity[] = await this.client.queryEntities(query);
    const processedEntities = this.applySkipAndLimit(entities, skip, limit);

    const entityResults = await Promise.all(
      processedEntities.map((entity) =>
        this.processEntityForMultiple(entity, sysCategory)
      )
    );

    const results: Record<string, unknown> = {};
    for (const result of entityResults) {
      if (result) {
        results[result.tokenId] = result.data;
      }
    }

    return {
      data: results,
      totalCount: entities.length,
    };
  }

  /**
   * Perform advanced search with entity type prioritization
   */
  private async performAdvancedSearch(params: {
    sysCategory: string;
    tokenTypes?: string[];
    tokenCategories?: string[];
    tokenCountry?: string;
    tokenKeywords?: string[];
    tokenSettlement?: string;
    skip: number;
    limit: number | null;
  }): Promise<GetAllDataResult> {
    const {
      sysCategory,
      tokenTypes,
      tokenCategories,
      tokenCountry,
      tokenKeywords,
      tokenSettlement,
      skip,
      limit,
    } = params;

    const initialQuery = this.queryBuilder.buildQuery({
      sysCategory,
      tokenTypes,
      tokenCategories,
      tokenCountry,
      tokenKeywords,
      tokenSettlement,
    });

    const initialEntities: Entity[] = await this.client.queryEntities(
      initialQuery
    );

    if (initialEntities.length === 0) {
      return { data: {}, totalCount: 0 };
    }

    const entityInfoList = await this.extractEntityInformation(
      initialEntities,
      sysCategory
    );
    const firstEntityInfo = this.selectPriorityEntity(entityInfoList);

    if (!firstEntityInfo) {
      return { data: {}, totalCount: 0 };
    }

    const allEntities = await this.fetchRelatedEntities(
      firstEntityInfo,
      sysCategory
    );
    const categorizedResults = await this.categorizeEntitiesByType(
      allEntities,
      sysCategory
    );

    const firstEntityData = await this.processEntityForMultiple(
      firstEntityInfo.entity,
      sysCategory
    );

    const { keys: orderedKeys, data: allData } = this.orderResultsByType(
      firstEntityData,
      firstEntityInfo.tokenId,
      firstEntityInfo.attrType,
      categorizedResults
    );

    if (orderedKeys.length === 0) {
      return { data: {}, totalCount: 0 };
    }

    const processedKeys = this.applySkipAndLimit(orderedKeys, skip, limit);

    const finalResults: Record<string, unknown> = {};
    for (const key of processedKeys) {
      finalResults[key] = allData[key];
    }

    return {
      data: finalResults,
      totalCount: orderedKeys.length,
      referenceId: firstEntityInfo.tokenId ?? undefined,
      referenceType: firstEntityInfo.attrType as EntityType | undefined,
    };
  }

  /**
   * Extract entity information from entities
   */
  private async extractEntityInformation(
    entities: Entity[],
    sysCategory: string
  ): Promise<EntityInfo[]> {
    const allMetadata = await Promise.all(
      entities.map((entity) => this.client.getEntityMetaData(entity.entityKey))
    );

    const typeKey = this.getAttributeKey(sysCategory, ATTRIBUTE_KEYS.TYPE);
    const settlementKey = this.getAttributeKey(
      sysCategory,
      ATTRIBUTE_KEYS.SETTLEMENT
    );
    const countryNameKey = this.getAttributeKey(
      sysCategory,
      ATTRIBUTE_KEYS.COUNTRY_NAME
    );

    return entities.map((entity, index) => {
      const metadata = allMetadata[index];
      const info: EntityInfo = {
        entity,
        metadata,
        tokenId: null,
        attrType: null,
        attrSettlement: undefined,
        attrCountryName: undefined,
      };

      for (const annotation of metadata.stringAnnotations) {
        switch (annotation.key) {
          case SYSTEM_ANNOTATION_KEYS.FILE_STEM:
            info.tokenId = annotation.value;
            break;
          case typeKey:
            info.attrType = annotation.value;
            break;
          case settlementKey:
            info.attrSettlement = annotation.value;
            break;
          case countryNameKey:
            info.attrCountryName = annotation.value;
            break;
        }
      }

      return info;
    });
  }

  /**
   * Select entity with highest priority based on type
   */
  private selectPriorityEntity(
    entityInfoList: EntityInfo[]
  ): EntityInfo | null {
    for (const entityType of ENTITY_TYPE_PRIORITY) {
      const found = entityInfoList.find((info) => info.attrType === entityType);
      if (found) return found;
    }

    return entityInfoList.length > 0 ? entityInfoList[0] : null;
  }

  /**
   * Fetch related entities based on first entity attributes
   */
  private async fetchRelatedEntities(
    firstEntityInfo: EntityInfo,
    sysCategory: string
  ): Promise<Entity[]> {
    const { attrType, attrSettlement, attrCountryName } = firstEntityInfo;

    let advancedQuery: string | null = null;

    switch (attrType) {
      case EntityType.BUILDING: {
        const keywords = [attrSettlement, attrCountryName].filter(
          Boolean
        ) as string[];
        advancedQuery = this.queryBuilder.buildAdvancedQuery({
          sysCategory,
          tokenTypes: [EntityType.CITY, EntityType.COUNTRY],
          tokenKeywords: keywords,
        });
        break;
      }
      case EntityType.COUNTRY:
        advancedQuery = this.queryBuilder.buildAdvancedQuery({
          sysCategory,
          tokenTypes: [EntityType.CITY, EntityType.BUILDING],
          tokenCountry: attrCountryName,
        });
        break;
      case EntityType.CITY:
        advancedQuery = this.queryBuilder.buildAdvancedQuery({
          sysCategory,
          tokenTypes: [EntityType.BUILDING, EntityType.COUNTRY],
          tokenSettlement: attrSettlement,
          tokenCountry: attrCountryName,
        });
        break;
    }

    return advancedQuery ? await this.client.queryEntities(advancedQuery) : [];
  }

  /**
   * Categorize entities by type
   */
  private async categorizeEntitiesByType(
    entities: Entity[],
    sysCategory: string
  ): Promise<Record<EntityType, Record<string, unknown>>> {
    const categorized: Record<EntityType, Record<string, unknown>> = {
      [EntityType.BUILDING]: {},
      [EntityType.CITY]: {},
      [EntityType.COUNTRY]: {},
    };

    const entityResults = await Promise.all(
      entities.map((entity) =>
        this.processEntityForMultiple(entity, sysCategory)
      )
    );

    for (const result of entityResults) {
      if (result) {
        const entityAttrType = this.dataProcessor.extractTypeFromData(
          result.data,
          sysCategory
        ) as EntityType | undefined;

        if (entityAttrType && categorized[entityAttrType]) {
          categorized[entityAttrType][result.tokenId] = result.data;
        }
      }
    }

    return categorized;
  }

  /**
   * Order results based on attribute type priority
   */
  private orderResultsByType(
    firstEntityData: ProcessedEntity | null,
    firstEntityTokenId: string | null,
    attrType: string | null,
    categorizedResults: Record<EntityType, Record<string, unknown>>
  ): { keys: string[]; data: Record<string, unknown> } {
    const orderedKeys: string[] = [];
    const allData: Record<string, unknown> = {};

    if (firstEntityTokenId && firstEntityData) {
      orderedKeys.push(firstEntityTokenId);
      allData[firstEntityTokenId] = firstEntityData.data;
    }

    const orderMap: Record<string, EntityType[]> = {
      [EntityType.BUILDING]: [
        EntityType.BUILDING,
        EntityType.CITY,
        EntityType.COUNTRY,
      ],
      [EntityType.COUNTRY]: [
        EntityType.COUNTRY,
        EntityType.CITY,
        EntityType.BUILDING,
      ],
      [EntityType.CITY]: [
        EntityType.CITY,
        EntityType.BUILDING,
        EntityType.COUNTRY,
      ],
    };

    const order = attrType ? orderMap[attrType] : null;

    if (order) {
      for (const type of order) {
        const typeData = categorizedResults[type];
        for (const key of Object.keys(typeData)) {
          if (!orderedKeys.includes(key)) {
            orderedKeys.push(key);
            allData[key] = typeData[key];
          }
        }
      }
    } else {
      console.warn(
        `Unknown attr_type: "${attrType}". Returning empty results.`
      );
    }

    return { keys: orderedKeys, data: allData };
  }

  /**
   * Apply skip and limit to an array
   * @param requiredItem Optional item that must be included in results
   */
  private applySkipAndLimit<T>(
    items: T[],
    skip: number,
    limit: number | null,
    requiredItem?: T
  ): T[] {
    const startIndex = Math.max(0, skip);
    const endIndex =
      limit !== null && limit > 0 ? startIndex + limit : undefined;
    const result = items.slice(startIndex, endIndex);

    if (requiredItem && !result.includes(requiredItem)) {
      if (limit && result.length >= limit) result.pop();
      result.push(requiredItem);
    }

    return result;
  }

  /**
   * Process a single entity for getData method
   */
  private async processEntity(
    entity: Entity,
    expectedTokenId: string,
    sysCategory: string
  ): Promise<unknown | null> {
    try {
      const entityMetadata = await this.client.getEntityMetaData(
        entity.entityKey
      );

      if (!this.isOwnedByTargetOwner(entityMetadata)) {
        return null;
      }

      const annotations = this.dataProcessor.extractAnnotations(
        entityMetadata.stringAnnotations,
        [SYSTEM_ANNOTATION_KEYS.DATA, SYSTEM_ANNOTATION_KEYS.COMPRESSION_METHOD]
      );

      if (!annotations[SYSTEM_ANNOTATION_KEYS.DATA]) {
        return null;
      }

      const data = this.dataProcessor.decodeAndDecompressData(
        annotations[SYSTEM_ANNOTATION_KEYS.DATA],
        annotations[SYSTEM_ANNOTATION_KEYS.COMPRESSION_METHOD] || null
      );

      const cacheKey = this.getCacheKey(sysCategory, expectedTokenId);
      this.cache.set(cacheKey, data);

      return data;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      console.warn(`Failed to process entity: ${message}`);
      return null;
    }
  }

  /**
   * Process a single entity for getMultipleData method
   */
  private async processEntityForMultiple(
    entity: Entity,
    sysCategory: string
  ): Promise<ProcessedEntity | null> {
    try {
      const entityMetadata = await this.client.getEntityMetaData(
        entity.entityKey
      );

      if (!this.isOwnedByTargetOwner(entityMetadata)) {
        return null;
      }

      const annotations = this.dataProcessor.extractAnnotations(
        entityMetadata.stringAnnotations,
        [
          SYSTEM_ANNOTATION_KEYS.FILE_STEM,
          SYSTEM_ANNOTATION_KEYS.DATA,
          SYSTEM_ANNOTATION_KEYS.COMPRESSION_METHOD,
        ]
      );

      const tokenId = annotations[SYSTEM_ANNOTATION_KEYS.FILE_STEM];
      const dataValue = annotations[SYSTEM_ANNOTATION_KEYS.DATA];

      if (!tokenId || !dataValue) {
        return null;
      }

      const data = this.dataProcessor.decodeAndDecompressData(
        dataValue,
        annotations[SYSTEM_ANNOTATION_KEYS.COMPRESSION_METHOD] || null
      );

      const cacheKey = this.getCacheKey(sysCategory, tokenId);
      this.cache.set(cacheKey, data);

      return { tokenId, data };
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      console.warn(`Failed to process entity: ${message}`);
      return null;
    }
  }

  /**
   * Check if the entity is owned by the target owner
   */
  private isOwnedByTargetOwner(entityMetadata: EntityMetadata): boolean {
    if (!entityMetadata.owner) {
      return false;
    }

    return (
      normalizeAddress(entityMetadata.owner) ===
      normalizeAddress(this.config.targetOwner)
    );
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
   */
  clearCacheForCategory(sysCategory: string): number {
    const prefix = `${sysCategory}:`;
    const keysToDelete = Array.from(this.cache.keys()).filter((key) =>
      key.startsWith(prefix)
    );

    keysToDelete.forEach((key) => this.cache.delete(key));

    console.log(
      `🗑️ Cleared ${keysToDelete.length} entries for category: ${sysCategory}`
    );
    return keysToDelete.length;
  }

  /**
   * Get cache statistics
   */
  getCacheStats(): CacheStats {
    const keys = Array.from(this.cache.keys());
    const categories: Record<string, number> = {};
    const categoryBreakdown: Record<string, string[]> = {};

    for (const key of keys) {
      const [category, tokenId] = key.split(":", 2);
      if (category && tokenId) {
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
   */
  removeFromCache(
    tokenId: string,
    sysCategory: string = SystemCategory.REALITY_NFT_METADATA
  ): boolean {
    const cacheKey = this.getCacheKey(sysCategory, tokenId);
    const deleted = this.cache.delete(cacheKey);

    if (deleted) {
      console.log(`🗑️ Removed ${tokenId} from cache`);
    }

    return deleted;
  }
}
