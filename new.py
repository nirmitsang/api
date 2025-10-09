Perfect! All clear. Let me start building the clean code from scratch.

---

## PROJECT STRUCTURE

```
api-migration-test-utility/
├── .env
├── .gitignore
├── requirements.txt
├── run_test.py
├── configs/
│   ├── test-sample.json
│   └── mapping-sample.json
├── src/
│   ├── __init__.py
│   ├── config_loader.py
│   ├── mongo_client.py
│   ├── token_manager.py
│   ├── api_client.py
│   ├── response_parser.py
│   ├── comparator.py
│   ├── coverage_tracker.py
│   ├── reporter.py
│   ├── utils.py
│   ├── logger.py
│   └── main.py
└── output/
```

---

## FILE 1: .env

Create this file in root directory:

```env
# MongoDB Credentials
MONGO_USERNAME=your_username
MONGO_PASSWORD=your_password
```

---

## FILE 2: .gitignore

```
# Environment variables
.env

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/

# Output files
output/*.csv
output/*.json
output/*.txt

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
```

---

## FILE 3: requirements.txt

```
pymongo==4.6.0
requests==2.31.0
python-dotenv==1.0.0
deepdiff==6.7.1
```

---

## FILE 4: src/logger.py

```python
"""
Logger Module
Provides colored console logging with debug levels
"""

import sys
from datetime import datetime
from typing import Optional


class Logger:
    """Simple colored logger with debug levels"""
    
    # ANSI color codes
    COLORS = {
        'RESET': '\033[0m',
        'RED': '\033[91m',
        'GREEN': '\033[92m',
        'YELLOW': '\033[93m',
        'BLUE': '\033[94m',
        'MAGENTA': '\033[95m',
        'CYAN': '\033[96m',
        'WHITE': '\033[97m',
        'BOLD': '\033[1m'
    }
    
    def __init__(self, debug_mode: bool = False):
        """
        Initialize logger
        
        Args:
            debug_mode: If True, show DEBUG level logs
        """
        self.debug_mode = debug_mode
    
    def _log(self, level: str, message: str, color: str):
        """Internal logging function"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        colored_level = f"{self.COLORS[color]}{level}{self.COLORS['RESET']}"
        print(f"[{timestamp}] {colored_level}: {message}")
    
    def debug(self, message: str):
        """Debug level - only shows if debug_mode is True"""
        if self.debug_mode:
            self._log('DEBUG', message, 'CYAN')
    
    def info(self, message: str):
        """Info level - always shows"""
        self._log('INFO', message, 'WHITE')
    
    def success(self, message: str):
        """Success level - always shows"""
        self._log('SUCCESS', message, 'GREEN')
    
    def warn(self, message: str):
        """Warning level - always shows"""
        self._log('WARN', message, 'YELLOW')
    
    def error(self, message: str):
        """Error level - always shows"""
        self._log('ERROR', message, 'RED')
    
    def header(self, message: str):
        """Print header"""
        print(f"\n{self.COLORS['BOLD']}{self.COLORS['MAGENTA']}{'='*70}{self.COLORS['RESET']}")
        print(f"{self.COLORS['BOLD']}{self.COLORS['MAGENTA']}{message.center(70)}{self.COLORS['RESET']}")
        print(f"{self.COLORS['BOLD']}{self.COLORS['MAGENTA']}{'='*70}{self.COLORS['RESET']}\n")
    
    def separator(self, char: str = '=', length: int = 70):
        """Print separator line"""
        print(f"{self.COLORS['BLUE']}{char * length}{self.COLORS['RESET']}")


# Global logger instance (will be initialized in main)
logger: Optional[Logger] = None


def init_logger(debug_mode: bool = False):
    """Initialize global logger"""
    global logger
    logger = Logger(debug_mode)
    return logger
```

---

## FILE 5: src/utils.py

```python
"""
Utility Functions
Helper functions for nested value extraction
"""

from typing import Any, Optional


def get_nested_value(data: Any, path: str) -> Any:
    """
    Extract value from nested dictionary/list using dot notation
    
    Args:
        data: Dictionary or list to extract from
        path: Dot-separated path (e.g., "user.address.city" or "items.0.name")
    
    Returns:
        Extracted value or None if not found
    
    Examples:
        >>> data = {"user": {"name": "John", "age": 30}}
        >>> get_nested_value(data, "user.name")
        'John'
        
        >>> data = {"items": [{"name": "Item1"}, {"name": "Item2"}]}
        >>> get_nested_value(data, "items.0.name")
        'Item1'
    """
    if not data or not path:
        return None
    
    # Clean array notation [] from path
    path = path.replace('[]', '')
    
    parts = path.split('.')
    current = data
    
    for part in parts:
        if current is None:
            return None
        
        # Handle list access
        if isinstance(current, list):
            try:
                # If part is numeric, use as index
                if part.isdigit():
                    index = int(part)
                    if index < len(current):
                        current = current[index]
                    else:
                        return None
                else:
                    # Access first element if not numeric
                    if len(current) > 0:
                        current = current[0]
                        # Then access the key in that element
                        if isinstance(current, dict) and part in current:
                            current = current[part]
                        else:
                            return None
                    else:
                        return None
            except (ValueError, IndexError):
                return None
        
        # Handle dict access
        elif isinstance(current, dict):
            if part in current:
                current = current[part]
            else:
                return None
        else:
            # Can't navigate further
            return None
    
    return current


def flatten_dict(nested_dict: dict, parent_key: str = '', sep: str = '.') -> dict:
    """
    Flatten a nested dictionary
    
    Args:
        nested_dict: Nested dictionary to flatten
        parent_key: Parent key for recursion
        sep: Separator for keys
    
    Returns:
        Flattened dictionary
    
    Example:
        >>> d = {"a": {"b": 1, "c": 2}}
        >>> flatten_dict(d)
        {"a.b": 1, "a.c": 2}
    """
    items = []
    
    for key, value in nested_dict.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        
        if isinstance(value, dict):
            items.extend(flatten_dict(value, new_key, sep=sep).items())
        elif isinstance(value, list):
            # For lists, just use first element for now
            if len(value) > 0 and isinstance(value[0], dict):
                items.extend(flatten_dict(value[0], new_key, sep=sep).items())
            else:
                items.append((new_key, value))
        else:
            items.append((new_key, value))
    
    return dict(items)
```

