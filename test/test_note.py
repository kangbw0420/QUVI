"""
특정 부분 테스트: note1 조건을 similar notes로 변환하는 기능
"""
import asyncio
import sqlglot
from sqlglot import exp
import re

# 테스트용 샘플 쿼리
SAMPLE_QUERY = """
SELECT * FROM aicfo_get_all_trsc('test_intt_id', 'test_user_id', 'test_company', '20240101', '20240131')
WHERE note1 = 'deposit'
"""

# similar_notes가 이미 준비되었다고 가정
def test_note_condition_replacement():
    """
    note1 조건을 similar notes로 변환하는 기능만 테스트
    """
    print("======== 노트 조건 변환 테스트 ========")
    
    # 파라미터 설정
    query = SAMPLE_QUERY
    original_notes = ['deposit']
    note_to_similar = {
        'deposit': ['deposit', 'bank deposit', 'cash deposit']
    }
    
    print(f"원본 쿼리: {query}")
    print(f"원본 노트: {original_notes}")
    print(f"유사 노트 매핑: {note_to_similar}")
    
    try:
        # SQL 쿼리 파싱
        ast = sqlglot.parse_one(query, dialect='postgres')
        
        # note1 조건 찾기
        note_conditions = find_note_conditions(ast)
        print(f"발견된 노트 조건 수: {len(note_conditions)}")
        
        # 노트 조건 교체 수행
        for condition in note_conditions:
            original_note = condition['value']
            similar_notes = note_to_similar.get(original_note, [])
            
            if not similar_notes:
                print(f"'{original_note}'에 대한 유사 노트가 없습니다. 원래 조건 유지")
                continue
            
            print(f"'{original_note}'에 대한 유사 노트: {similar_notes}")
            
            # 원본 컬럼 추출
            original_column = condition['node'].this
            print(f"원본 컬럼: {original_column}")
            
            # 각 유사 노트에 대한 ILIKE 조건 생성
            or_conditions = []
            for similar_note in similar_notes:
                ilike_expr = exp.ILike(
                    this=original_column.copy(),
                    expression=exp.Literal.string(f"%{similar_note}%")
                )
                or_conditions.append(ilike_expr)
                print(f"'{similar_note}'에 대한 ILIKE 조건 생성")
            
            # OR로 모든 조건 결합
            if len(or_conditions) == 1:
                new_expr = or_conditions[0]
                print("하나의 조건만 있음, 단일 ILIKE 표현식 사용")
            else:
                # OR 체인 생성
                new_expr = or_conditions[0]
                for i in range(1, len(or_conditions)):
                    new_expr = exp.Or(this=new_expr, expression=or_conditions[i])
                print(f"{len(or_conditions)}개 조건으로 OR 체인 생성")
            
            # 괄호로 감싸기
            new_expr = exp.Paren(this=new_expr)
            print("괄호로 감싸기 완료")
            
            # 변환 전 SQL
            before_sql = ast.sql(dialect='postgres')
            print(f"변환 전 SQL: {before_sql}")
            
            # 노드 교체 시도
            try:
                # 노드 객체 정보
                print(f"변환 전 노드: {type(condition['node']).__name__}")
                print(f"새 표현식: {type(new_expr).__name__}")
                
                # 노드 교체
                replaced = condition['node'].replace(new_expr)
                print(f"노드 교체 결과: {replaced}")
                
                # 변환 후 SQL
                after_sql = ast.sql(dialect='postgres')
                print(f"변환 후 SQL: {after_sql}")
                
                # 변환 여부 확인
                if before_sql == after_sql:
                    print("경고: SQL이 변경되지 않았습니다!")
                    
                    # 대안: 문자열 기반 직접 변환
                    print("\n대안: 문자열 기반 직접 변환 시도")
                    modified_query = modify_query_with_regex(query, note_to_similar)
                    print(f"문자열 변환 결과: {modified_query}")
                    
                    # 유사 노트가 포함되었는지 확인
                    for note in similar_notes:
                        if f"%{note}%" in modified_query:
                            print(f"  ✓ '{note}'가 변환된 쿼리에 있습니다")
                        else:
                            print(f"  ✗ 오류: '{note}'를 변환된 쿼리에서 찾을 수 없습니다")
                else:
                    print("SQL이 성공적으로 변경되었습니다")
                    
                    # 유사 노트가 포함되었는지 확인
                    for note in similar_notes:
                        if f"%{note}%" in after_sql:
                            print(f"  ✓ '{note}'가 변환된 쿼리에 있습니다")
                        else:
                            print(f"  ✗ 오류: '{note}'를 변환된 쿼리에서 찾을 수 없습니다")
            
            except Exception as e:
                print(f"노드 교체 중 오류 발생: {e}")
                # 노드 교체 실패 시 문자열 기반 방식 사용
                print("\n대안: 문자열 기반 직접 변환 시도")
                modified_query = modify_query_with_regex(query, note_to_similar)
                print(f"문자열 변환 결과: {modified_query}")
        
    except Exception as e:
        print(f"테스트 중 오류 발생: {e}")

