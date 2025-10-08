Excellent! Now let's test everything together.

---

## Complete Testing Plan

### **Step 1: Test Individual New Components First**

#### **Test Utils (with array index support)**

```bash
python tests/test_utils.py
```

**What to check:**
- ✅ All existing tests still pass
- ✅ New array index test passes (Test 7)
- ✅ Can access `data.items.0.name` correctly

---

#### **Test Coverage Tracker**

Create a quick test:

**tests/test_coverage_tracker.py**

```python
"""
Test Coverage Tracker
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.coverage_tracker import CoverageTracker
from src.logger import logger


def test_coverage_tracker():
    """Test coverage tracking"""
    
    logger.header("TESTING COVERAGE TRACKER")
    
    # Sample mapping config
    mapping_config = [
        {"mongoField": "field1", "jsonAttribute": "attr1", "mongoType": "String"},
        {"mongoField": "field2", "jsonAttribute": "attr2", "mongoType": "String"},
        {"mongoField": "field3", "jsonAttribute": "attr3", "mongoType": "String"},
    ]
    
    tracker = CoverageTracker(mapping_config)
    
    logger.info("\nTest 1: Initial State")
    summary = tracker.get_coverage_summary()
    logger.info(f"  Total: {summary['total_attributes']}")
    logger.info(f"  Covered: {summary['covered_count']}")
    logger.info(f"  Uncovered: {summary['uncovered_count']}")
    
    if summary['covered_count'] == 0 and summary['uncovered_count'] == 3:
        logger.success("✓ Initial state correct")
    else:
        logger.error("✗ Initial state wrong")
    
    logger.info("\nTest 2: Mark fields as tested")
    
    # Simulate field results
    field_result1 = {
        'jsonAttribute': 'attr1',
        'mongoValue': 'value1',
        'status': 'PASS'
    }
    
    field_result2 = {
        'jsonAttribute': 'attr2',
        'mongoValue': None,
        'status': 'NOT_COVERED'
    }
    
    tracker.mark_result(field_result1, 'PAY001')
    tracker.mark_result(field_result2, 'PAY001')
    
    summary = tracker.get_coverage_summary()
    logger.info(f"  Covered: {summary['covered_count']}")
    logger.info(f"  Uncovered: {summary['uncovered_count']}")
    
    if summary['covered_count'] == 1 and summary['uncovered_count'] == 2:
        logger.success("✓ Coverage tracking works")
    else:
        logger.error("✗ Coverage tracking wrong")
    
    logger.info("\nTest 3: Get uncovered mappings")
    uncovered = tracker.get_uncovered_mappings()
    logger.info(f"  Uncovered mappings: {len(uncovered)}")
    
    for mapping in uncovered:
        logger.info(f"    - {mapping['jsonAttribute']}")
    
    if len(uncovered) == 2:
        logger.success("✓ Uncovered mappings correct")
    else:
        logger.error("✗ Uncovered mappings wrong")
    
    logger.separator()
    logger.header("COVERAGE TRACKER TEST COMPLETE")


if __name__ == "__main__":
    test_coverage_tracker()
```

Run it:
```bash
python tests/test_coverage_tracker.py
```

---

### **Step 2: Run the Complete Utility**

Now run the full utility with your actual data:

```bash
python run_test.py
```

---

## What to Look For in the Output

### **Phase 1 Should Show:**

```
════════════════════════════════════════════════════════════
PHASE 1: Testing Configured Payment IDs
════════════════════════════════════════════════════════════

Testing 3 configured payment IDs...
────────────────────────────────────────────────────────────

[1/3] Testing Payment ID: PAY001
────────────────────────────────────────────────────────────
✓ Completed: X passed, Y warnings, Z failed, W not covered

[2/3] Testing Payment ID: PAY002
────────────────────────────────────────────────────────────
✓ Completed: X passed, Y warnings, Z failed, W not covered

[3/3] Testing Payment ID: PAY003
────────────────────────────────────────────────────────────
✓ Completed: X passed, Y warnings, Z failed, W not covered
```

**Check:**
- ✅ Values are populated (not blank) in console
- ✅ Status shows PASS/WARNING/CRITICAL/NOT_COVERED (not all PASS for empty fields)
- ✅ Coverage percentage makes sense

---

### **Coverage Report Should Show:**

```
════════════════════════════════════════════════════════════
COVERAGE REPORT
════════════════════════════════════════════════════════════

Total Attributes in Mapping: 50
✓ Covered: 35 (70.0%)
⚠ Uncovered: 15 (30.0%)

Uncovered Attributes:
  - messageInformation.creditorAccountName (MongoDB: MIFMP.CrAccName)
  - messageInformation.debtorAddress1 (MongoDB: MIFMP.DbAddr1)
  ...
```

**Check:**
- ✅ Coverage percentage is realistic (not 100% if some fields have no data)
- ✅ Uncovered attributes are listed

---

### **Phase 2 Should Show (if there are uncovered fields):**

```
════════════════════════════════════════════════════════════
PHASE 2: Finding Records for Uncovered Fields
════════════════════════════════════════════════════════════

15 attributes not yet covered
Searching for records with these fields...

Building MongoDB aggregation pipeline...
Executing aggregation to find candidate records...
✓ Found 47 candidate records

Selecting optimal records for maximum coverage...
✓ Selected 5 payment IDs
  Will cover 12 of 15 uncovered fields
  ⚠ 3 fields have no data in collection

Testing 5 selected payment IDs...

[1/5] Testing Payment ID: PAY150
  Expected to cover 7 new fields
────────────────────────────────────────────────────────────
✓ Completed: 7 fields tested
```

