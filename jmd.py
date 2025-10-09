Perfect! Crystal clear. Let me implement this now.

---

## Implementation

### **1. New Simple Reporter - src/reporter.py**

Replace the entire file with this:

```python
"""
Reporter Module
Generates simple Excel and JSON diff reports
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any
from .logger import logger


class Reporter:
    """Generates test reports"""
    
    def __init__(self, output_dir: str = "output"):
        """
        Initialize reporter
        
        Args:
            output_dir: Directory to save reports
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_excel_report(
        self,
        test_config: Dict[str, Any],
        attribute_results: List[Dict[str, Any]],
        uncovered_attributes: List[Dict[str, Any]]
    ) -> str:
        """
        Generate simple CSV/Excel report - one row per attribute
        
        Args:
            test_config: Test configuration
            attribute_results: List of tested attribute results
            uncovered_attributes: List of attributes with no data found
        
        Returns:
            Path to generated CSV file
        """
        api_name = test_config.get('apiName', 'unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{api_name}_attribute_report_{timestamp}.csv"
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                # Write header
                f.write("Payment ID,Attribute Name,MongoDB Field,MongoDB Value,Java 21 Value,Java 8 Value,Status\n")
                
                # Write tested attributes
                for result in attribute_results:
                    payment_id = result.get('paymentId', '')
                    attribute = result.get('attributeName', '')
                    mongo_field = result.get('mongoField', '')
                    mongo_value = self._escape_csv(str(result.get('mongoValue', '')))
                    java21_value = self._escape_csv(str(result.get('java21Value', '')))
                    java8_value = self._escape_csv(str(result.get('java8Value', '')))
                    status = result.get('status', 'UNKNOWN')
                    
                    f.write(f"{payment_id},{attribute},{mongo_field},{mongo_value},{java21_value},{java8_value},{status}\n")
                
                # Write uncovered attributes at the end
                for uncovered in uncovered_attributes:
                    attribute = uncovered.get('attributeName', '')
                    mongo_field = uncovered.get('mongoField', '')
                    
                    f.write(f",,{attribute},{mongo_field},,,UNCOVERED\n")
            
            logger.info(f"✓ Excel report saved: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to generate Excel report: {str(e)}")
            raise
    
    def generate_json_diff_report(
        self,
        test_config: Dict[str, Any],
        json_diff_results: List[Dict[str, Any]]
    ) -> str:
        """
        Generate JSON diff report (only when Java 8 URL exists)
        
        Args:
            test_config: Test configuration
            json_diff_results: List of JSON diff results per payment ID
        
        Returns:
            Path to generated JSON file
        """
        api_name = test_config.get('apiName', 'unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{api_name}_json_diff_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(json_diff_results, f, indent=2, default=str)
            
            logger.info(f"✓ JSON diff report saved: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to generate JSON diff report: {str(e)}")
            raise
    
    def _escape_csv(self, value: str) -> str:
        """
        Escape CSV value - wrap in quotes if contains comma or newline
        
        Args:
            value: String value
        
        Returns:
            Escaped value
        """
        if ',' in value or '\n' in value or '"' in value:
            # Escape quotes by doubling them
            value = value.replace('"', '""')
            return f'"{value}"'
        return value
```

---

### **2. Update Comparator for JSON Diff - src/comparator.py**

Add this method to the `Comparator` class:

```python
def compare_json_diff(
    self,
    java8_response: Dict[str, Any],
    java21_response: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compare Java 8 and Java 21 responses and return diff
    
    Args:
        java8_response: Java 8 API response
        java21_response: Java 21 API response
    
    Returns:
        Dict with 'status' (PASS/FAIL) and 'diff' (if failed)
    """
    try:
        # Simple deep comparison
        differences = {}
        
        def compare_recursive(path: str, val1: Any, val2: Any):
            # Convert to strings for comparison
            str1 = str(val1) if val1 is not None else ""
            str2 = str(val2) if val2 is not None else ""
            
            if str1 != str2:
                differences[path] = {
                    'java8': str1,
                    'java21': str2
                }
        
        # Get all attributes from mapping
        for mapping in self.mapping_config:
            json_attr = mapping['jsonAttribute']
            
            java8_value = get_nested_value(java8_response, json_attr)
            java21_value = get_nested_value(java21_response, json_attr)
            
            compare_recursive(json_attr, java8_value, java21_value)
        
        if differences:
            return {
                'status': 'FAIL',
                'diff': differences
            }
        else:
            return {
                'status': 'PASS'
            }
            
    except Exception as e:
        logger.error(f"JSON diff comparison failed: {str(e)}")
        return {
            'status': 'ERROR',
            'error': str(e)
        }
```

---

### **3. Update Main Orchestrator - src/main.py**

Update the class to track results differently:

