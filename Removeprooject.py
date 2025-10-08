Perfect! Now I can see the EXACT problem!

---

## The Problem is Crystal Clear

From **Image 3**, the debug output shows:

```
Top-level keys: ['_id', 'uncoveredFieldCount']

Trying to access: _id
  ✓ Found: PCTA000CA068

Trying to access: PkBtcSubset
  ✗ Not found or empty: None

Trying to access: MIFMP.DbAccNo
  ✗ Not found or empty: None
```

**The aggregation is returning ONLY `_id` and `uncoveredFieldCount`** - it's NOT returning the actual data fields (MIFMP, MsgFees, PkBtcSubset, etc.)!

---

## Why This Happens

Look at **Image 2** - the pipeline is projecting:

```
Will project these top-level objects: ['MIFMP', 'PkBtcSubset', '_id']
```

But the **returned record only has:** `['_id', 'uncoveredFieldCount']`

This means **the $project stage is NOT working as expected**.

---

## The Root Cause

The issue is that some of your fields are **NOT nested objects**. Looking at your mapping:

- `PkBtcSubset` - This is a TOP-LEVEL field (not nested)
- `MIFMP.DbAccNo` - This is nested under MIFMP
- `_id` - Top-level field

When we extract "top-level objects" from `PkBtcSubset`, we get `PkBtcSubset` (correct).
When we extract from `MIFMP.DbAccNo`, we get `MIFMP` (correct).

But the $project is built like:
```javascript
{
  $project: {
    '_id': 1,
    'MIFMP': 1,
    'PkBtcSubset': 1,
    'uncoveredFieldCount': 1
  }
}
```

**But these fields don't exist in the documents after $addFields!**

---

## The Real Issue: $addFields Creates New Structure

When MongoDB processes `$addFields` with nested field references like `$MIFMP.DbAccNo`, it might be creating a **new structure** or the fields are getting lost.

---

## Solution: Remove $project Stage Completely

Let's just NOT project anything and return the full documents. MongoDB will include all fields by default.

### **Update src/aggregation_builder.py - build_pipeline method**

Replace the entire `build_pipeline` method with this simpler version:

```python
def build_pipeline(
    self,
    uncovered_mappings: List[Dict[str, str]],
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Build aggregation pipeline to find records with uncovered fields
    
    Args:
        uncovered_mappings: List of mapping dicts for uncovered fields
        limit: Maximum number of candidate records to return
    
    Returns:
        MongoDB aggregation pipeline
    """
    if not uncovered_mappings:
        return []
    
    # Clean array notation from field names
    uncovered_fields = []
    for m in uncovered_mappings:
        field = m['mongoField']
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
    
    # Build the pipeline WITHOUT $project stage
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
        }
        
        # NO STAGE 6 - Just return full documents!
    ]
    
    logger.debug(f"Pipeline has {len(pipeline)} stages (no projection)")
    
    return pipeline
```

**Key change:** Removed the entire $project stage. MongoDB will return full documents with all fields.

---

## Why This Will Work

**Without $project:**
- MongoDB returns the **complete original document** from the collection
- Plus the `uncoveredFieldCount` field we added
- All your MIFMP, MsgFees, PkBtcSubset fields will be there!

**The Compass query confirmed this works:**
```javascript
db.odsMPYPaymentDetail.aggregate([
  { $match: { "MsgFees.FxRte": { $exists: true, $ne: null, $ne: "" } } },
  { $limit: 1 },
  { $project: { "_id": 1, "MsgFees": 1, "MIFMP": 1 } }
])
```

This returned the full objects because $project explicitly listed them. But when we try to build that dynamically, something goes wrong.

**Solution:** Don't use $project at all - just return everything!

---

## Test It

1. Update the `build_pipeline` method as shown above
2. Run the debug script again:

```bash
python debug_aggregation.py
```

**You should now see:**

```
Top-level keys: ['_id', 'MIFMP', 'MsgFees', 'PkBtcSubset', 'MessageRates', 'Msgerr', ... 'uncoveredFieldCount']

Trying to access: PkBtcSubset
  ✓ Found: [some value]

Trying to access: MIFMP.DbAccNo
  ✓ Found: 20687774157699
```

---

## Then Run Full Test

```bash
python run_test.py
```

**Expected Phase 2 output:**

```
✓ Found 100 candidate records

Selecting optimal records for maximum coverage...
  Record 0: Checked 10 fields, found 8 with data
  ✓ Selected [PaymentID]: covers 8 new fields

  Record 1: Checked 10 fields, found 3 with data
  ✓ Selected [PaymentID]: covers 3 new fields

📊 Selection complete:
  Records selected: 5
  Fields covered: 10/10
  Still uncovered: 0
```

---

## Why We Struggled With This

The problem was **MongoDB's behavior with $addFields + $project** on nested fields. When you:

1. Use `$addFields` with references like `$MIFMP.DbAccNo`
2. Then use `$project` to select fields

MongoDB can sometimes "optimize away" the original fields or restructure the document in unexpected ways.

**The simple solution:** Don't project at all - just return full documents. They're a bit bigger, but Python can handle it fine, and all the data is there.

---

Update that one method and try again! This should finally work! 🎯
