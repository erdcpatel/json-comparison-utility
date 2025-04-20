import requests
import json
from typing import Dict, Any, Optional


class APIHandler:
    @staticmethod
    def fetch_json(url: str,
                   method: str = 'GET',
                   headers: Optional[Dict] = None,
                   body: Optional[Dict] = None,
                   params: Optional[Dict] = None,
                   timeout: int = 10) -> Optional[Dict]:
        """
        Fetch JSON data from an API endpoint with support for GET/POST methods

        Args:
            url: API endpoint URL
            method: HTTP method (GET or POST)
            headers: Request headers
            body: Request body for POST requests
            params: Query parameters for GET requests
            timeout: Request timeout in seconds

        Returns:
            Parsed JSON data or None if request fails
        """
        try:
            if method.upper() == 'GET':
                response = requests.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=timeout
                )
            elif method.upper() == 'POST':
                response = requests.post(
                    url,
                    headers=headers,
                    json=body,
                    timeout=timeout
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")
        except json.JSONDecodeError:
            raise Exception("Invalid JSON response from API")
        except Exception as e:
            raise Exception(f"Error fetching data: {str(e)}")