```python
def __init__(self):
    """Initialize the test orchestrator"""
    self.test_config = None
    self.mapping_config = None
    self.mongo_client = None
    self.token_manager = None
    self.api_client = None
    self.comparator = None
    self.coverage_tracker = None
    self.reporter = None
    self.aggregation_builder = None
    self.start_time = None
    
    # NEW: Track results for reports
    self.attribute_results = []  # List of all attribute test results
    self.json_diff_results = []   # List of JSON diff results per payment ID
    self.uncovered_attributes = []  # List of attributes with no data
```

Update `_test_single_payment_id` method:

```python
def _test_single_payment_id(self, payment_id: str) -> Dict[str, Any]:
    """
    Test a single payment ID - compare MongoDB data with API responses
    
    Args:
        payment_id: Payment ID to test
    
    Returns:
        Dict with test results
    """
    result = {
        'paymentId': payment_id,
        'success': False,
        'passed': 0,
        'failed': 0,
        'notCovered': 0,
        'error': None
    }
    
    try:
        # Step 1: Get MongoDB data
        logger.debug("Querying MongoDB...")
        payment_id_field = self.test_config['paymentIdMapping']['mongoField']
        
        mongo_result = self.mongo_client.find_by_payment_id(payment_id, payment_id_field)
        
        if not mongo_result['success'] or not mongo_result['data']:
            logger.error(f"MongoDB record not found for {payment_id}")
            result['error'] = 'MongoDB record not found'
            return result
        
        mongo_data = mongo_result['data']
        logger.debug(f"✓ MongoDB record found ({len(mongo_data)} fields)")
        
        # Step 2: Call Java 21 API
        logger.debug("Calling Java 21 API...")
        java21_response = self.api_client.call_api(
            payment_id=payment_id,
            url_key='java21Url'
        )
        
        if not java21_response['success']:
            logger.error(f"Java 21 API call failed: {java21_response.get('error')}")
            result['error'] = f"Java 21 API failed: {java21_response.get('error')}"
            return result
        
        java21_data = java21_response['data']
        logger.debug(f"✓ Java 21 API response received")
        
        # Step 3: Call Java 8 API if URL exists
        java8_data = None
        has_java8 = self.test_config.get('java8Url') is not None
        
        if has_java8:
            logger.debug("Calling Java 8 API...")
            java8_response = self.api_client.call_api(
                payment_id=payment_id,
                url_key='java8Url'
            )
            
            if java8_response['success']:
                java8_data = java8_response['data']
                logger.debug(f"✓ Java 8 API response received")
            else:
                logger.warn(f"Java 8 API call failed: {java8_response.get('error')}")
        
        # Step 4: JSON Diff (only if Java 8 exists)
        if has_java8 and java8_data:
            json_diff_result = self.comparator.compare_json_diff(java8_data, java21_data)
            json_diff_result['paymentId'] = payment_id
            self.json_diff_results.append(json_diff_result)
            
            if json_diff_result['status'] == 'PASS':
                logger.debug("✓ JSON diff: PASS")
            else:
                logger.debug(f"✗ JSON diff: FAIL ({len(json_diff_result.get('diff', {}))} differences)")
        
        # Step 5: Compare each attribute
        logger.debug("Comparing attributes...")
        
        for mapping in self.mapping_config:
            mongo_field = mapping['mongoField']
            json_attr = mapping['jsonAttribute']
            
            # Get values
            mongo_value = get_nested_value(mongo_data, mongo_field.replace('[]', ''))
            java21_value = get_nested_value(java21_data, json_attr)
            java8_value = get_nested_value(java8_data, json_attr) if java8_data else None
            
            # Check if this attribute has data
            has_data = mongo_value is not None and mongo_value != "" and mongo_value != []
            
            if not has_data:
                # No data - add to uncovered, don't add to results yet
                result['notCovered'] += 1
                self.coverage_tracker.mark_not_covered(mapping, payment_id)
                continue
            
            # Has data - compare values
            if has_java8:
                # 3-way comparison: MongoDB vs Java 21 vs Java 8
                mongo_str = str(mongo_value)
                java21_str = str(java21_value) if java21_value is not None else ""
                java8_str = str(java8_value) if java8_value is not None else ""
                
                if mongo_str == java21_str == java8_str:
                    status = 'PASS'
                    result['passed'] += 1
                else:
                    status = 'FAIL'
                    result['failed'] += 1
            else:
                # 2-way comparison: MongoDB vs Java 21
                mongo_str = str(mongo_value)
                java21_str = str(java21_value) if java21_value is not None else ""
                
                if mongo_str == java21_str:
                    status = 'PASS'
                    result['passed'] += 1
                else:
                    status = 'FAIL'
                    result['failed'] += 1
            
            # Add to attribute results
            attr_result = {
                'paymentId': payment_id,
                'attributeName': json_attr,
                'mongoField': mongo_field,
                'mongoValue': mongo_value,
                'java21Value': java21_value,
                'java8Value': java8_value if has_java8 else '',
                'status': status
            }
            self.attribute_results.append(attr_result)
            
            # Mark as covered in tracker
            self.coverage_tracker.mark_covered(mapping, payment_id)
        
        result['success'] = True
        logger.debug(f"✓ Comparison complete: {result['passed']} passed, {result['failed']} failed, {result['notCovered']} not covered")
        
        return result
        
    except Exception as e:
        logger.error(f"Error testing payment ID: {str(e)}")
        result['error'] = str(e)
        return result
```

