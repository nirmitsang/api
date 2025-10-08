Absolutely! Let's do systematic debugging to find the exact issue. We'll check everything step by step.

---

## Step 1: Verify Your Current Code

First, let's make sure you have the correct code in place.

### **Create a verification script: verify_code.py**

```python
"""
Verification script to check if all code is correct
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

print("="*70)
print("CODE VERIFICATION SCRIPT")
print("="*70)

# Check 1: Verify aggregation_builder.py exists and has the right methods
print("\n1. Checking aggregation_builder.py...")
try:
    from src.aggregation_builder import AggregationBuilder
    
    # Check if class has all required methods
    methods = ['__init__', 'build_pipeline', 'select_optimal_records', '_get_field_from_record', '_get_field_reference']
    
    for method in methods:
        if hasattr(AggregationBuilder, method):
            print(f"   ✓ Method '{method}' exists")
        else:
            print(f"   ✗ Method '{method}' MISSING!")
    
    # Check the build_pipeline method signature
    import inspect
    sig = inspect.signature(AggregationBuilder.build_pipeline)
    params = list(sig.parameters.keys())
    print(f"\n   build_pipeline parameters: {params}")
    
    # Check if field cleaning happens in build_pipeline
    source = inspect.getsource(AggregationBuilder.build_pipeline)
    if 'replace' in source and '[]' in source:
        print(f"   ✓ build_pipeline contains array notation cleaning code")
    else:
        print(f"   ✗ build_pipeline MISSING array notation cleaning code!")
    
except Exception as e:
    print(f"   ✗ Error loading aggregation_builder: {e}")

# Check 2: Verify utils.py has correct get_nested_value
print("\n2. Checking utils.py...")
try:
    from src.utils import get_nested_value
    
    # Test it
    test_data = {
        "MIFMP": {
            "BbkBic": "TEST123"
        },
        "MsgFees": [
            {"FxRte": 0.85, "FeeAmt": 100}
        ]
    }
    
    # Test nested object access
    result1 = get_nested_value(test_data, "MIFMP.BbkBic")
    if result1 == "TEST123":
        print(f"   ✓ Nested object access works: {result1}")
    else:
        print(f"   ✗ Nested object access FAILED: got {result1}, expected TEST123")
    
    # Test array access
    result2 = get_nested_value(test_data, "MsgFees")
    if isinstance(result2, list):
        print(f"   ✓ Array access works: got list with {len(result2)} items")
    else:
        print(f"   ✗ Array access FAILED: got {type(result2)}")
    
except Exception as e:
    print(f"   ✗ Error with utils: {e}")

# Check 3: Test the cleaning logic
print("\n3. Testing field name cleaning logic...")
try:
    test_fields = [
        "MIFMP.BbkBic",
        "MsgFees[].FxRte",
        "MsgFees[].FeeAmt",
        "MIFMP.OrgAdr1"
    ]
    
    print("   Original → Cleaned:")
    for field in test_fields:
        cleaned = field.replace('[]', '')
        print(f"     {field} → {cleaned}")
    
    print("   ✓ Cleaning logic works")
    
except Exception as e:
    print(f"   ✗ Error: {e}")

# Check 4: Load your mapping config and check field names
print("\n4. Checking mapping config...")
try:
    from src.config_loader import config_loader
    
    mapping = config_loader.load_mapping_config('configs/mapping-sample.json')
    
    # Count fields with array notation
    array_fields = [m for m in mapping if '[]' in m['mongoField']]
    normal_fields = [m for m in mapping if '[]' not in m['mongoField']]
    
    print(f"   Total fields: {len(mapping)}")
    print(f"   Fields with [] notation: {len(array_fields)}")
    print(f"   Normal fields: {len(normal_fields)}")
    
    if len(array_fields) > 0:
        print(f"\n   Sample array fields:")
        for field in array_fields[:3]:
            print(f"     - {field['mongoField']}")
    
    if len(normal_fields) > 0:
        print(f"\n   Sample normal fields:")
        for field in normal_fields[:3]:
            print(f"     - {field['mongoField']}")
    
except Exception as e:
    print(f"   ✗ Error loading mapping: {e}")

print("\n" + "="*70)
print("VERIFICATION COMPLETE")
print("="*70)
```

---

## Step 2: Run Verification Script

```bash
python verify_code.py
```

**Share the output of this script.** This will tell us:
1. If all methods exist
2. If the cleaning code is present
3. If utils work correctly
4. What your mapping config looks like

---

## Step 3: Detailed Aggregation Debugging

Create this debug script to test ONLY the aggregation part:

### **debug_aggregation.py**

