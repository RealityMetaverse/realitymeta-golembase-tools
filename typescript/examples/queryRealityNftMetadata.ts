import { createClient, AccountData, Tagged } from "golem-base-sdk";
import arg from "arg";

const key: AccountData = new Tagged(
  "privatekey",
  Buffer.from(
    "a6a832651d60dd60e0706329387d74cf243d7d18f15d5e25ff9f5d00dfa006ff",
    "hex"
  )
);
const chainId = 60138453032;
const rpcUrl = "https://reality-games.holesky.golemdb.io/rpc";
const wsUrl = "wss://reality-games.holesky.golemdb.io/rpc/ws";

const decoder = new TextDecoder();

// Interface for complex query conditions
interface QueryCondition {
  field: string;
  operator: "=" | "!=" | ">" | "<" | ">=" | "<=";
  value: string | number;
}

// Interface for logical query groups
interface QueryGroup {
  conditions: QueryCondition[];
  operator: "&&" | "||";
}

// Interface for the query result dictionary
interface RealityNFTMetadataResult {
  entityKey: string;
  fileStems: string[];
  fileType: string;
  category: string;
  version: number;
  metadata: any;
  error?: string;
}

// Interface for the aggregated results
interface QueryResults {
  success: RealityNFTMetadataResult[];
  errors: RealityNFTMetadataResult[];
  totalFound: number;
  totalErrors: number;
  entities: Record<string, Record<string, unknown>>;
}

let results: QueryResults | null = null;

/**
 * Query REALITY_NFT_METADATA entities with flexible query conditions
 * @param baseQuery - Base query string (defaults to version and category filters)
 * @param additionalConditions - Optional array of additional query conditions
 * @param fileStems - Optional array of file stem filters (exact match)
 * @returns Promise<QueryResults> - Dictionary with success/error results
 */
async function queryRealityNFTMetadata(
  baseQuery?: string,
  additionalConditions?: QueryGroup[],
  fileStems?: string[]
): Promise<QueryResults> {
  let client;

  try {
    // Create a client to interact with the GolemDB API
    client = await createClient(chainId, key, rpcUrl, wsUrl);

    console.log("✅ Successfully connected to GolemDB");
  } catch (error) {
    console.error("❌ Failed to create GolemDB client:", error);
    throw new Error(`Client creation failed: ${error}`);
  }

  results = {
    success: [],
    errors: [],
    totalFound: 0,
    totalErrors: 0,
    entities: {},
  };

  try {
    // Build the query string - start with base query or default
    let query =
      baseQuery ||
      '_sys_version = 1 && _sys_category = "REALITY_NFT_METADATA" && _sys_status = "both" && _sys_file_type = "json"';

    // Add file stem filters if provided
    if (fileStems && fileStems.length > 0) {
      const fileStemConditions = fileStems
        .map((stem) => `_sys_file_stem = "${stem}"`)
        .join(" || ");
      query += ` && (${fileStemConditions})`;
    }

    // Add additional complex conditions if provided
    if (additionalConditions && additionalConditions.length > 0) {
      for (const group of additionalConditions) {
        const groupConditions = group.conditions
          .map((condition) => {
            const value =
              typeof condition.value === "string"
                ? `"${condition.value}"`
                : condition.value;
            return `${condition.field} ${condition.operator} ${value}`;
          })
          .join(` ${group.operator} `);
        query += ` && (${groupConditions})`;
      }
    }

    console.log(`🔍 Querying with: ${query}`);

    // Query entities
    const entities = await client.queryEntities(query);
    console.log(`📊 Found ${entities.length} entities matching criteria`);

    results.totalFound = entities.length;

    // Process each entity
    for (let i = 0; i < entities.length; i++) {
      const entity = entities[i];
      const result: RealityNFTMetadataResult = {
        entityKey: entity.entityKey,
        fileStems: [],
        fileType: "",
        category: "",
        version: 0,
        metadata: null,
      };

      try {
        // Get entity metadata
        const entityMetadata = await client.getEntityMetaData(entity.entityKey);

        // Extract system annotations
        let fileStems: string[] = [];
        let fileType = "";
        let category = "";
        let version = 0;

        // Aggregate all annotations into a key -> value(s) map
        const annotationMap: Record<string, unknown> = {};

        // Process string annotations
        for (const annotation of entityMetadata.stringAnnotations) {
          // Collect all string annotations
          if (annotationMap[annotation.key] === undefined) {
            annotationMap[annotation.key] = annotation.value;
          } else if (Array.isArray(annotationMap[annotation.key])) {
            (annotationMap[annotation.key] as unknown[]).push(annotation.value);
          } else {
            annotationMap[annotation.key] = [
              annotationMap[annotation.key] as unknown,
              annotation.value,
            ];
          }

          switch (annotation.key) {
            case "_sys_file_stem":
              fileStems.push(annotation.value);
              result.fileStems = fileStems;
              break;
            case "_sys_file_type":
              fileType = annotation.value;
              result.fileType = fileType;
              break;
            case "_sys_category":
              category = annotation.value;
              result.category = category;
              break;
          }
        }

        // Process numeric annotations
        for (const annotation of entityMetadata.numericAnnotations) {
          // Collect all numeric annotations
          if (annotationMap[annotation.key] === undefined) {
            annotationMap[annotation.key] = annotation.value;
          } else if (Array.isArray(annotationMap[annotation.key])) {
            (annotationMap[annotation.key] as unknown[]).push(annotation.value);
          } else {
            annotationMap[annotation.key] = [
              annotationMap[annotation.key] as unknown,
              annotation.value,
            ];
          }

          if (annotation.key === "_sys_version") {
            version = annotation.value;
            result.version = version;
            break;
          }
        }

        // Decode and parse metadata
        try {
          const decodedData = decoder.decode(entity.storageValue);
          result.metadata = JSON.parse(decodedData);
        } catch (parseError) {
          // If JSON parsing fails, store as raw string
          result.metadata = decoder.decode(entity.storageValue);
        }

        // Add decoded metadata to entities map as well
        (annotationMap as Record<string, unknown>)["_data"] = result.metadata;

        // Store entities keyed by entityKey
        results.entities[entity.entityKey] = annotationMap;

        results.success.push(result);
        console.log(
          `✅ [${i + 1}/${entities.length}] Processed: ${fileStems.join(
            ", "
          )} (${category})`
        );
      } catch (entityError) {
        console.error(
          `❌ [${i + 1}/${entities.length}] Error processing entity ${
            entity.entityKey
          }:`,
          entityError
        );
        result.error = `Entity processing failed: ${entityError}`;
        results.errors.push(result);
        results.totalErrors++;
      }
    }
  } catch (queryError) {
    console.error("❌ Query execution failed:", queryError);
    throw new Error(`Query execution failed: ${queryError}`);
  } finally {
    // Clean up client connection
    if (client) {
      try {
        // Note: GolemBaseClient doesn't have a close() method
        console.log("🔌 Client cleanup completed");
      } catch (closeError) {
        console.warn(
          "⚠️ Warning: Failed to cleanup client connection:",
          closeError
        );
      }
    }
  }

  return results;
}

