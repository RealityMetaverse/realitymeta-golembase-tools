from typing import List
from golem_base_sdk import Annotation, GolemBaseClient
from ..common.config import ARKIV_RPC, ARKIV_WSS, PRIVATE_KEY


# TODO: fix circular dependency
def _get_logger():
    """Lazy load logger to avoid circular dependency."""
    from ..common.globals import logger

    return logger


async def create_arkiv_client(
    rpc_url: str = None,
    ws_url: str = None,
    private_key: str = None,
):
    """Create and configure a GolemBaseClient instance."""
    if not rpc_url:
        rpc_url = ARKIV_RPC
    if not ws_url:
        ws_url = ARKIV_WSS
    if not private_key:
        private_key = PRIVATE_KEY

    # Create a client to interact with the Arkiv API
    arkiv_client = await GolemBaseClient.create(
        rpc_url=rpc_url,
        ws_url=ws_url,
        private_key=private_key,
    )
    _get_logger().info("Arkiv client initialized")

    return arkiv_client


def create_arkiv_entity_annotations(
    dictionary: dict[str, int | str],
) -> tuple[List[Annotation], List[Annotation]]:
    """
    Create annotations from dictionary.
    Returns tuple of (string_annotations, number_annotations)
    """
    string_annotations = []
    number_annotations = []

    for key, value in dictionary.items():
        if isinstance(value, str):
            string_annotations.append(Annotation(key, value))
        elif isinstance(value, int):
            number_annotations.append(Annotation(key, value))
        else:
            raise ValueError(f"Invalid value type: {type(value)}")

    return string_annotations, number_annotations


# ALIAS
create_annotations_from_dict = create_arkiv_entity_annotations
