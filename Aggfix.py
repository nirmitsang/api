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
    # Group fields by their top-level parent (e.g., "MIFMP" from "MIFMP.BbkBic")
    top_level_objects = set()
    for field in uncovered_fields:
        if '.' in field:
            top_level = field.split('.')[0]
            top_level_objects.add(top_level)
    
    # Build project stage
    project_fields = {
        self.payment_id_field: 1,  # Always include payment ID
        'uncoveredFieldCount': 1   # Include the count we calculated
    }
    
    # Include all top-level objects (like MIFMP, MsgFees, etc.)
    for top_level in top_level_objects:
        project_fields[top_level] = 1
    
    # Also include any non-nested uncovered fields
    for field in uncovered_fields:
        if '.' not in field:
            project_fields[field] = 1
    
    logger.debug(f"Will project these top-level objects: {list(top_level_objects)}")
    
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
        
        # Stage 6: Project the fields we need (CRITICAL!)
        {
            '$project': project_fields
        }
    ]
    
    return pipeline
