import sqlglot
from sqlglot.expressions import Limit, Offset, Expression, Union

from utils.logger import setup_logger
from core.postgresql import query_execute

logger = setup_logger("add_limit")


def count_rows(query: str, limit_value: int = 100) -> int:
    """
    SQL 쿼리가 반환할 총 행 수를 계산합니다.
    LIMIT이 limit_value이고 OFFSET이 있는 경우에는 LIMIT을 제거하고 카운트합니다.(남은 페이지 카운트)

    Args:
        query: 원본 SQL 쿼리 문자열
        limit_value: LIMIT 값 (기본값: 100)

    Returns:
        int: 예상되는 결과 행 수
    """
    try:
        # 쿼리를 파싱
        parsed_query = sqlglot.parse_one(query)

        def remove_limit_if_needed(node):
            """노드에서 LIMIT limit_value를 제거하는 헬퍼 함수"""
            if isinstance(node, sqlglot.expressions.Select):
                limit_node = node.args.get("limit")
                offset_node = node.args.get("offset")

                if (
                    limit_node
                    and isinstance(limit_node.expression, sqlglot.expressions.Literal)
                    and int(limit_node.expression.sql()) == limit_value
                    and offset_node
                ):
                    node.args.pop("limit")

            elif isinstance(node, sqlglot.expressions.Union):
                limit_node = node.args.get("limit")
                offset_node = node.args.get("offset")

                if (
                    limit_node
                    and isinstance(limit_node.expression, sqlglot.expressions.Literal)
                    and int(limit_node.expression.sql()) == limit_value
                    and offset_node
                ):
                    node.args.pop("limit")

        # 쿼리 타입에 관계없이 LIMIT 제거 시도
        remove_limit_if_needed(parsed_query)

        # COUNT(*) 쿼리로 변환
        count_query = sqlglot.select("COUNT(*) AS total_count").from_(
            sqlglot.exp.Subquery(this=parsed_query, alias="subq")
        )

        # SQL 문자열로 변환
        count_sql = count_query.sql()
        logger.info(f"Count query: {count_sql}")

        # 카운트 쿼리 실행
        result = query_execute(count_sql, use_prompt_db=False)
        
        # 결과가 없는 경우 0 반환
        if not result or len(result) == 0:
            logger.info("No results found in count query")
            return 0
            
        # 결과에서 행 수 추출
        if "total_count" in result[0]:
            count = int(result[0]["total_count"])
            logger.info(f"Total rows: {count}")
            return count

        logger.warning("Count query returned no results")
        return 0

    except Exception as e:
        logger.error(f"Error in count_rows: {str(e)}")
        return limit_value + 1


def add_limit(query: str, limit_value: int = 100, offset_value: int = 0) -> str:
    """
    SQL 쿼리에 LIMIT과 OFFSET을 추가합니다.
    컬럼명이나 테이블명에 'limit'이 포함되어 있어도 정확하게 동작합니다.

    Args:
        query: SQL 쿼리 문자열
        limit_value: 추가할 LIMIT 값 (기본값: 100)
        offset_value: 추가할 OFFSET 값 (기본값: 0)

    Returns:
        LIMIT과 OFFSET이 추가된 SQL 쿼리 문자열
    """
    # 1단계: 문자열 검사로 빠른 필터링
    if "limit" not in query.lower():
        return f"{query.replace(";", "")} LIMIT {limit_value} OFFSET {offset_value}"

    # 2단계: SQL 파싱으로 정확한 검증
    try:
        parsed_query = sqlglot.parse_one(query)

        # 실제 LIMIT 절이 있는지 확인
        limit_nodes = list(parsed_query.find_all(Limit))

        if limit_nodes:
            return query

        # LIMIT이 컬럼명 등에 포함된 경우
        return f"{query} LIMIT {limit_value} OFFSET {offset_value}"

    except Exception as e:
        # 파싱 실패 시 안전하게 LIMIT 추가
        return f"{query} LIMIT {limit_value} OFFSET {offset_value}"


def pagination(query: str, limit_value: int = 100) -> str:
    """
    기존 쿼리의 OFFSET 값을 찾아서 100을 더한 새로운 OFFSET 값으로 업데이트합니다.
    add_limit 함수의 효과로 모든 쿼리에는 LIMIT과 OFFSET이 포함되어 있다고 가정합니다.

    Args:
        query: SQL 쿼리 문자열
        limit_value: LIMIT 값 (기본값: 100)
        offset_value: 현재 OFFSET 값 (기본값: 0)

    Returns:
        OFFSET 값이 100 증가된 SQL 쿼리 문자열
    """
    try:
        parsed_query = sqlglot.parse_one(query)

        # 현재 OFFSET 값 찾기
        current_offset = 0
        offset_nodes = list(parsed_query.find_all(Offset))

        if offset_nodes:
            # Offset 노드의 구조 확인
            offset_node = offset_nodes[0]

            # Offset 노드의 expression에서 숫자 값을 추출
            offset_expr = offset_node.expression
            if isinstance(offset_expr, Expression):
                current_offset = int(offset_expr.sql())

        # 새로운 OFFSET 값 계산
        new_offset = current_offset + limit_value

        # AST 수정
        if offset_nodes:
            try:
                # 새로운 Offset 노드 생성
                new_offset_node = sqlglot.expressions.Offset(
                    expression=sqlglot.expressions.Literal.number(new_offset)
                )

                # Select 노드에서 offset 속성 업데이트
                if isinstance(parsed_query, sqlglot.expressions.Select):
                    parsed_query.args["offset"] = new_offset_node
                elif isinstance(parsed_query, Union):
                    # UNION 쿼리의 경우 마지막 Select 노드의 offset 속성 업데이트
                    last_select = parsed_query.right
                    if isinstance(last_select, sqlglot.expressions.Select):
                        last_select.args["offset"] = new_offset_node
            except Exception as e:
                logger.error(f"Offset 노드 수정 중 오류: {str(e)}")
                raise
        else:
            # Offset 노드가 없는 경우 (이론적으로는 있을 수 없지만, 안전을 위해)
            logger.info("새로운 Offset 노드 추가 시도")
            try:
                parsed_query = sqlglot.expressions.Select(
                    **parsed_query.args,
                    offset=sqlglot.expressions.Offset(
                        expression=sqlglot.expressions.Literal.number(new_offset)
                    ),
                )
            except Exception as e:
                logger.error(f"Offset 노드 추가 중 오류: {str(e)}")
                raise

        # 수정된 AST를 SQL 문자열로 변환
        result = parsed_query.sql()

        return result

    except Exception as e:
        logger.error(f"Pagination 처리 중 오류 발생: {str(e)}")
        # 오류 발생 시 안전하게 기존 쿼리 반환
        return query