```python
"""
Debug aggregation pipeline in isolation
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.config_loader import config_loader
from src.mongo_client import MongoDBClient
from src.aggregation_builder import AggregationBuilder
from src.logger import logger

logger.header("DEBUGGING AGGREGATION PIPELINE")

# Load configs
logger.info("\nStep 1: Loading configs...")
try:
    test_config = config_loader.load_test_config('configs/test-sample.json')
    mapping_config = config_loader.load_mapping_config('configs/mapping-sample.json')
    logger.success(f"✓ Loaded {len(mapping_config)} field mappings")
except Exception as e:
    logger.error(f"Failed to load configs: {e}")
    sys.exit(1)

# Create a minimal uncovered list for testing
logger.info("\nStep 2: Creating test uncovered fields list...")

# Take a few fields from your mapping - mix of array and non-array
test_uncovered = []
for mapping in mapping_config[:10]:  # Just first 10 for testing
    test_uncovered.append(mapping)

logger.info(f"Testing with {len(test_uncovered)} uncovered fields:")
for m in test_uncovered:
    logger.info(f"  - {m['mongoField']} → {m['jsonAttribute']}")

# Initialize aggregation builder
logger.info("\nStep 3: Building aggregation pipeline...")
payment_id_field = test_config['paymentIdMapping']['mongoField']
agg_builder = AggregationBuilder(payment_id_field)

pipeline = agg_builder.build_pipeline(test_uncovered, limit=5)

logger.info(f"\nGenerated pipeline with {len(pipeline)} stages:")
for idx, stage in enumerate(pipeline, 1):
    stage_name = list(stage.keys())[0]
    logger.info(f"  Stage {idx}: {stage_name}")

# Show the actual pipeline JSON
logger.info("\n" + "="*70)
logger.info("COMPLETE PIPELINE (for MongoDB testing):")
logger.info("="*70)
print(json.dumps(pipeline, indent=2, default=str))

# Connect to MongoDB
logger.info("\n" + "="*70)
logger.info("Step 4: Testing pipeline in MongoDB...")
logger.info("="*70)

try:
    mongo_client = MongoDBClient(
        test_config['mongoConnectionString'],
        test_config['mongoDatabase'],
        test_config['mongoCollection']
    )
    
    if not mongo_client.connect():
        logger.error("MongoDB connection failed")
        sys.exit(1)
    
    # Execute aggregation
    logger.info("\nExecuting aggregation...")
    result = mongo_client.execute_aggregation(pipeline)
    
    if not result['success']:
        logger.error(f"Aggregation failed: {result.get('error')}")
        sys.exit(1)
    
    candidates = result['data']
    logger.success(f"✓ Aggregation returned {len(candidates)} records")
    
    if len(candidates) > 0:
        logger.info("\n" + "="*70)
        logger.info("FIRST RECORD STRUCTURE:")
        logger.info("="*70)
        
        first = candidates[0]
        
        # Show top-level keys
        logger.info(f"\nTop-level keys: {list(first.keys())}")
        
        # Inspect each top-level key
        for key in first.keys():
            value = first[key]
            value_type = type(value).__name__
            
            if isinstance(value, dict):
                logger.info(f"\n'{key}': {value_type} with {len(value)} keys")
                logger.info(f"  Sub-keys: {list(value.keys())[:10]}")
            elif isinstance(value, list):
                logger.info(f"\n'{key}': {value_type} with {len(value)} items")
                if len(value) > 0 and isinstance(value[0], dict):
                    logger.info(f"  First item keys: {list(value[0].keys())[:10]}")
            else:
                value_str = str(value)[:100]
                logger.info(f"\n'{key}': {value_type} = {value_str}")
        
        # Try to access the uncovered fields
        logger.info("\n" + "="*70)
        logger.info("TESTING FIELD ACCESS:")
        logger.info("="*70)
        
        for mapping in test_uncovered[:5]:  # Test first 5
            mongo_field = mapping['mongoField']
            cleaned_field = mongo_field.replace('[]', '')
            
            logger.info(f"\nTrying to access: {mongo_field}")
            logger.info(f"  Cleaned to: {cleaned_field}")
            
            # Try manual access
            value = agg_builder._get_field_from_record(first, cleaned_field)
            
            if value is not None and value != "" and value != []:
                logger.success(f"  ✓ Found: {value}")
            else:
                logger.warn(f"  ✗ Not found or empty: {value}")
    
    mongo_client.close()
    
except Exception as e:
    logger.error(f"Error during testing: {str(e)}")
    import traceback
    traceback.print_exc()

logger.separator()
logger.info("Debug script complete!")
```

---

## Step 4: Run Aggregation Debug Script

```bash
python debug_aggregation.py
```

**This will show us:**
1. The exact pipeline being generated
2. What MongoDB returns
3. The structure of returned documents
4. Whether field access works

---

## Step 5: Manual MongoDB Test

Also, try running the aggregation directly in MongoDB Compass/Shell to see if it's a pipeline issue or code issue.

From Image 3, you showed this query works:
```javascript
db.odsMPYPaymentDetail.countDocuments({
  "MsgFees.FxRte": { $exists: true, $ne: null, $ne: "" }
})
// Returns: 1602
```

Now let's test a simple aggregation in Compass:

```javascript
db.odsMPYPaymentDetail.aggregate([
  {
    $match: {
      "MsgFees.FxRte": { $exists: true, $ne: null, $ne: "" }
    }
  },
  {
    $limit: 1
  },
  {
    $project: {
      "_id": 1,
      "MsgFees": 1,
      "MIFMP": 1
    }
  }
])
```

**What do you get?** Does it return the MIFMP and MsgFees objects?

---

## What to Share

Please run:

1. **verify_code.py** - share complete output
2. **debug_aggregation.py** - share complete output
3. **Manual MongoDB query** - share what you get

This will tell us exactly where the problem is:
- Is the code correct?
- Is the pipeline correct?
- Is MongoDB returning the data correctly?
- Is the field access logic working?

Once we see these outputs, we'll know exactly what's broken!
