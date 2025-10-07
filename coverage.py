Excellent! Now let's add the remaining features to make this a complete, production-ready utility.

---

## Next Features to Build

1. **Coverage Tracker** - Track which fields have been tested
2. **Report Generator** - Generate JSON and CSV reports
3. **Phase 2** - Smart aggregation to find uncovered fields
4. **File Logging** - Save execution logs to file

Let's build them one by one.

---

## 1. Coverage Tracker Module

### **src/coverage_tracker.py**

```python
"""
Coverage Tracker Module
Tracks which attributes have been tested and with which payment IDs
"""

from typing import Dict, List, Set, Any
from .logger import logger


class CoverageTracker:
    """Tracks test coverage for all mapped attributes"""
    
    def __init__(self, mapping_config: List[Dict[str, str]]):
        """
        Initialize coverage tracker
        
        Args:
            mapping_config: List of field mappings
        """
        self.mapping_config = mapping_config
        
        # Track coverage: {jsonAttribute: [payment_ids where it had data]}
        self.coverage: Dict[str, List[str]] = {}
        
        # Track which fields had what values: {jsonAttribute: {paymentId: value}}
        self.field_values: Dict[str, Dict[str, Any]] = {}
        
        # Initialize all attributes as uncovered
        for mapping in mapping_config:
            json_attr = mapping['jsonAttribute']
            self.coverage[json_attr] = []
            self.field_values[json_attr] = {}
    
    def mark_field_tested(
        self, 
        json_attribute: str, 
        payment_id: str, 
        had_data: bool,
        value: Any = None
    ):
        """
        Mark a field as tested for a payment ID
        
        Args:
            json_attribute: JSON attribute name
            payment_id: Payment ID tested
            had_data: Whether the field had data (not None/missing)
            value: The actual value (for tracking)
        """
        if json_attribute not in self.coverage:
            logger.warn(f"Attribute {json_attribute} not in mapping config")
            return
        
        # Only mark as covered if it had actual data
        if had_data and value is not None:
            if payment_id not in self.coverage[json_attribute]:
                self.coverage[json_attribute].append(payment_id)
            
            # Store the value
            self.field_values[json_attribute][payment_id] = value
    
    def mark_result(self, field_result: Dict[str, Any], payment_id: str):
        """
        Mark coverage based on a field comparison result
        
        Args:
            field_result: Result from comparator
            payment_id: Payment ID that was tested
        """
        json_attr = field_result['jsonAttribute']
        mongo_value = field_result.get('mongoValue')
        
        # Field is covered if MongoDB had data for it
        had_data = mongo_value is not None
        
        self.mark_field_tested(json_attr, payment_id, had_data, mongo_value)
    
    def get_covered_attributes(self) -> List[str]:
        """Get list of attributes that have been tested with data"""
        return [attr for attr, payment_ids in self.coverage.items() if len(payment_ids) > 0]
    
    def get_uncovered_attributes(self) -> List[str]:
        """Get list of attributes that haven't been tested yet"""
        return [attr for attr, payment_ids in self.coverage.items() if len(payment_ids) == 0]
    
    def get_uncovered_mappings(self) -> List[Dict[str, str]]:
        """Get mapping config entries for uncovered attributes"""
        uncovered = self.get_uncovered_attributes()
        return [m for m in self.mapping_config if m['jsonAttribute'] in uncovered]
    
    def get_coverage_percentage(self) -> float:
        """Calculate coverage percentage"""
        if len(self.coverage) == 0:
            return 0.0
        
        covered = len(self.get_covered_attributes())
        total = len(self.coverage)
        
        return (covered / total) * 100
    
    def get_coverage_summary(self) -> Dict[str, Any]:
        """Get comprehensive coverage summary"""
        covered_attrs = self.get_covered_attributes()
        uncovered_attrs = self.get_uncovered_attributes()
        
        return {
            'total_attributes': len(self.coverage),
            'covered_count': len(covered_attrs),
            'uncovered_count': len(uncovered_attrs),
            'coverage_percentage': self.get_coverage_percentage(),
            'covered_attributes': covered_attrs,
            'uncovered_attributes': uncovered_attrs
        }
    
    def get_attribute_details(self, json_attribute: str) -> Dict[str, Any]:
        """Get details about a specific attribute's coverage"""
        if json_attribute not in self.coverage:
            return None
        
        payment_ids = self.coverage[json_attribute]
        values = self.field_values[json_attribute]
        
        return {
            'attribute': json_attribute,
            'is_covered': len(payment_ids) > 0,
            'tested_with_payment_ids': payment_ids,
            'values_seen': values,
            'num_distinct_values': len(set(str(v) for v in values.values()))
        }
    
    def print_coverage_report(self):
        """Print a formatted coverage report"""
        summary = self.get_coverage_summary()
        
        logger.separator('=', 60)
        logger.header("COVERAGE REPORT")
        
        logger.info(f"\nTotal Attributes in Mapping: {summary['total_attributes']}")
        logger.success(f"✓ Covered: {summary['covered_count']} ({summary['coverage_percentage']:.1f}%)")
        
        if summary['uncovered_count'] > 0:
            logger.warn(f"⚠ Uncovered: {summary['uncovered_count']} ({100 - summary['coverage_percentage']:.1f}%)")
            
            logger.info("\nUncovered Attributes:")
            for attr in summary['uncovered_attributes'][:10]:  # Show first 10
                # Find corresponding mongo field
                mapping = next((m for m in self.mapping_config if m['jsonAttribute'] == attr), None)
                if mapping:
                    logger.info(f"  - {attr} (MongoDB: {mapping['mongoField']})")
            
            if len(summary['uncovered_attributes']) > 10:
                logger.info(f"  ... and {len(summary['uncovered_attributes']) - 10} more")
        else:
            logger.success("\n✓ ALL ATTRIBUTES COVERED!")
        
        logger.separator('=', 60)
```

