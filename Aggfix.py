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
    
    def _get_field_reference(self, field_path: str) -> str:
        """
        Get proper field reference for aggregation
        Handles both nested fields and literal dot notation
        
        Args:
            field_path: Field path (e.g., "MIFMP.DbAccNo" or "user.name")
        
        Returns:
            Proper reference string (e.g., "$MIFMP.DbAccNo")
        """
        # For aggregation expressions, prefix with $
        return f"${field_path}"
    
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
            field_ref = self._get_field_reference(field)
            count_expressions.append({
                '$cond': [
                    {
                        '$and': [
                            {'$ne': [field_ref, None]},
                            {'$ne': [field_ref, ""]},
                            {'$ne': [field_ref, []]}  # Also exclude empty arrays
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
            
            # Stage 3: Filter out records with 0 count (shouldn't happen, but safety)
            {
                '$match': {
                    'uncoveredFieldCount': {'$gt': 0}
                }
            },
            
            # Stage 4: Sort by count (descending - records with most fields first)
            {
                '$sort': {
                    'uncoveredFieldCount': -1
                }
            },
            
            # Stage 5: Limit to top candidates
            {
                '$limit': limit
            }
            
            # Note: We don't use $project to avoid losing nested data
            # We'll access fields using dot notation when selecting
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
        logger.debug(f"Total uncovered fields to find: {len(uncovered_fields)}")
        
        # DEBUG: Show structure of first record
        if len(aggregation_results) > 0:
            first_record = aggregation_results[0]
            logger.info("\n🔍 DEBUG: Inspecting first candidate record structure...")
            logger.info(f"  Top-level keys: {list(first_record.keys())[:15]}")
            
            # Check if MIFMP exists
            if 'MIFMP' in first_record:
                logger.info(f"  ✓ MIFMP exists and is type: {type(first_record['MIFMP']).__name__}")
                if isinstance(first_record['MIFMP'], dict):
                    logger.info(f"  MIFMP sub-keys (first 10): {list(first_record['MIFMP'].keys())[:10]}")
            else:
                logger.warn(f"  ✗ MIFMP not found in record")
            
            # Test accessing a few uncovered fields
            test_fields = list(uncovered_fields)[:3]
            logger.info(f"\n  Testing access to {len(test_fields)} sample uncovered fields:")
            for field in test_fields:
                value = self._get_field_from_record(first_record, field)
                if value is not None and value != "" and value != []:
                    logger.success(f"    ✓ {field}: {value}")
                else:
                    logger.warn(f"    ✗ {field}: {value} (empty or None)")
        
        # Now do the actual selection
        for idx, record in enumerate(aggregation_results):
            # Find which NEW fields this record would cover
            new_fields = []
            fields_checked = 0
            fields_found = 0
            
            for field in uncovered_fields:
                if field not in covered_fields:
                    fields_checked += 1
                    # Check if this record has data for this field
                    value = self._get_field_from_record(record, field)
                    
                    if value is not None and value != "" and value != []:
                        new_fields.append(field)
                        fields_found += 1
            
            if idx < 3:  # Log first 3 records in detail
                logger.debug(f"\n  Record {idx}: Checked {fields_checked} fields, found {fields_found} with data")
            
            # If this record covers new fields, select it
            if new_fields:
                payment_id = self._get_field_from_record(record, self.payment_id_field)
                
                if payment_id:
                    selected_records.append({
                        'paymentId': payment_id,
                        'coversFields': new_fields,
                        'totalUncoveredFields': record.get('uncoveredFieldCount', len(new_fields))
                    })
                    
                    # Mark these fields as covered
                    covered_fields.update(new_fields)
                    
                    logger.info(f"  ✓ Selected {payment_id}: covers {len(new_fields)} new fields")
                    if idx < 3:  # Show which fields for first 3
                        logger.debug(f"    Fields: {new_fields[:5]}{'...' if len(new_fields) > 5 else ''}")
            
            # Stop if all fields covered
            if len(covered_fields) == len(uncovered_fields):
                logger.debug("  All uncovered fields now have coverage candidates")
                break
        
        still_uncovered = uncovered_fields - covered_fields
        
        logger.info(f"\n📊 Selection complete:")
        logger.info(f"  Records selected: {len(selected_records)}")
        logger.info(f"  Fields covered: {len(covered_fields)}/{len(uncovered_fields)}")
        logger.info(f"  Still uncovered: {len(still_uncovered)}")
        
        if len(still_uncovered) > 0 and len(still_uncovered) <= 10:
            logger.info(f"  Uncovered fields: {list(still_uncovered)}")
        
        return {
            'selectedRecords': selected_records,
            'coveredCount': len(covered_fields),
            'stillUncoveredCount': len(still_uncovered),
            'stillUncoveredFields': list(still_uncovered)
        }
    
    def _get_field_from_record(self, record: Dict[str, Any], field_path: str) -> Any:
        """
        Get field value from record, handling dot notation for nested objects
        
        Args:
            record: MongoDB record
            field_path: Field path (e.g., "MIFMP.DbAccNo")
        
        Returns:
            Field value or None
        """
        if not record or not field_path:
            return None
        
        # Split path into parts
        parts = field_path.split('.')
        current = record
        
        # Navigate through nested structure
        for i, part in enumerate(parts):
            if current is None:
                return None
            
            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                else:
                    # Field not found at this level
                    return None
            else:
                # Current is not a dict, can't navigate further
                return None
        
        return current
