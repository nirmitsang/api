"""
Debug script to inspect API response structure
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.config_loader import config_loader
from src.auth import TokenManager
from src.api_client import APIClient
from src.logger import logger


def debug_api_response():
    """Inspect the actual API response structure"""
    
    logger.header("DEBUGGING API RESPONSE STRUCTURE")
    
    # Load config
    try:
        test_config = config_loader.load_test_config('configs/test-sample.json')
    except Exception as e:
        logger.error(f"Failed to load config: {str(e)}")
        return
    
    # Initialize auth
    logger.info("\nStep 1: Getting authentication token...")
    token_manager = TokenManager(
        token_api_url=test_config['tokenApiUrl'],
        username=os.getenv('TOKEN_API_USERNAME'),
        password=os.getenv('TOKEN_API_PASSWORD')
    )
    
    token_result = token_manager.get_token()
    if not token_result['success']:
        logger.error(f"Failed to get token: {token_result.get('error')}")
        return
    
    logger.success("Token acquired")
    
    # Initialize API client
    api_client = APIClient(token_manager)
    
    # Make a test call
    logger.info("\nStep 2: Calling Java 21 API...")
    
    payment_id_field = test_config['paymentIdMapping']['jsonAttribute']
    test_payment_id = test_config['testPaymentIds'][0]
    
    request_body = {
        payment_id_field: test_payment_id
    }
    
    logger.info(f"Request body: {json.dumps(request_body, indent=2)}")
    logger.info(f"Calling: {test_config['java21ApiUrl']}")
    
    result = api_client.call_api(
        url=test_config['java21ApiUrl'],
        request_body=request_body
    )
    
    if not result['success']:
        logger.error(f"API call failed: {result.get('error')}")
        return
    
    logger.success("API call successful!")
    
    # Inspect the response structure
    logger.separator()
    logger.header("RAW API RESPONSE STRUCTURE")
    
    response_data = result['data']
    
    print("\n" + "="*70)
    print("FULL RESPONSE (Pretty Printed):")
    print("="*70)
    print(json.dumps(response_data, indent=2, default=str))
    
    print("\n" + "="*70)
    print("TOP LEVEL KEYS:")
    print("="*70)
    if isinstance(response_data, dict):
        for key in response_data.keys():
            value = response_data[key]
            value_type = type(value).__name__
            
            if isinstance(value, dict):
                print(f"  {key}: {value_type} with {len(value)} keys")
                print(f"    Sub-keys: {list(value.keys())[:5]}")  # First 5 sub-keys
            elif isinstance(value, list):
                print(f"  {key}: {value_type} with {len(value)} items")
                if len(value) > 0 and isinstance(value[0], dict):
                    print(f"    First item keys: {list(value[0].keys())[:5]}")
            else:
                value_str = str(value)[:50]  # First 50 chars
                print(f"  {key}: {value_type} = {value_str}")
    else:
        print(f"Response is not a dict! It's a {type(response_data).__name__}")
    
    # Now let's test accessing a field from mapping
    logger.separator()
    logger.header("TESTING FIELD ACCESS FROM MAPPING")
    
    mapping_config = config_loader.load_mapping_config('configs/mapping-sample.json')
    
    print("\n" + "="*70)
    print("ATTEMPTING TO ACCESS MAPPED FIELDS:")
    print("="*70)
    
    from src.utils import get_nested_value
    
    for mapping in mapping_config[:5]:  # Test first 5 mappings
        json_path = mapping['jsonAttribute']
        mongo_field = mapping['mongoField']
        
        print(f"\nMapping: {mongo_field} → {json_path}")
        
        value = get_nested_value(response_data, json_path)
        
        if value is not None:
            logger.success(f"  ✓ Found value: {value}")
        else:
            logger.error(f"  ✗ Value is None - path may be incorrect")
            
            # Try to suggest the correct path
            print(f"  Attempting to find field in response...")
            
            # Check if the field name exists anywhere
            def find_key_in_nested(obj, target_key, current_path=""):
                """Recursively find a key in nested structure"""
                results = []
                
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        new_path = f"{current_path}.{key}" if current_path else key
                        
                        # Check if this key matches (case-insensitive partial match)
                        if target_key.lower() in key.lower() or key.lower() in target_key.lower():
                            results.append((new_path, value))
                        
                        # Recurse
                        results.extend(find_key_in_nested(value, target_key, new_path))
                
                elif isinstance(obj, list) and len(obj) > 0:
                    # Check first item in array
                    results.extend(find_key_in_nested(obj[0], target_key, f"{current_path}[0]"))
                
                return results
            
            # Extract the final field name from the path
            final_field_name = json_path.split('.')[-1]
            
            matches = find_key_in_nested(response_data, final_field_name)
            
            if matches:
                print(f"  Possible paths for '{final_field_name}':")
                for path, value in matches[:3]:  # Show first 3 matches
                    value_str = str(value)[:50]
                    print(f"    - {path} = {value_str}")
            else:
                print(f"  Could not find '{final_field_name}' anywhere in response")
    
    logger.separator()
    
    print("\n" + "="*70)
    print("WHAT TO DO NEXT:")
    print("="*70)
    print("1. Look at the 'FULL RESPONSE' above")
    print("2. Identify where your actual data fields are")
    print("3. Update your mapping config JSON paths accordingly")
    print("4. The paths should match the actual structure you see")
    print("="*70 + "\n")


if __name__ == "__main__":
    debug_api_response()
