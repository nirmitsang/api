requirements.txt

pymongo==4.6.0
requests==2.31.0
python-dotenv==1.0.0


logger.py

"""
Logger Module
Handles console logging with different levels and colors
"""

from datetime import datetime
from typing import List


class Logger:
    """Logger class for console output with colors and timestamps"""
    
    # ANSI color codes
    COLORS = {
        'GREEN': '\033[92m',
        'YELLOW': '\033[93m',
        'RED': '\033[91m',
        'CYAN': '\033[96m',
        'RESET': '\033[0m',
        'BOLD': '\033[1m'
    }
    
    def __init__(self):
        """Initialize logger with empty log storage"""
        self.logs: List[str] = []
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in readable format"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def _log(self, level: str, message: str, color: str = ''):
        """Internal method to log with timestamp and color"""
        timestamp = self._get_timestamp()
        log_entry = f"[{timestamp}] {level}: {message}"
        
        if color:
            print(f"{color}{log_entry}{self.COLORS['RESET']}")
        else:
            print(log_entry)
        
        self.logs.append(log_entry)
    
    def info(self, message: str):
        """Log INFO level message"""
        self._log('INFO', message, self.COLORS['GREEN'])
    
    def debug(self, message: str):
        """Log DEBUG level message"""
        self._log('DEBUG', message, self.COLORS['CYAN'])
    
    def warn(self, message: str):
        """Log WARN level message"""
        self._log('WARN', message, self.COLORS['YELLOW'])
    
    def error(self, message: str):
        """Log ERROR level message"""
        self._log('ERROR', message, self.COLORS['RED'])
    
    def success(self, message: str):
        """Log success message with checkmark"""
        timestamp = self._get_timestamp()
        log_entry = f"[{timestamp}] SUCCESS: {message}"
        print(f"{self.COLORS['GREEN']}✓ {message}{self.COLORS['RESET']}")
        self.logs.append(log_entry)
    
    def separator(self, char='━', length=60):
        """Print a separator line"""
        print(char * length)
    
    def header(self, message: str):
        """Print a bold header"""
        self.separator()
        print(f"{self.COLORS['BOLD']}{message}{self.COLORS['RESET']}")
        self.separator()
    
    def get_all_logs(self) -> List[str]:
        """Return all logged messages"""
        return self.logs
    
    def clear_logs(self):
        """Clear all stored logs"""
        self.logs = []


# Create a global logger instance
logger = Logger()


utils.py

"""
Utils Module
Helper functions used across the utility
"""

from typing import Any, Dict
from urllib.parse import urlparse


def get_nested_value(obj: Dict[str, Any], path: str) -> Any:
    """
    Get value from nested dictionary using dot notation
    
    Args:
        obj: Dictionary to extract value from
        path: Dot-separated path (e.g., "user.address.city")
    
    Returns:
        Value at the path, or None if not found
    
    Examples:
        >>> data = {"user": {"address": {"city": "New York"}}}
        >>> get_nested_value(data, "user.address.city")
        'New York'
    """
    if not obj or not path:
        return None
    
    parts = path.split('.')
    current = obj
    
    for part in parts:
        if current is None:
            return None
        
        # Regular nested access
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    
    return current