def find_note_conditions(ast: exp.Expression):
    """SQL AST에서 note1 조건 찾기"""
    note_conditions = []
    visited_nodes = set()
    
    def process_node(node):
        # 이미 방문한 노드는 건너뛰기
        node_id = id(node)
        if node_id in visited_nodes:
            return
        visited_nodes.add(node_id)
        
        # note1 조건인지 확인
        if isinstance(node, (exp.EQ, exp.Like, exp.ILike)):
            if (isinstance(node.this, exp.Column) and 
                node.this.name == 'note1'):
                # 값 추출
                if isinstance(node.expression, exp.Literal):
                    note_str = str(node.expression.this).strip("'%")
                else:
                    note_str = str(node.expression).strip("'%")
                
                # 조건 정보 저장
                note_conditions.append({
                    'type': type(node).__name__,
                    'value': note_str,
                    'node': node
                })
        
        # 자식 노드 처리
        for arg_name, arg_value in node.args.items():
            if isinstance(arg_value, exp.Expression):
                process_node(arg_value)
            elif isinstance(arg_value, list):
                for item in arg_value:
                    if isinstance(item, exp.Expression):
                        process_node(item)
    
    # 루트 노드부터 시작
    process_node(ast)
    
    return note_conditions

def modify_query_with_regex(query: str, note_to_similar: dict) -> str:
    """
    직접 문자열 조작으로 SQL 쿼리의 note1 조건을 유사 노트로 변경
    """
    # 각 원본 노트에 대해 처리
    for original_note, similar_notes in note_to_similar.items():
        if not similar_notes:
            continue
            
        # note1 조건을 찾기 위한 패턴
        patterns = [
            fr"note1\s*=\s*'?{re.escape(original_note)}'?",
            fr"note1\s+LIKE\s+'?%?{re.escape(original_note)}%?'?",
            fr"note1\s+ILIKE\s+'?%?{re.escape(original_note)}%?'?"
        ]
        
        # 유사 노트로 대체할 조건 생성
        similar_conditions = []
        for note in similar_notes:
            similar_conditions.append(f"note1 ILIKE '%{note}%'")
        
        replacement = f"({' OR '.join(similar_conditions)})"
        
        # 모든 패턴에 대해 대체 수행
        for pattern in patterns:
            query = re.sub(pattern, replacement, query, flags=re.IGNORECASE)
    
    return query

def test_complex_query():
    """여러 조건이 있는 복잡한 쿼리에서 테스트"""
    print("\n======== 복잡한 쿼리 테스트 ========")
    
    # 복잡한 쿼리
    query = """
    SELECT a.*, b.account_name 
    FROM aicfo_get_all_trsc('test_intt_id', 'test_user_id', 'test_company', '20240101', '20240131') a
    JOIN accounts b ON a.account_id = b.id
    WHERE a.note1 = 'deposit' 
      AND a.trsc_amt > 1000 
      AND (a.trsc_date BETWEEN '20240101' AND '20240131' OR a.note1 = 'withdraw')
    ORDER BY a.trsc_date DESC
    """
    
    print(f"원본 복잡한 쿼리: {query}")
    
    # 테스트 데이터
    note_to_similar = {
        'deposit': ['deposit', 'bank deposit', 'cash deposit'],
        'withdraw': ['withdraw', 'atm withdraw']
    }
    
    # 직접 문자열 변환 시도
    modified_query = modify_query_with_regex(query, note_to_similar)
    print(f"변환된 복잡한 쿼리: {modified_query}")
    
    # 유사 노트가 포함되었는지 확인
    for note, similar_notes in note_to_similar.items():
        print(f"\n'{note}'에 대한 유사 노트 확인:")
        for similar in similar_notes:
            if f"%{similar}%" in modified_query:
                print(f"  ✓ '{similar}'가 변환된 쿼리에 있습니다")
            else:
                print(f"  ✗ 오류: '{similar}'를 변환된 쿼리에서 찾을 수 없습니다")

if __name__ == "__main__":
    test_note_condition_replacement()
    test_complex_query()