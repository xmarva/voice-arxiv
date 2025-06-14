import logging
from typing import Optional
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
from langchain.llms.base import LLM
from langchain.callbacks.manager import CallbackManagerForLLMRun
from config.settings import settings

logger = logging.getLogger(__name__)

class HuggingFaceLLM(LLM):
    model_name: str
    pipeline: Optional[object] = None
    tokenizer: Optional[object] = None
    model: Optional[object] = None
    
    def __init__(self, model_name: str = None):
        super().__init__()
        self.model_name = model_name or settings.llm_model_name
        self._load_model()
    
    def _load_model(self):
        logger.info(f"Loading model: {self.model_name}")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(self.model_name)
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                max_length=512,
                temperature=0.7,
                do_sample=True
            )
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    @property
    def _llm_type(self) -> str:
        return "huggingface_custom"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[list] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> str:
        if not self.pipeline:
            raise ValueError("Model not loaded")
        
        try:
            result = self.pipeline(prompt, max_new_tokens=150, pad_token_id=self.tokenizer.eos_token_id)
            generated_text = result[0]['generated_text']
            
            if generated_text.startswith(prompt):
                generated_text = generated_text[len(prompt):].strip()
                
            if stop:
                for stop_word in stop:
                    if stop_word in generated_text:
                        generated_text = generated_text.split(stop_word)[0]
            
            return generated_text
        except Exception as e:
            logger.error(f"Error during text generation: {e}")
            return "Sorry, I encountered an error generating a response."

def get_llm() -> HuggingFaceLLM:
    return HuggingFaceLLM()