#!/bin/bash
set -e

# Get environment variables with defaults
MODEL_NAME="${LOCAL_LLM_MODEL:-mistral-7b-instruct-v0.2-q4_0}"
MODEL_PATH="/models/${MODEL_NAME}"
PORT="${LOCAL_LLM_PORT:-8001}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.9}"
QUANTIZATION="${QUANTIZATION:-awq}"
DEVICE="${DEVICE:-cuda}"  # Options: 'cuda', 'cpu'

echo "Starting vLLM service with model: ${MODEL_NAME}"
echo "Model path: ${MODEL_PATH}"
echo "API Port: ${PORT}"
echo "Device: ${DEVICE}"

# Check if model exists
if [ ! -d "$MODEL_PATH" ] && [ ! -f "$MODEL_PATH" ]; then
    echo "Model not found at ${MODEL_PATH}. Please ensure the model is mounted correctly."
    exit 1
fi

# Check for GPU availability
if [ "$DEVICE" = "cuda" ]; then
    if ! command -v nvidia-smi &> /dev/null || ! nvidia-smi &> /dev/null; then
        echo "Warning: CUDA device requested but no GPU available. Falling back to CPU."
        DEVICE="cpu"
    else
        echo "GPU detected, using CUDA."
    fi
fi

# Start the appropriate server based on device
if [ "$DEVICE" = "cpu" ]; then
    echo "Starting CPU-based server using Llama.cpp backend..."
    
    # Use Llama.cpp for CPU-based inference
    python -c "
import os
import sys
from llama_cpp import Llama
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import uvicorn

app = FastAPI()

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    max_tokens: int = 2048
    temperature: float = 0.2
    stop: Optional[List[str]] = None

class ChatCompletionResponse(BaseModel):
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]
    
# Load the model
model_path = '${MODEL_PATH}'
llm = Llama(model_path=model_path, n_ctx=4096)

@app.post('/v1/chat/completions')
async def chat_completion(request: ChatCompletionRequest):
    try:
        # Combine messages into a prompt
        prompt = ''
        for msg in request.messages:
            if msg.role == 'system':
                prompt += f'System: {msg.content}\\n'
            elif msg.role == 'user':
                prompt += f'User: {msg.content}\\n'
            elif msg.role == 'assistant':
                prompt += f'Assistant: {msg.content}\\n'
            else:
                prompt += f'{msg.role.capitalize()}: {msg.content}\\n'
        
        prompt += 'Assistant: '
        
        # Generate response
        result = llm(
            prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stop=request.stop
        )
        
        return {
            'choices': [{
                'message': {
                    'role': 'assistant',
                    'content': result['choices'][0]['text']
                },
                'finish_reason': result['choices'][0]['finish_reason']
            }],
            'usage': {
                'prompt_tokens': result.get('usage', {}).get('prompt_tokens', 0),
                'completion_tokens': result.get('usage', {}).get('completion_tokens', 0),
                'total_tokens': result.get('usage', {}).get('total_tokens', 0)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@app.get('/health')
async def health_check():
    return {'status': 'ok'}

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=${PORT})
    " &
else
    # Start the vLLM OpenAI-compatible server with GPU
    echo "Starting GPU-based server using vLLM backend..."
    python -m vllm.entrypoints.openai.api_server \
        --model "${MODEL_PATH}" \
        --host 0.0.0.0 \
        --port "${PORT}" \
        --tensor-parallel-size 1 \
        --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION}" \
        --quantization "${QUANTIZATION}" \
        --max-model-len 8192 \
        --trust-remote-code
fi

# Keep the script running
wait 