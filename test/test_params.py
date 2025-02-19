import unittest
import json
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# 테스트할 모듈 import
from graph.task.params import parameters, convert_date_format

class TestParamsFunction(unittest.TestCase):
    """parameters 함수에 대한 테스트 클래스"""

    def setUp(self):
        """테스트 설정"""
        self.trace_id = "test_trace_123"
        self.selected_api = "aicfo_get_financial_status"
        self.user_question = "3월 계좌 잔액 보여줘"
        self.main_com = "테스트회사"
        self.user_info = ("test_user", "test_intt")
        self.today = "2025-02-19"
        self.yogeumjae = "stock1"
        self.flags = {}
        
        # 공통으로 사용되는 mock 객체들
        self.mock_db_service = MagicMock()
        self.mock_db_service.get_prompt.return_value = [{"prompt": "테스트 프롬프트"}]
        
        self.mock_retriever = MagicMock()
        self.mock_retriever.get_few_shots.return_value = asyncio.Future()
        self.mock_retriever.get_few_shots.return_value.set_result([])
        
        self.mock_qna_manager = MagicMock()
        self.mock_qna_manager.create_question.return_value = "test_qna_id"
        self.mock_qna_manager.record_answer.return_value = None

    @patch('graph.task.params.database_service')
    @patch('graph.task.params.retriever')
    @patch('graph.task.params.qna_manager')
    @patch('graph.task.params.qwen_llm')
    def test_valid_json_response(self, mock_llm, mock_qna, mock_retriever, mock_db):
        """올바른 JSON 응답을 처리하는지 테스트"""
        # Mock 설정
        mock_db.get_prompt.return_value = [{"prompt": "테스트 프롬프트"}]
        mock_retriever.get_few_shots.return_value = asyncio.Future()
        mock_retriever.get_few_shots.return_value.set_result([])
        
        valid_json = {"from_date": "20250301", "to_date": "20250331"}
        mock_llm.invoke.return_value = json.dumps(valid_json)
        
        # 함수 실행 및 검증
        result = asyncio.run(parameters(
            self.trace_id, self.selected_api, self.user_question,
            self.main_com, self.user_info, self.today, self.yogeumjae, self.flags
        ))
        
        # 올바른 SQL 쿼리와 날짜 정보가 반환되는지 확인
        expected_query = f"SELECT * FROM aicfo_get_financial_status('test_intt', 'test_user', '테스트회사', '20250301', '20250331')"
        self.assertEqual(result[0].strip(), expected_query)
        self.assertEqual(result[1], ("20250301", "20250331"))

    @patch('graph.task.params.database_service')
    @patch('graph.task.params.retriever') 
    @patch('graph.task.params.qna_manager')
    @patch('graph.task.params.qwen_llm')
    def test_json_embedded_in_text(self, mock_llm, mock_qna, mock_retriever, mock_db):
        """텍스트 내에 JSON이 포함된 응답을 처리하는지 테스트"""
        # Mock 설정 
        mock_db.get_prompt.return_value = [{"prompt": "테스트 프롬프트"}]
        mock_retriever.get_few_shots.return_value = asyncio.Future()
        mock_retriever.get_few_shots.return_value.set_result([])
        
        # 다양한 형태의 텍스트에 포함된 JSON
        responses = [
            'AI: {"from_date": "20250301", "to_date": "20250331"}(안에는 예시 데이터로 채워.',
            'json 형식은 다음과 같습니다: {"from_date": "20250301", "to_date": "20250331"}',
            '분석 결과:\n{"from_date": "20250301", "to_date": "20250331"}\n이상입니다.'
        ]
        
        for response in responses:
            mock_llm.invoke.return_value = response
            
            # 함수 실행 및 검증
            result = asyncio.run(parameters(
                self.trace_id, self.selected_api, self.user_question,
                self.main_com, self.user_info, self.today, self.yogeumjae, self.flags
            ))
            
            # 올바른 날짜 정보가 추출되었는지 확인
            self.assertEqual(result[1], ("20250301", "20250331"))

    @patch('graph.task.params.database_service')
    @patch('graph.task.params.retriever')
    @patch('graph.task.params.qna_manager') 
    @patch('graph.task.params.qwen_llm')
    def test_different_date_formats(self, mock_llm, mock_qna, mock_retriever, mock_db):
        """다양한 날짜 형식을 처리하는지 테스트"""
        # Mock 설정
        mock_db.get_prompt.return_value = [{"prompt": "테스트 프롬프트"}]
        mock_retriever.get_few_shots.return_value = asyncio.Future()
        mock_retriever.get_few_shots.return_value.set_result([])
        
        # 다양한 날짜 형식
        date_formats = [
            {"from_date": "2025-03-01", "to_date": "2025-03-31"},
            {"from_date": " 20250301 ", "to_date": " 20250331 "}  # 공백 있는 경우
        ]
        
        for date_format in date_formats:
            mock_llm.invoke.return_value = json.dumps(date_format)
            
            # 함수 실행 및 검증
            result = asyncio.run(parameters(
                self.trace_id, self.selected_api, self.user_question,
                self.main_com, self.user_info, self.today, self.yogeumjae, self.flags
            ))
            
            # 날짜가 표준 형식(YYYYMMDD)으로 변환되었는지 확인
            self.assertEqual(result[1], ("20250301", "20250331"))

    @patch('graph.task.params.database_service')
    @patch('graph.task.params.retriever')
    @patch('graph.task.params.qna_manager')
    @patch('graph.task.params.qwen_llm') 
    def test_invalid_responses(self, mock_llm, mock_qna, mock_retriever, mock_db):
        """잘못된 응답 형식에 대해 적절한 오류를 발생시키는지 테스트"""
        # Mock 설정
        mock_db.get_prompt.return_value = [{"prompt": "테스트 프롬프트"}]
        mock_retriever.get_few_shots.return_value = asyncio.Future()
        mock_retriever.get_few_shots.return_value.set_result([])
        
        invalid_responses = [
            "이 질문에 대한 대답은 어렵습니다.",  # JSON 없음
            "{잘못된 json 형식}",  # 잘못된 JSON
            '{"only_from": "20250301"}'  # 필수 키 누락
        ]
        
        for response in invalid_responses:
            mock_llm.invoke.return_value = response
            
            # 예외가 발생하는지 확인
            with self.assertRaises(ValueError):
                asyncio.run(parameters(
                    self.trace_id, self.selected_api, self.user_question,
                    self.main_com, self.user_info, self.today, self.yogeumjae, self.flags
                ))

    def test_convert_date_format(self):
        """convert_date_format 함수가 다양한 입력을 올바르게 처리하는지 테스트"""
        test_cases = [
            # 입력, 기대 출력
            ("20250301", "20250301"),  # 이미 올바른 형식
            ("2025-03-01", "20250301"),  # 하이픈 포함
            (" 20250301 ", "20250301"),  # 공백 있음
            ("invalid", "invalid")  # 변환할 수 없는 형식
        ]
        
        for input_date, expected in test_cases:
            self.assertEqual(convert_date_format(input_date), expected)

    @patch('graph.task.params.database_service')
    @patch('graph.task.params.retriever')
    @patch('graph.task.params.qna_manager')
    @patch('graph.task.params.qwen_llm')
    def test_past_date_for_muryo_user(self, mock_llm, mock_qna, mock_retriever, mock_db):
        """무료 사용자가 과거 데이터를 요청할 때 플래그 설정 테스트"""
        # Mock 설정
        mock_db.get_prompt.return_value = [{"prompt": "테스트 프롬프트"}]
        mock_retriever.get_few_shots.return_value = asyncio.Future()
        mock_retriever.get_few_shots.return_value.set_result([])
        
        # 오늘보다 5일 전 날짜
        today_date = datetime.strptime(self.today, "%Y-%m-%d")
        past_date = (today_date - timedelta(days=5)).strftime("%Y%m%d")
        
        mock_llm.invoke.return_value = json.dumps({
            "from_date": past_date,
            "to_date": "20250331"
        })
        
        # 무료 사용자로 설정
        yogeumjae = "muryo"
        flags = {}
        
        # 함수 실행
        result = asyncio.run(parameters(
            self.trace_id, self.selected_api, self.user_question,
            self.main_com, self.user_info, self.today, yogeumjae, flags
        ))
        
        # past_date 플래그가 설정되었는지 확인
        self.assertTrue(flags["past_date"])
        
        # 날짜가 어제로 조정되었는지 확인
        yesterday = (today_date - timedelta(days=1)).strftime("%Y%m%d")
        self.assertEqual(result[1][0], yesterday)

if __name__ == '__main__':
    unittest.main()