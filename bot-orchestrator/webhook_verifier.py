"""Webhook signature verification for Recall.ai"""
import os
import hmac
import hashlib
from typing import Optional


def verify_webhook_signature(body: bytes, signature: Optional[str]) -> bool:
    """
    Verify webhook signature from Recall.ai
    
    Recall.ai signs webhooks using HMAC-SHA256 with your webhook secret.
    The signature is sent in the X-Recall-Signature header.
    
    Args:
        body: Raw request body bytes
        signature: Signature from X-Recall-Signature header
    
    Returns:
        True if signature is valid or if webhook secret is not configured
    """
    webhook_secret = os.getenv("RECALL_WEBHOOK_SECRET")
    
    # Debug logging
    print(f"[WEBHOOK-VERIFY] Secret configured: {bool(webhook_secret)}", flush=True)
    print(f"[WEBHOOK-VERIFY] Signature provided: {bool(signature)}", flush=True)
    
    # If no secret configured, skip verification (development mode)
    if not webhook_secret:
        print(f"[WEBHOOK-VERIFY] No secret - allowing", flush=True)
        return True
    
    # If secret configured but no signature provided, reject
    if not signature:
        print(f"[WEBHOOK-VERIFY] Secret set but no signature - rejecting", flush=True)
        return False
    
    # Compute HMAC-SHA256 signature
    expected_signature = hmac.new(
        webhook_secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    print(f"[WEBHOOK-VERIFY] Expected: {expected_signature[:20]}...", flush=True)
    print(f"[WEBHOOK-VERIFY] Received: {signature[:20]}...", flush=True)
    
    # Compare signatures (constant-time comparison)
    is_valid = hmac.compare_digest(expected_signature, signature)
    print(f"[WEBHOOK-VERIFY] Valid: {is_valid}", flush=True)
    
    return is_valid
