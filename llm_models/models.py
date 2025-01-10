import requests
from langchain.llms import BaseLLM
from typing import List, Optional, Any, Dict
from langchain_core.outputs import LLMResult, Generation
from pydantic import Field, BaseModel
from utils.config import Config
from dotenv import load_dotenv


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
            print("API Response Status:", response.status_code)
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
            print("\n=== Starting LLM Generation ===")
            print(f"Number of prompts to process: {len(prompts)}")
            print(f"Model being used: {self.model}")
            print(f"Temperature: {self.temperature}")
            print(f"Max tokens: {self.max_tokens}")
            
            generations = []
            for i, prompt in enumerate(prompts, 1):
                try:
                    print(f"\n--- Processing Prompt {i}/{len(prompts)} ---")
                    print(f"Prompt content: {prompt[:200]}..." if len(prompt) > 200 else f"Prompt content: {prompt}")

                    print("\nCalling LLM API...")
                    response = self._call(prompt, stop)
                    print(f"Response received (first 200 chars): {response[:200]}..." if len(response) > 200 else f"Response received: {response}")
                    
                    generations.append([Generation(text=response)])
                    print(f"Generation {i} added to results")

                except Exception as e:
                    print(f"\n!!! Error during generation: {str(e)}")
                    print("Full error details:")
                    import traceback
                    traceback.print_exc()
                    raise ValueError(f"오류 발생: {str(e)}")
            
            print("\n=== Generation Complete ===")
            print(f"Total generations created: {len(generations)}")
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
llama_70b_llm = CustomChatLLM(model="planner", temperature=0.1, max_tokens=3000)
qwen_llm = CustomChatLLM(model="nl2sql", temperature=0.1, max_tokens=1000)
llama_8b_llm = CustomChatLLM(model="solver", temperature=0.1, max_tokens=500)
