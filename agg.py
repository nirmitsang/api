Good catch! You're right - if a field has no data (blank/None), it shouldn't be marked as PASS. It should either be marked as NOT_COVERED or handled differently.

Let me fix this before we move ahead.

---

## The Problem

Currently, when both MongoDB and API have `None` for a field:

```python
# In comparator._compare_values()
if value1 is None and value2 is None:
    return {
        'match': True,  # ← This is wrong!
        'mismatchType': None,
        'severity': 'PASS',
        'note': 'Both values are None'
    }
```

This marks it as PASS, but it should be marked as NOT_COVERED (or NOT_TESTED).

---

## Solution: Add NOT_COVERED Status

### **Update src/comparator.py**

Replace the `_compare_values` method with this improved version:

```python
def _compare_values(
    self,
    value1: Any,
    value2: Any,
    data_type: str,
    label1: str = "Value1",
    label2: str = "Value2"
) -> Dict[str, Any]:
    """
    Compare two values
    
    Returns:
        Dict with 'match' (bool), 'mismatchType' (str or None), 
        'severity' (str), 'note' (str or None)
    """
    
    # Both are None or null - NOT COVERED (no data to test)
    if value1 is None and value2 is None:
        return {
            'match': False,  # Changed from True
            'mismatchType': 'NOT_COVERED',
            'severity': 'NOT_COVERED',
            'note': 'Field has no data in either source (not covered)'
        }
    
    # One is None, other is not
    if value1 is None and value2 is not None:
        return {
            'match': False,
            'mismatchType': 'NULL_MISMATCH',
            'severity': 'WARNING',
            'note': f'{label1} is None, but {label2} has value'
        }
    
    if value1 is not None and value2 is None:
        return {
            'match': False,
            'mismatchType': 'NULL_MISMATCH',
            'severity': 'WARNING',
            'note': f'{label1} has value, but {label2} is None'
        }
    
    # Exact match
    if deep_equal(value1, value2):
        return {
            'match': True,
            'mismatchType': None,
            'severity': 'PASS',
            'note': None
        }
    
    # Empty array vs None (Issue #2)
    if isinstance(value1, list) and len(value1) == 0 and value2 is None:
        return {
            'match': False,
            'mismatchType': 'EMPTY_ARRAY_HANDLING',
            'severity': 'WARNING',
            'note': f'{label1} has empty array [], {label2} is None (Known Issue #2)'
        }
    
    if value1 is None and isinstance(value2, list) and len(value2) == 0:
        return {
            'match': False,
            'mismatchType': 'EMPTY_ARRAY_HANDLING',
            'severity': 'WARNING',
            'note': f'{label1} is None, {label2} has empty array [] (Known Issue #2)'
        }
    
    # Numeric comparison with tolerance (for decimals)
    if data_type in ['Decimal128', 'Double', 'Float', 'BigDecimal']:
        if safe_float_compare(value1, value2):
            return {
                'match': True,
                'mismatchType': None,
                'severity': 'PASS',
                'note': 'Values are numerically equal'
            }
    
    # Number formatting difference (Issue #3)
    if is_numeric_string(str(value1)) and is_numeric_string(str(value2)):
        if safe_float_compare(value1, value2):
            return {
                'match': False,
                'mismatchType': 'NUMBER_FORMATTING',
                'severity': 'WARNING',
                'note': f'Number formatting difference: {value1} vs {value2} (Issue #3)'
            }
    
    # Type mismatch
    if type(value1).__name__ != type(value2).__name__:
        return {
            'match': False,
            'mismatchType': 'TYPE_MISMATCH',
            'severity': 'CRITICAL',
            'note': f'Type mismatch: {type(value1).__name__} vs {type(value2).__name__}'
        }
    
    # Array length mismatch
    if isinstance(value1, list) and isinstance(value2, list):
        if len(value1) != len(value2):
            return {
                'match': False,
                'mismatchType': 'ARRAY_LENGTH_MISMATCH',
                'severity': 'CRITICAL',
                'note': f'Array length: {len(value1)} vs {len(value2)}'
            }
    
    # Value difference
    return {
        'match': False,
        'mismatchType': 'VALUE_DIFFERENCE',
        'severity': 'CRITICAL',
        'note': f'Values differ: {value1} vs {value2}'
    }
```

