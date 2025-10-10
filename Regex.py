Perfect analysis! Let's fix both issues systematically.

---

## FIX 1: Add Payment ID Regex Validation

### **Step 1: Update configs/test-sample.json**

Add a regex pattern for payment ID validation:

```json
{
  "apiName": "getUserPaymentData",
  
  "mongoConnectionString": "${MONGO_CONNECTION_STRING}",
  "mongoDatabase": "odsCorporate",
  "mongoCollection": "odsMPYPaymentDetail",
  
  "tokenUrl": "https://your-auth-server.com/auth/token",
  
  "java21Url": "https://your-api-server.com/api/v1/payment/details",
  "java8Url": "https://your-legacy-server.com/api/v1/payment/details",
  
  "jsonResponseRootPath": "data.payload",
  
  "paymentIdMapping": {
    "mongoField": "_id",
    "jsonAttribute": "messageId",
    "validationRegex": "^[0-9A-Z]{1,16}$"
  },
  
  "testPaymentIds": [
    "2380924000000930",
    "2450924000000050",
    "2130913013200610"
  ]
}
```

### **Step 2: Update src/mongo_client.py**

Add regex validation to `find_one_with_field` method:

```python
def find_one_with_field(self, field_name: str, payment_id_field: str, validation_regex: str = None) -> Optional[str]:
    """
    Find ONE document that has the specified field with non-null value
    Used in Phase 2 to find payment IDs for uncovered attributes
    
    Args:
        field_name: MongoDB field name to search for
        payment_id_field: Payment ID field name to extract
        validation_regex: Optional regex pattern to validate payment ID format
    
    Returns:
        Payment ID if found and valid, None otherwise
    """
    if self.collection is None:
        _log('error', "Not connected to MongoDB")
        return None
    
    try:
        import re
        
        # Clean array notation from field name
        cleaned_field = field_name.replace('[]', '')
        
        # Build query
        query = {
            cleaned_field: {
                '$exists': True,
                '$ne': None,
                '$ne': ""
            }
        }
        
        # Project only payment ID field
        projection = {payment_id_field: 1}
        
        # DEBUG: Log the query
        _log('debug', f"Searching for document with field: {cleaned_field}")
        _log('debug', f"  Collection: {self.collection_name}")
        _log('debug', f"  Query: {query}")
        _log('debug', f"  Validation regex: {validation_regex if validation_regex else 'None'}")
        
        # If we have a validation regex, we might need to try multiple documents
        max_attempts = 10 if validation_regex else 1
        
        for attempt in range(max_attempts):
            # Skip documents we've already checked
            if attempt > 0:
                _log('debug', f"  Attempt {attempt + 1}/{max_attempts} - previous payment ID didn't match regex")
            
            # Execute query
            documents = list(self.collection.find(query, projection).skip(attempt).limit(1))
            
            if not documents:
                _log('debug', f"  ✗ No more documents found")
                return None
            
            document = documents[0]
            
            if payment_id_field in document:
                payment_id = document[payment_id_field]
                
                # Convert ObjectId to string if it's _id
                if payment_id_field == '_id' and hasattr(payment_id, '__str__'):
                    payment_id = str(payment_id)
                
                # Validate against regex if provided
                if validation_regex:
                    if re.match(validation_regex, str(payment_id)):
                        _log('debug', f"  ✓ Found valid payment ID: {payment_id} (matches regex)")
                        return payment_id
                    else:
                        _log('debug', f"  ✗ Payment ID {payment_id} doesn't match regex pattern")
                        continue  # Try next document
                else:
                    # No validation needed
                    _log('debug', f"  ✓ Found payment ID: {payment_id}")
                    return payment_id
        
        # If we exhausted all attempts
        _log('debug', f"  ✗ No valid payment ID found after {max_attempts} attempts")
        return None
        
    except Exception as e:
        _log('error', f"Error searching for field {field_name}: {str(e)}")
        return None
```

### **Step 3: Update src/main.py - run_phase_2 method**

Pass the validation regex to the find method:

```python
def run_phase_2(self):
    """Execute Phase 2: Find and test uncovered attributes"""
    self.logger.header("PHASE 2: Finding Records for Uncovered Attributes")
    
    # Get uncovered attributes
    uncovered_mappings = self.coverage_tracker.get_uncovered_mappings()
    
    if not uncovered_mappings:
        self.logger.info("All attributes covered in Phase 1! Phase 2 not needed.")
        return
    
    self.logger.info(f"{len(uncovered_mappings)} attributes not yet covered")
    self.logger.info("Searching for payment IDs with these attributes...\n")
    
    # Find payment IDs for uncovered attributes
    payment_ids_to_test: Set[str] = set()
    payment_id_field = self.test_config['paymentIdMapping']['mongoField']
    
    # Get validation regex from config (optional)
    validation_regex = self.test_config['paymentIdMapping'].get('validationRegex')
    
    if validation_regex:
        self.logger.debug(f"Payment ID validation regex: {validation_regex}")
    
    self.logger.info("Querying MongoDB for uncovered attributes...")
    
    for idx, mapping in enumerate(uncovered_mappings, 1):
        mongo_field = mapping['mongoField']
        json_attr = mapping['jsonAttribute']
        
        self.logger.debug(f"[{idx}/{len(uncovered_mappings)}] {json_attr}")
        
        # Find payment ID with this field (with regex validation)
        payment_id = self.mongo_client.find_one_with_field(
            mongo_field, 
            payment_id_field,
            validation_regex  # Pass regex for validation
        )
        
        if payment_id:
            if payment_id not in payment_ids_to_test:
                payment_ids_to_test.add(payment_id)
                self.logger.debug(f"  → Added {payment_id} to test queue")
            else:
                self.logger.debug(f"  → {payment_id} already in queue")
        else:
            self.logger.debug(f"  → No valid data found")
    
    # ... rest of the method stays the same
```

---

## FIX 2: Array Notation Mismatch in Response Parser

The issue is that your mapping has:
```json
"jsonAttribute": "messages[].amount"
```

But the response parser extracts it as:
```
"messages.amount"  (without the [])
```

So when comparing, it can't find the mapping!

### **Step 4: Update src/response_parser.py**

Modify to handle array attributes correctly:

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
            List of all attribute paths in dot notation (with [] for arrays)
        
        Example:
            Input: {"user": {"name": "John"}, "items": [{"id": 1}]}
            Output: ["user.name", "items[].id"]
        """
        attributes = []
        
        if isinstance(response, dict):
            for key, value in response.items():
                current_path = f"{prefix}.{key}" if prefix else key
                
                if isinstance(value, dict):
                    # Recurse into nested dict
                    attributes.extend(self.extract_all_attributes(value, current_path))
                elif isinstance(value, list):
                    # Handle list - add [] notation and extract from first element
                    if len(value) > 0 and isinstance(value[0], dict):
                        # Add [] to indicate array
                        array_path = f"{current_path}[]"
                        # Extract attributes from first element with [] prefix
                        child_attrs = self.extract_all_attributes(value[0], array_path)
                        attributes.extend(child_attrs)
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
                        array_path = f"{current_path}[]"
                        result.update(self.extract_attributes_with_values(value[0], array_path))
                    else:
                        result[current_path] = value
                else:
                    result[current_path] = value
        
        return result
```

### **Step 5: Update src/main.py - test_single_payment_id method**

Now the response parser returns `messages[].amount`, which will match the mapping `messages[].amount`:

```python
# In test_single_payment_id method, in Step 6:

for attribute in response_attributes:
    # Look up MongoDB field for this attribute
    mongo_field = self.json_to_mongo_map.get(attribute)
    
    if not mongo_field:
        # This attribute is not in our mapping config - skip it
        self.logger.debug(f"    Skipping {attribute} (not in mapping)")
        continue
    
    # Get values from all sources
    # For response attributes, remove [] for value extraction
    attribute_for_extraction = attribute.replace('[]', '')
    
    mongo_value = get_nested_value(mongo_doc, mongo_field.replace('[]', ''))
    java21_value = get_nested_value(java21_response, attribute_for_extraction)
    java8_value = get_nested_value(java8_response, attribute_for_extraction) if java8_response else None
    
    # ... rest stays the same
```

---

## SUMMARY OF CHANGES

**Config (test-sample.json):**
- Added `validationRegex` to `paymentIdMapping`

**mongo_client.py:**
- Added `validation_regex` parameter to `find_one_with_field`
- Tries up to 10 documents to find one matching regex
- Validates payment ID against regex pattern

**main.py:**
- Passes validation regex to MongoDB queries in Phase 2
- Handles array notation properly when extracting values

**response_parser.py:**
- Now returns `messages[].amount` instead of `messages.amount`
- Matches the mapping config format exactly

---

## TEST IT

1. Add `validationRegex` to your config
2. Run the test:

```bash
python run_test.py --debug
```

You should see:
- Payment IDs validated against regex
- Array attributes like `messages[].amount` properly matched
- Many fewer "not in mapping" skips

Let me know how it goes! 🚀
