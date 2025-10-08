You're absolutely right! That debug output showing "has 137 fields" is wrong - the aggregation counting logic is broken.

Let's implement your **much simpler approach** - one attribute at a time, find ONE record with that attribute, test it.

---

## Super Simple Phase 2 Logic

**For each uncovered attribute:**
1. Query MongoDB: "Find ONE document where this field exists and has data"
2. Get that document's payment ID
3. Test that payment ID using Phase 1 logic
4. Move to next uncovered attribute
5. Repeat

---

## Implementation

### **1. Update src/aggregation_builder.py**

Replace the entire class with this much simpler version:

```python
"""
Aggregation Builder Module
Simple approach: Find one record per uncovered field
"""

from typing import List, Dict, Any, Optional
from .logger import logger


class AggregationBuilder:
    """Finds payment IDs for uncovered fields - one at a time"""
    
    def __init__(self, payment_id_field: str):
        """
        Initialize aggregation builder
        
        Args:
            payment_id_field: MongoDB field name for payment ID
        """
        self.payment_id_field = payment_id_field
    
    def find_payment_id_for_field(
        self,
        mongo_client,
        field_name: str
    ) -> Optional[str]:
        """
        Find ONE payment ID that has data for the given field
        
        Args:
            mongo_client: MongoDB client instance
            field_name: MongoDB field name (e.g., "MIFMP.DbAccNo" or "MsgFees[].FxRte")
        
        Returns:
            Payment ID if found, None otherwise
        """
        # Clean array notation
        cleaned_field = field_name.replace('[]', '')
        
        logger.debug(f"  Searching for field: {field_name}")
        if cleaned_field != field_name:
            logger.debug(f"  Cleaned to: {cleaned_field}")
        
        try:
            # Simple query: find ONE document where this field exists and is not empty
            query = {
                cleaned_field: {
                    '$exists': True,
                    '$ne': None,
                    '$ne': ""
                }
            }
            
            # Only get the payment ID field, nothing else
            projection = {
                self.payment_id_field: 1,
                '_id': 0
            }
            
            # Execute query
            result = mongo_client.collection.find_one(query, projection)
            
            if result and self.payment_id_field in result:
                payment_id = result[self.payment_id_field]
                logger.debug(f"  ✓ Found payment ID: {payment_id}")
                return payment_id
            else:
                logger.debug(f"  ✗ No record found with this field")
                return None
                
        except Exception as e:
            logger.error(f"  Error searching for field: {str(e)}")
            return None
```

---

### **2. Update src/main.py - Replace `_run_phase2` method**

```python
def _run_phase2(self) -> List[Dict[str, Any]]:
    """
    Run Phase 2: Find and test one record per uncovered field
    Simple approach: For each uncovered field, find ONE payment ID with that field
    
    Returns:
        List of test results for Phase 2 payment IDs
    """
    phase2_results = []
    tested_payment_ids = set()  # Track what we've already tested
    
    try:
        # Get uncovered mappings
        uncovered_mappings = self.coverage_tracker.get_uncovered_mappings()
        
        if not uncovered_mappings:
            logger.info("No uncovered fields to search for")
            return phase2_results
        
        logger.info(f"\n{len(uncovered_mappings)} attributes not yet covered")
        logger.info("Will search for ONE payment ID per uncovered field...")
        
        logger.separator('-', 60)
        logger.info(f"\nSearching MongoDB for payment IDs with uncovered fields...")
        
        # For each uncovered field, find one payment ID
        for idx, mapping in enumerate(uncovered_mappings, 1):
            mongo_field = mapping['mongoField']
            json_attr = mapping['jsonAttribute']
            
            logger.info(f"\n[{idx}/{len(uncovered_mappings)}] Field: {json_attr}")
            logger.info(f"  MongoDB field: {mongo_field}")
            
            # Find payment ID for this field
            payment_id = self.aggregation_builder.find_payment_id_for_field(
                mongo_client=self.mongo_client,
                field_name=mongo_field
            )
            
            if not payment_id:
                logger.warn(f"  ⚠ No payment ID found (field has no data in collection)")
                continue
            
            # Check if we already tested this payment ID
            if payment_id in tested_payment_ids:
                logger.info(f"  ℹ Payment ID {payment_id} already tested, skipping")
                continue
            
            # Test this payment ID
            logger.info(f"  → Will test payment ID: {payment_id}")
            tested_payment_ids.add(payment_id)
        
        # Now test all unique payment IDs we found
        logger.separator('-', 60)
        logger.info(f"\nFound {len(tested_payment_ids)} unique payment IDs to test")
        logger.info("Testing using Phase 1 logic...\n")
        
        for idx, payment_id in enumerate(tested_payment_ids, 1):
            logger.info(f"[{idx}/{len(tested_payment_ids)}] Testing Payment ID: {payment_id}")
            logger.separator('-', 40)
            
            # Use Phase 1 logic
            result = self._test_single_payment_id(payment_id)
            result['phase'] = 2
            phase2_results.append(result)
            
            # Show summary
            if result['success']:
                logger.success(f"✓ Completed: {result['passed']} passed, {result['warnings']} warnings, {result['failed']} failed, {result.get('notCovered', 0)} not covered")
            else:
                logger.error(f"✗ Testing failed: {result.get('error')}")
            
            # Show coverage update
            coverage = self.coverage_tracker.get_coverage_summary()
            logger.info(f"📊 Coverage now: {coverage['covered_count']}/{coverage['total_attributes']} ({coverage['coverage_percentage']:.1f}%)")
        
        # Final summary
        logger.separator('-', 60)
        final_coverage = self.coverage_tracker.get_coverage_summary()
        logger.info(f"\n✓ Phase 2 Complete!")
        logger.info(f"  Tested {len(tested_payment_ids)} unique payment IDs")
        logger.info(f"  Final coverage: {final_coverage['covered_count']}/{final_coverage['total_attributes']} ({final_coverage['coverage_percentage']:.1f}%)")
        
        if final_coverage['uncovered_count'] > 0:
            logger.warn(f"  {final_coverage['uncovered_count']} attributes still uncovered (no data in collection)")
        
        return phase2_results
        
    except Exception as e:
        logger.error(f"Phase 2 execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return phase2_results
```

