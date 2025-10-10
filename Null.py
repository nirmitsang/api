Excellent catch! I see the issue now. Looking at your MongoDB document:

```json
"Bbi": null
```

The field **exists** but has a `null` value.

---

## THE PROBLEM

Our current query is:

```javascript
{
  "MIFMP.Bbi": {
    "$exists": true,
    "$ne": null,
    "$ne": ""
  }
}
```

**MongoDB behavior:** The `$ne: null` check **does NOT work as expected** when combined with `$exists` in this way!

The issue is that MongoDB evaluates:
- `$exists: true` → ✅ Field exists (even if it's null)
- `$ne: null` → Should exclude nulls, but...

**The `$ne` operator can have unexpected behavior with null values in arrays and complex structures.**

---

## THE FIX

Use `$and` with explicit conditions and also check for the field not being `null` explicitly:

### **Update src/mongo_client.py - find_one_with_field method:**

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
        
        # Build query - ensure field exists AND is not null AND is not empty string
        # Use $and to be explicit about all conditions
        query = {
            '$and': [
                {cleaned_field: {'$exists': True}},
                {cleaned_field: {'$ne': None}},
                {cleaned_field: {'$ne': ""}},
                {cleaned_field: {'$type': ['string', 'number', 'bool', 'object', 'array']}}  # Exclude null type
            ]
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

---

## EVEN BETTER APPROACH: Use $type with $nin

MongoDB has a better way to exclude nulls - use `$type` to exclude the null type:

### **Alternative (Simpler) Query:**

```python
# Build query - exclude nulls by type
query = {
    cleaned_field: {
        '$exists': True,
        '$not': {'$type': 'null'},  # Explicitly exclude null type
        '$ne': ""  # Also exclude empty strings
    }
}
```

---

## BEST APPROACH: Combine Both

```python
# Build query with multiple safeguards against null values
query = {
    '$and': [
        {cleaned_field: {'$exists': True}},          # Field must exist
        {cleaned_field: {'$not': {'$type': 'null'}}},  # Field must not be null type
        {cleaned_field: {'$ne': ""}},                 # Field must not be empty string
        {cleaned_field: {'$ne': []}}                  # Field must not be empty array (for array fields)
    ]
}
```

---

## UPDATE: Complete Fixed Method

Replace the `find_one_with_field` method with this version:

```python
def find_one_with_field(self, field_name: str, payment_id_field: str, validation_regex: str = None) -> Optional[str]:
    """
    Find ONE document that has the specified field with non-null, non-empty value
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
        
        # Build query - robust null/empty checking
        query = {
            '$and': [
                {cleaned_field: {'$exists': True}},                 # Must exist
                {cleaned_field: {'$not': {'$type': 'null'}}},      # Must not be null
                {cleaned_field: {'$ne': ""}},                       # Must not be empty string
                {cleaned_field: {'$ne': []}}                        # Must not be empty array
            ]
        }
        
        # Project only payment ID field
        projection = {payment_id_field: 1}
        
        # DEBUG: Log the query
        _log('debug', f"Searching for document with field: {cleaned_field}")
        _log('debug', f"  Collection: {self.collection_name}")
        _log('debug', f"  Query (excluding nulls, empty strings, empty arrays)")
        _log('debug', f"  Validation regex: {validation_regex if validation_regex else 'None'}")
        
        # If we have a validation regex, we might need to try multiple documents
        max_attempts = 10 if validation_regex else 1
        
        for attempt in range(max_attempts):
            if attempt > 0:
                _log('debug', f"  Attempt {attempt + 1}/{max_attempts}")
            
            # Execute query
            documents = list(self.collection.find(query, projection).skip(attempt).limit(1))
            
            if not documents:
                _log('debug', f"  ✗ No document found with non-null value for {cleaned_field}")
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
                        _log('debug', f"  ✓ Found valid payment ID: {payment_id}")
                        return payment_id
                    else:
                        _log('debug', f"  ✗ Payment ID {payment_id} doesn't match regex, trying next...")
                        continue
                else:
                    _log('debug', f"  ✓ Found payment ID: {payment_id}")
                    return payment_id
        
        _log('debug', f"  ✗ No valid payment ID found after {max_attempts} attempts")
        return None
        
    except Exception as e:
        _log('error', f"Error searching for field {field_name}: {str(e)}")
        import traceback
        _log('debug', traceback.format_exc())
        return None
```

---

## TEST IN COMPASS FIRST

Try this query in MongoDB Compass:

```javascript
db.odsMPYPaymentDetail.find({
  "$and": [
    {"MIFMP.Bbi": {"$exists": true}},
    {"MIFMP.Bbi": {"$not": {"$type": "null"}}},
    {"MIFMP.Bbi": {"$ne": ""}},
    {"MIFMP.Bbi": {"$ne": []}}
  ]
})
```

This should **only** return documents where `MIFMP.Bbi` has an actual value (not null, not empty).

---

## RUN THE TEST

```bash
python run_test.py --debug
```

Now it should only pick documents with actual non-null values! 🎯

Let me know if this fixes it!