def is_valid_url(url: str) -> bool:
    """
    Check if a string is a valid URL
    
    Args:
        url: String to validate
    
    Returns:
        True if valid URL, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def deep_equal(obj1: Any, obj2: Any) -> bool:
    """
    Deep equality check for any objects (handles nested dicts, lists)
    
    Args:
        obj1: First object
        obj2: Second object
    
    Returns:
        True if objects are deeply equal
    """
    import json
    try:
        return json.dumps(obj1, sort_keys=True, default=str) == json.dumps(obj2, sort_keys=True, default=str)
    except:
        return obj1 == obj2


def is_numeric_string(value: Any) -> bool:
    """
    Check if a value is a numeric string
    
    Args:
        value: Value to check
    
    Returns:
        True if value is a string that represents a number
    """
    if not isinstance(value, str):
        return False
    
    try:
        float(value)
        return True
    except ValueError:
        return False


def safe_float_compare(val1: Any, val2: Any, tolerance: float = 0.0000001) -> bool:
    """
    Compare two values as floats with tolerance for floating point errors
    
    Args:
        val1: First value
        val2: Second value
        tolerance: Acceptable difference
    
    Returns:
        True if values are equal within tolerance
    """
    try:
        num1 = float(val1)
        num2 = float(val2)
        return abs(num1 - num2) < tolerance
    except (ValueError, TypeError):
        return False


def format_duration(milliseconds: float) -> str:
    """
    Format duration in milliseconds to human-readable format
    
    Args:
        milliseconds: Duration in milliseconds
    
    Returns:
        Formatted string (e.g., "2.5s", "120ms")
    """
    if milliseconds < 1000:
        return f"{milliseconds:.0f}ms"
    else:
        seconds = milliseconds / 1000
        return f"{seconds:.1f}s"



config_loader.py


"""
Config Loader Module
Loads configuration from JSON files and environment variables
"""

import json
import os
from typing import Dict, List, Any
from dotenv import load_dotenv


class ConfigLoader:
    """Handles loading of mapping and test configurations"""
    
    def __init__(self):
        """Initialize config loader and load environment variables"""
        # Load environment variables from .env file
        load_dotenv()
        self.env_loaded = True
    
    def load_mapping_config(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Load mapping configuration from JSON file
        
        Format: [
            {
                "mongoField": "payment_id",
                "mongoType": "String",
                "jsonAttribute": "actualData.paymentInfo.paymentId"
            },
            ...
        ]
        
        Args:
            file_path: Path to mapping JSON file
        
        Returns:
            List of mapping dictionaries
        
        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file is not valid JSON
            ValueError: If required fields are missing
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Mapping config file not found: {file_path}")
        
        with open(file_path, 'r') as f:
            mapping_config = json.load(f)
        
        # Validate structure
        if not isinstance(mapping_config, list):
            raise ValueError("Mapping config must be a list of field mappings")
        
        # Validate each mapping has required fields
        required_fields = ['mongoField', 'mongoType', 'jsonAttribute']
        for idx, mapping in enumerate(mapping_config):
            for field in required_fields:
                if field not in mapping:
                    raise ValueError(f"Mapping entry {idx} missing required field: {field}")
        
        return mapping_config
    
    def load_test_config(self, file_path: str) -> Dict[str, Any]:
        """
        Load test configuration from JSON file and merge with environment variables
        
        JSON Format: {
            "apiName": "getUserPaymentData",
            "paymentIdMapping": {
                "mongoField": "payment_id",
                "jsonAttribute": "paymentId"
            },
            "testPaymentIds": ["PAY001", "PAY002"]
        }
        
        Environment variables override JSON values for sensitive data:
        - MONGO_CONNECTION_STRING
        - MONGO_DATABASE
        - MONGO_COLLECTION
        - JAVA21_API_URL
        - JAVA8_API_URL (optional)
        - TOKEN_API_URL
        
        Args:
            file_path: Path to test config JSON file
        
        Returns:
            Dictionary with test configuration
        
        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file is not valid JSON
            ValueError: If required fields are missing
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Test config file not found: {file_path}")
        
        with open(file_path, 'r') as f:
            test_config = json.load(f)
        
        # Merge with environment variables (env vars take priority for sensitive data)
        if os.getenv('MONGO_CONNECTION_STRING'):
            test_config['mongoConnectionString'] = os.getenv('MONGO_CONNECTION_STRING')
        
        if os.getenv('MONGO_DATABASE'):
            test_config['mongoDatabase'] = os.getenv('MONGO_DATABASE')
        
        if os.getenv('MONGO_COLLECTION'):
            test_config['mongoCollection'] = os.getenv('MONGO_COLLECTION')
        
        if os.getenv('JAVA21_API_URL'):
            test_config['java21ApiUrl'] = os.getenv('JAVA21_API_URL')
        
        if os.getenv('JAVA8_API_URL'):
            test_config['java8ApiUrl'] = os.getenv('JAVA8_API_URL')
        
        if os.getenv('TOKEN_API_URL'):
            test_config['tokenApiUrl'] = os.getenv('TOKEN_API_URL')
        
        # Validate required fields
        required_fields = [
            'apiName',
            'paymentIdMapping',
            'testPaymentIds',
            'mongoConnectionString',
            'mongoDatabase',
            'mongoCollection',
            'java21ApiUrl',
            'tokenApiUrl'
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in test_config or not test_config[field]:
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"Test config missing required fields: {', '.join(missing_fields)}")
        
        # Validate paymentIdMapping structure
        if 'mongoField' not in test_config['paymentIdMapping']:
            raise ValueError("paymentIdMapping must have 'mongoField'")
        if 'jsonAttribute' not in test_config['paymentIdMapping']:
            raise ValueError("paymentIdMapping must have 'jsonAttribute'")
        
        # Validate testPaymentIds
        if not isinstance(test_config['testPaymentIds'], list):
            raise ValueError("testPaymentIds must be a list")
        if len(test_config['testPaymentIds']) == 0:
            raise ValueError("testPaymentIds list cannot be empty")
        
        return test_config
    
    def get_masked_connection_string(self, connection_string: str) -> str:
        """
        Mask sensitive parts of connection string for safe logging
        
        Args:
            connection_string: MongoDB connection string
        
        Returns:
            Masked connection string
        """
        if not connection_string:
            return "Not configured"
        
        try:
            if '@' in connection_string:
                parts = connection_string.split('@')
                protocol_and_creds = parts[0]
                rest = '@'.join(parts[1:])
                
                if '://' in protocol_and_creds:
                    protocol = protocol_and_creds.split('://')[0]
                    return f"{protocol}://****:****@{rest}"
            
            return connection_string
        except:
            return "****"


