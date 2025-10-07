import { gunzipSync } from "zlib";
import { SystemCategory } from "./types";
import { COMPRESSION_METHODS, ATTRIBUTE_KEYS } from "./constants";
import { DataProcessingError } from "./errors";

/**
 * Handles entity data processing and transformation
 */
export class DataProcessor {
  /**
   * Extract specific annotations from entity metadata
   */
  extractAnnotations(
    annotations: Array<{ key: string; value: string }>,
    keys: string[]
  ): Record<string, string> {
    const result: Record<string, string> = {};
    for (const annotation of annotations) {
      if (keys.includes(annotation.key)) {
        result[annotation.key] = annotation.value;
      }
    }
    return result;
  }

  /**
   * Decode and decompress data from base64 string
   */
  decodeAndDecompressData(
    base64Data: string,
    compressionMethod: string | null
  ): unknown {
    try {
      const compressedBytes = Uint8Array.from(atob(base64Data), (c) =>
        c.charCodeAt(0)
      );

      let bytes = compressedBytes;
      if (compressionMethod?.toLowerCase() === COMPRESSION_METHODS.GZIP) {
        const gunzipped = gunzipSync(Buffer.from(compressedBytes));
        bytes = new Uint8Array(gunzipped);
      }

      const decodedString = new TextDecoder("utf-8").decode(bytes);
      return JSON.parse(decodedString);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      throw new DataProcessingError(
        `Failed to decode/decompress data: ${message}`
      );
    }
  }

  /**
   * Extract the type attribute from processed entity data
   */
  extractTypeFromData(data: any, sysCategory: string): string | undefined {
    if (sysCategory === SystemCategory.REALITY_NFT_SPECIAL_VENUES) {
      return data.type;
    }

    return data.attributes?.find(
      (attribute: { trait_type: string; value: string }) =>
        attribute.trait_type === ATTRIBUTE_KEYS.TYPE
    )?.value;
  }
}