---

## 2. Report Generator Module

### **src/reporter.py**

```python
"""
Reporter Module
Generates JSON and CSV reports
"""

import json
import csv
import os
from datetime import datetime
from typing import Dict, List, Any
from .logger import logger


class Reporter:
    """Generates various report formats"""
    
    def __init__(self, output_dir: str = "output"):
        """
        Initialize reporter
        
        Args:
            output_dir: Directory to save reports
        """
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"Created output directory: {output_dir}")
    
    def generate_json_report(
        self,
        test_config: Dict[str, Any],
        mapping_config: List[Dict[str, str]],
        test_results: List[Dict[str, Any]],
        coverage_summary: Dict[str, Any],
        execution_time: float
    ) -> str:
        """
        Generate detailed JSON report
        
        Returns:
            Path to generated report file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        api_name = test_config['apiName']
        filename = f"{api_name}_detailed_report_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        # Build report structure
        report = {
            'metadata': {
                'apiName': api_name,
                'testTimestamp': datetime.now().isoformat(),
                'executionTimeSeconds': round(execution_time, 2),
                'totalAttributesMapped': len(mapping_config),
                'totalPaymentIdsTested': len(test_results)
            },
            'configuration': {
                'java21ApiUrl': test_config['java21ApiUrl'],
                'java8ApiUrl': test_config.get('java8ApiUrl'),
                'testPaymentIds': test_config['testPaymentIds']
            },
            'coverage': coverage_summary,
            'paymentIdResults': []
        }
        
        # Add results for each payment ID
        for result in test_results:
            payment_result = {
                'paymentId': result['paymentId'],
                'success': result['success'],
                'summary': {
                    'passed': result.get('passed', 0),
                    'warnings': result.get('warnings', 0),
                    'failed': result.get('failed', 0),
                    'errors': result.get('errors', 0)
                },
                'fieldResults': []
            }
            
            # Add field-by-field results
            for field_result in result.get('fieldResults', []):
                payment_result['fieldResults'].append({
                    'mongoField': field_result['mongoField'],
                    'jsonAttribute': field_result['jsonAttribute'],
                    'mongoType': field_result['mongoType'],
                    'mongoValue': self._serialize_value(field_result['mongoValue']),
                    'java21Value': self._serialize_value(field_result['java21Value']),
                    'java8Value': self._serialize_value(field_result.get('java8Value')),
                    'status': field_result['status'],
                    'severity': field_result['severity'],
                    'mongoVsJava21': field_result.get('mongoVsJava21'),
                    'java8VsJava21': field_result.get('java8VsJava21')
                })
            
            report['paymentIdResults'].append(payment_result)
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        logger.success(f"✓ JSON report generated: {filepath}")
        return filepath
    
    def generate_csv_report(
        self,
        test_config: Dict[str, Any],
        test_results: List[Dict[str, Any]]
    ) -> str:
        """
        Generate CSV comparison matrix
        
        Returns:
            Path to generated report file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        api_name = test_config['apiName']
        filename = f"{api_name}_comparison_matrix_{timestamp}.csv"
        filepath = os.path.join(self.output_dir, filename)
        
        # CSV headers
        headers = [
            'Payment ID',
            'Attribute Name',
            'MongoDB Field',
            'MongoDB Type',
            'MongoDB Value',
            'Java 21 Value',
            'Java 8 Value',
            'Status',
            'Severity',
            'Mismatch Type',
            'Notes'
        ]
        
        # Write CSV
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            
            # Write data rows
            for result in test_results:
                if not result['success']:
                    continue
                
                payment_id = result['paymentId']
                
                for field_result in result.get('fieldResults', []):
                    mongo_vs_java21 = field_result.get('mongoVsJava21', {})
                    
                    row = [
                        payment_id,
                        field_result['jsonAttribute'],
                        field_result['mongoField'],
                        field_result['mongoType'],
                        self._format_value(field_result['mongoValue']),
                        self._format_value(field_result['java21Value']),
                        self._format_value(field_result.get('java8Value')),
                        field_result['status'],
                        field_result['severity'],
                        mongo_vs_java21.get('mismatchType', ''),
                        mongo_vs_java21.get('note', '')
                    ]
                    writer.writerow(row)
        
        logger.success(f"✓ CSV report generated: {filepath}")
        return filepath
    
    def generate_summary_report(
        self,
        test_config: Dict[str, Any],
        test_results: List[Dict[str, Any]],
        coverage_summary: Dict[str, Any],
        execution_time: float
    ) -> str:
        """
        Generate human-readable text summary
        
        Returns:
            Path to generated report file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        api_name = test_config['apiName']
        filename = f"{api_name}_summary_{timestamp}.txt"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write(f"API MIGRATION TEST REPORT - {api_name}\n")
            f.write("="*70 + "\n\n")
            
            f.write(f"Test Execution Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Execution Time: {execution_time:.2f} seconds\n\n")
            
            f.write("-"*70 + "\n")
            f.write("CONFIGURATION\n")
            f.write("-"*70 + "\n")
            f.write(f"Java 21 API: {test_config['java21ApiUrl']}\n")
            if test_config.get('java8ApiUrl'):
                f.write(f"Java 8 API: {test_config['java8ApiUrl']}\n")
            f.write(f"Payment IDs Tested: {len(test_config['testPaymentIds'])}\n\n")
            
            f.write("-"*70 + "\n")
            f.write("COVERAGE SUMMARY\n")
            f.write("-"*70 + "\n")
            f.write(f"Total Attributes: {coverage_summary['total_attributes']}\n")
            f.write(f"Covered: {coverage_summary['covered_count']} ({coverage_summary['coverage_percentage']:.1f}%)\n")
            f.write(f"Uncovered: {coverage_summary['uncovered_count']}\n\n")
            
            if coverage_summary['uncovered_count'] > 0:
                f.write("Uncovered Attributes:\n")
                for attr in coverage_summary['uncovered_attributes']:
                    f.write(f"  - {attr}\n")
                f.write("\n")
            
            f.write("-"*70 + "\n")
            f.write("TEST RESULTS\n")
            f.write("-"*70 + "\n\n")
            
            total_passed = sum(r.get('passed', 0) for r in test_results)
            total_warnings = sum(r.get('warnings', 0) for r in test_results)
            total_failed = sum(r.get('failed', 0) for r in test_results)
            total_errors = sum(r.get('errors', 0) for r in test_results)
            total_tests = total_passed + total_warnings + total_failed + total_errors
            
            f.write(f"Total Field Comparisons: {total_tests}\n")
            f.write(f"  Passed: {total_passed} ({total_passed/total_tests*100:.1f}%)\n" if total_tests > 0 else "  Passed: 0\n")
            f.write(f"  Warnings: {total_warnings} ({total_warnings/total_tests*100:.1f}%)\n" if total_tests > 0 else "  Warnings: 0\n")
            f.write(f"  Failed: {total_failed} ({total_failed/total_tests*100:.1f}%)\n" if total_tests > 0 else "  Failed: 0\n")
            if total_errors > 0:
                f.write(f"  Errors: {total_errors}\n")
            f.write("\n")
            
            f.write("Results by Payment ID:\n")
            for result in test_results:
                if result['success']:
                    status = "PASS" if result.get('failed', 0) == 0 else "FAIL"
                    f.write(f"  [{status}] {result['paymentId']}: ")
                    f.write(f"{result.get('passed', 0)} passed, ")
                    f.write(f"{result.get('warnings', 0)} warnings, ")
                    f.write(f"{result.get('failed', 0)} failed\n")
                else:
                    f.write(f"  [ERROR] {result['paymentId']}: {result.get('error', 'Unknown error')}\n")
            
            f.write("\n" + "="*70 + "\n")
            
            if total_failed == 0 and total_errors == 0:
                f.write("RESULT: ALL TESTS PASSED\n")
                if total_warnings > 0:
                    f.write(f"Note: {total_warnings} warnings detected (review recommended)\n")
            else:
                f.write("RESULT: TESTS FAILED\n")
                f.write(f"Critical failures: {total_failed}\n")
                if total_errors > 0:
                    f.write(f"Errors: {total_errors}\n")
            
            f.write("="*70 + "\n")
        
        logger.success(f"✓ Summary report generated: {filepath}")
        return filepath
    
    def _serialize_value(self, value: Any) -> Any:
        """Convert value to JSON-serializable format"""
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, (list, dict)):
            return value
        return str(value)
    
    def _format_value(self, value: Any) -> str:
        """Format value for CSV display"""
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, (list, dict)):
            return json.dumps(value, ensure_ascii=False, default=str)
        return str(value)
```