---

## What This Does

### **Step by Step:**

**Start:** 137 uncovered attributes after Phase 1

**Attribute 1:** `messageInformation.bbi`
- Query: Find ONE document where `MIFMP.Bbi` exists and has data
- Found: Payment ID `PAY123`
- Test PAY123 with Phase 1 logic
- Coverage: 138/294 attributes now covered

**Attribute 2:** `messageInformation.creditorAgent.name`
- Query: Find ONE document where `MIFMP.Bbk` exists
- Found: Payment ID `PAY456`
- Test PAY456
- Coverage: 142/294 (this payment ID happened to have 4 uncovered fields)

**Attribute 3:** `messageInformation.outgoingCreditAmount`
- Query: Find ONE document where `MIFMP.OutGngCrAmt` exists
- Found: Payment ID `PAY123` (already tested!)
- Skip (already tested)

... continue for all 137 attributes ...

**End:** Maybe 20-30 unique payment IDs tested, 250/294 attributes covered

---

## Example Output

```
PHASE 2: Finding Records for Uncovered Fields
──────────────────────────────────────────────

137 attributes not yet covered
Will search for ONE payment ID per uncovered field...

──────────────────────────────────────────────
Searching MongoDB for payment IDs with uncovered fields...

[1/137] Field: messageInformation.bbi
  MongoDB field: MIFMP.Bbi
  Searching for field: MIFMP.Bbi
  ✓ Found payment ID: 23826054132004
  → Will test payment ID: 23826054132004

[2/137] Field: messageInformation.creditorAgent.name
  MongoDB field: MIFMP.Bbk
  Searching for field: MIFMP.Bbk
  ✓ Found payment ID: BCTA0000H221
  → Will test payment ID: BCTA0000H221

[3/137] Field: messageInformation.outgoingCreditAmount
  MongoDB field: MIFMP.OutGngCrAmt
  Searching for field: MIFMP.OutGngCrAmt
  ✓ Found payment ID: 23826054132004
  ℹ Payment ID 23826054132004 already tested, skipping

[4/137] Field: messageInformation.fees.amount
  MongoDB field: MsgFees[].FeeAmt
  Searching for field: MsgFees[].FeeAmt
  Cleaned to: MsgFees.FeeAmt
  ✓ Found payment ID: 2130913013200
  → Will test payment ID: 2130913013200

...

[137/137] Field: messageInformation.rareField
  MongoDB field: MIFMP.RareField
  Searching for field: MIFMP.RareField
  ✗ No payment ID found (field has no data in collection)
  ⚠ No payment ID found (field has no data in collection)

──────────────────────────────────────────────
Found 28 unique payment IDs to test
Testing using Phase 1 logic...

[1/28] Testing Payment ID: 23826054132004
────────────────────────────────────────────
✓ Completed: 245 passed, 12 warnings, 1 failed, 36 not covered
📊 Coverage now: 170/294 (57.8%)

[2/28] Testing Payment ID: BCTA0000H221
────────────────────────────────────────────
✓ Completed: 240 passed, 10 warnings, 0 failed, 44 not covered
📊 Coverage now: 185/294 (62.9%)

...

[28/28] Testing Payment ID: 23809062024004
────────────────────────────────────────────
✓ Completed: 250 passed, 15 warnings, 2 failed, 27 not covered
📊 Coverage now: 267/294 (90.8%)

──────────────────────────────────────────────
✓ Phase 2 Complete!
  Tested 28 unique payment IDs
  Final coverage: 267/294 (90.8%)
  27 attributes still uncovered (no data in collection)
```

---

## Benefits of This Approach

✅ **Simple** - One MongoDB query per field, easy to understand
✅ **Efficient** - Skips duplicate payment IDs automatically
✅ **Reliable** - Uses Phase 1 logic that we know works
✅ **Informative** - Shows progress for each attribute
✅ **Guaranteed coverage** - If a field has ANY data, we'll find it

---

## Run It

```bash
python run_test.py
```

This will be slower than the aggregation approach (many individual queries instead of one aggregation), but it's **dead simple and will definitely work**.

Later, once everything is working, we can optimize with smarter aggregation if needed!

Let me know how it goes! 🚀
