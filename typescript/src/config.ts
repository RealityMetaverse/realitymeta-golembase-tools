import { RealityNFTConfig } from "./types";

/**
 * Default configuration - in production, load from environment variables
 */
export const DEFAULT_CONFIG: RealityNFTConfig = {
  chainId: process.env.CHAIN_ID || "60138453032",
  rpcUrl:
    process.env.RPC_URL || "https://reality-games.hoodi.arkiv.network/rpc",
  wsUrl: process.env.WS_URL || "wss://reality-games.hoodi.arkiv.network/rpc/ws",
  targetOwner:
    process.env.TARGET_OWNER || "0x744A2Bb994246810450375a23251F5298764122e",
  // This is a trash private key for demo purposes - can be exposed
  privateKey:
    process.env.PRIVATE_KEY ||
    "d4fa9b8ee991d792547ba95f779ee34780d1a705455200887c8721662f55e7ed",
};
