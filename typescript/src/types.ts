import { Hex } from "golem-base-sdk";

// ============================================================================
// Enums
// ============================================================================

/**
 * System categories for Reality NFT entities
 */
export enum SystemCategory {
  REALITY_NFT_METADATA = "REALITY_NFT_METADATA",
  REALITY_NFT_SPECIAL_VENUES = "REALITY_NFT_SPECIAL_VENUES",
}

/**
 * Entity types for Reality NFTs
 */
export enum EntityType {
  BUILDING = "building",
  CITY = "city",
  COUNTRY = "country",
}

// ============================================================================
// Interfaces
// ============================================================================

/**
 * Configuration interface with validation
 */
export interface RealityNFTConfig {
  readonly chainId: string;
  readonly rpcUrl: string;
  readonly wsUrl: string;
  readonly targetOwner: string;
  readonly privateKey: string;
}

/**
 * Entity metadata structure from the Arkiv network
 */
export interface EntityMetadata {
  owner?: string;
  stringAnnotations: Array<{
    key: string;
    value: string;
  }>;
}

/**
 * Entity structure from query results
 */
export interface Entity {
  entityKey: Hex;
  storageValue: Uint8Array;
}

/**
 * Processed entity result
 */
export interface ProcessedEntity {
  tokenId: string;
  data: unknown;
}

/**
 * Query parameters for fetching entities
 */
export interface QueryParams {
  tokenIds?: string[];
  sysCategory: string;
  tokenTypes?: string[];
  tokenCountry?: string;
  tokenKeywords?: string[];
  tokenSettlement?: string;
}

/**
 * Advanced query parameters
 */
export interface AdvancedQueryParams extends Omit<QueryParams, "tokenIds"> {
  excludeTokenIds?: string[];
}

/**
 * Result structure for getAllData
 */
export interface GetAllDataResult {
  data: Record<string, unknown>;
  totalCount: number;
  referenceId?: string; // The tokenId used as reference in advanced search
}

/**
 * Cache statistics
 */
export interface CacheStats {
  size: number;
  keys: string[];
  categories: Record<string, number>;
  categoryBreakdown: Record<string, string[]>;
}

/**
 * Entity information during processing
 */
export interface EntityInfo {
  entity: Entity;
  metadata: EntityMetadata;
  tokenId: string | null;
  attrType: string | null;
  attrSettlement: string | undefined;
  attrCountryName: string | undefined;
}
