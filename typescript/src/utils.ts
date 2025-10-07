import { AccountData, Tagged } from "golem-base-sdk";
import { RealityNFTConfig } from "./types";
import { ConfigurationError } from "./errors";

/**
 * Validates configuration completeness
 */
export function validateConfig(config: RealityNFTConfig): void {
  const requiredFields: (keyof RealityNFTConfig)[] = [
    "chainId",
    "rpcUrl",
    "wsUrl",
    "targetOwner",
    "privateKey",
  ];

  const missingFields = requiredFields.filter((field) => !config[field]);

  if (missingFields.length > 0) {
    throw new ConfigurationError(
      `Missing required configuration fields: ${missingFields.join(", ")}`
    );
  }
}

/**
 * Create account data from configuration
 */
export function createAccountDataFromConfig(privateKey: string): AccountData {
  try {
    const hexMatch = privateKey.match(/.{1,2}/g);
    if (!hexMatch) {
      throw new Error("Invalid private key format");
    }

    const bytes = new Uint8Array(hexMatch.map((byte) => parseInt(byte, 16)));

    return new Tagged("privatekey", bytes);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    throw new ConfigurationError(`Failed to create account data: ${message}`);
  }
}

/**
 * Safely converts string to lowercase for comparison
 */
export function normalizeAddress(address: string): string {
  return address.toLowerCase();
}
