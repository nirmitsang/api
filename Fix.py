Perfect! Now I understand the structure completely!

From your images, I can see:

**API Response Structure:**
```json
{
  "data": {
    "id": "MASSPAY",
    "type": "MASSPAY Payment Detailed",
    "attributes": {
      "paymentDetails": [
        {
          "mid": "23A172400000301",
          "messageInformation": {
            "accounts": {...},
            ...
          }
        }
      ]
    }
  }
}
```

**Your Mapping Config:**
```json
{
  "mongoField": "_id",
  "jsonAttribute": "paymentDetails.mid"
}
```

## The Problem

The actual path should be: `data.attributes.paymentDetails[0].mid`

But your mapping says: `paymentDetails.mid`

So we need to:
1. Navigate to `data.attributes.paymentDetails` 
2. Take the first element `[0]` from the array
3. Then access the field

---

## Solution: Update Test Config with Root Path

### **Update configs/test-sample.json**

Add `jsonResponseRootPath`:

```json
{
  "apiName": "getUserPaymentData",
  "jsonResponseRootPath": "data.attributes.paymentDetails.0",
  "paymentIdMapping": {
    "mongoField": "payment_id",
    "jsonAttribute": "mid"
  },
  "testPaymentIds": [
    "PAY001",
    "PAY002",
    "PAY003"
  ]
}
```

**Note:** The `.0` at the end means "take the first element of the paymentDetails array"

---

## Update Utils to Handle Array Index in Path

### **Update src/utils.py**

Replace the `get_nested_value` function:

```python
def get_nested_value(obj: Dict[str, Any], path: str) -> Any:
    """
    Get value from nested dictionary using dot notation with array index support
    
    Args:
        obj: Dictionary to extract value from
        path: Dot-separated path (e.g., "user.address.city" or "data.items.0.name")
    
    Returns:
        Value at the path, or None if not found
    
    Examples:
        >>> data = {"user": {"address": {"city": "New York"}}}
        >>> get_nested_value(data, "user.address.city")
        'New York'
        
        >>> data = {"data": {"items": [{"name": "John"}]}}
        >>> get_nested_value(data, "data.items.0.name")
        'John'
    """
    if not obj or not path:
        return None
    
    parts = path.split('.')
    current = obj
    
    for part in parts:
        if current is None:
            return None
        
        # Check if part is a numeric index (for arrays)
        if part.isdigit():
            index = int(part)
            if isinstance(current, list):
                if 0 <= index < len(current):
                    current = current[index]
                else:
                    return None
            else:
                return None
        
        # Regular key access
        elif isinstance(current, dict):
            if part in current:
                current = current[part]
            else:
                return None
        else:
            return None
    
    return current
```

---

## Update Comparator to Use Root Path

### **Update src/comparator.py**

Modify the `compare_field` method to apply root path:

```python
def compare_field(
    self,
    mongo_record: Dict[str, Any],
    java21_response: Optional[Dict[str, Any]],
    java8_response: Optional[Dict[str, Any]],
    mapping: Dict[str, str],
    json_root_path: Optional[str] = None  # ADD THIS PARAMETER
) -> Dict[str, Any]:
    """
    Compare a single field across MongoDB and API responses
    
    Args:
        mongo_record: MongoDB record
        java21_response: Java 21 API response
        java8_response: Java 8 API response (optional)
        mapping: Field mapping dict
        json_root_path: Root path to navigate to actual data (e.g., "data.attributes.paymentDetails.0")
    
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
            # Apply root path if provided
            response_data = java21_response
            if json_root_path:
                response_data = get_nested_value(java21_response, json_root_path)
                if response_data is None:
                    java21_error = f"Could not navigate to root path: {json_root_path}"
            
            if response_data and not java21_error:
                java21_value = get_nested_value(response_data, json_attribute)
    
    java8_value = None
    java8_error = None
    if java8_response:
        if 'success' in java8_response and not java8_response['success']:
            java8_error = java8_response.get('error', 'Unknown error')
        else:
            # Apply root path if provided
            response_data = java8_response
            if json_root_path:
                response_data = get_nested_value(java8_response, json_root_path)
                if response_data is None:
                    java8_error = f"Could not navigate to root path: {json_root_path}"
            
            if response_data and not java8_error:
                java8_value = get_nested_value(response_data, json_attribute)
    
    # Rest of the method stays the same...
    mongo_vs_java21 = self._compare_values(
        mongo_value, 
        java21_value, 
        mongo_type,
        "MongoDB",
        "Java 21"
    )
    
    java8_vs_java21 = None
    if java8_response and not java8_error:
        java8_vs_java21 = self._compare_values(
            java8_value,
            java21_value,
            mongo_type,
            "Java 8",
            "Java 21"
        )
    
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
```

---

## Update Main Orchestrator to Pass Root Path

### **Update src/main.py**

In the `_test_single_payment_id` method, pass the root path to comparator:

Find this section:
```python
# Step 3: Compare all fields
logger.debug("Comparing fields...")

for mapping in self.mapping_config:
    field_result = self.comparator.compare_field(
        mongo_record=mongo_record,
        java21_response=java21_result.get('data') if java21_result['success'] else java21_result,
        java8_response=java8_result.get('data') if java8_result and java8_result['success'] else java8_result,
        mapping=mapping
    )
```

