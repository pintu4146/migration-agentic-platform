"""
Quick test script to verify all imports work correctly.
"""

import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))

print("Testing imports...")

try:
    print("[OK] Testing config...")
    from app.config import settings
    print(f"  Environment: {settings.environment}")
    print(f"  Primary Provider: {settings.primary_provider}")
    
    print("\n[OK] Testing logging...")
    from app.logging_config import setup_logging
    setup_logging()
    
    print("\n[OK] Testing provider base...")
    from app.providers.base import LLMProvider, ProviderResponse
    
    print("\n[OK] Testing OpenAI provider...")
    from app.providers.openai_provider import OpenAIProvider
    
    print("\n[OK] Testing Gemini provider...")
    from app.providers.gemini_provider import GeminiProvider
    
    print("\n[OK] Testing provider factory...")
    from app.providers.factory import ProviderFactory
    
    print("\n[OK] Testing tracing...")
    from app.tracing.langsmith import setup_langsmith, trace_operation
    
    print("\n[OK] Testing models...")
    from app.models.schemas import (
        HealthResponse,
        ProviderHealthResponse,
        ProjectCreateRequest
    )
    
    print("\n[OK] Testing FastAPI app...")
    from app.main import app
    
    print("\n" + "="*50)
    print("SUCCESS: All imports successful!")
    print("="*50)
    
except Exception as e:
    print(f"\nERROR: Import failed: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Made with Bob