---

## FILE 6: src/config_loader.py

```python
"""
Configuration Loader Module
Loads and processes configuration files with environment variable substitution
"""

import os
import json
import re
from typing import Dict, Any, List
from dotenv import load_dotenv
from .logger import logger


class ConfigLoader:
    """Loads configuration files and handles environment variables"""
    
    def __init__(self):
        """Initialize config loader"""
        # Load .env file
        load_dotenv()
        logger.debug("Environment variables loaded from .env file")
    
    def replace_env_variables(self, text: str) -> str:
        """
        Replace ${ENV_VAR} placeholders with actual environment values
        
        Args:
            text: Text containing ${ENV_VAR} placeholders
        
        Returns:
            Text with placeholders replaced
        """
        def replacer(match):
            env_var = match.group(1)
            value = os.getenv(env_var)
            
            if value is None:
                logger.warn(f"Environment variable {env_var} not found in .env file")
                return match.group(0)  # Return original if not found
            
            logger.debug(f"Replaced ${{{env_var}}} with value from .env")
            return value
        
        # Replace all ${VAR} patterns
        return re.sub(r'\$\{([^}]+)\}', replacer, text)
    
    def load_test_config(self, filepath: str) -> Dict[str, Any]:
        """
        Load test configuration file
        
        Args:
            filepath: Path to test config JSON file
        
        Returns:
            Configuration dictionary with env vars replaced
        """
        logger.debug(f"Loading test config from: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Replace environment variables
            content = self.replace_env_variables(content)
            
            # Parse JSON
            config = json.loads(content)
            
            logger.success(f"✓ Test config loaded successfully")
            logger.debug(f"  API Name: {config.get('apiName')}")
            logger.debug(f"  MongoDB Collection: {config.get('mongoCollection')}")
            logger.debug(f"  Test Payment IDs: {len(config.get('testPaymentIds', []))}")
            
            return config
            
        except FileNotFoundError:
            logger.error(f"Config file not found: {filepath}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error loading test config: {str(e)}")
            raise
    
    def load_mapping_config(self, filepath: str) -> List[Dict[str, str]]:
        """
        Load mapping configuration file
        
        Args:
            filepath: Path to mapping config JSON file
        
        Returns:
            List of mapping dictionaries
        """
        logger.debug(f"Loading mapping config from: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                mappings = json.load(f)
            
            logger.success(f"✓ Mapping config loaded successfully")
            logger.info(f"  Total field mappings: {len(mappings)}")
            
            # Count array fields
            array_fields = sum(1 for m in mappings if '[]' in m.get('mongoField', ''))
            if array_fields > 0:
                logger.debug(f"  Array fields: {array_fields}")
            
            return mappings
            
        except FileNotFoundError:
            logger.error(f"Mapping file not found: {filepath}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in mapping file: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error loading mapping config: {str(e)}")
            raise
    
    def build_json_to_mongo_map(self, mappings: List[Dict[str, str]]) -> Dict[str, str]:
        """
        Build reverse mapping: JSON attribute -> MongoDB field
        
        Args:
            mappings: List of mapping dictionaries
        
        Returns:
            Dictionary mapping JSON attributes to MongoDB fields
        """
        logger.debug("Building reverse mapping (JSON attr -> MongoDB field)...")
        
        reverse_map = {}
        
        for mapping in mappings:
            json_attr = mapping.get('jsonAttribute')
            mongo_field = mapping.get('mongoField')
            
            if json_attr and mongo_field:
                reverse_map[json_attr] = mongo_field
        
        logger.debug(f"✓ Reverse mapping built: {len(reverse_map)} attributes")
        
        return reverse_map


# Global config loader instance
config_loader = ConfigLoader()
```

---

This is the first batch of files. Should I continue with the remaining files?

**Next files to create:**
- mongo_client.py
- token_manager.py
- api_client.py
- response_parser.py
- comparator.py
- coverage_tracker.py
- reporter.py
- main.py
- run_test.py

Let me know if these first files look good, and I'll continue! 🚀









Great! Continuing with the next batch of files.

---

## FILE 7: src/mongo_client.py

