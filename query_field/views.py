from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import logging

# Try to import neomodel for Neo4j connection
try:
    from neomodel import db
    HAS_NEO4J = True
except ImportError:
    HAS_NEO4J = False

logger = logging.getLogger(__name__)

def query_console(request):
    """
    Renders the dedicated template for the query console.
    """
    return render(request, 'query_field/console.html')

@require_http_methods(["POST"])
def execute_query(request):
    """
    Executes a Cypher query against the Neo4j database.
    """
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        
        if not query:
            return JsonResponse({
                "status": "error",
                "message": "Query cannot be empty."
            }, status=400)

        if not HAS_NEO4J:
            return JsonResponse({
                "status": "error",
                "message": "Neo4j driver (neomodel) not found. Please install neomodel and configure settings."
            }, status=500)

        # Execute query using neomodel
        # db.cypher_query returns (results, meta)
        # results is a list of lists (rows)
        # meta is a list of column names (headers)
        results, meta = db.cypher_query(query)
        
        # Format data for JSON response
        # Convert neomodel objects to simple types if necessary, but usually basic types work.
        # If nodes are returned, they might be complex objects. 
        # For a raw console, we usually expect the user to return properties or we stringify.
        # Let's try to serialize best effort.
        
        formatted_data = []
        for row in results:
            row_dict = {}
            for i, col_name in enumerate(meta):
                val = row[i]
                # Handle potential complex objects (Nodes, Relationships) by converting to string or dict
                if hasattr(val, '__properties__'): # neomodel StructuredNode
                    val = val.__properties__
                elif hasattr(val, 'id') and hasattr(val, '_properties'): # neo4j driver Node
                     val = dict(val._properties)
                
                row_dict[col_name] = val
            formatted_data.append(row_dict)

        return JsonResponse({
            "status": "success",
            "columns": meta,
            "data": formatted_data
        })

    except Exception as e:
        logger.error(f"Query execution failed: {str(e)}")
        return JsonResponse({
            "status": "error",
            "message": f"Error executing query: {str(e)}"
        }, status=400)
