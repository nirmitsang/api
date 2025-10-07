Good catch! The issue is that when the API returns data, we're wrapping it in a result dictionary with `success` and `data` keys, but when we pass it to the comparator, we need to pass just the `data` part, not the whole wrapper.

Let me show you the exact fix:

---

## The Problem

In `_test_single_payment_id` method, we're passing the entire API result object to the comparator:

```python
# CURRENT (WRONG)
field_result = self.comparator.compare_field(
    mongo_record=mongo_record,
    java21_response=java21_result.get('data') if java21_result['success'] else java21_result,
    java8_response=java8_result.get('data') if java8_result and java8_result['success'] else java8_result,
    mapping=mapping
)
```

The comparator is checking for `'success'` key to detect errors, but when API succeeds, we should pass ONLY the data, not the wrapper.

---

## The Fix

### **Update src/comparator.py**

Change the `compare_field` method to handle the data correctly:

**Find this section (around line 25-45):**

```python
def compare_field(
    self,
    mongo_record: Dict[str, Any],
    java21_response: Optional[Dict[str, Any]],
    java8_response: Optional[Dict[str, Any]],
    mapping: Dict[str, str]
) -> Dict[str, Any]:
    """
    Compare a single field across MongoDB and API responses
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
```

**Replace it with this:**

```python
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
        java21_response: Java 21 API response data (NOT the wrapper with success/error)
        java8_response: Java 8 API response data (NOT the wrapper with success/error)
        mapping: Field mapping dict with 'mongoField', 'jsonAttribute', 'mongoType'
    
    Returns:
        Dict with comparison results
    """
    
    # Extract values
    mongo_field = mapping['mongoField']
    json_attribute = mapping['jsonAttribute']
    mongo_type = mapping.get('mongoType', 'Unknown')
    
    mongo_value = get_nested_value(mongo_record, mongo_field)
    
    # Java 21 value extraction
    java21_value = None
    java21_error = None
    if java21_response is not None:
        # Check if it's an error response (has 'error' key but no 'data')
        if isinstance(java21_response, dict) and 'error' in java21_response and 'success' in java21_response:
            if not java21_response['success']:
                java21_error = java21_response.get('error', 'Unknown error')
        else:
            # It's actual response data, extract the field
            java21_value = get_nested_value(java21_response, json_attribute)
    
    # Java 8 value extraction
    java8_value = None
    java8_error = None
    if java8_response is not None:
        # Check if it's an error response
        if isinstance(java8_response, dict) and 'error' in java8_response and 'success' in java8_response:
            if not java8_response['success']:
                java8_error = java8_response.get('error', 'Unknown error')
        else:
            # It's actual response data, extract the field
            java8_value = get_nested_value(java8_response, json_attribute)
```

---

### **Update src/main.py**

Now fix how we call the comparator. Find the section in `_test_single_payment_id` where we compare fields (around line 170-180):

**Find this:**

```python
for mapping in self.mapping_config:
    field_result = self.comparator.compare_field(
        mongo_record=mongo_record,
        java21_response=java21_result.get('data') if java21_result['success'] else java21_result,
        java8_response=java8_result.get('data') if java8_result and java8_result['success'] else java8_result,
        mapping=mapping
    )
```

**Replace with this:**

```python
for mapping in self.mapping_config:
    # Prepare responses for comparator
    # If API call succeeded, pass the data; if failed, pass error dict
    java21_data = None
    if java21_result['success']:
        java21_data = java21_result.get('data')
    else:
        # Pass error information
        java21_data = {
            'success': False,
            'error': java21_result.get('error', 'Unknown error')
        }
    
    java8_data = None
    if java8_result:
        if java8_result['success']:
            java8_data = java8_result.get('data')
        else:
            # Pass error information
            java8_data = {
                'success': False,
                'error': java8_result.get('error', 'Unknown error')
            }
    
    field_result = self.comparator.compare_field(
        mongo_record=mongo_record,
        java21_response=java21_data,
        java8_response=java8_data,
        mapping=mapping
    )
```

---

## Alternative Simpler Fix (If Above Doesn't Work)

If the above still doesn't work, let's add debug logging to see what we're actually getting:

### **Add Debug Logging in comparator.py**

Add this right after extracting values in `compare_field`:

```python
# Extract values
mongo_field = mapping['mongoField']
json_attribute = mapping['jsonAttribute']
mongo_type = mapping.get('mongoType', 'Unknown')

mongo_value = get_nested_value(mongo_record, mongo_field)

# DEBUG: Log what we're receiving
logger.debug(f"\n--- Comparing field: {json_attribute} ---")
logger.debug(f"Mongo field: {mongo_field}")
logger.debug(f"Java21 response type: {type(java21_response)}")
if java21_response:
    logger.debug(f"Java21 response keys: {list(java21_response.keys()) if isinstance(java21_response, dict) else 'Not a dict'}")
logger.debug(f"Java8 response type: {type(java8_response)}")
if java8_response:
    logger.debug(f"Java8 response keys: {list(java8_response.keys()) if isinstance(java8_response, dict) else 'Not a dict'}")

# Java 21 value extraction
java21_value = None
java21_error = None
# ... rest of the code
```

---

## Test the Fix

After making these changes:

```bash
python run_test.py
```

### **What to check in the output:**

1. Look for the debug logs showing what response structure we're receiving
2. Check if the CSV report now shows values in Java 21 and Java 8 columns
3. Check if the JSON report has populated values

---

## If Still Not Working - Additional Debugging

If values are still not showing, let's check the **API response structure**. Add this temporary debug code in `_test_single_payment_id`:

**After calling the APIs, add:**

```python
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

# DEBUG: Show API response structure
logger.debug(f"\n=== DEBUG: API Response Structure ===")
logger.debug(f"Java 21 result keys: {list(java21_result.keys())}")
logger.debug(f"Java 21 success: {java21_result.get('success')}")
if java21_result.get('success') and java21_result.get('data'):
    data_keys = list(java21_result['data'].keys())[:5]  # First 5 keys
    logger.debug(f"Java 21 data top-level keys: {data_keys}")
    logger.debug(f"Java 21 data type: {type(java21_result['data'])}")

if java8_result:
    logger.debug(f"Java 8 result keys: {list(java8_result.keys())}")
    logger.debug(f"Java 8 success: {java8_result.get('success')}")
    if java8_result.get('success') and java8_result.get('data'):
        data_keys = list(java8_result['data'].keys())[:5]
        logger.debug(f"Java 8 data top-level keys: {data_keys}")
logger.debug(f"=====================================\n")
```

---

## Most Likely Issue

Based on your description, I suspect the problem is:

1. **API responses have the data nested** (like `response.actualData.paymentInfo.amount`)
2. **We're passing the whole response** instead of just the relevant data part
3. **The comparator can't find the values** because it's looking in the wrong place

**The fix above should resolve this by:**
- Passing only the `data` part to the comparator (not the wrapper with success/error)
- Handling error cases separately
- Using `get_nested_value` correctly with the full path from your mapping config

---

**Try these fixes and let me know what you see in the debug output!** That will help us pinpoint exactly where the issue is.
