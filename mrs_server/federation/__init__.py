"""Federation module for MRS peer management."""

from .peers import (
    Peer,
    add_peer,
    get_all_peers,
    get_configured_peers,
    get_peer,
    learn_peer_from_referral,
    remove_peer,
    update_peer_last_seen,
)
from .referrals import generate_referrals

__all__ = [
    "Peer",
    "add_peer",
    "remove_peer",
    "get_peer",
    "get_all_peers",
    "get_configured_peers",
    "update_peer_last_seen",
    "learn_peer_from_referral",
    "generate_referrals",
]