# Create a global config loader instance
config_loader = ConfigLoader()


mapping-sample.json


[
  {
    "mongoField": "payment_id",
    "mongoType": "String",
    "jsonAttribute": "actualData.paymentInfo.paymentId"
  },
  {
    "mongoField": "user.name",
    "mongoType": "String",
    "jsonAttribute": "actualData.userData.userName"
  },
  {
    "mongoField": "user.email",
    "mongoType": "String",
    "jsonAttribute": "actualData.userData.userEmail"
  },
  {
    "mongoField": "amount",
    "mongoType": "Decimal128",
    "jsonAttribute": "actualData.paymentInfo.amount"
  },
  {
    "mongoField": "status",
    "mongoType": "String",
    "jsonAttribute": "actualData.paymentInfo.status"
  },
  {
    "mongoField": "items",
    "mongoType": "Array",
    "jsonAttribute": "actualData.orderItems"
  },
  {
    "mongoField": "created_date",
    "mongoType": "Date",
    "jsonAttribute": "actualData.paymentInfo.createdDate"
  }
]



test_config_loader.py


"""
Test script for Config Loader module
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config_loader import ConfigLoader


def test_config_loader():
    """Test config loader functionality"""
    
    print("\n" + "="*60)
    print("TESTING CONFIG LOADER MODULE")
    print("="*60 + "\n")
    
    loader = ConfigLoader()
    
    # Test 1: Load mapping config
    print("Test 1: Load Mapping Config")
    try:
        mapping_config = loader.load_mapping_config('configs/mapping-sample.json')
        print(f"  ✓ PASS: Loaded {len(mapping_config)} field mappings")
        
        # Show first mapping
        if len(mapping_config) > 0:
            first_mapping = mapping_config[0]
            print(f"  First mapping:")
            print(f"    MongoDB Field: {first_mapping.get('mongoField')}")
            print(f"    MongoDB Type: {first_mapping.get('mongoType')}")
            print(f"    JSON Attribute: {first_mapping.get('jsonAttribute')}")
    except Exception as e:
        print(f"  ✗ FAIL: {str(e)}")
    
    # Test 2: Load test config
    print("\nTest 2: Load Test Config")
    print("  NOTE: This will use environment variables from .env file")
    print("  If .env doesn't exist, some fields may be missing\n")
    
    try:
        test_config = loader.load_test_config('configs/test-sample.json')
        print(f"  ✓ PASS: Test config loaded")
        print(f"  API Name: {test_config.get('apiName')}")
        print(f"  Test Payment IDs: {test_config.get('testPaymentIds')}")
        print(f"  Payment ID Mapping: {test_config.get('paymentIdMapping')}")
        
        # Show MongoDB connection (masked)
        if 'mongoConnectionString' in test_config:
            masked = loader.get_masked_connection_string(test_config['mongoConnectionString'])
            print(f"  MongoDB Connection: {masked}")
        else:
            print(f"  MongoDB Connection: Not configured (add to .env)")
        
        # Show API URLs
        if 'java21ApiUrl' in test_config:
            print(f"  Java 21 API URL: {test_config['java21ApiUrl']}")
        else:
            print(f"  Java 21 API URL: Not configured (add to .env)")
        
        if 'java8ApiUrl' in test_config:
            print(f"  Java 8 API URL: {test_config['java8ApiUrl']}")
        else:
            print(f"  Java 8 API URL: Not configured (optional)")
        
    except ValueError as e:
        print(f"  ⚠ Expected Error (missing env vars): {str(e)}")
        print(f"  This is normal if .env file is not set up yet")
    except Exception as e:
        print(f"  ✗ FAIL: {str(e)}")
    
    # Test 3: Test connection string masking
    print("\nTest 3: Connection String Masking")
    test_strings = [
        "mongodb://user:password@host:27017/database",
        "mongodb://localhost:27017",
        ""
    ]
    
    for conn_str in test_strings:
        masked = loader.get_masked_connection_string(conn_str)
        print(f"  Original: {conn_str if conn_str else '(empty)'}")
        print(f"  Masked: {masked}")
        
        # Verify password is hidden
        if 'password' in conn_str and 'password' in masked:
            print(f"  ✗ FAIL: Password not masked!")
        elif 'password' in conn_str and 'password' not in masked:
            print(f"  ✓ PASS: Password masked correctly")
        print()
    
    print("="*60)
    print("CONFIG LOADER MODULE TEST COMPLETE")
    print("="*60 + "\n")
    
    print("IMPORTANT NOTES:")
    print("- Create a .env file with your credentials (see .env.example)")
    print("- Never commit .env file to git!")
    print("- The .gitignore file already excludes .env")
    print()


if __name__ == "__main__":
    test_config_loader()


# API Migration Test Utility - MVP

A generic, configurable test utility for validating API migrations from Java 8 to Java 21.

## Project Structure

```
api-migration-test-utility/
├── src/
│   ├── __init__.py
│   ├── logger.py           # Logging module
│   ├── utils.py            # Helper functions
│   └── config_loader.py    # Config loading with env vars
├── tests/
│   ├── test_logger.py
│   ├── test_utils.py
│   └── test_config_loader.py
├── configs/
│   ├── mapping-sample.json
│   └── test-sample.json
├── output/                 # Generated reports
├── .env.example           # Template for environment variables
├── .env                   # Your actual credentials (DO NOT COMMIT!)
├── .gitignore
├── requirements.txt
└── README.md
```

## Setup Instructions

### 1. Create Project Structure

```bash
mkdir -p api-migration-test-utility/src
mkdir -p api-migration-test-utility/tests
mkdir -p api-migration-test-utility/configs
mkdir -p api-migration-test-utility/output
cd api-migration-test-utility
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

**IMPORTANT: This is how you keep credentials safe!**

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your actual credentials
nano .env  # or use any text editor
```

Edit `.env` file with your real values:

```
# MongoDB Connection
MONGO_CONNECTION_STRING=mongodb://your_username:your_password@your_host:27017

# API URLs
JAVA21_API_URL=https://your-java21-api.com/endpoint
JAVA8_API_URL=https://your-java8-api.com/endpoint

# Token API
TOKEN_API_URL=https://your-token-api.com/token

# MongoDB Details
MONGO_DATABASE=your_database_name
MONGO_COLLECTION=your_collection_name
```

**NEVER commit the .env file!** It's already in `.gitignore`.

### 4. Create Empty __init__.py

```bash
touch src/__init__.py
```

### 5. Save All Code Files

Save the following files from the artifacts:
- `logger.py` → `src/logger.py`
- `utils.py` → `src/utils.py`
- `config_loader.py` → `src/config_loader.py`
- `test_logger.py` → `tests/test_logger.py`
- `test_utils.py` → `tests/test_utils.py`
- `test_config_loader.py` → `tests/test_config_loader.py`
- `mapping-sample.json` → `configs/mapping-sample.json`
- `test-sample.json` → `configs/test-sample.json`
- `.gitignore` → `.gitignore`
- `.env.example` → `.env.example`

## Running Tests

### Test Individual Modules

```bash
# Test logger module
python tests/test_logger.py

# Test utils module
python tests/test_utils.py

# Test config loader module
python tests/test_config_loader.py
```

### Expected Output

Each test should show:
- ✓ PASS for working features
- ✗ FAIL for any issues
- Colored output (green for success, red for errors)

## Configuration Files

### Mapping Config Format

`configs/mapping-sample.json`:
```json
[
  {
    "mongoField": "payment_id",
    "mongoType": "String",
    "jsonAttribute": "actualData.paymentInfo.paymentId"
  },
  ...
]
```

**Fields:**
- `mongoField`: Field name in MongoDB (supports dot notation for nested: `user.name`)
- `mongoType`: Data type in MongoDB (`String`, `Long`, `Decimal128`, `Array`, etc.)
- `jsonAttribute`: Attribute path in JSON response (supports dot notation: `actualData.userData.userName`)

### Test Config Format

`configs/test-sample.json`:
```json
{
  "apiName": "getUserPaymentData",
  "paymentIdMapping": {
    "mongoField": "payment_id",
    "jsonAttribute": "paymentId"
  },
  "testPaymentIds": ["PAY001", "PAY002", "PAY003"]
}
```

**Fields:**
- `apiName`: Name of the API being tested
- `paymentIdMapping`: How payment ID is named in MongoDB vs API
- `testPaymentIds`: List of payment IDs to test (known to have good data)

**Note:** Sensitive values (URLs, credentials) come from `.env` file, not this JSON!

## Security Best Practices

✅ **DO:**
- Keep credentials in `.env` file only
- Add `.env` to `.gitignore`
- Share `.env.example` (without real values)
- Use environment variables for all sensitive data

❌ **DON'T:**
- Commit `.env` file to git
- Put credentials directly in code
- Put credentials in JSON config files
- Share your `.env` file

## What's Built So Far (MVP Components)

✅ **Logger Module** - Console logging with colors and timestamps
✅ **Utils Module** - Helper functions for nested access, comparisons
✅ **Config Loader Module** - Load configs safely with environment variables

## Next Components to Build

⏳ **Validator Module** - Validate configs before testing
⏳ **Auth Module** - Get and manage bearer tokens
⏳ **MongoDB Client** - Connect and query MongoDB
⏳ **API Client** - Call APIs with retry logic
⏳ **Comparator** - Compare field values
⏳ **Coverage Tracker** - Track tested fields
⏳ **Reporter** - Generate reports
⏳ **Main Orchestrator** - Tie everything together

## Troubleshooting

**Problem:** Config loader test fails with "missing required fields"
**Solution:** Make sure you've created `.env` file with all required variables

**Problem:** Import errors
**Solution:** Make sure `src/__init__.py` exists (can be empty)

**Problem:** Colors not showing in console
**Solution:** Some terminals don't support ANSI colors. Output will still work, just without colors.

## Questions?

If you encounter any issues:
1. Check that all files are in correct directories
2. Verify `.env` file exists and has correct values
3. Check that dependencies are installed: `pip list`
4. Run tests one by one to isolate issues


































.env.example (Template for users)
bash# MongoDB Configuration
MONGO_CONNECTION_STRING=mongodb://username:password@host:27017/database?authSource=admin
MONGO_DATABASE=your_database_name
MONGO_COLLECTION=your_collection_name

# API Configuration
JAVA21_API_URL=https://your-java21-api.com/endpoint
JAVA8_API_URL=https://your-java8-api.com/endpoint
TOKEN_API_URL=https://your-token-api.com/token

# Token API Credentials (if needed)
TOKEN_API_USERNAME=your_username
TOKEN_API_PASSWORD=your_password
.gitignore
# Environment variables
.env

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Test outputs
output/
*.log

# Pytest
.pytest_cache/
.coverage
htmlcov/
configs/test-sample.json
json{
  "apiName": "getUserPaymentData",
  "paymentIdMapping": {
    "mongoField": "payment_id",
    "jsonAttribute": "paymentId"
  },
  "testPaymentIds": [
    "PAY001",
    "PAY002",
    "PAY003"
  ]
}
Note: URLs and MongoDB config will come from .env file for security.

2. MongoDB Client Module
src/mongo_client.py
python"""
MongoDB Client Module
Handles all MongoDB operations
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from typing import Dict, Any, Optional, List
from .logger import logger


