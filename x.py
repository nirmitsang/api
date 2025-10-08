I can see the issue now! Looking at your screenshots:

**From Image 1 & 2:**
```
✗ MIFMP not found in record
Top-level keys: ['_id', 'MessageRates', 'uncoveredFieldCount']
```

**But it's projecting:**
```
['MemPst[]', 'Msgerr[]', 'MsgFees[]', 'MsgNotes[]', 'MessageRates', 'MIFMP', 'Advices[]', 'Mfamily[]', 'MessageFreeText[]']
```

**From Image 3 (MongoDB query):**
```
"MsgFees.FxRte": { $exists: true, $ne: null, $ne: "" }
```
Returns 1602 documents!

---

## The Real Problem: Array Notation in Field Names

Looking at your uncovered fields, I see things like:
- `MsgFees[].FxRte` 
- `MsgFees[].FeeAmt`

The `[]` means this is an **ARRAY** field in MongoDB!

Your MongoDB structure is:
```javascript
{
  "_id": "...",
  "MsgFees": [        // ← This is an ARRAY
    {
      "FxRte": "value",
      "FeeAmt": 100
    }
  ],
  "MIFMP": {          // ← This is an OBJECT
    "Bbi": "value"
  }
}
```

---

## The Issue with Array Projection

When the pipeline tries to match:
```javascript
{ "MsgFees[].FxRte": { $exists: true } }  // ← This syntax is WRONG!
```

**MongoDB doesn't understand `MsgFees[].FxRte`** in the $match stage. It thinks you're looking for a field literally named `"MsgFees[].FxRte"` (with brackets in the name), which doesn't exist!

---

## Solution: Strip the `[]` from Field Names in Aggregation

The `[]` notation is just for documentation in your mapping config. In actual MongoDB queries, we need to use `MsgFees.FxRte` (without brackets).

### **Fix the aggregation_builder.py**

Update the `build_pipeline` method to handle array notation:

```python
def build_pipeline(
    self,
    uncovered_mappings: List[Dict[str, str]],
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Build aggregation pipeline to find records with uncovered fields
    
    Strategy: Find records that have ANY of the uncovered fields with data,
    then rank them by how many uncovered fields they contain.
    
    Args:
        uncovered_mappings: List of mapping dicts for uncovered fields
        limit: Maximum number of candidate records to return
    
    Returns:
        MongoDB aggregation pipeline
    """
    if not uncovered_mappings:
        return []
    
    # Extract MongoDB field names and clean array notation
    uncovered_fields = []
    for m in uncovered_mappings:
        field = m['mongoField']
        # Remove [] notation from field names (e.g., "MsgFees[].FxRte" → "MsgFees.FxRte")
        # This is needed for MongoDB queries
        cleaned_field = field.replace('[]', '')
        uncovered_fields.append(cleaned_field)
    
    logger.debug(f"Building aggregation for {len(uncovered_fields)} uncovered fields")
    logger.debug(f"Sample cleaned fields: {uncovered_fields[:3]}")
    
    # Build $or conditions for $match stage
    match_conditions = []
    for field in uncovered_fields:
        match_conditions.append({
            field: {
                '$exists': True,
                '$ne': None,
                '$ne': ""
            }
        })
    
    # Build expressions to count how many uncovered fields each document has
    count_expressions = []
    for field in uncovered_fields:
        field_ref = self._get_field_reference(field)
        count_expressions.append({
            '$cond': [
                {
                    '$and': [
                        {'$ne': [field_ref, None]},
                        {'$ne': [field_ref, ""]},
                        {'$ne': [field_ref, []]}
                    ]
                },
                1,
                0
            ]
        })
    
    # Build projection to include all fields we need
    # Group fields by their top-level parent
    top_level_objects = set()
    for field in uncovered_fields:
        if '.' in field:
            top_level = field.split('.')[0]
            top_level_objects.add(top_level)
        else:
            # Non-nested field
            top_level_objects.add(field)
    
    # Build project stage
    project_fields = {
        self.payment_id_field: 1,
        'uncoveredFieldCount': 1
    }
    
    # Include all top-level objects
    for top_level in top_level_objects:
        project_fields[top_level] = 1
    
    logger.debug(f"Will project these top-level objects: {list(top_level_objects)}")
    
    # Build the pipeline
    pipeline = [
        # Stage 1: Match records with ANY uncovered field
        {
            '$match': {
                '$or': match_conditions
            }
        },
        
        # Stage 2: Add field counting
        {
            '$addFields': {
                'uncoveredFieldCount': {
                    '$add': count_expressions
                }
            }
        },
        
        # Stage 3: Filter out records with 0 count
        {
            '$match': {
                'uncoveredFieldCount': {'$gt': 0}
            }
        },
        
        # Stage 4: Sort by count (descending)
        {
            '$sort': {
                'uncoveredFieldCount': -1
            }
        },
        
        # Stage 5: Limit to top candidates
        {
            '$limit': limit
        },
        
        # Stage 6: Project the fields we need
        {
            '$project': project_fields
        }
    ]
    
    logger.debug(f"Pipeline stages: {len(pipeline)}")
    
    return pipeline
```