**Replace with:**
```python
# Step 3: Compare all fields
logger.debug("Comparing fields...")

# Get root path from config if exists
json_root_path = self.test_config.get('jsonResponseRootPath')

for mapping in self.mapping_config:
    field_result = self.comparator.compare_field(
        mongo_record=mongo_record,
        java21_response=java21_result.get('data') if java21_result['success'] else java21_result,
        java8_response=java8_result.get('data') if java8_result and java8_result['success'] else java8_result,
        mapping=mapping,
        json_root_path=json_root_path  # ADD THIS
    )
```

---

## Update Your Mapping Config Paths

Based on your screenshot, update **configs/mapping-sample.json**:

```json
[
  {
    "mongoField": "_id",
    "mongoType": "string(int)",
    "jsonAttribute": "mid"
  },
  {
    "mongoField": "PkBtcSubset",
    "mongoType": "decimal(\"\")",
    "jsonAttribute": "messageInformation.pkBatchSubset"
  },
  {
    "mongoField": "MIFMP.DbAccNo",
    "mongoType": "string(int)",
    "jsonAttribute": "messageInformation.debit.accountNumber"
  },
  {
    "mongoField": "MIFMP.OutGngCrAmt",
    "mongoType": "decimal(\"\")",
    "jsonAttribute": "messageInformation.outgoingCreditAmount"
  },
  {
    "mongoField": "MIFMP.BsAmt",
    "mongoType": "decimal(\"\")",
    "jsonAttribute": "messageInformation.outgoingCreditBaseAmount"
  },
  {
    "mongoField": "MIFMP.BlkIdn",
    "mongoType": "string(int)",
    "jsonAttribute": "messageInformation.bulkingIndicator"
  },
  {
    "mongoField": "MIFMP.BtcCmpyCd",
    "mongoType": "string(int)",
    "jsonAttribute": "messageInformation.batch.companyCode"
  },
  {
    "mongoField": "MIFMP.BtcMsgTp",
    "mongoType": "string(int)",
    "jsonAttribute": "messageInformation.batch.messageType"
  },
  {
    "mongoField": "MIFMP.BtcPmtTp",
    "mongoType": "string(int)",
    "jsonAttribute": "messageInformation.batch.paymentType"
  }
]
```

**Key changes:**
- Removed the `paymentDetails.` prefix from all `jsonAttribute` values
- Now the paths are relative to the root path (`data.attributes.paymentDetails.0`)

---

## Test the Updated Utils

### **tests/test_utils.py**

Add this test case to verify array index handling:

```python
def test_array_index_in_path():
    """Test accessing array elements using numeric index"""
    logger.info("\n" + "="*60)
    logger.info("Test 7: Array Index in Path")
    logger.info("="*60)
    
    # Simulate your actual API structure
    test_data = {
        "data": {
            "attributes": {
                "paymentDetails": [
                    {
                        "mid": "23A172400000301",
                        "messageInformation": {
                            "accounts": {
                                "creditorAccountType": "NA"
                            }
                        }
                    }
                ]
            }
        }
    }
    
    test_cases = [
        {
            "path": "data.attributes.paymentDetails.0.mid",
            "expected": "23A172400000301",
            "description": "Access array element using index"
        },
        {
            "path": "data.attributes.paymentDetails.0.messageInformation.accounts.creditorAccountType",
            "expected": "NA",
            "description": "Deep nested path with array index"
        },
        {
            "path": "data.attributes.paymentDetails.1.mid",
            "expected": None,
            "description": "Index out of bounds (should return None)"
        }
    ]
    
    passed = 0
    failed = 0
    
    for idx, test in enumerate(test_cases, 1):
        result = get_nested_value(test_data, test["path"])
        
        if result == test["expected"]:
            logger.success(f"  ✓ Test {idx}: {test['description']}")
            logger.debug(f"    Path: {test['path']}")
            logger.debug(f"    Result: {result}")
            passed += 1
        else:
            logger.error(f"  ✗ Test {idx}: {test['description']}")
            logger.error(f"    Path: {test['path']}")
            logger.error(f"    Expected: {test['expected']}")
            logger.error(f"    Got: {result}")
            failed += 1
    
    logger.info(f"\n  Results: {passed} passed, {failed} failed")
    return failed == 0
```

Add this to the `run_all_tests()` function:
```python
all_passed &= test_array_index_in_path()
```

---

## Summary of Changes

1. **Test Config**: Added `"jsonResponseRootPath": "data.attributes.paymentDetails.0"`
2. **Utils**: Updated `get_nested_value()` to handle numeric indices
3. **Comparator**: Added `json_root_path` parameter and logic to navigate to root first
4. **Main**: Pass root path from config to comparator
5. **Mapping Config**: Simplified paths (removed `paymentDetails.` prefix)

---

## Now Test It

```bash
# Test utils first
python tests/test_utils.py

# Then run the full utility
python run_test.py
```

The CSV should now show actual values instead of null!

Let me know if this works!
