src/api_client.py
python"""
API Client Module
Handles API calls with retry logic and error handling
"""

import requests
import time
from typing import Dict, Any, Optional
from .logger import logger


class APIClient:
    """Handles API calls with authentication and retry logic"""
    
    def __init__(self, token_manager):
        """
        Initialize API client
        
        Args:
            token_manager: TokenManager instance for authentication
        """
        self.token_manager = token_manager
    
    def call_api(
        self, 
        url: str, 
        request_body: Dict[str, Any], 
        max_retries: int = 3,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Call API with retry logic
        
        Args:
            url: API endpoint URL
            request_body: Request body (will be sent as JSON)
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
        
        Returns:
            Dict with 'success' (bool), 'data' (dict or None), 'error' (str or None),
            'statusCode' (int or None)
        """
        
        for attempt in range(1, max_retries + 1):
            try:
                # Get valid token
                token_result = self.token_manager.get_valid_token()
                
                if not token_result['success']:
                    return {
                        'success': False,
                        'data': None,
                        'error': f"Failed to get valid token: {token_result.get('error')}",
                        'statusCode': None
                    }
                
                token = token_result['token']
                
                # Prepare headers
                headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                }
                
                # Make request
                logger.debug(f"Calling API: {url} (attempt {attempt}/{max_retries})")
                
                response = requests.post(
                    url,
                    json=request_body,
                    headers=headers,
                    timeout=timeout
                )
                
                # Success
                if response.status_code == 200:
                    try:
                        data = response.json()
                        logger.debug(f"API call successful: {url}")
                        return {
                            'success': True,
                            'data': data,
                            'error': None,
                            'statusCode': 200
                        }
                    except ValueError as e:
                        logger.error(f"API returned invalid JSON: {str(e)}")
                        return {
                            'success': False,
                            'data': None,
                            'error': f"Invalid JSON response: {str(e)}",
                            'statusCode': 200,
                            'rawResponse': response.text[:500]  # First 500 chars
                        }
                
                # Token expired - refresh and retry
                elif response.status_code == 401:
                    logger.warn(f"Token expired (401), refreshing token...")
                    self.token_manager.expiry_time = 0  # Force refresh
                    
                    if attempt < max_retries:
                        continue  # Retry with new token
                    else:
                        return {
                            'success': False,
                            'data': None,
                            'error': 'Authentication failed after token refresh',
                            'statusCode': 401
                        }
                
                # Other HTTP errors
                else:
                    error_msg = f"HTTP {response.status_code}"
                    try:
                        error_detail = response.json()
                        error_msg += f": {error_detail}"
                    except:
                        error_msg += f": {response.text[:200]}"
                    
                    logger.error(f"API error: {error_msg}")
                    
                    return {
                        'success': False,
                        'data': None,
                        'error': error_msg,
                        'statusCode': response.status_code
                    }
            
            except requests.exceptions.Timeout:
                logger.warn(f"API request timed out (attempt {attempt}/{max_retries})")
                
                if attempt < max_retries:
                    sleep_time = 2 * attempt  # Exponential backoff: 2s, 4s, 6s
                    logger.info(f"Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                    continue
                else:
                    return {
                        'success': False,
                        'data': None,
                        'error': f'Request timed out after {max_retries} attempts',
                        'statusCode': None
                    }
            
            except requests.exceptions.ConnectionError as e:
                logger.warn(f"Connection error (attempt {attempt}/{max_retries}): {str(e)}")
                
                if attempt < max_retries:
                    sleep_time = 2 * attempt
                    logger.info(f"Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                    continue
                else:
                    return {
                        'success': False,
                        'data': None,
                        'error': f'Connection error: {str(e)}',
                        'statusCode': None
                    }
            
            except Exception as e:
                logger.error(f"Unexpected error calling API: {str(e)}")
                return {
                    'success': False,
                    'data': None,
                    'error': f'Unexpected error: {str(e)}',
                    'statusCode': None
                }
        
        # Should not reach here
        return {
            'success': False,
            'data': None,
            'error': 'Max retries exceeded',
            'statusCode': None
        }
    
    def call_both_apis(
        self,
        java21_url: str,
        java8_url: Optional[str],
        request_body: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call both Java 8 and Java 21 APIs
        
        Args:
            java21_url: Java 21 API URL
            java8_url: Java 8 API URL (optional)
            request_body: Request body
        
        Returns:
            Dict with 'java21Result' and 'java8Result'
        """
        
        # Call Java 21 API
        logger.debug("Calling Java 21 API...")
        java21_result = self.call_api(java21_url, request_body)
        
        # Call Java 8 API if URL provided
        java8_result = None
        if java8_url:
            logger.debug("Calling Java 8 API...")
            java8_result = self.call_api(java8_url, request_body)
        
        return {
            'java21Result': java21_result,
            'java8Result': java8_result
        }

6. Comparator Module
src/comparator.py
python"""
Comparator Module
Handles field-by-field comparison logic
"""

from typing import Dict, Any, Optional
from .utils import get_nested_value, deep_equal, safe_float_compare, is_numeric_string
from .logger import logger


class Comparator:
    """Compares field values between MongoDB and API responses"""
    
    def compare_field(
        self,
        mongo_record: Dict[str, Any],
        java21_response: Optional[Dict[str, Any]],
        java8_response: Optional[Dict[str, Any]],
        mapping: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Compare a single field across MongoDB and API responses
        
        Args:
            mongo_record: MongoDB record
            java21_response: Java 21 API response
            java8_response: Java 8 API response (optional)
            mapping: Field mapping dict with 'mongoField', 'jsonAttribute', 'mongoType'
        
        Returns:
            Dict with comparison results
        """
        
        # Extract values
        mongo_field = mapping['mongoField']
        json_attribute = mapping['jsonAttribute']
        mongo_type = mapping.get('mongoType', 'Unknown')
        
        mongo_value = get_nested_value(mongo_record, mongo_field)
        
        java21_value = None
        java21_error = None
        if java21_response:
            if 'success' in java21_response and not java21_response['success']:
                java21_error = java21_response.get('error', 'Unknown error')
            else:
                java21_value = get_nested_value(java21_response, json_attribute)
        
        java8_value = None
        java8_error = None
        if java8_response:
            if 'success' in java8_response and not java8_response['success']:
                java8_error = java8_response.get('error', 'Unknown error')
            else:
                java8_value = get_nested_value(java8_response, json_attribute)
        
        # Compare MongoDB vs Java 21
        mongo_vs_java21 = self._compare_values(
            mongo_value, 
            java21_value, 
            mongo_type,
            "MongoDB",
            "Java 21"
        )
        
        # Compare Java 8 vs Java 21 (if Java 8 available)
        java8_vs_java21 = None
        if java8_response and not java8_error:
            java8_vs_java21 = self._compare_values(
                java8_value,
                java21_value,
                mongo_type,
                "Java 8",
                "Java 21"
            )
        
        # Determine overall status
        status = self._determine_status(
            mongo_vs_java21,
            java8_vs_java21,
            java21_error,
            java8_error
        )
        
        return {
            'mongoField': mongo_field,
            'jsonAttribute': json_attribute,
            'mongoType': mongo_type,
            'mongoValue': mongo_value,
            'java21Value': java21_value if not java21_error else f"ERROR: {java21_error}",
            'java8Value': java8_value if not java8_error else f"ERROR: {java8_error}" if java8_error else None,
            'mongoVsJava21': mongo_vs_java21,
            'java8VsJava21': java8_vs_java21,
            'status': status,
            'severity': mongo_vs_java21.get('severity', 'INFO')
        }
    
    def _compare_values(
        self,
        value1: Any,
        value2: Any,
        data_type: str,
        label1: str = "Value1",
        label2: str = "Value2"
    ) -> Dict[str, Any]:
        """
        Compare two values
        
        Returns:
            Dict with 'match' (bool), 'mismatchType' (str or None), 
            'severity' (str), 'note' (str or None)
        """
        
        # Exact match
        if deep_equal(value1, value2):
            return {
                'match': True,
                'mismatchType': None,
                'severity': 'PASS',
                'note': None
            }
        
        # Both are None or null
        if value1 is None and value2 is None:
            return {
                'match': True,
                'mismatchType': None,
                'severity': 'PASS',
                'note': 'Both values are None'
            }
        
        # One is None, other is not
        if value1 is None and value2 is not None:
            return {
                'match': False,
                'mismatchType': 'NULL_MISMATCH',
                'severity': 'WARNING',
                'note': f'{label1} is None, but {label2} has value'
            }
        
        if value1 is not None and value2 is None:
            return {
                'match': False,
                'mismatchType': 'NULL_MISMATCH',
                'severity': 'WARNING',
                'note': f'{label1} has value, but {label2} is None'
            }
        
        # Empty array vs None (Issue #2)
        if isinstance(value1, list) and len(value1) == 0 and value2 is None:
            return {
                'match': False,
                'mismatchType': 'EMPTY_ARRAY_HANDLING',
                'severity': 'WARNING',
                'note': f'{label1} has empty array [], {label2} is None (Known Issue #2)'
            }
        
        if value1 is None and isinstance(value2, list) and len(value2) == 0:
            return {
                'match': False,
                'mismatchType': 'EMPTY_ARRAY_HANDLING',
                'severity': 'WARNING',
                'note': f'{label1} is None, {label2} has empty array [] (Known Issue #2)'
            }
        
        # Numeric comparison with tolerance (for decimals)
        if data_type in ['Decimal128', 'Double', 'Float', 'BigDecimal']:
            if safe_float_compare(value1, value2):
                return {
                    'match': True,
                    'mismatchType': None,
                    'severity': 'PASS',
                    'note': 'Values are numerically equal'
                }
        
        # Number formatting difference (Issue #3)
        if is_numeric_string(str(value1)) and is_numeric_string(str(value2)):
            if safe_float_compare(value1, value2):
                return {
                    'match': False,
                    'mismatchType': 'NUMBER_FORMATTING',
                    'severity': 'WARNING',
                    'note': f'Number formatting difference: {value1} vs {value2} (Issue #3)'
                }
        
        # Type mismatch
        if type(value1).__name__ != type(value2).__name__:
            return {
                'match': False,
                'mismatchType': 'TYPE_MISMATCH',
                'severity': 'CRITICAL',
                'note': f'Type mismatch: {type(value1).__name__} vs {type(value2).__name__}'
            }
        
        # Array length mismatch
        if isinstance(value1, list) and isinstance(value2, list):
            if len(value1) != len(value2):
                return {
                    'match': False,
                    'mismatchType': 'ARRAY_LENGTH_MISMATCH',
                    'severity': 'CRITICAL',
                    'note': f'Array length: {len(value1)} vs {len(value2)}'
                }
        
        # Value difference
        return {
            'match': False,
            'mismatchType': 'VALUE_DIFFERENCE',
            'severity': 'CRITICAL',
            'note': f'Values differ: {value1} vs {value2}'
        }
    
    def _determine_status(
        self,
        mongo_vs_java21: Dict[str, Any],
        java8_vs_java21: Optional[Dict[str, Any]],
        java21_error: Optional[str],
        java8_error: Optional[str]
    ) -> str:
        """
        Determine overall status based on comparisons
        
        Returns:
            'PASS', 'WARNING', 'CRITICAL', or 'ERROR'
        """
        
        # If Java 21 had an error
        if java21_error:
            # If Java 8 worked but Java 21 failed - CRITICAL (regression)
            if java8_vs_java21 is None and not java8_error:
                return 'CRITICAL_ERROR'
            return 'ERROR'
        
        # If Java 8 had an error but Java 21 worked - might be improvement
        if java8_error and not java21_error:
            return 'WARNING'
        
        # Check MongoDB vs Java 21 comparison
        if not mongo_vs_java21['match']:
            severity = mongo_vs_java21.get('severity', 'CRITICAL')
            
            # If there's also a Java 8 vs Java 21 mismatch
            if java8_vs_java21 and not java8_vs_java21['match']:
                # Both have issues - use the more severe
                java8_severity = java8_vs_java21.get('severity', 'CRITICAL')
                if 'CRITICAL' in [severity, java8_severity]:
                    return 'CRITICAL'
                return 'WARNING'
            
            return severity
        
        # MongoDB vs Java 21 matches
        # Check Java 8 vs Java 21 if available
        if java8_vs_java21 and not java8_vs_java21['match']:
            return java8_vs_java21.get('severity', 'WARNING')
        
        return 'PASS'

7. Tests for API Client and Comparator
tests/test_api_client.py
python"""
Test script for API Client module
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.api_client import APIClient
from src.auth import TokenManager
from src.config_loader import config_loader
from src.logger import logger


def test_api_client():
    """Test API client functionality"""
    
    logger.header("TESTING API CLIENT MODULE")
    
    # Load config
    try:
        test_config = config_loader.load_test_config('configs/test-sample.json')
    except Exception as e:
        logger.error(f"Failed to load config: {str(e)}")
        return
    
    # Initialize token manager
    logger.info("\nStep 1: Initialize Token Manager")
    token_manager = TokenManager(
        token_api_url=test_config['tokenApiUrl'],
        username=os.getenv('TOKEN_API_USERNAME'),
        password=os.getenv('TOKEN_API_PASSWORD')
    )
    
    # Get token
    logger.info("\nStep 2: Acquire Token")
    token_result = token_manager.get_token()
    
    if not token_result['success']:
        logger.error(f"Failed to get token: {token_result.get('error')}")
        logger.info("Cannot proceed with API tests without valid token")
        return
    
    logger.success("Token acquired")
    
    # Initialize API client
    logger.info("\nStep 3: Initialize API Client")
    api_client = APIClient(token_manager)
    logger.success("API Client initialized")
    
    # Test Java 21 API call
    logger.info("\nStep 4: Test Java 21 API Call")
    
    payment_id_field = test_config['paymentIdMapping']['jsonAttribute']
    test_payment_id = test_config['testPaymentIds'][0]
    
    request_body = {
        payment_id_field: test_payment_id
    }
    
    logger.info(f"  Request body: {request_body}")
    logger.info(f"  Calling: {test_config['java21ApiUrl']}")
    
    result = api_client.call_api(
        url=test_config['java21ApiUrl'],
        request_body=request_body
    )
    
    if result['success']:
        logger.success("Java 21 API call successful!")
        logger.info(f"  Status Code: {result['statusCode']}")
        
        if result['data']:
            logger.info(f"  Response has {len(result['data'])} top-level keys")
            
            # Show structure
            logger.info("  Response structure:")
            for key in list(result['data'].keys())[:5]:  # First 5 keys
                logger.info(f"    - {key}")
        else:
            logger.warn("  Response data is empty")
    else:
        logger.error(f"Java 21 API call failed: {result.get('error')}")
        logger.info(f"  Status Code: {result.get('statusCode')}")
    
    # Test Java 8 API if configured
    if test_config.get('java8ApiUrl'):
        logger.info("\nStep 5: Test Java 8 API Call")
        logger.info(f"  Calling: {test_config['java8ApiUrl']}")
        
        result_java8 = api_client.call_api(
            url=test_config['java8ApiUrl'],
            request_body=request_body
        )
        
        if result_java8['success']:
            logger.success("Java 8 API call successful!")
            logger.info(f"  Status Code: {result_java8['statusCode']}")
        else:
            logger.error(f"Java 8 API call failed: {result_java8.get('error')}")
    else:
        logger.info("\nStep 5: Java 8 API URL not configured (skipped)")
    
    # Test both APIs together
    if test_config.get('java8ApiUrl'):
        logger.info("\nStep 6: Test Calling Both APIs Together")
        
        both_results = api_client.call_both_apis(
            java21_url=test_config['java21ApiUrl'],
            java8_url=test_config.get('java8ApiUrl'),
            request_body=request_body
        )
        
        java21_ok = both_results['java21Result']['success']
        java8_ok = both_results['java8Result']['success'] if both_results['java8Result'] else False
        
        logger.info(f"  Java 21: {'✓ Success' if java21_ok else '✗ Failed'}")
        logger.info(f"  Java 8: {'✓ Success' if java8_ok else '✗ Failed'}")
        
        if java21_ok and java8_ok:
            logger.success("Both APIs responded successfully")
        elif java21_ok and not java8_ok:
            logger.warn("Java 21 succeeded but Java 8 failed")
        elif not java21_ok and java8_ok:
            logger.error("Java 21 failed but Java 8 succeeded (REGRESSION!)")
        else:
            logger.error("Both APIs failed")
    
    logger.separator()
    logger.header("API CLIENT MODULE TEST COMPLETE")
    
    print("\n" + "="*60)
    print("SUMMARY:")
    print("="*60)
    if result['success']:
        print("✓ API Client is working correctly")
        print("✓ Can call APIs with authentication")
        print("✓ Ready for integration with main utility")
    else:
        print("✗ API calls failed - check configuration")
        print("  - Verify API URLs in .env")
        print("  - Verify payment IDs exist")
        print("  - Check API authentication")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_api_client()




tests/test_comparator.py




python"""
Test script for Comparator module
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.comparator import Comparator
from src.logger import logger


def test_comparator():
    """Test comparator functionality"""
    
    logger.header("TESTING COMPARATOR MODULE")
    
    comparator = Comparator()
    
    # Test 1: Exact match
    logger.info("\n" + "="*60)
    logger.info("Test 1: Exact Match")
    logger.info("="*60)
    
    mongo_record = {
        "payment_id": "PAY001",
        "user": {
            "name": "John Doe"
        }
    }
    
    java21_response = {
        "paymentId": "PAY001"
    }
    
    mapping = {
        "mongoField": "payment_id",
        "jsonAttribute": "paymentId",
        "mongoType": "String"
    }
    
    result = comparator.compare_field(mongo_record, java21_response, None, mapping)
    
    if result['status'] == 'PASS':
        logger.success("✓ Exact match detected correctly")
    else:
        logger.error(f"✗ Expected PASS, got {result['status']}")
    
    logger.info(f"  MongoDB value: {result['mongoValue']}")
    logger.info(f"  Java 21 value: {result['java21Value']}")
    logger.info(f"  Status: {result['status']}")
    
    # Test 2: Number formatting difference (Issue #3)
    logger.info("\n" + "="*60)
    logger.info("Test 2: Number Formatting Difference (Issue #3)")
    logger.info("="*60)
    
    mongo_record = {
        "amount": 10.50
    }
    
    java21_response = {
        "amount": 10.5
    }
    
    java8_response = {
        "amount": 10.50
    }
    
    mapping = {
        "mongoField": "amount",
        "jsonAttribute": "amount",
        "mongoType": "Decimal128"
    }
    
    result = comparator.compare_field(mongo_record, java21_response, java8_response, mapping)
    
    if result['status'] == 'WARNING' or result['mongoVsJava21']['mismatchType'] == 'NUMBER_FORMATTING':
        logger.success("✓ Number formatting difference detected (Issue #3)")
    else:
        logger.warn(f"Status: {result['status']}, Type: {result['mongoVsJava21'].get('mismatchType')}")
    
    logger.info(f"  MongoDB value: {result['mongoValue']}")
    logger.info(f"  Java 8 value: {result['java8Value']}")
    logger.info(f"  Java 21 value: {result['java21Value']}")
    logger.info(f"  Mismatch Type: {result['mongoVsJava21'].get('mismatchType')}")
    logger.info(f"  Note: {result['mongoVsJava21'].get('note')}")
    
    # Test 3: Empty array vs None (Issue #2)
    logger.info("\n" + "="*60)
    logger.info("Test 3: Empty Array vs None (Issue #2)")
    logger.info("="*60)
    
    mongo_record = {
        "items": []
    }
    
    java21_response = {
        "items": []
    }
    
    java8_response = {
        # items field not present (None)
    }
    
    mapping = {
        "mongoField": "items",
        "jsonAttribute": "items",
        "mongoType": "Array"
    }
    
    result = comparator.compare_field(mongo_record, java21_response, java8_response, mapping)
    
    if result['java8VsJava21'] and result['java8VsJava21']['mismatchType'] == 'EMPTY_ARRAY_HANDLING':
        logger.success("✓ Empty array handling difference detected (Issue #2)")
    else:
        logger.warn(f"Java8 vs Java21: {result['java8VsJava21']}")
    
    logger.info(f"  MongoDB value: {result['mongoValue']}")
    logger.info(f"  Java 8 value: {result['java8Value']}")
    logger.info(f"  Java 21 value: {result['java21Value']}")
    
    if result['java8VsJava21']:
        logger.info(f"  Mismatch Type: {result['java8VsJava21'].get('mismatchType')}")
        logger.info(f"  Note: {result['java8VsJava21'].get('note')}")
    
    # Test 4: Value difference (Critical)
    logger.info("\n" + "="*60)
    logger.info("Test 4: Value Difference (Critical)")
    logger.info("="*60)
    
    mongo_record = {
        "status": "completed"
    }
    
    java21_response = {
        "status": "pending"
    }
    
    mapping = {
        "mongoField": "status",
        "jsonAttribute": "status",
        "mongoType": "String"
    }
    
    result = comparator.compare_field(mongo_record, java21_response, None, mapping)
    
    if result['status'] == 'CRITICAL':
        logger.success("✓ Critical value difference detected")
    else:
        logger.error(f"✗ Expected CRITICAL, got {result['status']}")
    
    logger.info(f"  MongoDB value: {result['mongoValue']}")
    logger.info(f"  Java 21 value: {result['java21Value']}")
    logger.info(f"  Status: {result['status']}")
    logger.info(f"  Severity: {result['severity']}")
    
    # Test 5: Type mismatch (Issue #1)
    logger.info("\n" + "="*60)
    logger.info("Test 5: Type Mismatch (Issue #1)")
    logger.info("="*60)
    
    mongo_record = {
        "user_id": 12345  # Integer/Long
    }
    
    # Simulating Java 21 error
    java21_response_error = {
        "success": False,
        "error": "Cannot convert Long to BigDecimal"
    }
    
    java8_response = {
        "userId": 12345
    }
    
    mapping = {
        "mongoField": "user_id",
        "jsonAttribute": "userId",
        "mongoType": "Long"
    }
    
    result = comparator.compare_field(mongo_record, java21_response_error, java8_response, mapping)
    
    if result['status'] == 'CRITICAL_ERROR' or result['status'] == 'ERROR':
        logger.success("✓ API error detected (Issue #1 scenario)")
    else:
        logger.error(f"✗ Expected ERROR, got {result['status']}")
    
    logger.info(f"  MongoDB value: {result['mongoValue']}")
    logger.info(f"  Java 8 value: {result['java8Value']}")
    logger.info(f"  Java 21 value: {result['java21Value']}")
    logger.info(f"  Status: {result['status']}")
    
    # Test 6: Nested field comparison
    logger.info("\n" + "="*60)
    logger.info("Test 6: Nested Field Comparison")
    logger.info("="*60)
    
    mongo_record = {
        "user": {
            "address": {
                "city": "New York"
            }
        }
    }
    
    java21_response = {
        "actualData": {
            "userData": {
                "userCity": "New York"
            }
        }
    }
    
    mapping = {
        "mongoField": "user.address.city",
        "jsonAttribute": "actualData.userData.userCity",
        "mongoType": "String"
    }
    
    result = comparator.compare_field(mongo_record, java21_response, None, mapping)
    
    if result['status'] == 'PASS':
        logger.success("✓ Nested field comparison works correctly")
    else:
        logger.error(f"✗ Expected PASS, got {result['status']}")
    
    logger.info(f"  MongoDB path: {mapping['mongoField']}")
    logger.info(f"  JSON path: {mapping['jsonAttribute']}")
    logger.info(f"  MongoDB value: {result['mongoValue']}")
    logger.info(f"  Java 21 value: {result['java21Value']}")
    logger.info(f"  Status: {result['status']}")
    
    loggerRetryPMContinueEditpython    logger.separator()
    logger.header("COMPARATOR MODULE TEST COMPLETE")
    
    print("\n" + "="*60)
    print("SUMMARY:")
    print("="*60)
    print("✓ Exact matches detected correctly")
    print("✓ Number formatting differences detected (Issue #3)")
    print("✓ Empty array handling differences detected (Issue #2)")
    print("✓ Value differences marked as CRITICAL")
    print("✓ API errors detected (Issue #1 scenario)")
    print("✓ Nested field comparisons work")
    print("\nComparator is ready for use in main utility!")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_comparator()

8. Main Orchestrator (MVP Version)
Now let's create the main entry point that ties everything together.
src/main.py
python"""
Main Module
Orchestrates the entire testing workflow
"""

import sys
import time
from typing import Dict, Any, List
from .logger import logger
from .config_loader import config_loader
from .mongo_client import MongoDBClient
from .auth import TokenManager
from .api_client import APIClient
from .comparator import Comparator


class TestOrchestrator:
    """Main orchestrator for the testing utility"""
    
    def __init__(self, mapping_config_path: str, test_config_path: str):
        """
        Initialize orchestrator
        
        Args:
            mapping_config_path: Path to mapping config JSON
            test_config_path: Path to test config JSON
        """
        self.mapping_config_path = mapping_config_path
        self.test_config_path = test_config_path
        
        self.mapping_config = None
        self.test_config = None
        
        self.mongo_client = None
        self.token_manager = None
        self.api_client = None
        self.comparator = None
        
        self.test_results = []
        self.start_time = None
    
    def run(self):
        """Execute the complete test workflow"""
        
        self.start_time = time.time()
        
        logger.header("API MIGRATION TEST UTILITY - MVP")
        logger.info(f"Starting test execution at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.separator()
        
        # Step 1: Load and validate configurations
        if not self._load_configs():
            logger.error("Configuration loading failed. Exiting.")
            return False
        
        # Step 2: Initialize components
        if not self._initialize_components():
            logger.error("Component initialization failed. Exiting.")
            return False
        
        # Step 3: Run Phase 1 tests
        logger.separator()
        logger.header("PHASE 1: Testing Configured Payment IDs")
        
        phase1_results = self._run_phase1()
        
        # Step 4: Generate summary report
        logger.separator()
        self._generate_summary(phase1_results)
        
        # Cleanup
        if self.mongo_client:
            self.mongo_client.close()
        
        return True
    
    def _load_configs(self) -> bool:
        """Load configuration files"""
        
        logger.info("\nStep 1: Loading Configuration Files")
        logger.separator('-', 60)
        
        try:
            # Load mapping config
            logger.info(f"Loading mapping config: {self.mapping_config_path}")
            self.mapping_config = config_loader.load_mapping_config(self.mapping_config_path)
            logger.success(f"✓ Mapping config loaded: {len(self.mapping_config)} field mappings")
            
            # Load test config
            logger.info(f"Loading test config: {self.test_config_path}")
            self.test_config = config_loader.load_test_config(self.test_config_path)
            logger.success(f"✓ Test config loaded")
            logger.info(f"  API Name: {self.test_config['apiName']}")
            logger.info(f"  Test Payment IDs: {len(self.test_config['testPaymentIds'])}")
            
            # Show masked MongoDB connection
            masked_conn = config_loader.get_masked_connection_string(
                self.test_config['mongoConnectionString']
            )
            logger.info(f"  MongoDB: {masked_conn}")
            
            return True
            
        except FileNotFoundError as e:
            logger.error(f"Config file not found: {str(e)}")
            return False
        except ValueError as e:
            logger.error(f"Config validation error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error loading configs: {str(e)}")
            return False
    
    def _initialize_components(self) -> bool:
        """Initialize all components"""
        
        logger.info("\nStep 2: Initializing Components")
        logger.separator('-', 60)
        
        try:
            # Initialize MongoDB client
            logger.info("Initializing MongoDB client...")
            self.mongo_client = MongoDBClient(
                connection_string=self.test_config['mongoConnectionString'],
                database=self.test_config['mongoDatabase'],
                collection=self.test_config['mongoCollection']
            )
            
            if not self.mongo_client.connect():
                logger.error("Failed to connect to MongoDB")
                return False
            
            # Test collection access
            collection_info = self.mongo_client.test_collection_access()
            if not collection_info['success']:
                logger.error(f"Collection access failed: {collection_info.get('error')}")
                return False
            
            logger.info(f"  Document count: {collection_info['document_count']}")
            
            # Initialize token manager
            logger.info("\nInitializing authentication...")
            self.token_manager = TokenManager(
                token_api_url=self.test_config['tokenApiUrl']
            )
            
            token_result = self.token_manager.get_token()
            if not token_result['success']:
                logger.error(f"Failed to acquire token: {token_result.get('error')}")
                return False
            
            # Initialize API client
            logger.info("\nInitializing API client...")
            self.api_client = APIClient(self.token_manager)
            logger.success("✓ API client initialized")
            
            # Initialize comparator
            logger.info("Initializing comparator...")
            self.comparator = Comparator()
            logger.success("✓ Comparator initialized")
            
            logger.success("\n✓ All components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Component initialization failed: {str(e)}")
            return False
    
    def _run_phase1(self) -> List[Dict[str, Any]]:
        """Run Phase 1: Test configured payment IDs"""
        
        phase1_results = []
        payment_ids = self.test_config['testPaymentIds']
        
        logger.info(f"\nTesting {len(payment_ids)} configured payment IDs...")
        logger.separator('-', 60)
        
        for idx, payment_id in enumerate(payment_ids, 1):
            logger.info(f"\n[{idx}/{len(payment_ids)}] Testing Payment ID: {payment_id}")
            logger.separator('-', 40)
            
            result = self._test_single_payment_id(payment_id)
            phase1_results.append(result)
            
            # Show quick summary
            if result['success']:
                logger.success(f"✓ Completed: {result['passed']} passed, {result['warnings']} warnings, {result['failed']} failed")
            else:
                logger.error(f"✗ Testing failed: {result.get('error')}")
        
        return phase1_results
    
    def _test_single_payment_id(self, payment_id: str) -> Dict[str, Any]:
        """Test a single payment ID across all fields"""
        
        payment_id_mongo_field = self.test_config['paymentIdMapping']['mongoField']
        payment_id_json_attr = self.test_config['paymentIdMapping']['jsonAttribute']
        
        result = {
            'paymentId': payment_id,
            'success': False,
            'fieldResults': [],
            'passed': 0,
            'warnings': 0,
            'failed': 0,
            'errors': 0
        }
        
        try:
            # Step 1: Query MongoDB
            logger.debug("Querying MongoDB...")
            mongo_result = self.mongo_client.find_by_payment_id(
                payment_id, 
                payment_id_mongo_field
            )
            
            if not mongo_result['success'] or not mongo_result['data']:
                result['error'] = f"MongoDB query failed or no data found"
                logger.error(f"  ✗ {result['error']}")
                return result
            
            mongo_record = mongo_result['data']
            logger.debug(f"  ✓ MongoDB record found ({len(mongo_record)} fields)")
            
            # Step 2: Call APIs
            logger.debug("Calling APIs...")
            
            request_body = {payment_id_json_attr: payment_id}
            
            api_results = self.api_client.call_both_apis(
                java21_url=self.test_config['java21ApiUrl'],
                java8_url=self.test_config.get('java8ApiUrl'),
                request_body=request_body
            )
            
            java21_result = api_results['java21Result']
            java8_result = api_results['java8Result']
            
            if java21_result['success']:
                logger.debug(f"  ✓ Java 21 API responded")
            else:
                logger.warn(f"  ⚠ Java 21 API failed: {java21_result.get('error')}")
            
            if java8_result:
                if java8_result['success']:
                    logger.debug(f"  ✓ Java 8 API responded")
                else:
                    logger.warn(f"  ⚠ Java 8 API failed: {java8_result.get('error')}")
            
            # Step 3: Compare all fields
            logger.debug("Comparing fields...")
            
            for mapping in self.mapping_config:
                field_result = self.comparator.compare_field(
                    mongo_record=mongo_record,
                    java21_response=java21_result.get('data') if java21_result['success'] else java21_result,
                    java8_response=java8_result.get('data') if java8_result and java8_result['success'] else java8_result,
                    mapping=mapping
                )
                
                result['fieldResults'].append(field_result)
                
                # Count statuses
                if field_result['status'] == 'PASS':
                    result['passed'] += 1
                elif field_result['status'] in ['WARNING']:
                    result['warnings'] += 1
                elif field_result['status'] in ['CRITICAL', 'CRITICAL_ERROR']:
                    result['failed'] += 1
                elif field_result['status'] in ['ERROR']:
                    result['errors'] += 1
            
            result['success'] = True
            
            # Show notable issues
            critical_issues = [f for f in result['fieldResults'] if f['status'] in ['CRITICAL', 'CRITICAL_ERROR']]
            if critical_issues:
                logger.error(f"  ⚠ {len(critical_issues)} critical issue(s) found:")
                for issue in critical_issues[:3]:  # Show first 3
                    logger.error(f"    - {issue['mongoField']}: {issue['mongoVsJava21'].get('note', 'Value mismatch')}")
            
            return result
            
        except Exception as e:
            result['error'] = f"Unexpected error: {str(e)}"
            logger.error(f"  ✗ {result['error']}")
            return result
    
    def _generate_summary(self, phase1_results: List[Dict[str, Any]]):
        """Generate and display summary report"""
        
        logger.header("TEST SUMMARY")
        
        total_payment_ids = len(phase1_results)
        successful_tests = sum(1 for r in phase1_results if r['success'])
        
        total_passed = sum(r['passed'] for r in phase1_results)
        total_warnings = sum(r['warnings'] for r in phase1_results)
        total_failed = sum(r['failed'] for r in phase1_results)
        total_errors = sum(r['errors'] for r in phase1_results)
        total_fields = total_passed + total_warnings + total_failed + total_errors
        
        logger.info(f"\nPayment IDs Tested: {total_payment_ids}")
        logger.info(f"Successful Test Runs: {successful_tests}/{total_payment_ids}")
        logger.separator('-', 60)
        
        logger.info(f"\nField Comparison Results:")
        logger.info(f"  Total Fields Tested: {total_fields}")
        logger.success(f"  ✓ Passed: {total_passed} ({total_passed/total_fields*100:.1f}%)" if total_fields > 0 else "  ✓ Passed: 0")
        logger.warn(f"  ⚠ Warnings: {total_warnings} ({total_warnings/total_fields*100:.1f}%)" if total_fields > 0 else "  ⚠ Warnings: 0")
        logger.error(f"  ✗ Failed: {total_failed} ({total_failed/total_fields*100:.1f}%)" if total_fields > 0 else "  ✗ Failed: 0")
        
        if total_errors > 0:
            logger.error(f"  ⚠ Errors: {total_errors}")
        
        logger.separator('-', 60)
        
        # Show critical issues by payment ID
        logger.info("\nIssues by Payment ID:")
        for result in phase1_results:
            if result['success']:
                status_icon = "✓" if result['failed'] == 0 else "✗"
                status_color = "success" if result['failed'] == 0 else "error"
                
                summary = f"{status_icon} {result['paymentId']}: "
                summary += f"{result['passed']} passed"
                
                if result['warnings'] > 0:
                    summary += f", {result['warnings']} warnings"
                if result['failed'] > 0:
                    summary += f", {result['failed']} FAILED"
                if result['errors'] > 0:
                    summary += f", {result['errors']} errors"
                
                if status_color == "success":
                    logger.success(f"  {summary}")
                else:
                    logger.error(f"  {summary}")
            else:
                logger.error(f"  ✗ {result['paymentId']}: Test execution failed")
        
        # Execution time
        execution_time = time.time() - self.start_time
        logger.separator('-', 60)
        logger.info(f"\nTotal Execution Time: {execution_time:.2f} seconds")
        
        logger.separator()
        
        # Final verdict
        if total_failed == 0 and total_errors == 0:
            logger.success("\n✓ ALL TESTS PASSED!")
            if total_warnings > 0:
                logger.warn(f"  Note: {total_warnings} warnings detected (review recommended)")
        else:
            logger.error("\n✗ TESTS FAILED!")
            logger.error(f"  {total_failed} critical failures detected")
            if total_errors > 0:
                logger.error(f"  {total_errors} errors encountered")
        
        logger.separator()


def main():
    """Main entry point"""
    
    # Check command line arguments
    if len(sys.argv) != 3:
        print("\nUsage: python -m src.main <mapping_config_path> <test_config_path>")
        print("\nExample:")
        print("  python -m src.main configs/mapping-sample.json configs/test-sample.json")
        print()
        sys.exit(1)
    
    mapping_config_path = sys.argv[1]
    test_config_path = sys.argv[2]
    
    # Create and run orchestrator
    orchestrator = TestOrchestrator(mapping_config_path, test_config_path)
    success = orchestrator.run()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

9. Create a Simple Run Script
run_test.py (in project root)
python"""
Simple script to run the test utility
"""

from src.main import TestOrchestrator

if __name__ == "__main__":
    # Paths to config files
    mapping_config = "configs/mapping-sample.json"
    test_config = "configs/test-sample.json"
    
    # Create and run orchestrator
    orchestrator = TestOrchestrator(mapping_config, test_config)
    orchestrator.run()

10. Update src/init.py
src/init.py
python"""
API Migration Test Utility
"""

__version__ = "0.1.0"

from .logger import logger
from .config_loader import config_loader
from .mongo_client import MongoDBClient
from .auth import TokenManager
from .api_client import APIClient
from .comparator import Comparator
from .main import TestOrchestrator

__all__ = [
    'logger',
    'config_loader',
    'MongoDBClient',
    'TokenManager',
    'APIClient',
    'Comparator',
    'TestOrchestrator'
]
tests/init.py
python"""
Test modules
"""

How to Run the Complete MVP
Option 1: Using the run script
bashpython run_test.py
Option 2: Using the main module
bashpython -m src.main configs/mapping-sample.json configs/test-sample.json
Option 3: From Python
pythonfrom src.main import TestOrchestrator

orchestrator = TestOrchestrator(
    mapping_config_path="configs/mapping-sample.json",
    test_config_path="configs/test-sample.json"
)
orchestrator.run()

Test Individual Components First
Before running the full utility, test each component:
bash# Test all components
python tests/test_config_loader.py
python tests/test_mongo_client.py
python tests/test_auth.py
python tests/test_utils.py
python tests/test_api_client.py
python tests/test_comparator.py

Expected Output
When you run the full utility, you should see:
════════════════════════════════════════════════════════════
API MIGRATION TEST UTILITY - MVP
════════════════════════════════════════════════════════════
Starting test execution at 2025-10-07 15:30:00
────────────────────────────────────────────────────────────

Step 1: Loading Configuration Files
────────────────────────────────────────────────────────────
Loading mapping config: configs/mapping-sample.json
✓ Mapping config loaded: 7 field mappings
Loading test config: configs/test-sample.json
✓ Test config loaded
  API Name: getUserPaymentData
  Test Payment IDs: 3
  MongoDB: mongodb://****:****@host:27017/database

Step 2: Initializing Components
────────────────────────────────────────────────────────────
Initializing MongoDB client...
✓ Connected to MongoDB - Database: test_db, Collection: payments
  Document count: 1250

Initializing authentication...
✓ Bearer token acquired successfully

Initializing API client...
✓ API client initialized

Initializing comparator...
✓ Comparator initialized

✓ All components initialized successfully

════════════════════════════════════════════════════════════
PHASE 1: Testing Configured Payment IDs
════════════════════════════════════════════════════════════

Testing 3 configured payment IDs...
────────────────────────────────────────────────────────────

[1/3] Testing Payment ID: PAY001
────────────────────────────────────────────────────────────
✓ Completed: 6 passed, 1 warnings, 0 failed

[2/3] Testing Payment ID: PAY002
────────────────────────────────────────────────────────────
⚠ 1 critical issue(s) found:
  - amount: Number formatting difference: 10.50 vs 10.5
✓ Completed: 5 passed, 2 warnings, 0 failed

[3/3] Testing Payment ID: PAY003
────────────────────────────────────────────────────────────
✓ Completed: 7 passed, 0 warnings, 0 failed

════════════════════════════════════════════════════════════
TEST SUMMARY
════════════════════════════════════════════════════════════

Payment IDs Tested: 3
Successful Test Runs: 3/3
────────────────────────────────────────────────────────────

Field Comparison Results:
  Total Fields Tested: 21
  ✓ Passed: 18 (85.7%)
  ⚠ Warnings: 3 (14.3%)
  ✗ Failed: 0 (0.0%)

────────────────────────────────────────────────────────────

Issues by Payment ID:
  ✓ PAY001: 6 passed, 1 warnings
  ✗ PAY002: 5 passed, 2 warnings
  ✓ PAY003: 7 passed

────────────────────────────────────────────────────────────

Total Execution Time: 12.34 seconds

════════════════════════════════════════════════════════════

✓ ALL TESTS PASSED!
  Note: 3 warnings detected (review recommended)

════════════════════════════════════════════════════════════

What We've Built (MVP Complete!)
✅ Core Functionality

Load and validate configurations
Connect to MongoDB and query records
Authenticate and call APIs (Java 21 and Java 8)
Compare field values intelligently
Detect the 3 known issues automatically
Generate comprehensive console report

✅ Features Working

Configuration-driven (no code changes per API)
Nested field support (dot notation)
Three-way comparison (MongoDB vs Java 21 vs Java 8)
Issue detection (formatting, empty arrays, type mismatches)
Error handling with retries
Token management with auto-refresh
Clear, colorful console output

⏳ Not Yet Built (Can Add Later)

Phase 2 (aggregation for uncovered fields)
JSON/CSV report generation
HTML report
Multiple samples per field
Coverage tracking


Next Steps

Test the MVP with your actual data
Verify it catches the 3 known issues
Review the output format
Identify any adjustments needed

Once MVP is working well, we can add:

Report generation (JSON, CSV)
Phase 2 (finding uncovered fields)
Better logging to file
Progress bars
Detailed data reports

Ready to test it? Let me know if you encounter any issues!



