import {
  QueryParams,
  AdvancedQueryParams,
  SystemCategory,
  EntityType,
} from "./types";
import {
  SYSTEM_ANNOTATION_KEYS,
  ATTRIBUTE_KEYS,
  QUERY_STATUS_VALUES,
  FILE_TYPE,
} from "./constants";

/**
 * Handles construction of query strings for entity fetching
 */
export class QueryBuilder {
  /**
   * Get the correct attribute key based on system category
   */
  private getAttributeKey(sysCategory: string, baseKey: string): string {
    const useAttrPrefix =
      sysCategory !== SystemCategory.REALITY_NFT_SPECIAL_VENUES;
    return useAttrPrefix ? `attr_${baseKey}` : baseKey;
  }

  /**
   * Convert keyword to pattern for case-insensitive matching
   */
  private createKeywordPattern(keyword: string): string {
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
   * Build query conditions for arrays with OR logic
   */
  private buildArrayCondition(key: string, values: string[]): string {
    if (values.length === 0) return "";
    if (values.length === 1) return ` && ${key} = "${values[0]}"`;
    return ` && (${values.map((value) => `${key} = "${value}"`).join(" || ")})`;
  }

  /**
   * Build base query string
   */
  buildQuery(params: QueryParams): string {
    const {
      tokenIds,
      sysCategory,
      tokenTypes,
      tokenCountry,
      tokenKeywords,
      tokenSettlement,
    } = params;

    let query = `${SYSTEM_ANNOTATION_KEYS.VERSION} >= 1 && (${SYSTEM_ANNOTATION_KEYS.STATUS} = "${QUERY_STATUS_VALUES.BOTH}" || ${SYSTEM_ANNOTATION_KEYS.STATUS} = "${QUERY_STATUS_VALUES.PROD}") && ${SYSTEM_ANNOTATION_KEYS.FILE_TYPE} = "${FILE_TYPE.JSON}"`;

    if (sysCategory) {
      query += ` && ${SYSTEM_ANNOTATION_KEYS.CATEGORY} = "${sysCategory}"`;
    }

    if (tokenIds && tokenIds.length > 0) {
      query += this.buildArrayCondition(
        SYSTEM_ANNOTATION_KEYS.FILE_STEM,
        tokenIds
      );
    }

    if (tokenTypes && tokenTypes.length > 0) {
      const typeKey = this.getAttributeKey(sysCategory, ATTRIBUTE_KEYS.TYPE);
      query += this.buildArrayCondition(typeKey, tokenTypes);
    }

    if (tokenCountry) {
      const countryKey = this.getAttributeKey(
        sysCategory,
        ATTRIBUTE_KEYS.COUNTRY_NAME
      );
      query += ` && ${countryKey} = "${tokenCountry}"`;
    }

    if (tokenKeywords && tokenKeywords.length > 0) {
      const keywordPatterns = tokenKeywords.map((keyword) =>
        this.createKeywordPattern(keyword)
      );
      const keywordConditions = keywordPatterns.map(
        (pattern) => `name ~ "*${pattern}*"`
      );
      const keywordQuery =
        keywordConditions.length === 1
          ? keywordConditions[0]
          : `(${keywordConditions.join(" || ")})`;
      query += ` && ${keywordQuery}`;
    }

    if (tokenSettlement) {
      const settlementKey = this.getAttributeKey(
        sysCategory,
        ATTRIBUTE_KEYS.SETTLEMENT
      );
      query += ` && ${settlementKey} = "${tokenSettlement}"`;
    }

    return query;
  }

  /**
   * Build advanced query with additional filters
   */
  buildAdvancedQuery(params: AdvancedQueryParams): string {
    const {
      sysCategory,
      tokenTypes,
      tokenKeywords,
      tokenCountry,
      tokenSettlement,
      excludeTokenIds,
    } = params;

    // Build base query, excluding country/settlement if both are provided (handled separately)
    const hasCountryAndSettlement = tokenCountry && tokenSettlement;
    let query = this.buildQuery({
      sysCategory,
      tokenTypes: hasCountryAndSettlement ? undefined : tokenTypes,
      tokenKeywords,
      tokenCountry: hasCountryAndSettlement ? undefined : tokenCountry,
      tokenSettlement: hasCountryAndSettlement ? undefined : tokenSettlement,
    });

    // Handle country and settlement with OR logic when both are provided
    if (hasCountryAndSettlement) {
      const typeKey = this.getAttributeKey(sysCategory, ATTRIBUTE_KEYS.TYPE);

      const countryKey = this.getAttributeKey(
        sysCategory,
        ATTRIBUTE_KEYS.COUNTRY_NAME
      );
      const settlementKey = this.getAttributeKey(
        sysCategory,
        ATTRIBUTE_KEYS.SETTLEMENT
      );
      query += ` && (( ${typeKey} = "${EntityType.COUNTRY}" && ${countryKey} = "${tokenCountry}") || (${typeKey} = "${EntityType.BUILDING}" && ${settlementKey} = "${tokenSettlement}"))`;
    }

    // Add exclusion conditions
    if (excludeTokenIds && excludeTokenIds.length > 0) {
      const exclusionConditions = excludeTokenIds.map(
        (tokenId) => `${SYSTEM_ANNOTATION_KEYS.FILE_STEM} != "${tokenId}"`
      );
      const exclusionQuery =
        exclusionConditions.length === 1
          ? exclusionConditions[0]
          : `(${exclusionConditions.join(" && ")})`;
      query += ` && ${exclusionQuery}`;
    }

    return query;
  }
}
