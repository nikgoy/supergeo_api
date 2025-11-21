"""
Cloudflare Workers integration service.

Provides methods to deploy, update, delete, and manage Cloudflare Workers.
Supports worker script deployment with KV namespace bindings and route management.
"""
import os
import requests
from typing import Dict, Optional
from datetime import datetime

from app.config import settings


class CloudflareWorkerService:
    """Service for managing Cloudflare Workers via API."""

    # Cloudflare API base URL
    API_BASE = "https://api.cloudflare.com/client/v4"

    def __init__(
        self,
        account_id: str,
        api_token: str,
        zone_id: Optional[str] = None
    ):
        """
        Initialize Cloudflare Worker service.

        Args:
            account_id: Cloudflare account ID
            api_token: Cloudflare API token with Workers write permissions
            zone_id: Optional Cloudflare zone ID for route management
        """
        self.account_id = account_id
        self.api_token = api_token
        self.zone_id = zone_id

        # Base URLs
        self.workers_url = f"{self.API_BASE}/accounts/{account_id}/workers/scripts"
        if zone_id:
            self.routes_url = f"{self.API_BASE}/zones/{zone_id}/workers/routes"

    @staticmethod
    def generate_worker_name(client_id: str) -> str:
        """
        Generate worker script name from client ID.

        Args:
            client_id: Client UUID

        Returns:
            Worker script name (e.g., "geo-bot-detector-abc123")
        """
        # Remove hyphens from UUID and take first 8 chars
        short_id = str(client_id).replace('-', '')[:8]
        return f"geo-bot-detector-{short_id}"

    @staticmethod
    def load_worker_template() -> str:
        """
        Load worker script template from file.

        Returns:
            Worker script template string

        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'templates',
            'worker_script.js'
        )

        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()

    @staticmethod
    def prepare_worker_script(
        template: str,
        kv_namespace_id: str,
        api_endpoint: str,
        api_key: str,
        zone_name: str,
        client_id: str
    ) -> str:
        """
        Prepare worker script by replacing template variables.

        Args:
            template: Worker script template
            kv_namespace_id: KV namespace ID to bind
            api_endpoint: API endpoint URL for analytics
            api_key: API key for analytics
            zone_name: Zone name/domain
            client_id: Client UUID

        Returns:
            Prepared worker script with variables replaced
        """
        script = template.replace('{{KV_NAMESPACE_ID}}', kv_namespace_id)
        script = script.replace('{{API_ENDPOINT}}', api_endpoint)
        script = script.replace('{{API_KEY}}', api_key)
        script = script.replace('{{ZONE_NAME}}', zone_name)
        script = script.replace('{{CLIENT_ID}}', client_id)

        return script

    def deploy_worker(
        self,
        script_name: str,
        script_content: str,
        kv_namespace_id: str
    ) -> Dict:
        """
        Deploy or update a worker script.

        Args:
            script_name: Name for the worker script
            script_content: JavaScript worker code
            kv_namespace_id: KV namespace ID to bind as "GEO_PAGES"

        Returns:
            Dictionary containing:
                - success: bool
                - script_name: str
                - id: Optional worker ID
                - error: Optional error message

        Example:
            >>> service = CloudflareWorkerService(account_id, token, zone_id)
            >>> result = service.deploy_worker("my-worker", script, namespace_id)
            >>> print(result['success'])
        """
        url = f"{self.workers_url}/{script_name}"

        headers = {
            "Authorization": f"Bearer {self.api_token}",
        }

        # Prepare multipart form data for worker upload
        # Cloudflare Workers API requires specific format with metadata and script
        metadata = {
            "main_module": "worker.js",
            "bindings": [
                {
                    "type": "kv_namespace",
                    "name": "GEO_PAGES",
                    "namespace_id": kv_namespace_id
                }
            ]
        }

        files = {
            'metadata': (None, str(metadata).replace("'", '"'), 'application/json'),
            'worker.js': (None, script_content, 'application/javascript+module')
        }

        try:
            print(f"[CloudflareWorker] Deploying worker: {script_name}")

            response = requests.put(
                url,
                headers=headers,
                files=files,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    worker_data = result.get('result', {})
                    worker_id = worker_data.get('id', script_name)

                    print(f"[CloudflareWorker] Successfully deployed worker: {script_name}")
                    return {
                        "success": True,
                        "script_name": script_name,
                        "id": worker_id,
                        "error": None
                    }
                else:
                    errors = result.get('errors', [])
                    error_msg = errors[0].get('message', 'Unknown error') if errors else 'Unknown error'
                    print(f"[CloudflareWorker] Deploy failed for {script_name}: {error_msg}")
                    return {
                        "success": False,
                        "script_name": script_name,
                        "id": None,
                        "error": error_msg
                    }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                print(f"[CloudflareWorker] Deploy failed for {script_name}: {error_msg}")
                return {
                    "success": False,
                    "script_name": script_name,
                    "id": None,
                    "error": error_msg
                }

        except Exception as e:
            error_msg = f"Exception during deploy: {str(e)}"
            print(f"[CloudflareWorker] Error deploying {script_name}: {error_msg}")
            return {
                "success": False,
                "script_name": script_name,
                "id": None,
                "error": error_msg
            }

    def get_worker(self, script_name: str) -> Dict:
        """
        Get worker script details.

        Args:
            script_name: Name of the worker script

        Returns:
            Dictionary containing:
                - success: bool
                - script_name: str
                - exists: bool
                - created_on: Optional datetime string
                - modified_on: Optional datetime string
                - error: Optional error message

        Example:
            >>> service = CloudflareWorkerService(account_id, token)
            >>> result = service.get_worker("my-worker")
            >>> print(result['exists'])
        """
        url = f"{self.workers_url}/{script_name}"

        headers = {
            "Authorization": f"Bearer {self.api_token}"
        }

        try:
            print(f"[CloudflareWorker] Getting worker: {script_name}")

            response = requests.get(
                url,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    worker_data = result.get('result', {})

                    print(f"[CloudflareWorker] Worker found: {script_name}")
                    return {
                        "success": True,
                        "script_name": script_name,
                        "exists": True,
                        "created_on": worker_data.get('created_on'),
                        "modified_on": worker_data.get('modified_on'),
                        "error": None
                    }
                else:
                    error_msg = result.get('errors', [{}])[0].get('message', 'Unknown error')
                    print(f"[CloudflareWorker] Get worker failed for {script_name}: {error_msg}")
                    return {
                        "success": False,
                        "script_name": script_name,
                        "exists": False,
                        "created_on": None,
                        "modified_on": None,
                        "error": error_msg
                    }
            elif response.status_code == 404:
                print(f"[CloudflareWorker] Worker not found: {script_name}")
                return {
                    "success": True,
                    "script_name": script_name,
                    "exists": False,
                    "created_on": None,
                    "modified_on": None,
                    "error": None
                }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                print(f"[CloudflareWorker] Get worker failed for {script_name}: {error_msg}")
                return {
                    "success": False,
                    "script_name": script_name,
                    "exists": False,
                    "created_on": None,
                    "modified_on": None,
                    "error": error_msg
                }

        except Exception as e:
            error_msg = f"Exception during get worker: {str(e)}"
            print(f"[CloudflareWorker] Error getting {script_name}: {error_msg}")
            return {
                "success": False,
                "script_name": script_name,
                "exists": False,
                "created_on": None,
                "modified_on": None,
                "error": error_msg
            }

    def delete_worker(self, script_name: str) -> Dict:
        """
        Delete a worker script.

        Args:
            script_name: Name of the worker script to delete

        Returns:
            Dictionary containing:
                - success: bool
                - script_name: str
                - error: Optional error message

        Example:
            >>> service = CloudflareWorkerService(account_id, token)
            >>> result = service.delete_worker("my-worker")
            >>> print(result['success'])
        """
        url = f"{self.workers_url}/{script_name}"

        headers = {
            "Authorization": f"Bearer {self.api_token}"
        }

        try:
            print(f"[CloudflareWorker] Deleting worker: {script_name}")

            response = requests.delete(
                url,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print(f"[CloudflareWorker] Successfully deleted worker: {script_name}")
                    return {
                        "success": True,
                        "script_name": script_name,
                        "error": None
                    }
                else:
                    error_msg = result.get('errors', [{}])[0].get('message', 'Unknown error')
                    print(f"[CloudflareWorker] Delete failed for {script_name}: {error_msg}")
                    return {
                        "success": False,
                        "script_name": script_name,
                        "error": error_msg
                    }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                print(f"[CloudflareWorker] Delete failed for {script_name}: {error_msg}")
                return {
                    "success": False,
                    "script_name": script_name,
                    "error": error_msg
                }

        except Exception as e:
            error_msg = f"Exception during delete: {str(e)}"
            print(f"[CloudflareWorker] Error deleting {script_name}: {error_msg}")
            return {
                "success": False,
                "script_name": script_name,
                "error": error_msg
            }

    def list_workers(self) -> Dict:
        """
        List all worker scripts in the account.

        Returns:
            Dictionary containing:
                - success: bool
                - workers: List of worker objects
                - count: Number of workers
                - error: Optional error message

        Example:
            >>> service = CloudflareWorkerService(account_id, token)
            >>> result = service.list_workers()
            >>> print(f"Found {result['count']} workers")
        """
        url = self.workers_url

        headers = {
            "Authorization": f"Bearer {self.api_token}"
        }

        try:
            print(f"[CloudflareWorker] Listing workers")

            response = requests.get(
                url,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    workers = result.get('result', [])

                    print(f"[CloudflareWorker] Listed {len(workers)} workers")
                    return {
                        "success": True,
                        "workers": workers,
                        "count": len(workers),
                        "error": None
                    }
                else:
                    error_msg = result.get('errors', [{}])[0].get('message', 'Unknown error')
                    print(f"[CloudflareWorker] List workers failed: {error_msg}")
                    return {
                        "success": False,
                        "workers": [],
                        "count": 0,
                        "error": error_msg
                    }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                print(f"[CloudflareWorker] List workers failed: {error_msg}")
                return {
                    "success": False,
                    "workers": [],
                    "count": 0,
                    "error": error_msg
                }

        except Exception as e:
            error_msg = f"Exception during list workers: {str(e)}"
            print(f"[CloudflareWorker] Error listing workers: {error_msg}")
            return {
                "success": False,
                "workers": [],
                "count": 0,
                "error": error_msg
            }

    def add_route(self, pattern: str, script_name: str) -> Dict:
        """
        Add a route to connect worker to zone.

        Args:
            pattern: Route pattern (e.g., "example.com/*")
            script_name: Name of the worker script

        Returns:
            Dictionary containing:
                - success: bool
                - route_id: Optional route ID
                - pattern: Route pattern
                - error: Optional error message

        Example:
            >>> service = CloudflareWorkerService(account_id, token, zone_id)
            >>> result = service.add_route("example.com/*", "my-worker")
            >>> print(result['success'])
        """
        if not self.zone_id:
            return {
                "success": False,
                "route_id": None,
                "pattern": pattern,
                "error": "Zone ID not configured"
            }

        url = self.routes_url

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "pattern": pattern,
            "script": script_name
        }

        try:
            print(f"[CloudflareWorker] Adding route: {pattern} -> {script_name}")

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    route_data = result.get('result', {})
                    route_id = route_data.get('id')

                    print(f"[CloudflareWorker] Successfully added route: {pattern}")
                    return {
                        "success": True,
                        "route_id": route_id,
                        "pattern": pattern,
                        "error": None
                    }
                else:
                    error_msg = result.get('errors', [{}])[0].get('message', 'Unknown error')
                    print(f"[CloudflareWorker] Add route failed: {error_msg}")
                    return {
                        "success": False,
                        "route_id": None,
                        "pattern": pattern,
                        "error": error_msg
                    }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                print(f"[CloudflareWorker] Add route failed: {error_msg}")
                return {
                    "success": False,
                    "route_id": None,
                    "pattern": pattern,
                    "error": error_msg
                }

        except Exception as e:
            error_msg = f"Exception during add route: {str(e)}"
            print(f"[CloudflareWorker] Error adding route: {error_msg}")
            return {
                "success": False,
                "route_id": None,
                "pattern": pattern,
                "error": error_msg
            }

    def list_routes(self) -> Dict:
        """
        List all routes in the zone.

        Returns:
            Dictionary containing:
                - success: bool
                - routes: List of route objects
                - count: Number of routes
                - error: Optional error message

        Example:
            >>> service = CloudflareWorkerService(account_id, token, zone_id)
            >>> result = service.list_routes()
            >>> print(f"Found {result['count']} routes")
        """
        if not self.zone_id:
            return {
                "success": False,
                "routes": [],
                "count": 0,
                "error": "Zone ID not configured"
            }

        url = self.routes_url

        headers = {
            "Authorization": f"Bearer {self.api_token}"
        }

        try:
            print(f"[CloudflareWorker] Listing routes")

            response = requests.get(
                url,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    routes = result.get('result', [])

                    print(f"[CloudflareWorker] Listed {len(routes)} routes")
                    return {
                        "success": True,
                        "routes": routes,
                        "count": len(routes),
                        "error": None
                    }
                else:
                    error_msg = result.get('errors', [{}])[0].get('message', 'Unknown error')
                    print(f"[CloudflareWorker] List routes failed: {error_msg}")
                    return {
                        "success": False,
                        "routes": [],
                        "count": 0,
                        "error": error_msg
                    }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                print(f"[CloudflareWorker] List routes failed: {error_msg}")
                return {
                    "success": False,
                    "routes": [],
                    "count": 0,
                    "error": error_msg
                }

        except Exception as e:
            error_msg = f"Exception during list routes: {str(e)}"
            print(f"[CloudflareWorker] Error listing routes: {error_msg}")
            return {
                "success": False,
                "routes": [],
                "count": 0,
                "error": error_msg
            }

    def delete_route(self, route_id: str) -> Dict:
        """
        Delete a route.

        Args:
            route_id: Route ID to delete

        Returns:
            Dictionary containing:
                - success: bool
                - route_id: str
                - error: Optional error message

        Example:
            >>> service = CloudflareWorkerService(account_id, token, zone_id)
            >>> result = service.delete_route("route123")
            >>> print(result['success'])
        """
        if not self.zone_id:
            return {
                "success": False,
                "route_id": route_id,
                "error": "Zone ID not configured"
            }

        url = f"{self.routes_url}/{route_id}"

        headers = {
            "Authorization": f"Bearer {self.api_token}"
        }

        try:
            print(f"[CloudflareWorker] Deleting route: {route_id}")

            response = requests.delete(
                url,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print(f"[CloudflareWorker] Successfully deleted route: {route_id}")
                    return {
                        "success": True,
                        "route_id": route_id,
                        "error": None
                    }
                else:
                    error_msg = result.get('errors', [{}])[0].get('message', 'Unknown error')
                    print(f"[CloudflareWorker] Delete route failed: {error_msg}")
                    return {
                        "success": False,
                        "route_id": route_id,
                        "error": error_msg
                    }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                print(f"[CloudflareWorker] Delete route failed: {error_msg}")
                return {
                    "success": False,
                    "route_id": route_id,
                    "error": error_msg
                }

        except Exception as e:
            error_msg = f"Exception during delete route: {str(e)}"
            print(f"[CloudflareWorker] Error deleting route: {error_msg}")
            return {
                "success": False,
                "route_id": route_id,
                "error": error_msg
            }

    @classmethod
    def from_client(cls, client) -> Optional["CloudflareWorkerService"]:
        """
        Factory method to create service from Client model.

        Args:
            client: Client model instance

        Returns:
            CloudflareWorkerService instance or None if credentials missing

        Example:
            >>> from app.models.client import Client
            >>> client = db.query(Client).first()
            >>> service = CloudflareWorkerService.from_client(client)
            >>> if service:
            ...     service.deploy_worker(...)
        """
        if not all([
            client.cloudflare_account_id,
            client.cloudflare_api_token
        ]):
            return None

        return cls(
            account_id=client.cloudflare_account_id,
            api_token=client.cloudflare_api_token,
            zone_id=getattr(client, 'cloudflare_zone_id', None)
        )
