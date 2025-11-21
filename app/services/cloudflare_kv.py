"""
Cloudflare Workers KV integration service.

Provides methods to upload, delete, and manage key-value pairs in Cloudflare KV namespaces.
Supports both single and batch operations with progress tracking.
"""
import hashlib
import requests
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse, quote
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from app.config import settings


class CloudflareKVService:
    """Service for integrating with Cloudflare Workers KV REST API."""

    # Cloudflare API base URL
    API_BASE = "https://api.cloudflare.com/client/v4"

    def __init__(
        self,
        account_id: str,
        api_token: str,
        namespace_id: str,
        max_parallel: int = 5
    ):
        """
        Initialize Cloudflare KV service.

        Args:
            account_id: Cloudflare account ID
            api_token: Cloudflare API token with KV write permissions
            namespace_id: KV namespace ID
            max_parallel: Maximum parallel requests (default: 5)
        """
        self.account_id = account_id
        self.api_token = api_token
        self.namespace_id = namespace_id
        self.max_parallel = max_parallel

        # Base URL for this namespace
        self.base_url = (
            f"{self.API_BASE}/accounts/{account_id}/storage/kv/"
            f"namespaces/{namespace_id}"
        )

    @staticmethod
    def generate_kv_key(url: str) -> str:
        """
        Generate KV key from URL.

        Converts URL to a safe key format:
        - https://example.com/page -> "https/example.com/page"
        - http://test.com -> "http/test.com"

        Args:
            url: URL to convert

        Returns:
            Safe KV key string
        """
        parsed = urlparse(url)
        # Remove :// and replace with /
        scheme = parsed.scheme
        netloc = parsed.netloc
        path = parsed.path.lstrip('/')

        # Build key: scheme/domain/path
        if path:
            key = f"{scheme}/{netloc}/{path}"
        else:
            key = f"{scheme}/{netloc}"

        # Remove trailing slashes
        key = key.rstrip('/')

        return key

    @staticmethod
    def generate_kv_key_from_hash(url: str) -> str:
        """
        Generate KV key from URL hash (alternative method).

        Uses SHA-256 hash of URL as the key for maximum compatibility.

        Args:
            url: URL to hash

        Returns:
            Hex digest of SHA-256 hash
        """
        normalized = url.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()

    def upload_value(
        self,
        key: str,
        value: str,
        expiration_ttl: Optional[int] = None
    ) -> Dict:
        """
        Upload a single key-value pair to KV.

        Args:
            key: KV key (max 512 bytes)
            value: Value to store (max 25 MiB)
            expiration_ttl: Optional seconds until expiration (min 60)

        Returns:
            Dictionary containing:
                - success: bool
                - key: str
                - error: Optional error message

        Example:
            >>> service = CloudflareKVService(account_id, token, namespace_id)
            >>> result = service.upload_value("my-key", "<html>...</html>")
            >>> print(result['success'])
        """
        # URL-encode the key for special characters
        encoded_key = quote(key, safe='')
        url = f"{self.base_url}/values/{encoded_key}"

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "text/html; charset=utf-8"
        }

        params = {}
        if expiration_ttl:
            params["expiration_ttl"] = max(60, expiration_ttl)  # Minimum 60 seconds

        try:
            print(f"[CloudflareKV] Uploading key: {key} ({len(value)} bytes)")

            response = requests.put(
                url,
                data=value.encode('utf-8'),
                headers=headers,
                params=params,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print(f"[CloudflareKV] Successfully uploaded key: {key}")
                    return {
                        "success": True,
                        "key": key,
                        "error": None
                    }
                else:
                    error_msg = result.get('errors', [{}])[0].get('message', 'Unknown error')
                    print(f"[CloudflareKV] Upload failed for key {key}: {error_msg}")
                    return {
                        "success": False,
                        "key": key,
                        "error": error_msg
                    }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                print(f"[CloudflareKV] Upload failed for key {key}: {error_msg}")
                return {
                    "success": False,
                    "key": key,
                    "error": error_msg
                }

        except Exception as e:
            error_msg = f"Exception during upload: {str(e)}"
            print(f"[CloudflareKV] Error uploading key {key}: {error_msg}")
            return {
                "success": False,
                "key": key,
                "error": error_msg
            }

    def upload_bulk(
        self,
        key_value_pairs: List[Dict[str, str]],
        expiration_ttl: Optional[int] = None
    ) -> Dict:
        """
        Upload multiple key-value pairs in a single request.

        Args:
            key_value_pairs: List of dicts with 'key' and 'value' fields
            expiration_ttl: Optional seconds until expiration (min 60)

        Returns:
            Dictionary containing:
                - success: bool
                - successful_count: int
                - failed_count: int
                - unsuccessful_keys: List[str]
                - error: Optional error message

        Example:
            >>> service = CloudflareKVService(account_id, token, namespace_id)
            >>> pairs = [
            ...     {"key": "key1", "value": "value1"},
            ...     {"key": "key2", "value": "value2"}
            ... ]
            >>> result = service.upload_bulk(pairs)
            >>> print(f"{result['successful_count']} keys uploaded")
        """
        if not key_value_pairs:
            return {
                "success": True,
                "successful_count": 0,
                "failed_count": 0,
                "unsuccessful_keys": [],
                "error": None
            }

        # Cloudflare KV bulk API accepts max 10,000 pairs
        if len(key_value_pairs) > 10000:
            return {
                "success": False,
                "successful_count": 0,
                "failed_count": len(key_value_pairs),
                "unsuccessful_keys": [pair['key'] for pair in key_value_pairs],
                "error": "Maximum 10,000 key-value pairs allowed per bulk request"
            }

        url = f"{self.base_url}/bulk"

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

        # Format payload for Cloudflare KV bulk API
        payload = []
        for pair in key_value_pairs:
            item = {
                "key": pair['key'],
                "value": pair['value']
            }
            if expiration_ttl:
                item["expiration_ttl"] = max(60, expiration_ttl)
            payload.append(item)

        try:
            print(f"[CloudflareKV] Bulk uploading {len(key_value_pairs)} keys")

            response = requests.put(
                url,
                json=payload,
                headers=headers,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    data = result.get('result', {})
                    successful_count = data.get('successful_key_count', 0)
                    unsuccessful_keys = data.get('unsuccessful_keys', [])
                    failed_count = len(unsuccessful_keys)

                    print(f"[CloudflareKV] Bulk upload completed: {successful_count} successful, {failed_count} failed")

                    return {
                        "success": True,
                        "successful_count": successful_count,
                        "failed_count": failed_count,
                        "unsuccessful_keys": unsuccessful_keys,
                        "error": None
                    }
                else:
                    error_msg = result.get('errors', [{}])[0].get('message', 'Unknown error')
                    print(f"[CloudflareKV] Bulk upload failed: {error_msg}")
                    return {
                        "success": False,
                        "successful_count": 0,
                        "failed_count": len(key_value_pairs),
                        "unsuccessful_keys": [pair['key'] for pair in key_value_pairs],
                        "error": error_msg
                    }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                print(f"[CloudflareKV] Bulk upload failed: {error_msg}")
                return {
                    "success": False,
                    "successful_count": 0,
                    "failed_count": len(key_value_pairs),
                    "unsuccessful_keys": [pair['key'] for pair in key_value_pairs],
                    "error": error_msg
                }

        except Exception as e:
            error_msg = f"Exception during bulk upload: {str(e)}"
            print(f"[CloudflareKV] Error in bulk upload: {error_msg}")
            return {
                "success": False,
                "successful_count": 0,
                "failed_count": len(key_value_pairs),
                "unsuccessful_keys": [pair['key'] for pair in key_value_pairs],
                "error": error_msg
            }

    def delete_value(self, key: str) -> Dict:
        """
        Delete a single key from KV.

        Args:
            key: KV key to delete

        Returns:
            Dictionary containing:
                - success: bool
                - key: str
                - error: Optional error message

        Example:
            >>> service = CloudflareKVService(account_id, token, namespace_id)
            >>> result = service.delete_value("my-key")
            >>> print(result['success'])
        """
        # URL-encode the key for special characters
        encoded_key = quote(key, safe='')
        url = f"{self.base_url}/values/{encoded_key}"

        headers = {
            "Authorization": f"Bearer {self.api_token}"
        }

        try:
            print(f"[CloudflareKV] Deleting key: {key}")

            response = requests.delete(
                url,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print(f"[CloudflareKV] Successfully deleted key: {key}")
                    return {
                        "success": True,
                        "key": key,
                        "error": None
                    }
                else:
                    error_msg = result.get('errors', [{}])[0].get('message', 'Unknown error')
                    print(f"[CloudflareKV] Delete failed for key {key}: {error_msg}")
                    return {
                        "success": False,
                        "key": key,
                        "error": error_msg
                    }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                print(f"[CloudflareKV] Delete failed for key {key}: {error_msg}")
                return {
                    "success": False,
                    "key": key,
                    "error": error_msg
                }

        except Exception as e:
            error_msg = f"Exception during delete: {str(e)}"
            print(f"[CloudflareKV] Error deleting key {key}: {error_msg}")
            return {
                "success": False,
                "key": key,
                "error": error_msg
            }

    def list_keys(
        self,
        limit: int = 1000,
        cursor: Optional[str] = None,
        prefix: Optional[str] = None
    ) -> Dict:
        """
        List keys in the namespace.

        Args:
            limit: Maximum keys to return (max 1000)
            cursor: Pagination cursor
            prefix: Optional key prefix filter

        Returns:
            Dictionary containing:
                - success: bool
                - keys: List of key objects
                - cursor: Optional cursor for next page
                - error: Optional error message

        Example:
            >>> service = CloudflareKVService(account_id, token, namespace_id)
            >>> result = service.list_keys(limit=100, prefix="https/")
            >>> print(f"Found {len(result['keys'])} keys")
        """
        url = f"{self.base_url}/keys"

        headers = {
            "Authorization": f"Bearer {self.api_token}"
        }

        params = {
            "limit": min(limit, 1000)
        }
        if cursor:
            params["cursor"] = cursor
        if prefix:
            params["prefix"] = prefix

        try:
            print(f"[CloudflareKV] Listing keys (limit={limit}, prefix={prefix})")

            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    data = result.get('result', [])
                    result_info = result.get('result_info', {})
                    cursor = result_info.get('cursor')

                    print(f"[CloudflareKV] Listed {len(data)} keys")

                    return {
                        "success": True,
                        "keys": data,
                        "cursor": cursor,
                        "error": None
                    }
                else:
                    error_msg = result.get('errors', [{}])[0].get('message', 'Unknown error')
                    print(f"[CloudflareKV] List keys failed: {error_msg}")
                    return {
                        "success": False,
                        "keys": [],
                        "cursor": None,
                        "error": error_msg
                    }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                print(f"[CloudflareKV] List keys failed: {error_msg}")
                return {
                    "success": False,
                    "keys": [],
                    "cursor": None,
                    "error": error_msg
                }

        except Exception as e:
            error_msg = f"Exception during list keys: {str(e)}"
            print(f"[CloudflareKV] Error listing keys: {error_msg}")
            return {
                "success": False,
                "keys": [],
                "cursor": None,
                "error": error_msg
            }

    def get_namespace_status(self) -> Dict:
        """
        Get status information about the namespace.

        Returns statistics by listing a sample of keys.

        Returns:
            Dictionary containing:
                - success: bool
                - namespace_id: str
                - sample_key_count: int (number of keys in sample)
                - has_keys: bool
                - error: Optional error message

        Example:
            >>> service = CloudflareKVService(account_id, token, namespace_id)
            >>> result = service.get_namespace_status()
            >>> print(f"Namespace has keys: {result['has_keys']}")
        """
        result = self.list_keys(limit=100)

        if result['success']:
            keys = result.get('keys', [])
            return {
                "success": True,
                "namespace_id": self.namespace_id,
                "sample_key_count": len(keys),
                "has_keys": len(keys) > 0,
                "error": None
            }
        else:
            return {
                "success": False,
                "namespace_id": self.namespace_id,
                "sample_key_count": 0,
                "has_keys": False,
                "error": result.get('error')
            }

    @classmethod
    def from_client(cls, client) -> Optional["CloudflareKVService"]:
        """
        Factory method to create service from Client model.

        Args:
            client: Client model instance

        Returns:
            CloudflareKVService instance or None if credentials missing

        Example:
            >>> from app.models.client import Client
            >>> client = db.query(Client).first()
            >>> service = CloudflareKVService.from_client(client)
            >>> if service:
            ...     service.upload_value("key", "value")
        """
        if not all([
            client.cloudflare_account_id,
            client.cloudflare_api_token,
            client.cloudflare_kv_namespace_id
        ]):
            return None

        return cls(
            account_id=client.cloudflare_account_id,
            api_token=client.cloudflare_api_token,
            namespace_id=client.cloudflare_kv_namespace_id
        )