class MongoDBClient:
    """Handles MongoDB connections and queries"""
    
    def __init__(self, connection_string: str, database: str, collection: str):
        """
        Initialize MongoDB client
        
        Args:
            connection_string: MongoDB connection string
            database: Database name
            collection: Collection name
        """
        self.connection_string = connection_string
        self.database_name = database
        self.collection_name = collection
        self.client: Optional[MongoClient] = None
        self.db = None
        self.collection = None
    
    def connect(self) -> bool:
        """
        Connect to MongoDB
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info("Connecting to MongoDB...")
            self.client = MongoClient(self.connection_string, serverSelectionTimeoutMS=5000)
            
            # Test connection
            self.client.admin.command('ping')
            
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]
            
            logger.success(f"Connected to MongoDB - Database: {self.database_name}, Collection: {self.collection_name}")
            return True
            
        except ConnectionFailure as e:
            logger.error(f"MongoDB connection failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {str(e)}")
            return False
    
    def find_by_payment_id(self, payment_id: str, payment_id_field: str) -> Dict[str, Any]:
        """
        Find a record by payment ID
        
        Args:
            payment_id: Payment ID value to search for
            payment_id_field: MongoDB field name for payment ID
        
        Returns:
            Dict with 'success' (bool), 'data' (record or None), 'error' (str or None)
        """
        if not self.collection:
            return {
                'success': False,
                'data': None,
                'error': 'Not connected to MongoDB'
            }
        
        try:
            query = {payment_id_field: payment_id}
            logger.debug(f"Querying MongoDB: {query}")
            
            record = self.collection.find_one(query)
            
            if record:
                # Convert ObjectId to string for JSON serialization
                if '_id' in record:
                    record['_id'] = str(record['_id'])
                
                logger.debug(f"Found record for payment ID: {payment_id}")
                return {
                    'success': True,
                    'data': record,
                    'error': None
                }
            else:
                logger.warn(f"No record found for payment ID: {payment_id}")
                return {
                    'success': True,
                    'data': None,
                    'error': f'No record found for payment ID: {payment_id}'
                }
                
        except OperationFailure as e:
            logger.error(f"MongoDB operation failed: {str(e)}")
            return {
                'success': False,
                'data': None,
                'error': f'MongoDB operation failed: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Error querying MongoDB: {str(e)}")
            return {
                'success': False,
                'data': None,
                'error': f'Error querying MongoDB: {str(e)}'
            }
    
    def test_collection_access(self) -> Dict[str, Any]:
        """
        Test if collection exists and has data
        
        Returns:
            Dict with collection stats
        """
        if not self.collection:
            return {
                'success': False,
                'error': 'Not connected to MongoDB'
            }
        
        try:
            # Check if collection exists
            collections = self.db.list_collection_names()
            
            if self.collection_name not in collections:
                return {
                    'success': False,
                    'error': f"Collection '{self.collection_name}' not found",
                    'available_collections': collections
                }
            
            # Get document count
            count = self.collection.count_documents({})
            
            return {
                'success': True,
                'collection_name': self.collection_name,
                'document_count': count
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error accessing collection: {str(e)}'
            }
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
tests/test_mongo_client.py
python"""
Test script for MongoDB Client module
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.mongo_client import MongoDBClient
from src.config_loader import config_loader
from src.logger import logger