```python
"""
MongoDB Client Module
Handles MongoDB connection and queries
"""

from typing import Dict, Any, Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from .logger import logger


class MongoDBClient:
    """MongoDB client for querying payment data"""
    
    def __init__(self, connection_string: str, database: str, collection: str):
        """
        Initialize MongoDB client
        
        Args:
            connection_string: MongoDB connection string (with credentials from .env)
            database: Database name
            collection: Collection name
        """
        self.connection_string = connection_string
        self.database_name = database
        self.collection_name = collection
        self.client: Optional[MongoClient] = None
        self.db = None
        self.collection = None
        
        logger.debug(f"MongoDB client initialized")
        logger.debug(f"  Database: {database}")
        logger.debug(f"  Collection: {collection}")
    
    def connect(self) -> bool:
        """
        Connect to MongoDB
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.debug("Connecting to MongoDB...")
            
            self.client = MongoClient(self.connection_string, serverSelectionTimeoutMS=5000)
            
            # Test connection
            self.client.admin.command('ping')
            
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]
            
            logger.success(f"✓ Connected to MongoDB - Database: {self.database_name}, Collection: {self.collection_name}")
            
            return True
            
        except ConnectionFailure as e:
            logger.error(f"MongoDB connection failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error connecting to MongoDB: {str(e)}")
            return False
    
    def find_by_payment_id(self, payment_id: str, payment_id_field: str) -> Dict[str, Any]:
        """
        Find document by payment ID
        
        Args:
            payment_id: Payment ID value
            payment_id_field: MongoDB field name for payment ID (from config)
        
        Returns:
            Dict with 'success' (bool), 'data' (dict or None), 'error' (str or None)
        """
        if self.collection is None:
            return {
                'success': False,
                'data': None,
                'error': 'Not connected to MongoDB'
            }
        
        try:
            logger.debug(f"Querying MongoDB: {payment_id_field} = {payment_id}")
            
            # Build query using config field name
            query = {payment_id_field: payment_id}
            
            # Execute query
            document = self.collection.find_one(query)
            
            if document:
                # Convert ObjectId to string if present
                if '_id' in document:
                    document['_id'] = str(document['_id'])
                
                logger.debug(f"✓ MongoDB record found ({len(document)} fields)")
                
                return {
                    'success': True,
                    'data': document,
                    'error': None
                }
            else:
                logger.warn(f"MongoDB record not found for {payment_id_field} = {payment_id}")
                return {
                    'success': False,
                    'data': None,
                    'error': f'No document found with {payment_id_field} = {payment_id}'
                }
            
        except OperationFailure as e:
            logger.error(f"MongoDB query failed: {str(e)}")
            return {
                'success': False,
                'data': None,
                'error': f'Query failed: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Error querying MongoDB: {str(e)}")
            return {
                'success': False,
                'data': None,
                'error': f'Error: {str(e)}'
            }
    
    def find_one_with_field(self, field_name: str, payment_id_field: str) -> Optional[str]:
        """
        Find ONE document that has the specified field with non-null value
        Used in Phase 2 to find payment IDs for uncovered attributes
        
        Args:
            field_name: MongoDB field name to search for
            payment_id_field: Payment ID field name to extract
        
        Returns:
            Payment ID if found, None otherwise
        """
        if self.collection is None:
            logger.error("Not connected to MongoDB")
            return None
        
        try:
            # Clean array notation from field name
            cleaned_field = field_name.replace('[]', '')
            
            logger.debug(f"Searching for document with field: {cleaned_field}")
            
            # Build query
            query = {
                cleaned_field: {
                    '$exists': True,
                    '$ne': None,
                    '$ne': ""
                }
            }
            
            # Project only payment ID field
            projection = {payment_id_field: 1, '_id': 0}
            
            # Execute query with limit 1
            document = self.collection.find_one(query, projection)
            
            if document and payment_id_field in document:
                payment_id = document[payment_id_field]
                logger.debug(f"  ✓ Found payment ID: {payment_id}")
                return payment_id
            else:
                logger.debug(f"  ✗ No document found with field {cleaned_field}")
                return None
            
        except Exception as e:
            logger.error(f"Error searching for field {field_name}: {str(e)}")
            return None
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.debug("MongoDB connection closed")
```

---

## FILE 8: src/token_manager.py

```python
"""
Token Manager Module
Handles authentication token retrieval
"""

import requests
from typing import Optional
from .logger import logger


class TokenManager:
    """Manages API authentication tokens"""
    
    def __init__(self, token_url: str):
        """
        Initialize token manager
        
        Args:
            token_url: URL to get authentication token
        """
        self.token_url = token_url
        self.token: Optional[str] = None
        
        logger.debug(f"Token manager initialized with URL: {token_url}")
    
    def get_token(self) -> Optional[str]:
        """
        Get bearer token from authentication endpoint
        Simple POST request with no credentials (as per your auth logic)
        
        Returns:
            Bearer token string or None if failed
        """
        try:
            logger.debug(f"Requesting authentication token from {self.token_url}")
            
            # Simple POST request (no username/password as specified)
            response = requests.post(
                self.token_url,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            
            # Extract token (adjust key name if needed)
            token = data.get('token') or data.get('access_token') or data.get('accessToken')
            
            if token:
                self.token = token
                logger.success("✓ Authentication token obtained successfully")
                logger.debug(f"  Token: {token[:20]}..." if len(token) > 20 else f"  Token: {token}")
                return token
            else:
                logger.error("Token not found in response")
                logger.debug(f"Response data: {data}")
                return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get authentication token: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error getting token: {str(e)}")
            return None
```

---

## FILE 9: src/api_client.py

```python
"""
API Client Module
Handles API calls to Java 8 and Java 21 endpoints
"""

import requests
from typing import Dict, Any, Optional
from .utils import get_nested_value
from .logger import logger


class APIClient:
    """Client for calling payment APIs"""
    
    def __init__(
        self,
        token: str,
        json_response_root_path: str,
        payment_id_attribute: str
    ):
        """
        Initialize API client
        
        Args:
            token: Bearer token for authentication
            json_response_root_path: Path to extract data from response (e.g., "data.payload")
            payment_id_attribute: Attribute name for payment ID in request (from config)
        """
        self.token = token
        self.root_path = json_response_root_path
        self.payment_id_attribute = payment_id_attribute
        
        logger.debug("API client initialized")
        logger.debug(f"  Root path: {json_response_root_path}")
        logger.debug(f"  Payment ID attribute: {payment_id_attribute}")
    
    def call_api(self, payment_id: str, url: str) -> Dict[str, Any]:
        """
        Call API endpoint
        
        Args:
            payment_id: Payment ID value
            url: API endpoint URL
        
        Returns:
            Dict with 'success' (bool), 'data' (dict or None), 'error' (str or None)
        """
        try:
            # Build request body using config attribute name
            request_body = {
                self.payment_id_attribute: payment_id
            }
            
            logger.debug(f"Calling API: {url}")
            logger.debug(f"  Request body: {request_body}")
            
            # Make POST request
            response = requests.post(
                url,
                json=request_body,
                headers={
                    'Authorization': f'Bearer {self.token}',
                    'Content-Type': 'application/json'
                },
                timeout=30
            )
            
            # Check response status
            response.raise_for_status()
            
            # Parse JSON response
            full_response = response.json()
            
            logger.debug(f"✓ API responded with status {response.status_code}")
            
            # Extract data using root path
            if self.root_path:
                extracted_data = get_nested_value(full_response, self.root_path)
                
                if extracted_data:
                    logger.debug(f"  Extracted data from root path: {self.root_path}")
                else:
                    logger.warn(f"  Could not extract data from root path: {self.root_path}")
                    logger.debug(f"  Full response keys: {list(full_response.keys())}")
                    # Fall back to full response
                    extracted_data = full_response
            else:
                # No root path, use full response
                extracted_data = full_response
            
            return {
                'success': True,
                'data': extracted_data,
                'error': None
            }
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"API returned error status: {e}")
            logger.debug(f"  Response: {e.response.text if e.response else 'No response'}")
            return {
                'success': False,
                'data': None,
                'error': f'HTTP {e.response.status_code}: {e.response.text if e.response else str(e)}'
            }
        except requests.exceptions.Timeout:
            logger.error("API request timed out")
            return {
                'success': False,
                'data': None,
                'error': 'Request timed out after 30 seconds'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            return {
                'success': False,
                'data': None,
                'error': f'Request failed: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Error calling API: {str(e)}")
            return {
                'success': False,
                'data': None,
                'error': f'Error: {str(e)}'
            }
```

