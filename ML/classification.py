import json
import requests
from typing import Dict, Any, TypedDict
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import SystemMessage, HumanMessage
from llm_models.models import qwen_llm

class ClassifierResponse(TypedDict):
    answer: str
    raw_data: Dict[str, Any]

class TransactionClassifier:
    def __init__(self, api_url: str = "http://localhost:8005"):
        self.api_url = api_url
        self.output_parser = StrOutputParser()

    async def get_patterns(self) -> Dict[str, Any]:
        """Fetch transaction patterns from the API"""
        try:
            response = requests.get(f"{self.api_url}/classification")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching patterns: {str(e)}")
            raise

    def _create_prompt(self, patterns: Dict[str, Any], user_question: str) -> ChatPromptTemplate:
        """Create the prompt for the LLM"""
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""당신은 금융 데이터 분석 전문가입니다. 주어진 거래 패턴 데이터를 분석하여 사용자의 질문에 정확하게 답변해주세요.

    거래 패턴 데이터는 다음과 같은 구조로 되어 있습니다:
    - 각 계좌번호 아래에 정기적인 거래들이 나열됩니다
    - 각 거래는 다음 정보를 포함합니다:
    * type: "Income"(입금) 또는 "Expense"(지출)
    * interval: 거래 주기와 편차
    * amount: 거래 금액
    * next_expected: 다음 예상 거래일
    * descriptions: 거래 설명과 발생 횟수

    아래는 머신러닝으로 분석된 실제 거래 패턴입니다:
    {patterns}

    위 데이터를 기반으로 답변할 때 다음 사항을 지켜주세요:
    1. Income과 Expense를 모두 포함하여 분석할 것
    2. 금액은 쉼표를 포함한 숫자 형식으로 표시 (예: 1,234,567)
    3. 계좌번호는 그대로 표시
    4. 거래 유형(입금/지출)을 명시
    5. 답변은 간단명료하게, 불필요한 설명 없이"""),
            HumanMessage(content="{question}")
        ])
        
        return prompt

    async def analyze_question(self, user_question: str) -> ClassifierResponse:
        """
        Analyze user question using transaction patterns and LLM
        
        Args:
            user_question (str): The user's question about transaction patterns
            
        Returns:
            ClassifierResponse: Dictionary containing LLM response and raw API data
            
        Raises:
            Exception: If API request fails or LLM processing encounters an error
        """
        try:
            print("\n=== Transaction Classification Analysis Started ===")
            print(f"User Question: {user_question}")
            
            # 1. Fetch patterns from API
            print("\n=== Fetching Patterns from API ===")
            patterns_data = await self.get_patterns()
            print("API Response:")
            print(json.dumps(patterns_data, ensure_ascii=False, indent=2))
            
            # 2. Create and format prompt
            print("\n=== Creating LLM Prompt ===")
            prompt = self._create_prompt(patterns_data, user_question)
            
            # Format the prompt with actual values
            formatted_messages = prompt.format_messages(
                patterns=json.dumps(patterns_data, ensure_ascii=False, indent=2),
                question=user_question
            )
            
            # Print formatted prompt with actual values
            print("\n=== Formatted Prompt ===")
            for msg in formatted_messages:
                print(f"\n{msg.type.upper()}:")
                # Replace template variables with actual values
                content = msg.content
                if "{patterns}" in content:
                    content = content.replace("{patterns}", json.dumps(patterns_data, ensure_ascii=False, indent=2))
                if "{question}" in content:
                    content = content.replace("{question}", user_question)
                print(content)
                
            # 3. Create chain and get LLM response
            print("\n=== Getting LLM Response ===")
            chain = prompt | qwen_llm | self.output_parser
            
            llm_response = chain.invoke({
                "patterns": json.dumps(patterns_data, ensure_ascii=False, indent=2),
                "question": user_question
            })
            
            print("\n=== LLM Response ===")
            print(llm_response)
            
            # 4. Return structured response
            response = {
                "answer": llm_response,
                "raw_data": patterns_data
            }
            
            print("\n=== Analysis Completed ===")
            return response

        except Exception as e:
            print(f"\n=== Error in analyze_question ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            import traceback
            print("Full traceback:")
            traceback.print_exc()
            raise

# Create singleton instance
classifier = TransactionClassifier()