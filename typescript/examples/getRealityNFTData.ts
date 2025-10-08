import { RealityNFTService, SystemCategory } from "../src";

// ============================================================================
// Example Usage
// ============================================================================

(async () => {
  const result = await new RealityNFTService().getAllData({
    sysCategory: SystemCategory.REALITY_NFT_SPECIAL_VENUES,
    tokenKeywords: ["paris"],
    advancedSearch: true,
  });

  console.log(result);
})();
