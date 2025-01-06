from typing import Dict, Any, TypedDict
import requests
import pandas as pd

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from llm_models.models import qwen_llm


class RegressionResponse(TypedDict):
    answer: str
    data: list[Dict[str, Any]]
    raw_data: Dict[str, Any]


class TransactionRegressor:
    def __init__(self, api_url: str = "http://localhost:8005"):
        self.api_url = api_url
        self.output_parser = StrOutputParser()

    async def get_predictions(self) -> Dict[str, Any]:
        """Fetch regression predictions from the API"""
        try:
            response = requests.get(f"{self.api_url}/regression")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching predictions: {str(e)}")
            raise

    def _create_dataframes(self, api_response: Dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Convert API response into two separate DataFrames"""
        try:
            # Create DataFrame for monthly predictions
            predictions_df = pd.DataFrame(api_response["data"])
            
            # Create DataFrame for raw transaction data
            raw_data = api_response["raw_data"]
            raw_df = {
                category: pd.DataFrame(data, columns=['date', 'amount'])
                for category, data in raw_data.items()
            }
            
            return predictions_df, raw_df
            
        except Exception as e:
            print(f"Error creating DataFrames: {str(e)}")
            raise

    def _create_prompt(self, predictions_df: pd.DataFrame, user_question: str) -> ChatPromptTemplate:
        """Create the prompt for the LLM"""
        prompt = ChatPromptTemplate.from_messages([
            ("human", """당신은 금융 데이터 분석 전문가입니다. 아래 표의 데이터를 정확하게 분석하여 사용자의 질문에 직접적으로 답변하세요.

    예측 데이터 정보:
    - month: 예측 월
    - income: 해당 월의 예상 수입
    - expense: 해당 월의 예상 지출
    - net: 해당 월의 순수입 (수입 - 지출)

    아래는 월간 거래 예측 데이터입니다:
    {predictions}
                          
    위 데이터를 기반으로 다음 질문에 답변해주세요: {question}

    답변 시 다음 사항을 반드시 지켜주세요:
    1. 질문에 대해 계산된 결과값을 직접적으로 제시하세요
    2. 금액은 쉼표를 포함한 숫자 형식으로 표시하세요 (예: 1,234,567)
    3. '~을 도와드리겠습니다'와 같은 대화형 문구는 사용하지 마세요
    4. 분석이 필요한 경우, 계산 과정을 간단히 포함하세요""")
        ])

        return prompt

    async def analyze_question(self, user_question: str) -> RegressionResponse:
        """
        Analyze user question using regression predictions and LLM
        
        Args:
            user_question (str): The user's question about financial predictions
            
        Returns:
            RegressionResponse: Dictionary containing LLM response and prediction datasets
            
        Raises:
            Exception: If API request fails or LLM processing encounters an error
        """
        try:
            print("\n=== Regression Analysis Started ===")
            print(f"User Question: {user_question}")
            
            # 1. Fetch predictions from API
            print("\n=== Fetching Predictions from API ===")
            api_response = await self.get_predictions()
            
            # 2. Create DataFrames
            predictions_df, raw_df = self._create_dataframes(api_response)
            
            # Print DataFrame information
            print("\n=== Predictions DataFrame Info ===")
            print("Shape:", predictions_df.shape)
            print("\nColumns:", list(predictions_df.columns))
            print("\nFirst few rows:")
            print(predictions_df.head().to_string())
            
            # 3. Create and format prompt
            print("\n=== Creating LLM Prompt ===")
            raw_prompt = self._create_prompt(predictions_df, user_question)
            
            # Format the prompt with actual values
            formatted_messages = raw_prompt.format_messages(
                predictions=predictions_df.to_string(index=False),
                question=user_question
            )
            
            prompt_content = formatted_messages[0].content
            print(prompt_content)

            # 4. Create chain and get LLM response
            print("\n=== Getting LLM Response ===")
            llm_response = qwen_llm._call(prompt_content)
            
            
            print("\n=== LLM Response ===")
            print(llm_response)
            
            # 5. Return structured response
            response = {
                "answer": llm_response,
                "data": api_response["data"],
                "raw_data": api_response["raw_data"]
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
regressor = TransactionRegressor()