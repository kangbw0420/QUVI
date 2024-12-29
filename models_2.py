from typing import List, Optional

import requests
from langchain.llms import BaseLLM
from langchain_core.outputs import LLMResult, Generation

from utils.config import Config


class CustomChatLLM(BaseLLM):
    api_url: str = Config.API_URL
    model: str = "nl2sql"
    temperature: float = 1.0
    max_tokens: int = 150

    def __init__(self, model: str, temperature: float, max_tokens: int):
        """동적으로 속성 초기화"""
        super().__init__()
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        try:
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()

            # JSON 응답 처리
            response_data = response.json()
            choices = response_data.get("choices", [])
            if not choices:
                raise ValueError("API 응답의 'choices' 필드가 비어있습니다.")

            message = choices[0].get("message", {})
            if 'content' not in message:
                raise ValueError("'message.content'가 응답에 포함되어 있지 않습니다.")

            content = message["content"]
            if not isinstance(content, str):
                raise TypeError("'content'가 문자열이 아니라 다른 데이터 형식입니다.")

            return content.strip()

        except requests.RequestException as e:
            raise ValueError(f"HTTP 요청 오류: {str(e)}")
        except (ValueError, KeyError, TypeError) as e:
            raise ValueError(f"API 응답 오류: {str(e)}")

    def _generate(self, prompts: List[str], stop: Optional[List[str]] = None) -> LLMResult:
        generations = []
        for prompt in prompts:
            try:
                response = self._call(prompt, stop)
                if isinstance(response, list):
                    response = " ".join(response)
                generations.append([Generation(text=response)])
            except Exception as e:
                raise ValueError(f"오류 발생: {str(e)}")
        return LLMResult(generations=generations)

    @property
    def _llm_type(self):
        """LLM 유형 정의"""
        return "custom_llama"



# LLM 인스턴스 생성
planner = CustomChatLLM(model="planner", temperature=0.7, max_tokens=150)
nl2sql = CustomChatLLM(model="nl2sql", temperature=0.7, max_tokens=150)
solver = CustomChatLLM(model="solver", temperature=0.7, max_tokens=150)