---

## 3. Update Main Orchestrator with Coverage and Reports

### **Update src/main.py** (add these methods and modify existing ones)

Add these imports at the top:
```python
from .coverage_tracker import CoverageTracker
from .reporter import Reporter
```

Add to `__init__`:
```python
self.coverage_tracker = None
self.reporter = None
```

Add to `_initialize_components`:
```python
# Initialize coverage tracker
logger.info("\nInitializing coverage tracker...")
self.coverage_tracker = CoverageTracker(self.mapping_config)
logger.success("✓ Coverage tracker initialized")

# Initialize reporter
logger.info("Initializing reporter...")
self.reporter = Reporter(output_dir="output")
logger.success("✓ Reporter initialized")
```

Update `_test_single_payment_id` to track coverage (add after field comparison loop):
```python
# Track coverage for each field
for field_result in result['fieldResults']:
    self.coverage_tracker.mark_result(field_result, payment_id)
```

Update `_generate_summary` to include coverage and generate reports:
```python
def _generate_summary(self, phase1_results: List[Dict[str, Any]]):
    """Generate and display summary report"""
    
    logger.header("TEST SUMMARY")
    
    total_payment_ids = len(phase1_results)
    successful_tests = sum(1 for r in phase1_results if r['success'])
    
    total_passed = sum(r['passed'] for r in phase1_results)
    total_warnings = sum(r['warnings'] for r in phase1_results)
    total_failed = sum(r['failed'] for r in phase1_results)
    total_errors = sum(r['errors'] for r in phase1_results)
    total_fields = total_passed + total_warnings + total_failed + total_errors
    
    logger.info(f"\nPayment IDs Tested: {total_payment_ids}")
    logger.info(f"Successful Test Runs: {successful_tests}/{total_payment_ids}")
    logger.separator('-', 60)
    
    logger.info(f"\nField Comparison Results:")
    logger.info(f"  Total Fields Tested: {total_fields}")
    logger.success(f"  ✓ Passed: {total_passed} ({total_passed/total_fields*100:.1f}%)" if total_fields > 0 else "  ✓ Passed: 0")
    logger.warn(f"  ⚠ Warnings: {total_warnings} ({total_warnings/total_fields*100:.1f}%)" if total_fields > 0 else "  ⚠ Warnings: 0")
    logger.error(f"  ✗ Failed: {total_failed} ({total_failed/total_fields*100:.1f}%)" if total_fields > 0 else "  ✗ Failed: 0")
    
    if total_errors > 0:
        logger.error(f"  ⚠ Errors: {total_errors}")
    
    logger.separator('-', 60)
    
    # Show critical issues by payment ID
    logger.info("\nIssues by Payment ID:")
    for result in phase1_results:
        if result['success']:
            status_icon = "✓" if result['failed'] == 0 else "✗"
            status_color = "success" if result['failed'] == 0 else "error"
            
            summary = f"{status_icon} {result['paymentId']}: "
            summary += f"{result['passed']} passed"
            
            if result['warnings'] > 0:
                summary += f", {result['warnings']} warnings"
            if result['failed'] > 0:
                summary += f", {result['failed']} FAILED"
            if result['errors'] > 0:
                summary += f", {result['errors']} errors"
            
            if status_color == "success":
                logger.success(f"  {summary}")
            else:
                logger.error(f"  {summary}")
        else:
            logger.error(f"  ✗ {result['paymentId']}: Test execution failed")
    
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
            test_results=phase1_results,
            coverage_summary=coverage_summary,
            execution_time=execution_time
        )
        
        # CSV report
        csv_file = self.reporter.generate_csv_report(
            test_config=self.test_config,
            test_results=phase1_results
        )
        
        # Summary report
        summary_file = self.reporter.generate_summary_report(
            test_config=self.test_config,
            test_results=phase1_results,
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
```

---

## Test These New Features

Run the utility again:

```bash
python run_test.py
```

You should now see:
1. Coverage report showing which attributes were tested
2. Three report files generated in `output/` directory:
   - `{apiName}_detailed_report_{timestamp}.json`
   - `{apiName}_comparison_matrix_{timestamp}.csv`
   - `{apiName}_summary_{timestamp}.txt`

---

**Ready to continue with Phase 2 (aggregation for uncovered fields)?** Let me know if the coverage tracking and report generation are working well!
