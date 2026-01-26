"""Well-known endpoints for MRS discovery."""

from fastapi import APIRouter, HTTPException

from mrs_server.auth import get_public_key
from mrs_server.config import settings
from mrs_server.federation import get_all_peers
from mrs_server.models import (
    KeyResponse,
    PeerInfo,
    PublicKey,
    ServerCapabilities,
    WellKnownMRS,
)

router = APIRouter(prefix="/.well-known/mrs")


@router.get("", response_model=WellKnownMRS)
async def get_server_info() -> WellKnownMRS:
    """
    Get MRS server metadata.

    This endpoint provides information about the server's identity,
    capabilities, and known peers. It's used for server discovery
    and federation.
    """
    # Get known peers
    peers = get_all_peers()
    peer_info = [PeerInfo(server=p.server_url, hint=p.hint) for p in peers]

    return WellKnownMRS(
        mrs_version="0.5.0",
        server=settings.server_url,
        operator=settings.admin_email,
        authoritative_regions=[],  # Can be configured later
        known_peers=peer_info,
        capabilities=ServerCapabilities(
            geometry_types=["sphere"],
            max_radius=settings.max_radius,
        ),
    )


@router.get("/keys/{identity}", response_model=KeyResponse)
async def get_identity_key(identity: str) -> KeyResponse:
    """
    Get the public key for an identity.

    The identity can be:
    - A username (for local users at this server)
    - "_server" for the server's own signing key

    This endpoint is used by other servers to verify HTTP signatures
    from federated identities.
    """
    # Handle server key request
    if identity == "_server":
        key_info = get_public_key("_server")
        if not key_info:
            raise HTTPException(status_code=404, detail="Server key not found")

        return KeyResponse(
            id=f"_server@{settings.server_domain}",
            public_key=PublicKey(
                type="Ed25519",
                key=key_info["public_key_b64"],
            ),
            created=key_info["created_at"],
        )

    # For user keys, construct the full identity if needed
    if "@" not in identity:
        full_identity = f"{identity}@{settings.server_domain}"
    else:
        # Verify the domain matches this server
        _, domain = identity.split("@", 1)
        if domain != settings.server_domain:
            raise HTTPException(
                status_code=404,
                detail=f"Identity {identity} is not managed by this server",
            )
        full_identity = identity

    key_info = get_public_key(full_identity)
    if not key_info:
        raise HTTPException(status_code=404, detail=f"Key not found for {identity}")

    return KeyResponse(
        id=full_identity,
        public_key=PublicKey(
            type="Ed25519",
            key=key_info["public_key_b64"],
        ),
        created=key_info["created_at"],
    )
