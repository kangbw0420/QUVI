import requests
import traceback
from typing import List, Optional, Any, Dict
from pydantic import Field, BaseModel
from dotenv import load_dotenv

from langchain_core.outputs import LLMResult, Generation
from langchain.llms import BaseLLM

from utils.config import Config

load_dotenv()

class CustomChatLLM(BaseLLM, BaseModel):
    api_url: str = Config.API_URL
    model: str = Field(...)
    temperature: float = Field(0.0)
    max_tokens: int = Field(10000)

    class Config:
        arbitrary_types_allowed = True

    # max_token 설정 안 하면 기본값 125
    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        # print("API Payload:", json.dumps(payload, indent=2))
        try:
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()

            response_data = response.json()
            choices = response_data.get("choices", [])
            if not choices:
                raise ValueError("Empty choices in API response")

            message = choices[0].get("message", {})
            if "content" not in message:
                raise ValueError("No content in message")

            content = message["content"]
            if not isinstance(content, str):
                raise TypeError("Content is not a string")

            return content.strip()

        except requests.RequestException as e:
            raise ValueError(f"HTTP request error: {str(e)}")
        except (ValueError, KeyError, TypeError) as e:
            raise ValueError(f"API response error: {str(e)}")

    def _generate(
            self, prompts: List[str], stop: Optional[List[str]] = None
        ) -> LLMResult:
            
            generations = []
            for i, prompt in enumerate(prompts, 1):
                try:
                    response = self._call(prompt, stop)

                    generations.append([Generation(text=response)])

                except Exception as e:
                    traceback.print_exc()
                    raise ValueError(f"오류 발생: {str(e)}")
            
            return LLMResult(generations=generations)

    @property
    def _llm_type(self) -> str:
        return "custom_llama"

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

# Create model instances, max_token 설정 안 하면 기본값 125
qwen_llm = CustomChatLLM(model="Qwen/Qwen2.5-Coder-14B-Instruct-AWQ", temperature=0.01, max_tokens=1000)
qwen_high = CustomChatLLM(model="Qwen/Qwen2.5-Coder-14B-Instruct-AWQ", temperature=0.7, max_tokens=1000)
qwen_boolean = CustomChatLLM(model="Qwen/Qwen2.5-Coder-14B-Instruct-AWQ", temperature=0.01, max_tokens=1)

solver = CustomChatLLM(model="Qwen/Qwen2.5-Coder-14B-Instruct-AWQ", temperature=0.2, max_tokens=1000)
selector = CustomChatLLM(model="selector", temperature=0.01, max_tokens=300)
nl2sql = CustomChatLLM(model="nl2sql", temperature=0.01, max_tokens=3000)

# yadon = CustomChatLLM(model="yadon", temperature=0.01, max_tokens=1)
# yadoran = CustomChatLLM(model="yadoran", temperature=0.01, max_tokens=1000)