// Removed unused helper functions `createCondition` and `createQueryGroup`

/**
 * Main function to demonstrate the query functionality
 */
async function main() {
  console.log("🚀 Starting REALITY_NFT_METADATA query example...\n");
  console.log("🔧 Debug: Script is starting...");

  // Parse CLI flags
  const args = arg({
    "--interactive": Boolean,
    "-i": "--interactive",
  });

  try {
    // Query all REALITY_NFT_METADATA entities
    console.log("📋 Querying all REALITY_NFT_METADATA entities...");
    const allResults = await queryRealityNFTMetadata();

    if (args["--interactive"]) {
      // Expose entities on global scope for Bun/REPL interactive inspection
      (globalThis as any).entities = allResults.entities;
      console.log(JSON.stringify(allResults.entities, null, 2));
      console.log("\nℹ️ entities is now available on globalThis.entities");
      // Do not exit in interactive mode to allow further inspection
      return;
    }
    console.log(`\n📊 All Results Summary:`);
    console.log(`   Total found: ${allResults.totalFound}`);
    console.log(`   Successful: ${allResults.success.length}`);
    console.log(`   Errors: ${allResults.totalErrors}`);

    if (allResults.success.length > 0) {
      console.log(`\n📝 Sample successful results:`);
      allResults.success.slice(0, 10).forEach((result, index) => {
        console.log(
          `   ${index + 1}. ${result.fileStems.join(", ")} (${
            result.category
          }) - v${result.version}`
        );
      });

      if (allResults.success.length > 10) {
        console.log(
          `   ... and ${allResults.success.length - 10} more results`
        );
      }
    }

    // Display errors if any
    if (allResults.errors.length > 0) {
      console.log(`\n❌ Errors encountered:`);
      allResults.errors.forEach((error, index) => {
        console.log(`   ${index + 1}. ${error.entityKey}: ${error.error}`);
      });
    }
  } catch (error) {
    console.error("💥 Fatal error in main execution:", error);
    process.exit(1);
  }

  console.log("\n✅ Example completed successfully!");
  process.exit(0);
}

// Run the main function
console.log("🔧 Debug: About to start main function...");
main().catch((error) => {
  console.error("💥 Unhandled error:", error);
  process.exit(1);
});