---

## FILE 10: src/response_parser.py

```python
"""
Response Parser Module
Extracts all attributes from API response
"""

from typing import List, Any, Dict
from .logger import logger


class ResponseParser:
    """Parses API responses to extract all attribute paths"""
    
    def extract_all_attributes(self, response: Any, prefix: str = '') -> List[str]:
        """
        Recursively extract all attribute paths from response
        
        Args:
            response: API response (dict or list)
            prefix: Current path prefix for recursion
        
        Returns:
            List of all attribute paths in dot notation
        
        Example:
            Input: {"user": {"name": "John", "age": 30}, "items": [{"id": 1}]}
            Output: ["user.name", "user.age", "items.id"]
        """
        attributes = []
        
        if isinstance(response, dict):
            for key, value in response.items():
                current_path = f"{prefix}.{key}" if prefix else key
                
                if isinstance(value, dict):
                    # Recurse into nested dict
                    attributes.extend(self.extract_all_attributes(value, current_path))
                elif isinstance(value, list):
                    # Handle list - extract attributes from first element
                    if len(value) > 0 and isinstance(value[0], dict):
                        attributes.extend(self.extract_all_attributes(value[0], current_path))
                    else:
                        # List of primitives or empty list
                        attributes.append(current_path)
                else:
                    # Primitive value
                    attributes.append(current_path)
        
        elif isinstance(response, list):
            # Top-level list - extract from first element
            if len(response) > 0:
                attributes.extend(self.extract_all_attributes(response[0], prefix))
        
        return attributes
    
    def extract_attributes_with_values(self, response: Any, prefix: str = '') -> Dict[str, Any]:
        """
        Extract all attributes with their values (for debugging)
        
        Args:
            response: API response
            prefix: Current path prefix
        
        Returns:
            Dict mapping attribute paths to values
        """
        result = {}
        
        if isinstance(response, dict):
            for key, value in response.items():
                current_path = f"{prefix}.{key}" if prefix else key
                
                if isinstance(value, dict):
                    result.update(self.extract_attributes_with_values(value, current_path))
                elif isinstance(value, list):
                    if len(value) > 0 and isinstance(value[0], dict):
                        result.update(self.extract_attributes_with_values(value[0], current_path))
                    else:
                        result[current_path] = value
                else:
                    result[current_path] = value
        
        return result
```

---

## FILE 11: src/comparator.py

```python
"""
Comparator Module
Compares values and performs JSON diff
"""

from typing import Dict, Any, Optional
from deepdiff import DeepDiff
from .logger import logger


class Comparator:
    """Compares MongoDB and API values"""
    
    def compare_values(
        self,
        mongo_value: Any,
        java21_value: Any,
        java8_value: Optional[Any] = None
    ) -> str:
        """
        Compare values with exact string matching
        
        Args:
            mongo_value: Value from MongoDB
            java21_value: Value from Java 21 API
            java8_value: Value from Java 8 API (optional)
        
        Returns:
            "PASS" if all values match exactly, "FAIL" otherwise
        """
        # Convert all values to strings for comparison
        mongo_str = str(mongo_value) if mongo_value is not None else ""
        java21_str = str(java21_value) if java21_value is not None else ""
        
        if java8_value is not None:
            # 3-way comparison
            java8_str = str(java8_value)
            
            if mongo_str == java21_str == java8_str:
                return "PASS"
            else:
                logger.debug(f"    Value mismatch: MongoDB='{mongo_str}', Java21='{java21_str}', Java8='{java8_str}'")
                return "FAIL"
        else:
            # 2-way comparison
            if mongo_str == java21_str:
                return "PASS"
            else:
                logger.debug(f"    Value mismatch: MongoDB='{mongo_str}', Java21='{java21_str}'")
                return "FAIL"
    
    def compare_json_diff(
        self,
        java8_response: Dict[str, Any],
        java21_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform deep JSON diff between Java 8 and Java 21 responses
        
        Args:
            java8_response: Java 8 API response
            java21_response: Java 21 API response
        
        Returns:
            Dict with 'status' ("PASS"/"FAIL"), and 'diff' (if failed)
        """
        try:
            logger.debug("Performing JSON diff (Java 8 vs Java 21)...")
            
            # Use deepdiff to find differences
            diff = DeepDiff(
                java8_response,
                java21_response,
                ignore_order=False,
                report_repetition=True
            )
            
            if diff:
                # Differences found
                logger.debug(f"  JSON diff: FAIL ({len(diff)} difference types)")
                
                # Convert diff to serializable format
                diff_dict = diff.to_dict()
                
                return {
                    'status': 'FAIL',
                    'diff': diff_dict
                }
            else:
                # No differences
                logger.debug("  JSON diff: PASS")
                
                return {
                    'status': 'PASS'
                }
            
        except Exception as e:
            logger.error(f"Error performing JSON diff: {str(e)}")
            return {
                'status': 'ERROR',
                'error': str(e)
            }
```

