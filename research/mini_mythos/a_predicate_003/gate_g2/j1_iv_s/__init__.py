"""Independent, provisional byte-level verifier for J1 synthetic sidecars.

This is NOT an acceptance oracle or a source of authenticated evidence.
"""

from .sidecar import ChainResult, ReferenceResult, verify_chain, verify_f05_reference

__all__ = ["ChainResult", "ReferenceResult", "verify_chain", "verify_f05_reference"]