**Check:**
- ✅ Aggregation finds candidate records
- ✅ Optimal selection logic runs
- ✅ Selected payment IDs are tested
- ✅ Coverage improves after Phase 2

---

### **Final Summary Should Show:**

```
════════════════════════════════════════════════════════════
TEST SUMMARY
════════════════════════════════════════════════════════════

Phase 1 Payment IDs Tested: 3
Phase 2 Payment IDs Tested: 5
Total Payment IDs Tested: 8
Successful Test Runs: 8/8
────────────────────────────────────────────────────────────

Field Comparison Results:
  Total Field Tests: 400
  ✓ Passed: 350 (87.5%)
  ⚠ Warnings: 20 (5.0%)
  ✗ Failed: 5 (1.25%)
  ⊘ Not Covered: 25 (6.25%)

────────────────────────────────────────────────────────────

Phase 1 Results:
  ✓ PAY001: 45 passed, 2 warnings, 3 not covered
  ✓ PAY002: 42 passed, 5 warnings, 1 failed, 2 not covered
  ...

Phase 2 Results:
  ✓ PAY150: 7 passed
  ✓ PAY287: 5 passed, 2 not covered
  ...

════════════════════════════════════════════════════════════
COVERAGE REPORT
════════════════════════════════════════════════════════════

Total Attributes in Mapping: 50
✓ Covered: 47 (94.0%)
⚠ Uncovered: 3 (6.0%)

Uncovered Attributes:
  - rareField1 (MongoDB: rare_field_1)
  - rareField2 (MongoDB: rare_field_2)
  - rareField3 (MongoDB: rare_field_3)

════════════════════════════════════════════════════════════

Generating Reports...
────────────────────────────────────────────────────────────
✓ JSON report generated: output/getUserPaymentData_detailed_report_20251007_163102.json
✓ CSV report generated: output/getUserPaymentData_comparison_matrix_20251007_163102.csv
✓ Summary report generated: output/getUserPaymentData_summary_20251007_163102.txt

✓ ALL TESTS PASSED!
  Note: 20 warnings detected (review recommended)
```

---

### **Reports Should Be Generated:**

Check the `output/` directory:

```bash
ls -la output/
```

You should see:
- `{apiName}_detailed_report_{timestamp}.json`
- `{apiName}_comparison_matrix_{timestamp}.csv`
- `{apiName}_summary_{timestamp}.txt`

---

## Check the CSV Report

Open the CSV file in Excel and verify:

**Columns:**
- Payment ID
- Attribute Name
- MongoDB Field
- MongoDB Type
- MongoDB Value ← **Should have actual values now!**
- Java 21 Value ← **Should have actual values now!**
- Java 8 Value (if tested)
- Status (PASS/WARNING/CRITICAL/NOT_COVERED)
- Severity
- Mismatch Type
- Notes

**What to verify:**
- ✅ MongoDB Value column has actual data (not all blank)
- ✅ Java 21 Value column has actual data (not all blank)
- ✅ Status is accurate:
  - PASS for matching values
  - WARNING for formatting differences (10.50 vs 10.5)
  - CRITICAL for value mismatches
  - NOT_COVERED for fields with no data
- ✅ Phase 2 payment IDs appear in the CSV

---

## Potential Issues to Watch For

### **Issue 1: If Phase 2 doesn't find any candidates**

**Symptom:**
```
Executing aggregation to find candidate records...
✓ Found 0 candidate records
```

**Possible causes:**
- All fields are already covered in Phase 1
- Uncovered fields truly have no data in MongoDB
- Aggregation pipeline issue

**What to do:**
Check which fields are uncovered and manually query MongoDB to see if they have data.

---

### **Issue 2: If aggregation fails**

**Symptom:**
```
Aggregation failed: [some error message]
```

**Possible causes:**
- MongoDB version doesn't support certain operators
- Field names have special characters causing issues
- Pipeline syntax error

**What to do:**
Share the error message and we'll fix the aggregation pipeline.

---

### **Issue 3: If values still appear blank in CSV**

**Symptom:**
CSV shows empty MongoDB Value and Java 21 Value columns

**Possible causes:**
- Root path is still incorrect
- Field paths in mapping config are wrong
- API response structure different than expected

**What to do:**
Run the debug script again:
```bash
python debug_api_response.py
```

And verify the paths in mapping config match the actual response structure.

---

### **Issue 4: If Phase 2 takes very long**

**Symptom:**
Aggregation or testing seems to hang

**Possible causes:**
- MongoDB collection is very large
- Aggregation is slow without indexes
- Too many candidate records

**What to do:**
- Reduce the `limit` parameter in aggregation (currently 100)
- Add indexes on frequently queried fields
- Increase timeout values

---

## After Testing - Share Results

Once you run the complete test, please share:

1. **Did Phase 1 complete successfully?**
   - How many payment IDs tested?
   - What was the coverage percentage?

2. **Did Phase 2 run?**
   - How many candidates found?
   - How many payment IDs selected?
   - Did coverage improve?

3. **Are values populated in CSV?**
   - Can you see actual MongoDB values?
   - Can you see actual API values?
   - Are statuses accurate (PASS/WARNING/CRITICAL/NOT_COVERED)?

4. **Were the 3 known issues detected?**
   - Issue #1: Type conversion errors (if any)
   - Issue #2: Empty array differences
   - Issue #3: Trailing zero formatting (10.50 vs 10.5)

5. **Any errors or unexpected behavior?**

---

**Go ahead and run it! Let me know what happens!** 🚀