---

Should I continue with the remaining files? Next up:
- coverage_tracker.py
- reporter.py
- main.py
- run_test.py

Let me know! 🚀













Continuing with the final batch of files!

---

## FILE 12: src/coverage_tracker.py

```python
"""
Coverage Tracker Module
Tracks which attributes have been covered during testing
"""

from typing import List, Dict, Set
from .logger import logger


class CoverageTracker:
    """Tracks attribute coverage during testing"""
    
    def __init__(self, mapping_config: List[Dict[str, str]]):
        """
        Initialize coverage tracker
        
        Args:
            mapping_config: List of mapping dictionaries
        """
        self.mapping_config = mapping_config
        
        # Set of all attributes that need to be covered
        self.to_be_covered: Set[str] = set()
        for mapping in mapping_config:
            json_attr = mapping.get('jsonAttribute')
            if json_attr:
                self.to_be_covered.add(json_attr)
        
        # Set of attributes that have been covered (tested)
        self.covered_attributes: Set[str] = set()
        
        logger.debug(f"Coverage tracker initialized")
        logger.debug(f"  Total attributes to cover: {len(self.to_be_covered)}")
    
    def mark_covered(self, attribute: str):
        """
        Mark an attribute as covered
        
        Args:
            attribute: JSON attribute name
        """
        if attribute in self.to_be_covered:
            self.covered_attributes.add(attribute)
            logger.debug(f"  Marked as covered: {attribute}")
    
    def get_uncovered_attributes(self) -> List[str]:
        """
        Get list of attributes that haven't been covered yet
        
        Returns:
            List of uncovered attribute names
        """
        uncovered = self.to_be_covered - self.covered_attributes
        return list(uncovered)
    
    def get_uncovered_mappings(self) -> List[Dict[str, str]]:
        """
        Get full mapping objects for uncovered attributes
        
        Returns:
            List of mapping dictionaries for uncovered attributes
        """
        uncovered_attrs = self.get_uncovered_attributes()
        
        uncovered_mappings = []
        for mapping in self.mapping_config:
            if mapping.get('jsonAttribute') in uncovered_attrs:
                uncovered_mappings.append(mapping)
        
        return uncovered_mappings
    
    def get_coverage_summary(self) -> Dict[str, any]:
        """
        Get coverage statistics
        
        Returns:
            Dictionary with coverage stats
        """
        total = len(self.to_be_covered)
        covered = len(self.covered_attributes)
        uncovered = total - covered
        percentage = (covered / total * 100) if total > 0 else 0
        
        return {
            'total_attributes': total,
            'covered_count': covered,
            'uncovered_count': uncovered,
            'coverage_percentage': percentage
        }
    
    def print_coverage_summary(self):
        """Print coverage summary to console"""
        summary = self.get_coverage_summary()
        
        logger.info(f"\n📊 Coverage Summary:")
        logger.info(f"  Total attributes: {summary['total_attributes']}")
        logger.success(f"  ✓ Covered: {summary['covered_count']} ({summary['coverage_percentage']:.1f}%)")
        
        if summary['uncovered_count'] > 0:
            logger.warn(f"  ⚠ Uncovered: {summary['uncovered_count']} ({100 - summary['coverage_percentage']:.1f}%)")
```

---

## FILE 13: src/reporter.py

```python
"""
Reporter Module
Generates Excel and JSON diff reports
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any
from .logger import logger


class Reporter:
    """Generates test reports"""
    
    def __init__(self, output_dir: str = "output"):
        """
        Initialize reporter
        
        Args:
            output_dir: Directory to save reports
        """
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        logger.debug(f"Reporter initialized with output dir: {output_dir}")
    
    def generate_excel_report(
        self,
        api_name: str,
        attribute_results: List[Dict[str, Any]],
        uncovered_attributes: List[Dict[str, str]]
    ) -> str:
        """
        Generate Excel report (CSV format) with all attribute test results
        
        Args:
            api_name: API name for filename
            attribute_results: List of tested attribute results
            uncovered_attributes: List of uncovered attributes
        
        Returns:
            Path to generated CSV file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{api_name}_attribute_report_{timestamp}.csv"
        filepath = os.path.join(self.output_dir, filename)
        
        logger.info(f"Generating Excel report...")
        logger.debug(f"  Tested attributes: {len(attribute_results)}")
        logger.debug(f"  Uncovered attributes: {len(uncovered_attributes)}")
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                # Write header
                f.write("Payment ID,Attribute Name,MongoDB Field,MongoDB Value,Java 21 Value,Java 8 Value,Status\n")
                
                # Write tested attributes
                for result in attribute_results:
                    payment_id = result.get('paymentId', '')
                    attribute = result.get('attributeName', '')
                    mongo_field = result.get('mongoField', '')
                    mongo_value = self._escape_csv(str(result.get('mongoValue', '')))
                    java21_value = self._escape_csv(str(result.get('java21Value', '')))
                    java8_value = self._escape_csv(str(result.get('java8Value', '')))
                    status = result.get('status', 'UNKNOWN')
                    
                    f.write(f"{payment_id},{attribute},{mongo_field},{mongo_value},{java21_value},{java8_value},{status}\n")
                
                # Write uncovered attributes
                for uncovered in uncovered_attributes:
                    attribute = uncovered.get('attributeName', '')
                    mongo_field = uncovered.get('mongoField', '')
                    
                    # Payment ID blank, attribute name, mongo field, blank values, UNCOVERED status
                    f.write(f",{attribute},{mongo_field},,,UNCOVERED\n")
            
            logger.success(f"✓ Excel report generated: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to generate Excel report: {str(e)}")
            raise
    
    def generate_json_diff_report(
        self,
        api_name: str,
        json_diff_results: List[Dict[str, Any]]
    ) -> str:
        """
        Generate JSON diff report (only when Java 8 exists)
        
        Args:
            api_name: API name for filename
            json_diff_results: List of JSON diff results per payment ID
        
        Returns:
            Path to generated JSON file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{api_name}_json_diff_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        logger.info(f"Generating JSON diff report...")
        logger.debug(f"  Payment IDs tested: {len(json_diff_results)}")
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(json_diff_results, f, indent=2, default=str)
            
            logger.success(f"✓ JSON diff report generated: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to generate JSON diff report: {str(e)}")
            raise
    
    def _escape_csv(self, value: str) -> str:
        """
        Escape CSV value - wrap in quotes if contains comma, newline, or quotes
        
        Args:
            value: String value
        
        Returns:
            Escaped value
        """
        if ',' in value or '\n' in value or '"' in value:
            # Escape quotes by doubling them
            value = value.replace('"', '""')
            return f'"{value}"'
        return value
```

