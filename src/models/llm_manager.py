import logging
import os
import requests
from typing import Optional, List, Dict, Any, Union

from langchain.llms.base import LLM
from langchain.callbacks.manager import CallbackManagerForLLMRun

from src.config.settings import settings
from src.monitoring.metrics import metrics_collector

logger = logging.getLogger(__name__)

class OpenAILLM(LLM):
    """LLM implementation using OpenAI API"""
    model_name: str = None
    api_key: str = None  # Define api_key as a class attribute
    
    def __init__(self):
        super().__init__()
        self.model_name = settings.openai_model_name
        self.api_key = settings.openai_api_key  # Assign to instance attribute
        if not self.api_key:
            logger.warning("OpenAI API key not found in settings. Set OPENAI_API_KEY in .env file.")
        logger.info(f"Initialized OpenAI LLM with model: {self.model_name}")
    
    @property
    def _llm_type(self) -> str:
        return "openai"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> str:
        """Call the OpenAI API to generate a response"""
        start_time = metrics_collector.start_timer("llm_inference_time")
        
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)  # Use client with api_key
            
            messages = [
                {"role": "system", "content": "You are a helpful research assistant."},
                {"role": "user", "content": prompt}
            ]
            
            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=2048,
                temperature=0.2,
                stop=stop or None,
            )
            
            result = response.choices[0].message.content
            
            # Log token usage for monitoring
            if hasattr(response, 'usage') and response.usage:
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
                total_tokens = response.usage.total_tokens
                
                logger.info(f"OpenAI token usage: {prompt_tokens} prompt, {completion_tokens} completion, {total_tokens} total")
                metrics_collector.track_token_usage(prompt_tokens, completion_tokens, total_tokens)
            
            metrics_collector.stop_timer("llm_inference_time", start_time)
            return result
            
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            metrics_collector.stop_timer("llm_inference_time", start_time)
            return f"Error: Could not generate response from OpenAI API. Details: {str(e)}"


class LocalLLM(LLM):
    """LLM implementation using local vLLM server"""
    model_name: str = None
    url: str = None  # Define url as a class attribute
    
    def __init__(self):
        super().__init__()
        self.model_name = settings.local_llm_model
        self.url = settings.local_llm_url
        logger.info(f"Initialized Local LLM with model: {self.model_name} at {self.url}")
    
    @property
    def _llm_type(self) -> str:
        return "local_vllm"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> str:
        """Call the local vLLM server to generate a response"""
        start_time = metrics_collector.start_timer("llm_inference_time")
        
        try:
            # Format prompt for the specific model
            formatted_prompt = self._format_prompt_for_model(prompt)
            
            # Prepare request payload for OpenAI-compatible API
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "user", "content": formatted_prompt}
                ],
                "max_tokens": 2048,
                "temperature": 0.2,
            }
            
            if stop:
                payload["stop"] = stop
            
            # Call vLLM OpenAI-compatible API
            response = requests.post(
                f"{self.url}/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=120  # 120 second timeout for long generations
            )
            
            if response.status_code != 200:
                logger.error(f"Error from vLLM server: {response.status_code}, {response.text}")
                raise Exception(f"vLLM server error: {response.status_code}")
            
            # Parse response
            response_data = response.json()
            
            # Extract generated text from OpenAI format response
            if "choices" in response_data and len(response_data["choices"]) > 0:
                result = response_data["choices"][0]["message"]["content"]
            else:
                logger.error(f"Unexpected response format from vLLM: {response_data}")
                result = "Error: Unexpected response format from LLM server"
            
            metrics_collector.stop_timer("llm_inference_time", start_time)
            return result
            
        except Exception as e:
            logger.error(f"Error calling local LLM: {e}")
            metrics_collector.stop_timer("llm_inference_time", start_time)
            
            # Check if vLLM server is running
            try:
                health_check = requests.get(f"{self.url}/health", timeout=5)
                if health_check.status_code != 200:
                    return "Error: Local LLM server is not responding properly. Please check the server status."
            except:
                return "Error: Cannot connect to the local LLM server. Please ensure the server is running."
                
            return f"Error: Could not generate response from local LLM. Details: {str(e)}"
    
    def _format_prompt_for_model(self, prompt: str) -> str:
        """Format the prompt according to model requirements"""
        # No special formatting needed since we're using the OpenAI chat completions API format
        return prompt


def get_llm() -> LLM:
    """Factory function to get the configured LLM"""
    try:
        if settings.is_using_openai:
            logger.info("Using OpenAI API for LLM")
            return OpenAILLM()
        elif settings.is_using_local_model:
            logger.info("Using local vLLM for LLM")
            return LocalLLM()
        else:
            logger.warning(f"Unknown LLM type: {settings.llm_type}. Defaulting to OpenAI.")
            return OpenAILLM()
    except Exception as e:
        logger.error(f"Error initializing LLM: {e}. Using fallback implementation.")
        return OpenAILLM()  # Default to OpenAI as fallback