Update `run` method to generate new reports:

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
    
    # Step 3: Run Phase 1
    logger.separator()
    logger.header("PHASE 1: Testing Configured Payment IDs")
    
    phase1_results = self._run_phase1()
    
    # Step 4: Run Phase 2 if needed
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
    
    # Step 5: Collect uncovered attributes (fields with no data anywhere)
    logger.separator()
    logger.info("Collecting truly uncovered attributes...")
    
    uncovered_mappings = self.coverage_tracker.get_uncovered_mappings()
    for mapping in uncovered_mappings:
        self.uncovered_attributes.append({
            'attributeName': mapping['jsonAttribute'],
            'mongoField': mapping['mongoField']
        })
    
    logger.info(f"Found {len(self.uncovered_attributes)} attributes with no data in collection")
    
    # Step 6: Generate reports
    logger.separator()
    logger.header("GENERATING REPORTS")
    
    try:
        # Excel report
        excel_file = self.reporter.generate_excel_report(
            test_config=self.test_config,
            attribute_results=self.attribute_results,
            uncovered_attributes=self.uncovered_attributes
        )
        
        # JSON diff report (only if Java 8 URL exists)
        if self.test_config.get('java8Url') and self.json_diff_results:
            json_diff_file = self.reporter.generate_json_diff_report(
                test_config=self.test_config,
                json_diff_results=self.json_diff_results
            )
        
        logger.separator()
        logger.success("✓ All reports generated successfully")
        
    except Exception as e:
        logger.error(f"Error generating reports: {str(e)}")
    
    # Cleanup
    if self.mongo_client:
        self.mongo_client.close()
    
    execution_time = time.time() - self.start_time
    logger.separator()
    logger.info(f"\nTotal Execution Time: {execution_time:.2f} seconds")
    logger.separator()
    
    return True
```

Update Phase 2:

```python
def _run_phase2(self) -> List[Dict[str, Any]]:
    """
    Run Phase 2: Find one record per uncovered field
    """
    phase2_results = []
    tested_payment_ids = set()
    
    try:
        uncovered_mappings = self.coverage_tracker.get_uncovered_mappings()
        
        if not uncovered_mappings:
            return phase2_results
        
        logger.info(f"\nSearching for payment IDs with uncovered fields...")
        
        # For each uncovered field, find one payment ID
        for idx, mapping in enumerate(uncovered_mappings, 1):
            mongo_field = mapping['mongoField']
            json_attr = mapping['jsonAttribute']
            
            logger.info(f"[{idx}/{len(uncovered_mappings)}] {json_attr}")
            
            payment_id = self.aggregation_builder.find_payment_id_for_field(
                mongo_client=self.mongo_client,
                field_name=mongo_field
            )
            
            if not payment_id:
                logger.warn(f"  ⚠ No data found")
                continue
            
            if payment_id in tested_payment_ids:
                logger.info(f"  ℹ Already testing {payment_id}")
                continue
            
            logger.info(f"  → Found {payment_id}")
            tested_payment_ids.add(payment_id)
        
        # Test all unique payment IDs
        logger.separator('-', 60)
        logger.info(f"\nTesting {len(tested_payment_ids)} unique payment IDs...\n")
        
        for idx, payment_id in enumerate(tested_payment_ids, 1):
            logger.info(f"[{idx}/{len(tested_payment_ids)}] {payment_id}")
            logger.separator('-', 40)
            
            result = self._test_single_payment_id(payment_id)
            result['phase'] = 2
            phase2_results.append(result)
            
            if result['success']:
                logger.success(f"✓ Done: {result['passed']} passed, {result['failed']} failed")
        
        return phase2_results
        
    except Exception as e:
        logger.error(f"Phase 2 failed: {str(e)}")
        return phase2_results
```

---

## Run It

```bash
python run_test.py
```

**You should get:**
1. ✅ Excel CSV with exactly 300 rows (one per attribute)
2. ✅ JSON diff report (if Java 8 URL exists)
3. ✅ Uncovered attributes at the end with status "UNCOVERED"

Let me know how it goes! 🚀