---

## FILE 14: src/main.py

```python
"""
Main Orchestrator Module
Coordinates the entire test workflow
"""

import time
from typing import List, Dict, Any, Set
from .config_loader import config_loader
from .mongo_client import MongoDBClient
from .token_manager import TokenManager
from .api_client import APIClient
from .response_parser import ResponseParser
from .comparator import Comparator
from .coverage_tracker import CoverageTracker
from .reporter import Reporter
from .utils import get_nested_value
from .logger import logger


class TestOrchestrator:
    """Main orchestrator for API migration testing"""
    
    def __init__(self):
        """Initialize the test orchestrator"""
        self.test_config = None
        self.mapping_config = None
        self.json_to_mongo_map = None
        
        # Components
        self.mongo_client = None
        self.token_manager = None
        self.api_client = None
        self.response_parser = None
        self.comparator = None
        self.coverage_tracker = None
        self.reporter = None
        
        # Result collectors
        self.attribute_results = []
        self.json_diff_results = []
        self.tested_payment_ids = set()
        
        # Timing
        self.start_time = None
    
    def load_configurations(self) -> bool:
        """
        Load all configuration files
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Loading configurations...")
            
            # Load test config
            self.test_config = config_loader.load_test_config('configs/test-sample.json')
            
            # Load mapping config
            self.mapping_config = config_loader.load_mapping_config('configs/mapping-sample.json')
            
            # Build reverse mapping (JSON attribute -> MongoDB field)
            self.json_to_mongo_map = config_loader.build_json_to_mongo_map(self.mapping_config)
            
            logger.success("✓ All configurations loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load configurations: {str(e)}")
            return False
    
    def initialize_components(self) -> bool:
        """
        Initialize all components with config values
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("\nInitializing components...")
            
            # Extract config values
            mongo_conn = self.test_config['mongoConnectionString']
            mongo_db = self.test_config['mongoDatabase']
            mongo_coll = self.test_config['mongoCollection']
            token_url = self.test_config['tokenUrl']
            root_path = self.test_config.get('jsonResponseRootPath', '')
            payment_id_attr = self.test_config['paymentIdMapping']['jsonAttribute']
            
            # Initialize MongoDB client
            logger.info("  Initializing MongoDB client...")
            self.mongo_client = MongoDBClient(mongo_conn, mongo_db, mongo_coll)
            
            if not self.mongo_client.connect():
                logger.error("MongoDB connection failed")
                return False
            
            # Initialize token manager
            logger.info("  Initializing token manager...")
            self.token_manager = TokenManager(token_url)
            token = self.token_manager.get_token()
            
            if not token:
                logger.error("Failed to obtain authentication token")
                return False
            
            # Initialize API client
            logger.info("  Initializing API client...")
            self.api_client = APIClient(token, root_path, payment_id_attr)
            
            # Initialize other components
            logger.info("  Initializing other components...")
            self.response_parser = ResponseParser()
            self.comparator = Comparator()
            self.coverage_tracker = CoverageTracker(self.mapping_config)
            self.reporter = Reporter()
            
            logger.success("✓ All components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {str(e)}")
            return False
    
    def test_single_payment_id(self, payment_id: str) -> Dict[str, Any]:
        """
        Test a single payment ID - core testing logic
        
        Args:
            payment_id: Payment ID to test
        
        Returns:
            Dict with test results summary
        """
        result = {
            'paymentId': payment_id,
            'success': False,
            'tested_count': 0,
            'passed': 0,
            'failed': 0
        }
        
        try:
            payment_id_field = self.test_config['paymentIdMapping']['mongoField']
            java21_url = self.test_config['java21Url']
            java8_url = self.test_config.get('java8Url')
            
            # Step 1: Query MongoDB
            logger.debug(f"  Step 1: Querying MongoDB...")
            mongo_result = self.mongo_client.find_by_payment_id(payment_id, payment_id_field)
            
            if not mongo_result['success']:
                logger.error(f"  MongoDB query failed: {mongo_result.get('error')}")
                result['error'] = mongo_result.get('error')
                return result
            
            mongo_doc = mongo_result['data']
            
            # Step 2: Call Java 21 API
            logger.debug(f"  Step 2: Calling Java 21 API...")
            java21_result = self.api_client.call_api(payment_id, java21_url)
            
            if not java21_result['success']:
                logger.error(f"  Java 21 API call failed: {java21_result.get('error')}")
                result['error'] = java21_result.get('error')
                return result
            
            java21_response = java21_result['data']
            
            # Step 3: Call Java 8 API (if exists)
            java8_response = None
            has_java8 = java8_url is not None
            
            if has_java8:
                logger.debug(f"  Step 3: Calling Java 8 API...")
                java8_result = self.api_client.call_api(payment_id, java8_url)
                
                if java8_result['success']:
                    java8_response = java8_result['data']
                else:
                    logger.warn(f"  Java 8 API call failed: {java8_result.get('error')}")
            
            # Step 4: JSON Diff (only if Java 8 exists)
            if has_java8 and java8_response:
                logger.debug(f"  Step 4: Performing JSON diff...")
                diff_result = self.comparator.compare_json_diff(java8_response, java21_response)
                diff_result['paymentId'] = payment_id
                self.json_diff_results.append(diff_result)
            
            # Step 5: Parse API response to get all attributes
            logger.debug(f"  Step 5: Parsing API response attributes...")
            response_attributes = self.response_parser.extract_all_attributes(java21_response)
            
            logger.debug(f"    Found {len(response_attributes)} attributes in response")
            
            # Step 6: Compare each attribute
            logger.debug(f"  Step 6: Comparing attributes...")
            
            for attribute in response_attributes:
                # Look up MongoDB field for this attribute
                mongo_field = self.json_to_mongo_map.get(attribute)
                
                if not mongo_field:
                    # This attribute is not in our mapping config - skip it
                    logger.debug(f"    Skipping {attribute} (not in mapping)")
                    continue
                
                # Get values from all sources
                mongo_value = get_nested_value(mongo_doc, mongo_field.replace('[]', ''))
                java21_value = get_nested_value(java21_response, attribute)
                java8_value = get_nested_value(java8_response, attribute) if java8_response else None
                
                # Compare values
                status = self.comparator.compare_values(mongo_value, java21_value, java8_value)
                
                # Add to results
                attr_result = {
                    'paymentId': payment_id,
                    'attributeName': attribute,
                    'mongoField': mongo_field,
                    'mongoValue': mongo_value if mongo_value is not None else '',
                    'java21Value': java21_value if java21_value is not None else '',
                    'java8Value': java8_value if java8_value is not None else '',
                    'status': status
                }
                
                self.attribute_results.append(attr_result)
                
                # Update counters
                result['tested_count'] += 1
                if status == 'PASS':
                    result['passed'] += 1
                else:
                    result['failed'] += 1
                
                # Mark as covered
                self.coverage_tracker.mark_covered(attribute)
            
            result['success'] = True
            logger.debug(f"  ✓ Testing complete: {result['tested_count']} attributes tested, {result['passed']} passed, {result['failed']} failed")
            
            return result
            
        except Exception as e:
            logger.error(f"  Error testing payment ID: {str(e)}")
            result['error'] = str(e)
            return result
    
    def run_phase_1(self):
        """Execute Phase 1: Test configured payment IDs"""
        logger.header("PHASE 1: Testing Configured Payment IDs")
        
        test_payment_ids = self.test_config.get('testPaymentIds', [])
        
        if not test_payment_ids:
            logger.warn("No test payment IDs configured!")
            return
        
        logger.info(f"Testing {len(test_payment_ids)} configured payment IDs...\n")
        
        for idx, payment_id in enumerate(test_payment_ids, 1):
            logger.info(f"[{idx}/{len(test_payment_ids)}] Testing Payment ID: {payment_id}")
            logger.separator('-', 60)
            
            result = self.test_single_payment_id(payment_id)
            self.tested_payment_ids.add(payment_id)
            
            if result['success']:
                logger.success(f"✓ Completed: {result['tested_count']} attributes, {result['passed']} passed, {result['failed']} failed\n")
            else:
                logger.error(f"✗ Testing failed: {result.get('error')}\n")
        
        # Show Phase 1 coverage
        self.coverage_tracker.print_coverage_summary()
    
    def run_phase_2(self):
        """Execute Phase 2: Find and test uncovered attributes"""
        logger.header("PHASE 2: Finding Records for Uncovered Attributes")
        
        # Get uncovered attributes
        uncovered_mappings = self.coverage_tracker.get_uncovered_mappings()
        
        if not uncovered_mappings:
            logger.info("All attributes covered in Phase 1! Phase 2 not needed.")
            return
        
        logger.info(f"{len(uncovered_mappings)} attributes not yet covered")
        logger.info("Searching for payment IDs with these attributes...\n")
        
        # Find payment IDs for uncovered attributes
        payment_ids_to_test: Set[str] = set()
        payment_id_field = self.test_config['paymentIdMapping']['mongoField']
        
        logger.info("Querying MongoDB for uncovered attributes...")
        
        for idx, mapping in enumerate(uncovered_mappings, 1):
            mongo_field = mapping['mongoField']
            json_attr = mapping['jsonAttribute']
            
            logger.debug(f"[{idx}/{len(uncovered_mappings)}] {json_attr}")
            
            # Find payment ID with this field
            payment_id = self.mongo_client.find_one_with_field(mongo_field, payment_id_field)
            
            if payment_id:
                if payment_id not in payment_ids_to_test:
                    payment_ids_to_test.add(payment_id)
                    logger.debug(f"  → Added {payment_id} to test queue")
                else:
                    logger.debug(f"  → {payment_id} already in queue")
            else:
                logger.debug(f"  → No data found")
        
        logger.info(f"\n✓ Found {len(payment_ids_to_test)} unique payment IDs to test\n")
        
        if not payment_ids_to_test:
            logger.warn("No payment IDs found for uncovered attributes")
            return
        
        # Test each found payment ID
        logger.info("Testing found payment IDs...\n")
        
        for idx, payment_id in enumerate(payment_ids_to_test, 1):
            logger.info(f"[{idx}/{len(payment_ids_to_test)}] Testing Payment ID: {payment_id}")
            logger.separator('-', 60)
            
            result = self.test_single_payment_id(payment_id)
            self.tested_payment_ids.add(payment_id)
            
            if result['success']:
                logger.success(f"✓ Completed: {result['tested_count']} attributes, {result['passed']} passed, {result['failed']} failed\n")
            else:
                logger.error(f"✗ Testing failed: {result.get('error')}\n")
        
        # Show final coverage
        self.coverage_tracker.print_coverage_summary()
    
    def generate_reports(self):
        """Generate all reports"""
        logger.header("GENERATING REPORTS")
        
        api_name = self.test_config.get('apiName', 'unknown')
        
        # Get uncovered attributes for report
        uncovered_mappings = self.coverage_tracker.get_uncovered_mappings()
        uncovered_attrs = [
            {
                'attributeName': m['jsonAttribute'],
                'mongoField': m['mongoField']
            }
            for m in uncovered_mappings
        ]
        
        try:
            # Generate Excel report
            excel_file = self.reporter.generate_excel_report(
                api_name=api_name,
                attribute_results=self.attribute_results,
                uncovered_attributes=uncovered_attrs
            )
            
            # Generate JSON diff report (only if Java 8 exists)
            if self.test_config.get('java8Url') and self.json_diff_results:
                json_diff_file = self.reporter.generate_json_diff_report(
                    api_name=api_name,
                    json_diff_results=self.json_diff_results
                )
            
            logger.success("\n✓ All reports generated successfully")
            
        except Exception as e:
            logger.error(f"Error generating reports: {str(e)}")
    
    def print_final_summary(self):
        """Print final test summary"""
        logger.header("TEST SUMMARY")
        
        # Calculate stats
        total_tested = len(self.attribute_results)
        total_passed = sum(1 for r in self.attribute_results if r['status'] == 'PASS')
        total_failed = sum(1 for r in self.attribute_results if r['status'] == 'FAIL')
        
        coverage = self.coverage_tracker.get_coverage_summary()
        
        logger.info(f"\nPayment IDs Tested: {len(self.tested_payment_ids)}")
        logger.info(f"\nAttribute Testing:")
        logger.info(f"  Total tests: {total_tested}")
        logger.success(f"  ✓ Passed: {total_passed} ({total_passed/total_tested*100:.1f}%)" if total_tested > 0 else "  ✓ Passed: 0")
        logger.error(f"  ✗ Failed: {total_failed} ({total_failed/total_tested*100:.1f}%)" if total_tested > 0 else "  ✗ Failed: 0")
        
        logger.info(f"\nCoverage:")
        logger.info(f"  Total attributes: {coverage['total_attributes']}")
        logger.success(f"  ✓ Covered: {coverage['covered_count']} ({coverage['coverage_percentage']:.1f}%)")
        logger.warn(f"  ⚠ Uncovered: {coverage['uncovered_count']} ({100-coverage['coverage_percentage']:.1f}%)")
        
        if self.json_diff_results:
            diff_passed = sum(1 for r in self.json_diff_results if r['status'] == 'PASS')
            diff_failed = len(self.json_diff_results) - diff_passed
            logger.info(f"\nJSON Diff (Java 8 vs Java 21):")
            logger.success(f"  ✓ Passed: {diff_passed}")
            if diff_failed > 0:
                logger.error(f"  ✗ Failed: {diff_failed}")
        
        execution_time = time.time() - self.start_time
        logger.info(f"\nTotal Execution Time: {execution_time:.2f} seconds")
        logger.separator()
    
    def run(self):
        """Main execution flow"""
        self.start_time = time.time()
        
        logger.header("API MIGRATION TEST UTILITY")
        logger.info(f"Started at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Load configurations
        if not self.load_configurations():
            logger.error("Failed to load configurations. Exiting.")
            return False
        
        # Initialize components
        if not self.initialize_components():
            logger.error("Failed to initialize components. Exiting.")
            return False
        
        # Run Phase 1
        logger.separator()
        self.run_phase_1()
        
        # Run Phase 2
        logger.separator()
        self.run_phase_2()
        
        # Generate reports
        logger.separator()
        self.generate_reports()
        
        # Print summary
        logger.separator()
        self.print_final_summary()
        
        # Cleanup
        if self.mongo_client:
            self.mongo_client.close()
        
        return True
```