**Key change:** Moved the "both None" check to the top and changed it to return `NOT_COVERED` status instead of `PASS`.

---

### **Update src/main.py**

Update the status counting logic to handle NOT_COVERED:

Find this section in `_test_single_payment_id`:

```python
# Count statuses
if field_result['status'] == 'PASS':
    result['passed'] += 1
elif field_result['status'] in ['WARNING']:
    result['warnings'] += 1
elif field_result['status'] in ['CRITICAL', 'CRITICAL_ERROR']:
    result['failed'] += 1
elif field_result['status'] in ['ERROR']:
    result['errors'] += 1
```

**Replace with:**

```python
# Count statuses
if field_result['status'] == 'PASS':
    result['passed'] += 1
elif field_result['status'] in ['WARNING']:
    result['warnings'] += 1
elif field_result['status'] in ['CRITICAL', 'CRITICAL_ERROR']:
    result['failed'] += 1
elif field_result['status'] in ['ERROR']:
    result['errors'] += 1
elif field_result['status'] in ['NOT_COVERED']:
    # Don't count as passed or failed - it's uncovered
    pass  # Will be tracked by coverage tracker separately
```

Also update the result dictionary initialization:

```python
result = {
    'paymentId': payment_id,
    'success': False,
    'fieldResults': [],
    'passed': 0,
    'warnings': 0,
    'failed': 0,
    'errors': 0,
    'notCovered': 0  # ADD THIS
}
```

And update the counting:

```python
elif field_result['status'] in ['NOT_COVERED']:
    result['notCovered'] += 1
```

And update the summary display:

```python
# Show quick summary
if result['success']:
    summary_parts = []
    if result['passed'] > 0:
        summary_parts.append(f"{result['passed']} passed")
    if result['warnings'] > 0:
        summary_parts.append(f"{result['warnings']} warnings")
    if result['failed'] > 0:
        summary_parts.append(f"{result['failed']} failed")
    if result['notCovered'] > 0:
        summary_parts.append(f"{result['notCovered']} not covered")
    
    logger.success(f"✓ Completed: {', '.join(summary_parts)}")
else:
    logger.error(f"✗ Testing failed: {result.get('error')}")
```

---

### **Update src/coverage_tracker.py**

Update the `mark_result` method to properly handle NOT_COVERED:

```python
def mark_result(self, field_result: Dict[str, Any], payment_id: str):
    """
    Mark coverage based on a field comparison result
    
    Args:
        field_result: Result from comparator
        payment_id: Payment ID that was tested
    """
    json_attr = field_result['jsonAttribute']
    mongo_value = field_result.get('mongoValue')
    
    # Field is covered only if MongoDB had actual data for it (not None)
    had_data = (mongo_value is not None and 
                field_result['status'] != 'NOT_COVERED')
    
    self.mark_field_tested(json_attr, payment_id, had_data, mongo_value)
```

---

### **Update src/reporter.py**

Update CSV headers to include NOT_COVERED:

In the `generate_csv_report` method, the status column will automatically show "NOT_COVERED" now.

Also update the summary report generation in `_generate_summary` (in main.py):

```python
total_passed = sum(r.get('passed', 0) for r in phase1_results)
total_warnings = sum(r.get('warnings', 0) for r in phase1_results)
total_failed = sum(r.get('failed', 0) for r in phase1_results)
total_errors = sum(r.get('errors', 0) for r in phase1_results)
total_not_covered = sum(r.get('notCovered', 0) for r in phase1_results)  # ADD THIS
total_fields = total_passed + total_warnings + total_failed + total_errors + total_not_covered  # UPDATE THIS
```

And in the display:

```python
logger.info(f"\nField Comparison Results:")
logger.info(f"  Total Fields Tested: {total_fields}")
logger.success(f"  ✓ Passed: {total_passed} ({total_passed/total_fields*100:.1f}%)" if total_fields > 0 else "  ✓ Passed: 0")
logger.warn(f"  ⚠ Warnings: {total_warnings} ({total_warnings/total_fields*100:.1f}%)" if total_fields > 0 else "  ⚠ Warnings: 0")
logger.error(f"  ✗ Failed: {total_failed} ({total_failed/total_fields*100:.1f}%)" if total_fields > 0 else "  ✗ Failed: 0")

if total_errors > 0:
    logger.error(f"  ⚠ Errors: {total_errors}")

if total_not_covered > 0:
    logger.warn(f"  ⊘ Not Covered: {total_not_covered} (no data in MongoDB)")  # ADD THIS
```