---

### **Also Update `select_optimal_records`**

The selection logic also needs to clean the array notation:

```python
def select_optimal_records(
    self,
    aggregation_results: List[Dict[str, Any]],
    uncovered_mappings: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Intelligently select minimal set of records for best coverage
    
    Strategy: Greedy algorithm - pick records that cover the most NEW fields
    
    Args:
        aggregation_results: Results from aggregation pipeline
        uncovered_mappings: List of mapping dicts for uncovered fields
    
    Returns:
        Dict with selected payment IDs and coverage info
    """
    # Clean field names (remove [] notation)
    uncovered_fields_original = set(m['mongoField'] for m in uncovered_mappings)
    uncovered_fields_cleaned = set()
    field_mapping = {}  # Map cleaned field → original field
    
    for original_field in uncovered_fields_original:
        cleaned_field = original_field.replace('[]', '')
        uncovered_fields_cleaned.add(cleaned_field)
        field_mapping[cleaned_field] = original_field
    
    covered_fields: Set[str] = set()
    selected_records = []
    
    logger.debug(f"Selecting optimal records from {len(aggregation_results)} candidates")
    logger.debug(f"Total uncovered fields to find: {len(uncovered_fields_cleaned)}")
    
    # DEBUG: Show structure of first record
    if len(aggregation_results) > 0:
        first_record = aggregation_results[0]
        logger.info("\n🔍 DEBUG: Inspecting first candidate record structure...")
        logger.info(f"  Top-level keys: {list(first_record.keys())}")
        
        # Check for common parent objects
        for obj_name in ['MIFMP', 'MsgFees', 'MessageRates', 'Msgerr']:
            if obj_name in first_record:
                obj_type = type(first_record[obj_name]).__name__
                logger.info(f"  ✓ {obj_name} exists and is type: {obj_type}")
                
                if isinstance(first_record[obj_name], dict):
                    logger.info(f"    {obj_name} sub-keys (first 5): {list(first_record[obj_name].keys())[:5]}")
                elif isinstance(first_record[obj_name], list) and len(first_record[obj_name]) > 0:
                    logger.info(f"    {obj_name} is array with {len(first_record[obj_name])} items")
                    if isinstance(first_record[obj_name][0], dict):
                        logger.info(f"    First item keys: {list(first_record[obj_name][0].keys())[:5]}")
            else:
                logger.warn(f"  ✗ {obj_name} not found in record")
        
        # Test accessing a few uncovered fields
        test_fields = list(uncovered_fields_cleaned)[:3]
        logger.info(f"\n  Testing access to {len(test_fields)} sample uncovered fields:")
        for field in test_fields:
            value = self._get_field_from_record(first_record, field)
            original_field = field_mapping.get(field, field)
            if value is not None and value != "" and value != []:
                logger.success(f"    ✓ {original_field} (as {field}): {value}")
            else:
                logger.warn(f"    ✗ {original_field} (as {field}): {value} (empty or None)")
    
    # Now do the actual selection using CLEANED field names
    for idx, record in enumerate(aggregation_results):
        new_fields = []
        fields_checked = 0
        fields_found = 0
        
        for cleaned_field in uncovered_fields_cleaned:
            if cleaned_field not in covered_fields:
                fields_checked += 1
                value = self._get_field_from_record(record, cleaned_field)
                
                if value is not None and value != "" and value != []:
                    new_fields.append(cleaned_field)
                    fields_found += 1
        
        if idx < 3:
            logger.debug(f"\n  Record {idx}: Checked {fields_checked} fields, found {fields_found} with data")
        
        if new_fields:
            payment_id = self._get_field_from_record(record, self.payment_id_field)
            
            if payment_id:
                # Convert back to original field names for reporting
                original_new_fields = [field_mapping.get(f, f) for f in new_fields]
                
                selected_records.append({
                    'paymentId': payment_id,
                    'coversFields': original_new_fields,  # Use original names
                    'totalUncoveredFields': record.get('uncoveredFieldCount', len(new_fields))
                })
                
                covered_fields.update(new_fields)
                
                logger.info(f"  ✓ Selected {payment_id}: covers {len(new_fields)} new fields")
                if idx < 3:
                    logger.debug(f"    Fields: {original_new_fields[:5]}{'...' if len(original_new_fields) > 5 else ''}")
        
        if len(covered_fields) == len(uncovered_fields_cleaned):
            logger.debug("  All uncovered fields now have coverage candidates")
            break
    
    still_uncovered = uncovered_fields_cleaned - covered_fields
    still_uncovered_original = [field_mapping.get(f, f) for f in still_uncovered]
    
    logger.info(f"\n📊 Selection complete:")
    logger.info(f"  Records selected: {len(selected_records)}")
    logger.info(f"  Fields covered: {len(covered_fields)}/{len(uncovered_fields_cleaned)}")
    logger.info(f"  Still uncovered: {len(still_uncovered)}")
    
    if len(still_uncovered) > 0 and len(still_uncovered) <= 10:
        logger.info(f"  Uncovered fields: {still_uncovered_original}")
    
    return {
        'selectedRecords': selected_records,
        'coveredCount': len(covered_fields),
        'stillUncoveredCount': len(still_uncovered),
        'stillUncoveredFields': still_uncovered_original  # Use original names
    }
```