def test_mongo_client():
    """Test MongoDB client functionality"""
    
    logger.header("TESTING MONGODB CLIENT MODULE")
    
    # Load config to get MongoDB details
    try:
        test_config = config_loader.load_test_config('configs/test-sample.json')
    except Exception as e:
        logger.error(f"Failed to load config: {str(e)}")
        logger.info("Make sure .env file exists with MongoDB credentials")
        return
    
    # Test 1: Create MongoDB client
    logger.info("\nTest 1: Initialize MongoDB Client")
    try:
        mongo_client = MongoDBClient(
            connection_string=test_config['mongoConnectionString'],
            database=test_config['mongoDatabase'],
            collection=test_config['mongoCollection']
        )
        logger.success("MongoDB client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize: {str(e)}")
        return
    
    # Test 2: Connect to MongoDB
    logger.info("\nTest 2: Connect to MongoDB")
    connected = mongo_client.connect()
    
    if not connected:
        logger.error("Connection failed - check your .env file credentials")
        return
    
    # Test 3: Test collection access
    logger.info("\nTest 3: Test Collection Access")
    collection_info = mongo_client.test_collection_access()
    
    if collection_info['success']:
        logger.success(f"Collection accessible")
        logger.info(f"  Collection: {collection_info['collection_name']}")
        logger.info(f"  Document count: {collection_info['document_count']}")
    else:
        logger.error(f"Collection access failed: {collection_info.get('error')}")
        if 'available_collections' in collection_info:
            logger.info(f"Available collections: {collection_info['available_collections']}")
        return
    
    # Test 4: Query by payment ID
    logger.info("\nTest 4: Query by Payment ID")
    payment_id_field = test_config['paymentIdMapping']['mongoField']
    test_payment_id = test_config['testPaymentIds'][0]
    
    logger.info(f"  Querying for payment ID: {test_payment_id}")
    logger.info(f"  Using MongoDB field: {payment_id_field}")
    
    result = mongo_client.find_by_payment_id(test_payment_id, payment_id_field)
    
    if result['success']:
        if result['data']:
            logger.success(f"Record found!")
            logger.info(f"  Record has {len(result['data'])} fields")
            
            # Show first few fields
            logger.info(f"  Sample fields:")
            count = 0
            for key, value in result['data'].items():
                if count < 5:  # Show first 5 fields
                    value_str = str(value)[:50]  # Truncate long values
                    logger.info(f"    {key}: {value_str}")
                    count += 1
        else:
            logger.warn(f"No record found for payment ID: {test_payment_id}")
            logger.info(f"  This payment ID may not exist in the database")
            logger.info(f"  Update testPaymentIds in test-sample.json with valid IDs")
    else:
        logger.error(f"Query failed: {result.get('error')}")
    
    # Test 5: Test with all configured payment IDs
    logger.info("\nTest 5: Test All Configured Payment IDs")
    for payment_id in test_config['testPaymentIds']:
        result = mongo_client.find_by_payment_id(payment_id, payment_id_field)
        
        if result['success'] and result['data']:
            logger.success(f"✓ {payment_id}: Found")
        elif result['success'] and not result['data']:
            logger.warn(f"⚠ {payment_id}: Not found")
        else:
            logger.error(f"✗ {payment_id}: Error - {result.get('error')}")
    
    # Close connection
    logger.info("\nTest 6: Close Connection")
    mongo_client.close()
    logger.success("Connection closed")
    
    logger.separator()
    logger.header("MONGODB CLIENT MODULE TEST COMPLETE")
    
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    print("1. If payment IDs were not found, update test-sample.json")
    print("   with valid payment IDs from your database")
    print("2. You can query MongoDB directly to find valid payment IDs:")
    print(f"   db.{test_config['mongoCollection']}.find().limit(5)")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_mongo_client()