---

## What This Changes

### **Before:**
```
Payment ID: PAY001
  ✓ PASS: userId (both None)
  ✓ PASS: amount (both None)
  ✓ PASS: email (both have values)

Result: 3 passed, 0 warnings, 0 failed
Coverage: 33% (only email has data)
```

### **After:**
```
Payment ID: PAY001
  ⊘ NOT_COVERED: userId (no data)
  ⊘ NOT_COVERED: amount (no data)
  ✓ PASS: email (values match)

Result: 1 passed, 0 warnings, 0 failed, 2 not covered
Coverage: 33% (only email has data)
```

---

## Summary of Changes

1. **Comparator**: Changed "both None" to return `NOT_COVERED` instead of `PASS`
2. **Main**: Added `notCovered` counter and handling
3. **Coverage Tracker**: Properly excludes NOT_COVERED from coverage
4. **Reports**: Show NOT_COVERED status in CSV and summary

This way:
- ✅ Fields with data that match → **PASS**
- ⚠️ Fields with data that have issues → **WARNING/CRITICAL**
- ⊘ Fields with no data → **NOT_COVERED** (doesn't count as pass or fail)
- Coverage tracker only counts fields that had actual data

---

**Ready to continue? This fix will make your coverage tracking more accurate!** Should we test this change first, or move ahead with Phase 2 (aggregation for uncovered fields)?






Perfect! Let's build Phase 2 - the smart aggregation to find uncovered fields.

---

## Phase 2: Aggregation for Uncovered Fields

This is the intelligent part where the utility automatically finds MongoDB records that have data for fields that weren't covered in Phase 1.

---

## 1. Aggregation Builder Module

### **src/aggregation_builder.py**

```python
"""
Aggregation Builder Module
Builds optimized MongoDB aggregation pipelines to find uncovered fields
"""

from typing import List, Dict, Any, Set
from .logger import logger


class AggregationBuilder:
    """Builds MongoDB aggregation pipelines for finding uncovered fields"""
    
    def __init__(self, payment_id_field: str):
        """
        Initialize aggregation builder
        
        Args:
            payment_id_field: MongoDB field name for payment ID
        """
        self.payment_id_field = payment_id_field
    
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
        
        # Extract MongoDB field names
        uncovered_fields = [m['mongoField'] for m in uncovered_mappings]
        
        logger.debug(f"Building aggregation for {len(uncovered_fields)} uncovered fields")
        
        # Build $or conditions for $match stage
        # Match documents that have ANY uncovered field with actual data
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
            count_expressions.append({
                '$cond': [
                    {
                        '$and': [
                            {'$ne': [f'${field}', None]},
                            {'$ne': [f'${field}', ""]}
                        ]
                    },
                    1,
                    0
                ]
            })
        
        # Build the pipeline
        pipeline = [
            # Stage 1: Match records with ANY uncovered field
            {
                '$match': {
                    '$or': match_conditions
                }
            },
            
            # Stage 2: Add field counting how many uncovered fields this record has
            {
                '$addFields': {
                    'uncoveredFieldCount': {
                        '$add': count_expressions
                    }
                }
            },
            
            # Stage 3: Sort by count (descending - records with most fields first)
            {
                '$sort': {
                    'uncoveredFieldCount': -1
                }
            },
            
            # Stage 4: Limit to top candidates
            {
                '$limit': limit
            },
            
            # Stage 5: Project only what we need
            {
                '$project': {
                    self.payment_id_field: 1,
                    'uncoveredFieldCount': 1,
                    **{field: 1 for field in uncovered_fields}
                }
            }
        ]
        
        return pipeline
    
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
        uncovered_fields = set(m['mongoField'] for m in uncovered_mappings)
        covered_fields: Set[str] = set()
        selected_records = []
        
        logger.debug(f"Selecting optimal records from {len(aggregation_results)} candidates")
        
        for record in aggregation_results:
            # Find which NEW fields this record would cover
            new_fields = []
            
            for field in uncovered_fields:
                if field not in covered_fields:
                    # Check if this record has data for this field
                    value = record.get(field)
                    if value is not None and value != "":
                        new_fields.append(field)
            
            # If this record covers new fields, select it
            if new_fields:
                payment_id = record.get(self.payment_id_field)
                
                selected_records.append({
                    'paymentId': payment_id,
                    'coversFields': new_fields,
                    'totalUncoveredFields': record.get('uncoveredFieldCount', 0)
                })
                
                # Mark these fields as covered
                covered_fields.update(new_fields)
                
                logger.debug(f"Selected {payment_id}: covers {len(new_fields)} new fields")
            
            # Stop if all fields covered
            if len(covered_fields) == len(uncovered_fields):
                logger.debug("All uncovered fields now have coverage candidates")
                break
        
        still_uncovered = uncovered_fields - covered_fields
        
        return {
            'selectedRecords': selected_records,
            'coveredCount': len(covered_fields),
            'stillUncoveredCount': len(still_uncovered),
            'stillUncoveredFields': list(still_uncovered)
        }


def get_field_with_dot_notation(record: Dict[str, Any], field_path: str) -> Any:
    """
    Helper to get field value with dot notation support
    Used when checking if a field has data in aggregation results
    
    Args:
        record: MongoDB record
        field_path: Field path (may include dots for nested fields)
    
    Returns:
        Field value or None
    """
    parts = field_path.split('.')
    current = record
    
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    
    return current
```

---

## 2. Update MongoDB Client with Aggregation Support

### **Add to src/mongo_client.py**

Add this method to the `MongoDBClient` class:

```python
def execute_aggregation(self, pipeline: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Execute an aggregation pipeline
    
    Args:
        pipeline: MongoDB aggregation pipeline
    
    Returns:
        Dict with 'success' (bool), 'data' (list or None), 'error' (str or None)
    """
    if self.collection is None:
        return {
            'success': False,
            'data': None,
            'error': 'Not connected to MongoDB'
        }
    
    try:
        logger.debug("Executing aggregation pipeline...")
        
        results = list(self.collection.aggregate(pipeline))
        
        # Convert ObjectId to string in results
        for record in results:
            if '_id' in record:
                record['_id'] = str(record['_id'])
        
        logger.debug(f"Aggregation returned {len(results)} records")
        
        return {
            'success': True,
            'data': results,
            'error': None
        }
        
    except OperationFailure as e:
        logger.error(f"MongoDB aggregation failed: {str(e)}")
        return {
            'success': False,
            'data': None,
            'error': f'Aggregation failed: {str(e)}'
        }
    except Exception as e:
        logger.error(f"Error executing aggregation: {str(e)}")
        return {
            'success': False,
            'data': None,
            'error': f'Error executing aggregation: {str(e)}'
        }
```

---

## 3. Update Main Orchestrator with Phase 2

### **Update src/main.py**

Add import:
```python
from .aggregation_builder import AggregationBuilder
```

Add to `__init__`:
```python
self.aggregation_builder = None
```

Add to `_initialize_components`:
```python
# Initialize aggregation builder
logger.info("Initializing aggregation builder...")
payment_id_mongo_field = self.test_config['paymentIdMapping']['mongoField']
self.aggregation_builder = AggregationBuilder(payment_id_mongo_field)
logger.success("✓ Aggregation builder initialized")
```

Update the `run` method to add Phase 2:

```python
def run(self):
    """Execute the complete test workflow"""
    
    self.start_time = time.time()
    
    logger.header("API MIGRATION TEST UTILITY")
    logger.info(f"Starting test execution at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.separator()
    
    # Step 1: Load and validate configurations
    if not self._load_configs():
        logger.error("Configuration loading failed. Exiting.")
        return False
    
    # Step 2: Initialize components
    if not self._initialize_components():
        logger.error("Component initialization failed. Exiting.")
        return False
    
    # Step 3: Run Phase 1 tests
    logger.separator()
    logger.header("PHASE 1: Testing Configured Payment IDs")
    
    phase1_results = self._run_phase1()
    
    # Step 4: Check coverage and run Phase 2 if needed
    coverage_summary = self.coverage_tracker.get_coverage_summary()
    
    phase2_results = []
    if coverage_summary['uncovered_count'] > 0:
        logger.separator()
        logger.header("PHASE 2: Finding Records for Uncovered Fields")
        
        logger.info(f"\n{coverage_summary['uncovered_count']} attributes not yet covered")
        logger.info("Searching for records with these fields...")
        
        phase2_results = self._run_phase2()
    else:
        logger.separator()
        logger.success("\n✓ ALL ATTRIBUTES COVERED IN PHASE 1!")
        logger.info("Phase 2 not needed.")
    
    # Step 5: Generate summary report
    logger.separator()
    all_results = phase1_results + phase2_results
    self._generate_summary(all_results)
    
    # Cleanup
    if self.mongo_client:
        self.mongo_client.close()
    
    return True
```

Add the new `_run_phase2` method:

```python
def _run_phase2(self) -> List[Dict[str, Any]]:
    """
    Run Phase 2: Find and test records for uncovered fields
    
    Returns:
        List of test results for Phase 2 payment IDs
    """
    phase2_results = []
    
    try:
        # Get uncovered mappings
        uncovered_mappings = self.coverage_tracker.get_uncovered_mappings()
        
        if not uncovered_mappings:
            logger.info("No uncovered fields to search for")
            return phase2_results
        
        logger.info(f"\nUncovered fields:")
        for mapping in uncovered_mappings[:10]:  # Show first 10
            logger.info(f"  - {mapping['jsonAttribute']} (MongoDB: {mapping['mongoField']})")
        
        if len(uncovered_mappings) > 10:
            logger.info(f"  ... and {len(uncovered_mappings) - 10} more")
        
        # Build aggregation pipeline
        logger.separator('-', 60)
        logger.info("\nBuilding MongoDB aggregation pipeline...")
        
        pipeline = self.aggregation_builder.build_pipeline(
            uncovered_mappings=uncovered_mappings,
            limit=100  # Get top 100 candidates
        )
        
        logger.debug(f"Pipeline has {len(pipeline)} stages")
        
        # Execute aggregation
        logger.info("Executing aggregation to find candidate records...")
        
        agg_result = self.mongo_client.execute_aggregation(pipeline)
        
        if not agg_result['success']:
            logger.error(f"Aggregation failed: {agg_result.get('error')}")
            return phase2_results
        
        candidates = agg_result['data']
        logger.success(f"✓ Found {len(candidates)} candidate records")
        
        if len(candidates) == 0:
            logger.warn("⚠ No records found with uncovered fields")
            logger.info("This means these fields have no data in the entire collection")
            return phase2_results
        
        # Select optimal records
        logger.info("\nSelecting optimal records for maximum coverage...")
        
        selection_result = self.aggregation_builder.select_optimal_records(
            aggregation_results=candidates,
            uncovered_mappings=uncovered_mappings
        )
        
        selected_records = selection_result['selectedRecords']
        
        logger.success(f"✓ Selected {len(selected_records)} payment IDs")
        logger.info(f"  Will cover {selection_result['coveredCount']} of {len(uncovered_mappings)} uncovered fields")
        
        if selection_result['stillUncoveredCount'] > 0:
            logger.warn(f"  ⚠ {selection_result['stillUncoveredCount']} fields have no data in collection:")
            for field in selection_result['stillUncoveredFields'][:5]:
                logger.warn(f"    - {field}")
            if len(selection_result['stillUncoveredFields']) > 5:
                logger.warn(f"    ... and {len(selection_result['stillUncoveredFields']) - 5} more")
        
        # Test selected payment IDs
        logger.separator('-', 60)
        logger.info(f"\nTesting {len(selected_records)} selected payment IDs...")
        
        for idx, record_info in enumerate(selected_records, 1):
            payment_id = record_info['paymentId']
            covers_fields = record_info['coversFields']
            
            logger.info(f"\n[{idx}/{len(selected_records)}] Testing Payment ID: {payment_id}")
            logger.info(f"  Expected to cover {len(covers_fields)} new fields")
            logger.separator('-', 40)
            
            result = self._test_single_payment_id(payment_id)
            result['phase'] = 2  # Mark as Phase 2
            result['expectedCoverage'] = covers_fields
            phase2_results.append(result)
            
            # Show quick summary
            if result['success']:
                newly_covered = len([f for f in result['fieldResults'] 
                                    if f['status'] not in ['NOT_COVERED', 'ERROR']])
                logger.success(f"✓ Completed: {newly_covered} fields tested")
            else:
                logger.error(f"✗ Testing failed: {result.get('error')}")
        
        return phase2_results
        
    except Exception as e:
        logger.error(f"Phase 2 execution failed: {str(e)}")
        return phase2_results
```

Update `_generate_summary` to handle both phases:

```python
def _generate_summary(self, all_results: List[Dict[str, Any]]):
    """Generate and display summary report"""
    
    logger.header("TEST SUMMARY")
    
    # Separate Phase 1 and Phase 2 results
    phase1_results = [r for r in all_results if r.get('phase', 1) == 1]
    phase2_results = [r for r in all_results if r.get('phase') == 2]
    
    logger.info(f"\nPhase 1 Payment IDs Tested: {len(phase1_results)}")
    if phase2_results:
        logger.info(f"Phase 2 Payment IDs Tested: {len(phase2_results)}")
    logger.info(f"Total Payment IDs Tested: {len(all_results)}")
    
    successful_tests = sum(1 for r in all_results if r['success'])
    logger.info(f"Successful Test Runs: {successful_tests}/{len(all_results)}")
    logger.separator('-', 60)
    
    # Calculate totals
    total_passed = sum(r.get('passed', 0) for r in all_results)
    total_warnings = sum(r.get('warnings', 0) for r in all_results)
    total_failed = sum(r.get('failed', 0) for r in all_results)
    total_errors = sum(r.get('errors', 0) for r in all_results)
    total_not_covered = sum(r.get('notCovered', 0) for r in all_results)
    total_fields = total_passed + total_warnings + total_failed + total_errors + total_not_covered
    
    logger.info(f"\nField Comparison Results:")
    logger.info(f"  Total Field Tests: {total_fields}")
    logger.success(f"  ✓ Passed: {total_passed} ({total_passed/total_fields*100:.1f}%)" if total_fields > 0 else "  ✓ Passed: 0")
    logger.warn(f"  ⚠ Warnings: {total_warnings} ({total_warnings/total_fields*100:.1f}%)" if total_fields > 0 else "  ⚠ Warnings: 0")
    logger.error(f"  ✗ Failed: {total_failed} ({total_failed/total_fields*100:.1f}%)" if total_fields > 0 else "  ✗ Failed: 0")
    
    if total_errors > 0:
        logger.error(f"  ⚠ Errors: {total_errors}")
    
    if total_not_covered > 0:
        logger.warn(f"  ⊘ Not Covered: {total_not_covered} (no data in MongoDB)")
    
    logger.separator('-', 60)
    
    # Show results by phase
    if phase1_results:
        logger.info("\nPhase 1 Results:")
        for result in phase1_results:
            self._print_payment_result(result)
    
    if phase2_results:
        logger.info("\nPhase 2 Results:")
        for result in phase2_results:
            self._print_payment_result(result)
    
    # Coverage report
    logger.separator()
    self.coverage_tracker.print_coverage_report()
    
    # Execution time
    execution_time = time.time() - self.start_time
    logger.separator('-', 60)
    logger.info(f"\nTotal Execution Time: {execution_time:.2f} seconds")
    
    logger.separator()
    
    # Generate reports
    logger.info("\nGenerating Reports...")
    logger.separator('-', 60)
    
    coverage_summary = self.coverage_tracker.get_coverage_summary()
    
    try:
        # JSON report
        json_file = self.reporter.generate_json_report(
            test_config=self.test_config,
            mapping_config=self.mapping_config,
            test_results=all_results,
            coverage_summary=coverage_summary,
            execution_time=execution_time
        )
        
        # CSV report
        csv_file = self.reporter.generate_csv_report(
            test_config=self.test_config,
            test_results=all_results
        )
        
        # Summary report
        summary_file = self.reporter.generate_summary_report(
            test_config=self.test_config,
            test_results=all_results,
            coverage_summary=coverage_summary,
            execution_time=execution_time
        )
        
        logger.info("\nGenerated Reports:")
        logger.info(f"  - {json_file}")
        logger.info(f"  - {csv_file}")
        logger.info(f"  - {summary_file}")
        
    except Exception as e:
        logger.error(f"Error generating reports: {str(e)}")
    
    logger.separator()
    
    # Final verdict
    if total_failed == 0 and total_errors == 0:
        logger.success("\n✓ ALL TESTS PASSED!")
        if total_warnings > 0:
            logger.warn(f"  Note: {total_warnings} warnings detected (review recommended)")
    else:
        logger.error("\n✗ TESTS FAILED!")
        logger.error(f"  {total_failed} critical failures detected")
        if total_errors > 0:
            logger.error(f"  {total_errors} errors encountered")
    
    logger.separator()

def _print_payment_result(self, result: Dict[str, Any]):
    """Helper to print a single payment result"""
    if result['success']:
        status_icon = "✓" if result.get('failed', 0) == 0 else "✗"
        
        summary_parts = []
        if result.get('passed', 0) > 0:
            summary_parts.append(f"{result['passed']} passed")
        if result.get('warnings', 0) > 0:
            summary_parts.append(f"{result['warnings']} warnings")
        if result.get('failed', 0) > 0:
            summary_parts.append(f"{result['failed']} FAILED")
        if result.get('errors', 0) > 0:
            summary_parts.append(f"{result['errors']} errors")
        if result.get('notCovered', 0) > 0:
            summary_parts.append(f"{result['notCovered']} not covered")
        
        summary = f"{status_icon} {result['paymentId']}: {', '.join(summary_parts)}"
        
        if result.get('failed', 0) == 0:
            logger.success(f"  {summary}")
        else:
            logger.error(f"  {summary}")
    else:
        logger.error(f"  ✗ {result['paymentId']}: Test execution failed")
```

---

## 4. Update src/__init__.py

Add the new module:

```python
from .aggregation_builder import AggregationBuilder

__all__ = [
    'logger',
    'config_loader',
    'MongoDBClient',
    'TokenManager',
    'APIClient',
    'Comparator',
    'CoverageTracker',
    'Reporter',
    'AggregationBuilder',
    'TestOrchestrator'
]
```

---

## What Phase 2 Does

### **Workflow:**

1. **Identify Uncovered Fields** - Get list of attributes not covered in Phase 1
2. **Build Smart Aggregation** - Create MongoDB pipeline to find records with these fields
3. **Rank Candidates** - Sort records by how many uncovered fields they contain
4. **Select Optimal Set** - Greedy algorithm picks minimal records for maximum coverage
5. **Test Selected Records** - Run same Phase 1 process on these new payment IDs
6. **Report Results** - Combined summary of both phases

### **Example Output:**

```
PHASE 2: Finding Records for Uncovered Fields
──────────────────────────────────────────────────────────────

15 attributes not yet covered
Searching for records with these fields...

Uncovered fields:
  - messageInformation.creditorAccountName
  - messageInformation.debtorAddress1
  - messageInformation.creditorCity
  ... and 12 more

──────────────────────────────────────────────────────────────

Building MongoDB aggregation pipeline...
Executing aggregation to find candidate records...
✓ Found 47 candidate records

Selecting optimal records for maximum coverage...
✓ Selected 5 payment IDs
  Will cover 12 of 15 uncovered fields
  ⚠ 3 fields have no data in collection:
    - rareField1
    - rareField2
    - rareField3

──────────────────────────────────────────────────────────────

Testing 5 selected payment IDs...

[1/5] Testing Payment ID: PAY150
  Expected to cover 7 new fields
────────────────────────────────────────────
✓ Completed: 7 fields tested
```

---

## Summary of Phase 2

**Phase 2 is now complete!** It will:
- ✅ Automatically find uncovered fields
- ✅ Build optimized MongoDB aggregation
- ✅ Use greedy algorithm for optimal record selection
- ✅ Test minimal payment IDs for maximum coverage
- ✅ Report fields with no data in collection
- ✅ Include Phase 2 results in final reports

**This completes the MVP + Phase 2!** The utility now has all core features.

Ready to test everything together?