---

### **Update `_get_field_from_record` to Handle Arrays**

```python
def _get_field_from_record(self, record: Dict[str, Any], field_path: str) -> Any:
    """
    Get field value from record, handling dot notation and arrays
    
    Args:
        record: MongoDB record
        field_path: Field path (e.g., "MIFMP.DbAccNo" or "MsgFees.FxRte")
                   Note: Array notation [] should already be removed
    
    Returns:
        Field value or None
    """
    if not record or not field_path:
        return None
    
    parts = field_path.split('.')
    current = record
    
    for i, part in enumerate(parts):
        if current is None:
            return None
        
        # If current is an array, access the first element
        if isinstance(current, list):
            if len(current) == 0:
                return None
            current = current[0]  # Take first element
        
        # Now access the key
        if isinstance(current, dict):
            if part in current:
                current = current[part]
            else:
                return None
        else:
            return None
    
    return current
```

---

## Summary of Changes

**Problem:** Field names like `MsgFees[].FxRte` don't work in MongoDB queries.

**Solution:**
1. **Clean field names:** Remove `[]` before using in aggregation → `MsgFees.FxRte`
2. **Handle arrays in access:** When navigating, if we encounter an array, take the first element `[0]`
3. **Track mapping:** Keep track of original field names for reporting

---

## What Should Happen Now

After these changes:

```
✓ MsgFees exists and is type: list
  MsgFees is array with 3 items
  First item keys: ['FxRte', 'FeeAmt', ...]

Testing access to 3 sample uncovered fields:
  ✓ MsgFees[].FxRte (as MsgFees.FxRte): 0.85
  ✓ MsgFees[].FeeAmt (as MsgFees.FeeAmt): 100
  ✓ MIFMP.OrgAdr1 (as MIFMP.OrgAdr1): Some Address

Record 0: Checked 137 fields, found 82 with data
✓ Selected 2450924000000050A: covers 82 new fields
```

---

**Replace the entire `aggregation_builder.py` file with these fixes and run again!**

Let me know what happens!