---

## FILE 15: src/__init__.py

```python
"""
API Migration Test Utility Package
"""

from .logger import init_logger
from .main import TestOrchestrator

__version__ = '1.0.0'
__all__ = ['init_logger', 'TestOrchestrator']
```

---

## FILE 16: run_test.py

```python
"""
Entry Point
Run the API migration test utility
"""

import sys
import argparse
from src import init_logger, TestOrchestrator


def main():
    """Main entry point"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='API Migration Test Utility')
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode (verbose logging)'
    )
    
    args = parser.parse_args()
    
    # Initialize logger
    logger = init_logger(debug_mode=args.debug)
    
    # Create and run orchestrator
    orchestrator = TestOrchestrator()
    
    try:
        success = orchestrator.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.warn("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\nUnexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

## SETUP INSTRUCTIONS

### **1. Install Dependencies**

```bash
pip install -r requirements.txt
```

### **2. Configure .env File**

Edit `.env` and add your credentials:
```
MONGO_USERNAME=your_actual_username
MONGO_PASSWORD=your_actual_password
```

### **3. Configure test-sample.json**

Create/update `configs/test-sample.json` with your settings.

### **4. Run the Test**

**Normal mode:**
```bash
python run_test.py
```

**Debug mode (verbose):**
```bash
python run_test.py --debug
```

---

## ALL FILES COMPLETE! 🎉

The utility is now ready to use. Everything is:
- ✅ Config-driven (no hardcoding)
- ✅ Response-driven testing
- ✅ Phase 1 + Phase 2 logic
- ✅ Excel + JSON diff reports
- ✅ Detailed debugging
- ✅ .env for sensitive data

Try running it and let me know if you encounter any issues! 🚀