3. Auth Manager Module
src/auth.py
python"""
Auth Module
Handles bearer token acquisition and management
"""

import requests
import time
from typing import Dict, Any, Optional
from .logger import logger


class TokenManager:
    """Manages bearer token acquisition and refresh"""
    
    def __init__(self, token_api_url: str, username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize token manager
        
        Args:
            token_api_url: URL to get bearer token
            username: Username for token API (if needed)
            password: Password for token API (if needed)
        """
        self.token_api_url = token_api_url
        self.username = username
        self.password = password
        self.token: Optional[str] = None
        self.expiry_time: Optional[float] = None
        self.token_duration: int = 8 * 60 * 60  # 8 hours in seconds (default)
    
    def get_token(self) -> Dict[str, Any]:
        """
        Acquire bearer token from token API
        
        Returns:
            Dict with 'success' (bool), 'token' (str or None), 'error' (str or None)
        """
        try:
            logger.info(f"Acquiring bearer token from: {self.token_api_url}")
            
            # Prepare request based on whether credentials are needed
            if self.username and self.password:
                # If credentials provided, use basic auth
                response = requests.post(
                    self.token_api_url,
                    auth=(self.username, self.password),
                    timeout=30
                )
            else:
                # No credentials - direct POST
                response = requests.post(
                    self.token_api_url,
                    timeout=30
                )
            
            if response.status_code == 200:
                data = response.json()
                
                # Token might be in different fields depending on API
                token = data.get('token') or data.get('access_token') or data.get('bearer_token')
                
                if not token:
                    logger.error("Token not found in response")
                    logger.debug(f"Response keys: {list(data.keys())}")
                    return {
                        'success': False,
                        'token': None,
                        'error': 'Token not found in API response'
                    }
                
                # Check for expiry information
                expires_in = data.get('expires_in') or data.get('expiresIn') or self.token_duration
                
                self.token = token
                self.expiry_time = time.time() + expires_in
                
                logger.success("Bearer token acquired successfully")
                logger.info(f"  Token valid for: {expires_in / 3600:.1f} hours")
                
                return {
                    'success': True,
                    'token': token,
                    'expires_in': expires_in,
                    'error': None
                }
            
            else:
                logger.error(f"Token API returned status code: {response.status_code}")
                return {
                    'success': False,
                    'token': None,
                    'error': f'Token API error: {response.status_code} - {response.text}'
                }
                
        except requests.exceptions.Timeout:
            logger.error("Token API request timed out")
            return {
                'success': False,
                'token': None,
                'error': 'Token API request timed out'
            }
        except requests.exceptions.ConnectionError:
            logger.error(f"Could not connect to token API: {self.token_api_url}")
            return {
                'success': False,
                'token': None,
                'error': f'Connection error to token API'
            }
        except Exception as e:
            logger.error(f"Error acquiring token: {str(e)}")
            return {
                'success': False,
                'token': None,
                'error': f'Error acquiring token: {str(e)}'
            }
    
    def is_token_expired(self) -> bool:
        """
        Check if token is expired or about to expire
        
        Returns:
            True if token is expired or will expire in next 5 minutes
        """
        if not self.token or not self.expiry_time:
            return True
        
        # Refresh 5 minutes before actual expiry
        buffer_time = 5 * 60  # 5 minutes
        return time.time() + buffer_time >= self.expiry_time
    
    def get_valid_token(self) -> Dict[str, Any]:
        """
        Get a valid token (refresh if needed)
        
        Returns:
            Dict with 'success' (bool), 'token' (str or None), 'error' (str or None)
        """
        if self.is_token_expired():
            logger.info("Token expired or not acquired, getting new token...")
            return self.get_token()
        
        logger.debug("Using existing valid token")
        return {
            'success': True,
            'token': self.token,
            'error': None
        }
tests/test_auth.py
python"""
Test script for Auth module
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.auth import TokenManager
from src.config_loader import config_loader
from src.logger import logger


def test_auth():
    """Test authentication and token management"""
    
    logger.header("TESTING AUTH MODULE")
    
    # Load config
    try:
        test_config = config_loader.load_test_config('configs/test-sample.json')
    except Exception as e:
        logger.error(f"Failed to load config: {str(e)}")
        logger.info("Make sure .env file exists with TOKEN_API_URL")
        return
    
    token_api_url = test_config.get('tokenApiUrl')
    
    if not token_api_url:
        logger.error("TOKEN_API_URL not configured in .env file")
        return
    
    # Get optional credentials from environment
    username = os.getenv('TOKEN_API_USERNAME')
    password = os.getenv('TOKEN_API_PASSWORD')
    
    # Test 1: Initialize TokenManager
    logger.info("\nTest 1: Initialize TokenManager")
    try:
        token_manager = TokenManager(
            token_api_url=token_api_url,
            username=username,
            password=password
        )
        logger.success("TokenManager initialized")
        
        if username and password:
            logger.info("  Using credentials from .env")
        else:
            logger.info("  No credentials configured (using direct POST)")
    except Exception as e:
        logger.error(f"Failed to initialize: {str(e)}")
        return
    
    # Test 2: Acquire token
    logger.info("\nTest 2: Acquire Bearer Token")
    result = token_manager.get_token()
    
    if result['success']:
        logger.success("Token acquired successfully")
        logger.info(f"  Token (first 20 chars): {result['token'][:20]}...")
        logger.info(f"  Valid for: {result.get('expires_in', 'unknown')} seconds")
    else:
        logger.error(f"Token acquisition failed: {result.get('error')}")
        logger.info("\nTroubleshooting:")
        logger.info("1. Check TOKEN_API_URL in .env is correct")
        logger.info("2. If API requires authentication, add:")
        logger.info("   TOKEN_API_USERNAME=your_username")
        logger.info("   TOKEN_API_PASSWORD=your_password")
        logger.info("3. Check API documentation for correct endpoint and auth method")
        return
    
    # Test 3: Check token expiry
    logger.info("\nTest 3: Check Token Expiry Status")
    is_expired = token_manager.is_token_expired()
    
    if is_expired:
        logger.warn("Token is expired (should not happen right after acquisition!)")
    else:
        logger.success("Token is valid and not expired")
    
    # Test 4: Get valid token (should use cached token)
    logger.info("\nTest 4: Get Valid Token (Should Use Cache)")
    result = token_manager.get_valid_token()
    
    if result['success']:
        logger.success("Got valid token from cache")
        logger.info("  No new API call was made (efficient!)")
    else:
        logger.error(f"Failed to get valid token: {result.get('error')}")
    
    # Test 5: Simulate token expiry
    logger.info("\nTest 5: Simulate Token Expiry and Refresh")
    logger.info("  Manually expiring token...")
    token_manager.expiry_time = 0  # Force expiry
    
    is_expired = token_manager.is_token_expired()
    if is_expired:
        logger.success("Token marked as expired")
    
    logger.info("  Getting valid token (should refresh)...")
    result = token_manager.get_valid_token()
    
    if result['success']:
        logger.success("Token refreshed successfully")
        logger.info("  New token acquired automatically")
    else:
        logger.error(f"Token refresh failed: {result.get('error')}")
    
    logger.separator()
    logger.header("AUTH MODULE TEST COMPLETE")
    
    print("\n" + "="*60)
    print("SUMMARY:")
    print("="*60)
    if result['success']:
        print("✓ Auth module is working correctly")
        print("✓ Token acquisition works")
        print("✓ Token caching works")
        print("✓ Token refresh works")
    else:
        print("✗ Some tests failed - check configuration")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_auth()

4. How to Test These Components
Step 1: Set up your .env file
Create .env file in project root:
bash# Copy from .env.example and fill in your actual values
MONGO_CONNECTION_STRING=mongodb://your_user:your_password@your_host:27017/your_db
MONGO_DATABASE=your_database
MONGO_COLLECTION=your_collection
JAVA21_API_URL=https://your-api.com/endpoint
TOKEN_API_URL=https://your-token-api.com/token

# Optional: If token API needs auth
TOKEN_API_USERNAME=your_username
TOKEN_API_PASSWORD=your_password
Step 2: Run tests
bash# Test Config Loader
python tests/test_config_loader.py

# Test MongoDB Client
python tests/test_mongo_client.py

# Test Auth
python tests/test_auth.py




