from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Set
import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from utils.query.view.classify_query import QueryClassifier
from utils.query.view.extract_date import DateExtractor

@dataclass
class ViewFunction:
    """View function parameters and metadata"""
    base_name: str
    use_intt_id: str
    user_id: str
    view_com: str
    from_date: str
    to_date: str
    alias: Optional[str] = None

class ViewTableTransformer:
    """SQL query transformer for view table functionality"""
    
    def __init__(self, selected_table: str, user_info: Tuple[str, str], 
                 view_com: str, view_date: Tuple[str, str], flags: Dict[str, bool]):
        self.selected_table = selected_table
        self.use_intt_id, self.user_id = user_info
        self.view_com = view_com
        self.from_date, self.to_date = view_date
        self.flags = flags
        self.classifier = QueryClassifier()

    def transform_query(self, query: str) -> str:
        """Transform SQL query by adding view table functions"""
        try:
            # Parse the query
            ast = sqlglot.parse_one(query, dialect='postgres')
            
            # Get query structure info
            query_info = self.classifier.classify_query(query)
            
            # Handle different query types
            if query_info.has_union:
                transformed_ast = self._handle_union_query(ast)
            else:
                transformed_ast = self._handle_single_query(ast)
            
            return transformed_ast.sql(dialect='postgres')
            
        except ParseError as e:
            raise ValueError(f"Failed to parse SQL query: {str(e)}")

    def _handle_union_query(self, ast: exp.Union) -> exp.Expression:
        transformed_left = self._handle_single_query(ast.left)
        transformed_right = self._handle_single_query(ast.right)
        
        return exp.Union(
            this=transformed_left,
            expression=transformed_right,
            distinct=False
        )

    def _handle_single_query(self, ast: exp.Expression) -> exp.Expression:
        """Transform a single SELECT query"""
        def transform_table(node: exp.Expression) -> exp.Expression:
            if isinstance(node, exp.Table):
                if node.name.startswith('aicfo_get_all_'):
                    view_func = self._create_view_function(
                        ViewFunction(
                            base_name=node.name,
                            use_intt_id=self.use_intt_id,
                            user_id=self.user_id,
                            view_com=self.view_com,
                            from_date=self.from_date,
                            to_date=self.to_date,
                            alias=node.alias
                        )
                    )
                    return view_func
            return node

        # Transform the AST
        transformed_ast = ast.transform(transform_table)
        
        # Handle subqueries if present
        if self.classifier.has_subquery(ast.sql()):
            transformed_ast = self._handle_subqueries(transformed_ast)
        
        return transformed_ast

    def _handle_subqueries(self, ast: exp.Expression) -> exp.Expression:
        """Handle subqueries in the AST"""
        def transform_subquery(node: exp.Expression) -> exp.Expression:
            if isinstance(node, exp.Subquery):
                subquery_ast = self._handle_single_query(node.this)
                return exp.Subquery(this=subquery_ast)
            return node

        return ast.transform(transform_subquery)

    def _create_view_function(self, view_func: ViewFunction) -> exp.Expression:
        """Create a view function call expression"""
        func_call = exp.Anonymous(
            this=view_func.base_name,
            expressions=[
                exp.Literal.string(view_func.use_intt_id),
                exp.Literal.string(view_func.user_id),
                exp.Literal.string(view_func.view_com),
                exp.Literal.string(view_func.from_date),
                exp.Literal.string(view_func.to_date)
            ]
        )
        
        if view_func.alias:
            return exp.Alias(this=func_call, alias=view_func.alias)
        return func_call

    @staticmethod
    def _validate_query(query: str) -> bool:
        """Validate if the query can be transformed"""
        try:
            sqlglot.parse_one(query, dialect='postgres')
            return True
        except ParseError:
            return False

class ViewTableBuilder:
    """Helper class for building view table queries"""
    
    @staticmethod
    def transform_query(query: str, selected_table: str, view_com: str, 
                       user_info: Tuple[str, str], view_date: Tuple[str, str], 
                       flags: Dict[str, bool]) -> str:
        """Main entry point for transforming queries with view tables
        
        Args:
            query: Original SQL query
            selected_table: Target table type ('amt', 'stock', 'trsc')
            view_com: Company view name
            user_info: Tuple of (use_intt_id, user_id)
            view_date: Tuple of (from_date, to_date)
            flags: Dictionary for tracking transformation flags
            
        Returns:
            Transformed SQL query with view table functions
        """
        transformer = ViewTableTransformer(
            selected_table=selected_table,
            user_info=user_info,
            view_com=view_com,
            view_date=view_date,
            flags=flags
        )
        
        # Transform the query
        transformed_query = transformer.transform_query(query)
        
        return transformed_query

def add_view_table(query: str, selected_table: str, view_com: str,
                  user_info: Tuple[str, str], view_date: Tuple[str, str],
                  flags: Dict[str, bool]) -> str:
    """Legacy interface wrapper for view table transformation"""
    return ViewTableBuilder.transform_query(
        query=query,
        selected_table=selected_table,
        view_com=view_com,
        user_info=user_info,
        view_date=view_date,
        flags=flags
    )