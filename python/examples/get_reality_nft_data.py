#!/usr/bin/env python3
import asyncio
import base64
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from golem_base_sdk import GolemBaseClient, GenericBytes


# Configuration - these would typically come from environment variables
@dataclass
class Config:
    CHAIN_ID: str = "60138453032"
    RPC_URL: str = "https://reality-games.hoodi.arkiv.network/rpc"
    WS_URL: str = "wss://reality-games.hoodi.arkiv.network/rpc/ws"
    TARGET_OWNER: str = "0x744A2Bb994246810450375a23251F5298764122e"
    # This is trash private key, can be exposed
    PRIVATE_KEY: str = (
        "d4fa9b8ee991d792547ba95f779ee34780d1a705455200887c8721662f55e7ed"
    )


config = Config()


class RealityNFTService:
    """Service for querying Reality NFT data from Arkiv."""

    def __init__(self):
        self.client: Optional[GolemBaseClient] = None
        self.cache: Dict[str, Any] = {}
        self.is_initialized = False
        self.is_service_available = False

    def _get_cache_key(self, category: str, token_id: str) -> str:
        """
        Generate a composite cache key from category and tokenId.

        Args:
            category: The system category
            token_id: The token ID

        Returns:
            The composite cache key
        """
        return f"{category}:{token_id}"

    async def _initialize(self) -> None:
        """Initialize the Arkiv client."""
        if self.is_initialized:
            return

        try:
            # Check if all required config is available
            if not all(
                [
                    config.CHAIN_ID,
                    config.RPC_URL,
                    config.WS_URL,
                    config.TARGET_OWNER,
                ]
            ):
                raise ValueError("Missing required Arkiv configuration")

            if not config.PRIVATE_KEY:
                raise ValueError("Failed to create account data from configuration")

            self.client = await GolemBaseClient.create(
                rpc_url=config.RPC_URL,
                ws_url=config.WS_URL,
                private_key=config.PRIVATE_KEY,
            )

            self.is_initialized = True
            self.is_service_available = True
            print("✅ RealityNFTService initialized with environment config")
            print(f"   Chain ID: {config.CHAIN_ID}")
            print(f"   RPC URL: {config.RPC_URL}")
            print(f"   Target Owner: {config.TARGET_OWNER}")
        except Exception as error:
            print(f"❌ Failed to initialize RealityNFTService: {error}")
            self.is_service_available = False
            self.is_initialized = (
                True  # Mark as initialized even if failed to prevent retries
            )
            raise Exception(f"Service initialization failed: {error}")

    async def is_available(self) -> bool:
        """
        Check if the service is available and configured properly.

        Returns:
            True if service is ready to use
        """
        if not self.is_initialized:
            try:
                await self._initialize()
                return self.is_service_available
            except:
                return False
        return self.is_service_available

    async def get_data(
        self,
        token_id: str,
        sys_category: str = "REALITY_NFT_METADATA",
    ) -> Optional[Dict[str, Any]]:
        """
        Get data for a single tokenId.

        Args:
            token_id: The file stem (tokenId) to fetch
            sys_category: The system category (default: "REALITY_NFT_METADATA")

        Returns:
            The converted JSON data or None if not found
        """
        # Check cache first using composite key
        cache_key = self._get_cache_key(sys_category, token_id)
        if cache_key in self.cache:
            return self.cache[cache_key]

        await self._initialize()

        try:
            query = self._build_query(token_ids=[token_id], sys_category=sys_category)
            entities = await self.client.query_entities(query)

            if not entities:
                return None

            # Process entities to find one that belongs to the target owner
            for entity in entities:
                result = await self._process_entity(entity, token_id, sys_category)
                if result:
                    return result

            return None
        except Exception:
            return None

    async def get_multiple_data(
        self,
        token_ids: List[str],
        sys_category: str = "REALITY_NFT_METADATA",
    ) -> Dict[str, Any]:
        """
        Get data for multiple tokenIds.

        Args:
            token_ids: Array of tokenIds to fetch
            sys_category: The system category (default: "REALITY_NFT_METADATA")

        Returns:
            Dictionary mapping tokenId to data
        """
        if not token_ids:
            return {}

        await self._initialize()

        results: Dict[str, Any] = {}
        uncached_token_ids: List[str] = []

        # Check cache first using composite keys
        for token_id in token_ids:
            cache_key = self._get_cache_key(sys_category, token_id)
            if cache_key in self.cache:
                cached_data = self.cache[cache_key]
                results[token_id] = cached_data
            else:
                uncached_token_ids.append(token_id)

        # If all are cached, return results
        if not uncached_token_ids:
            return results

        try:
            query = self._build_query(
                token_ids=uncached_token_ids,
                sys_category=sys_category,
            )
            entities = await self.client.query_entities(query)

            # Process each entity
            for entity in entities:
                result = await self._process_entity_for_multiple(entity, sys_category)
                if result:
                    results[result["token_id"]] = result["data"]

            return results
        except Exception:
            return {}

    async def get_all_data(
        self,
        sys_category: str = "REALITY_NFT_METADATA",
        token_category: Optional[str] = None,
        token_country: Optional[str] = None,
        token_keyword: Optional[str] = None,
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get all data for a specific category without filtering by tokenIds.

        Args:
            sys_category: The system category to fetch data for
            token_category: Optional category filter
            token_country: Optional country filter
            token_keyword: Optional keyword filter
            skip: Number of elements to skip from the beginning (default: 0)
            limit: Maximum number of elements to return after skip (default: None for no limit)

        Returns:
            Dictionary with 'data' (mapping tokenId to data) and 'totalCount'
        """
        await self._initialize()
        results: Dict[str, Any] = {}

        try:
            query = self._build_query(
                sys_category=sys_category,
                token_category=token_category,
                token_country=token_country,
                token_keyword=token_keyword,
            )

            entities = await self.client.query_entities(query)

            # Apply skip and limit to entities list
            processed_entities = entities

            # Apply skip: remove first x elements
            if skip > 0:
                processed_entities = entities[skip:]

            # Apply limit: keep first x elements after skip
            if limit is not None and limit > 0:
                processed_entities = processed_entities[:limit]

            # Process each entity
            for entity in processed_entities:
                result = await self._process_entity_for_multiple(entity, sys_category)
                if result:
                    results[result["token_id"]] = result["data"]

            return {
                "data": results,
                "totalCount": len(entities),
            }
        except Exception as error:
            print(f"Error fetching all data: {error}")
            return {
                "data": {},
                "totalCount": 0,
            }

    def _build_query(
        self,
        sys_category: str,
        token_ids: Optional[List[str]] = None,
        token_category: Optional[str] = None,
        token_country: Optional[str] = None,
        token_keyword: Optional[str] = None,
    ) -> str:
        """
        Build query string for tokenIds.

        Args:
            sys_category: System category to filter by
            token_ids: Optional array of tokenIds to query for
            token_category: Optional category filter
            token_country: Optional country filter
            token_keyword: Optional keyword filter

        Returns:
            The constructed query string
        """
        base_query = '_sys_version = 1 && (_sys_status = "both" || _sys_status = "prod") && _sys_file_type = "json"'

        if sys_category:
            base_query += f' && _sys_category = "{sys_category}"'

        if token_ids:
            if len(token_ids) == 1:
                base_query += f' && _sys_file_stem = "{token_ids[0]}"'
            else:
                token_conditions = " || ".join(
                    f'_sys_file_stem = "{token_id}"' for token_id in token_ids
                )
                base_query += f" && ({token_conditions})"

        # Category filter
        if token_category:
            base_query += f' && attr_category = "{token_category}"'

        # Country filter
        if token_country:
            base_query += f' && attr_country_code = "{token_country}"'

        # Keyword filter
        if token_keyword:
            # Convert keyword to pattern: "*[<Ch1Capital><Ch1lower>][<Ch2Capital><Ch2lower>]...*"
            keyword_pattern = "".join(
                f"[{char.upper()}{char.lower()}]" for char in token_keyword
            )
            base_query += f' && name ~ "*{keyword_pattern}*"'

        return base_query

    async def _process_entity(
        self,
        entity: Any,
        expected_token_id: str,
        sys_category: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Process a single entity for get_data method.

        Args:
            entity: The entity to process
            expected_token_id: The expected tokenId to match
            sys_category: The system category for cache key

        Returns:
            The processed data or None
        """
        try:
            entity_key_bytes = GenericBytes.from_hex_string(entity.entity_key)
            entity_metadata = await self.client.get_entity_metadata(entity_key_bytes)

            # Check if this entity belongs to the target owner
            if self._has_owner_in_entity_metadata(entity_metadata, config.TARGET_OWNER):
                # Get _sys_data from string annotations
                base64_data = ""
                for annotation in entity_metadata.string_annotations:
                    if annotation.key == "_sys_data":
                        base64_data = annotation.value
                        break

                if not base64_data:
                    return None

                # Decode base64 and parse JSON
                try:
                    decoded_data = base64.b64decode(base64_data).decode("utf-8")
                    data = json.loads(decoded_data)
                except (ValueError, json.JSONDecodeError):
                    return None

                # Cache the result using composite key
                cache_key = self._get_cache_key(sys_category, expected_token_id)
                self.cache[cache_key] = data
                return data
        except Exception:
            # Skip failed entities
            pass
        return None

    async def _process_entity_for_multiple(
        self,
        entity: Any,
        sys_category: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Process a single entity for get_multiple_data method.

        Args:
            entity: The entity to process
            sys_category: The system category for cache key

        Returns:
            Dictionary with 'token_id' and 'data' or None
        """
        try:
            entity_key_bytes = GenericBytes.from_hex_string(entity.entity_key)
            entity_metadata = await self.client.get_entity_metadata(entity_key_bytes)

            # Check if this entity belongs to the target owner
            if self._has_owner_in_entity_metadata(entity_metadata, config.TARGET_OWNER):
                # Extract tokenId and _sys_data from annotations
                token_id = ""
                base64_data = ""

                for annotation in entity_metadata.string_annotations:
                    if annotation.key == "_sys_file_stem":
                        token_id = annotation.value
                    elif annotation.key == "_sys_data":
                        base64_data = annotation.value

                if not token_id or not base64_data:
                    return None

                # Decode base64 and parse JSON
                try:
                    decoded_data = base64.b64decode(base64_data).decode("utf-8")
                    data = json.loads(decoded_data)
                except (ValueError, json.JSONDecodeError):
                    return None

                # Cache and return result using composite key
                cache_key = self._get_cache_key(sys_category, token_id)
                self.cache[cache_key] = data
                return {"token_id": token_id, "data": data}
        except Exception:
            # Skip failed entities
            pass
        return None

    def clear_cache(self) -> None:
        """Clear the cache."""
        self.cache.clear()
        print("🗑️ Cache cleared")

    def clear_cache_for_category(self, sys_category: str) -> int:
        """
        Clear cache for a specific category.

        Args:
            sys_category: The system category to clear

        Returns:
            Number of entries cleared
        """
        keys_to_delete = [
            key for key in self.cache.keys() if key.startswith(f"{sys_category}:")
        ]

        for key in keys_to_delete:
            del self.cache[key]

        print(f"🗑️ Cleared {len(keys_to_delete)} entries for category: {sys_category}")
        return len(keys_to_delete)

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        keys = list(self.cache.keys())
        categories: Dict[str, int] = {}
        category_breakdown: Dict[str, List[str]] = {}

        # Analyze cache keys to extract category information
        for key in keys:
            parts = key.split(":", 1)
            if len(parts) == 2:
                category, token_id = parts
                categories[category] = categories.get(category, 0) + 1
                if category not in category_breakdown:
                    category_breakdown[category] = []
                category_breakdown[category].append(token_id)

        return {
            "size": len(self.cache),
            "keys": keys,
            "categories": categories,
            "categoryBreakdown": category_breakdown,
        }

    def remove_from_cache(
        self,
        token_id: str,
        sys_category: str = "REALITY_NFT_METADATA",
    ) -> bool:
        """
        Remove specific tokenId from cache for a specific category.

        Args:
            token_id: The tokenId to remove from cache
            sys_category: The system category (default: "REALITY_NFT_METADATA")

        Returns:
            True if the item was removed, False if it wasn't in cache
        """
        cache_key = self._get_cache_key(sys_category, token_id)
        if cache_key in self.cache:
            del self.cache[cache_key]
            return True
        return False

    def _has_owner_in_entity_metadata(
        self,
        entity_metadata: Any,
        owner_address: str,
    ) -> bool:
        """
        Check if the entity metadata has the specified owner.

        Args:
            entity_metadata: The entity metadata object to check
            owner_address: The owner address to check for

        Returns:
            True if the entity belongs to the owner
        """
        # Check if entityMetadata has owner property
        if (
            hasattr(entity_metadata, "owner")
            and entity_metadata.owner
            and entity_metadata.owner == GenericBytes.from_hex_string(owner_address)
        ):
            return True

        return False

    async def disconnect(self) -> None:
        """Disconnect the Arkiv client."""
        if self.client:
            await self.client.disconnect()
            print("🔌 Client disconnected")


# Export a singleton instance for easy use
reality_nft_service = RealityNFTService()


# Example usage
async def main():
    """Example usage of the RealityNFTService."""
    try:
        print("Search by token id: 613")
        result = await reality_nft_service.get_data(
            token_id="613",
            sys_category="REALITY_NFT_METADATA",
        )
        print(json.dumps(result, indent=2))

        print("Search by token id: 911 and 736")
        result = await reality_nft_service.get_multiple_data(
            token_ids=["911", "736"],
            sys_category="REALITY_NFT_METADATA",
        )
        print(json.dumps(result, indent=2))

        print("Search by keyword: main")
        result = await reality_nft_service.get_all_data(
            sys_category="REALITY_NFT_METADATA",
            token_keyword="main",
            skip=0,
            limit=30,
        )
        print(json.dumps(result, indent=2))
    finally:
        await reality_nft_service.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
