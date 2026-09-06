#!/usr/bin/env python3
# load_model.py - PRODUCTION-GRADE SECURE VERSION
# Comprehensive security with API key protection

import os
import re
import sys
import logging
from typing import Optional
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# ============================================================================
# SECURE LOGGING CONFIGURATION
# ============================================================================

class SecureLogFilter(logging.Filter):
    """Filter to prevent API keys from appearing in logs."""
    
    SENSITIVE_PATTERNS = [
        re.compile(r'(gsk_[a-zA-Z0-9]{32,})', re.IGNORECASE),
        re.compile(r'([a-zA-Z0-9]{40,})', re.IGNORECASE),
    ]
    
    def filter(self, record):
        if isinstance(record.msg, str):
            for pattern in self.SENSITIVE_PATTERNS:
                record.msg = pattern.sub('[REDACTED]', record.msg)
        return True

# Configure logging
logging.basicConfig(
    filename='security.log',
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)

logger = logging.getLogger(__name__)
logger.addFilter(SecureLogFilter())

# ============================================================================
# ENVIRONMENT LOADING
# ============================================================================

load_dotenv()

print("=" * 70)
print("🔒 LOADING GROQ LLM MODEL (PRODUCTION-GRADE SECURE VERSION)")
print("=" * 70 + "\n")

# ============================================================================
# API KEY VALIDATION
# ============================================================================

def validate_api_key(api_key: Optional[str]) -> str:
    """
    Comprehensive API key validation.
    
    Args:
        api_key: The API key to validate
        
    Returns:
        str: The validated API key
        
    Raises:
        ValueError: If API key is invalid
    """
    # Check existence
    if not api_key:
        error_msg = (
            "❌ GROQ_API_KEY is missing from environment.\n"
            "\n"
            "Required actions:\n"
            "1. Create a .env file in the project root\n"
            "2. Add this line: GROQ_API_KEY=your_actual_key_here\n"
            "3. Get your API key from: https://console.groq.com/keys\n"
            "\n"
            "Example .env file:\n"
            "GROQ_API_KEY=gsk_abcdefghijklmnopqrstuvwxyz123456"
        )
        logger.error("GROQ_API_KEY missing from environment")
        raise ValueError(error_msg)
    
    # Strip whitespace
    api_key = api_key.strip()
    
    # Check for empty after stripping
    if not api_key:
        error_msg = "❌ GROQ_API_KEY is empty (contains only whitespace)"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Length validation (Groq keys are typically 40-200 chars)
    if len(api_key) < 20:
        error_msg = (
            f"❌ API key too short: {len(api_key)} characters\n"
            f"   Expected at least 20 characters\n"
            f"   Please verify your API key from: https://console.groq.com/keys"
        )
        logger.error(f"API key too short: {len(api_key)} chars")
        raise ValueError(error_msg)
    
    if len(api_key) > 200:
        error_msg = (
            f"❌ API key too long: {len(api_key)} characters\n"
            f"   Expected maximum 200 characters\n"
            f"   Please verify your API key"
        )
        logger.error(f"API key too long: {len(api_key)} chars")
        raise ValueError(error_msg)
    
    # Format validation (alphanumeric, hyphens, underscores only)
    if not re.match(r'^[a-zA-Z0-9\-_]+$', api_key):
        error_msg = (
            "❌ API key contains invalid characters\n"
            "   Only alphanumeric characters, hyphens, and underscores are allowed\n"
            "   Please check for extra spaces or special characters"
        )
        logger.error("API key contains invalid characters")
        raise ValueError(error_msg)
    
    # Check for common mistakes
    if api_key.lower() in ['your_api_key_here', 'your-api-key', 'api_key', 'groq_api_key']:
        error_msg = (
            "❌ API key appears to be a placeholder\n"
            "   Please replace it with your actual API key from:\n"
            "   https://console.groq.com/keys"
        )
        logger.error("Placeholder API key detected")
        raise ValueError(error_msg)
    
    return api_key

def mask_api_key(api_key: str) -> str:
    """
    Safely mask API key for display.
    
    Args:
        api_key: The API key to mask
        
    Returns:
        str: Masked API key showing only first 4 and last 4 characters
    """
    if len(api_key) <= 8:
        return "*" * len(api_key)
    
    return api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]

# ============================================================================
# MODEL LOADING
# ============================================================================

def load_llm_model(
    api_key: str,
    model_name: str = "llama-3.3-70b-versatile",
    temperature: float = 0.1,
    max_tokens: int = 4096,
    timeout: int = 30
) -> ChatGroq:
    """
    Load Groq LLM model with comprehensive error handling.
    
    Args:
        api_key: Validated API key
        model_name: Model identifier
        temperature: Temperature setting (0.0-1.0)
        max_tokens: Maximum tokens in response
        timeout: Request timeout in seconds
        
    Returns:
        ChatGroq: Initialized LLM model
        
    Raises:
        RuntimeError: If model loading fails
    """
    try:
        # Validate parameters
        if not 0.0 <= temperature <= 1.0:
            raise ValueError(f"Temperature must be between 0.0 and 1.0, got {temperature}")
        
        if max_tokens < 1 or max_tokens > 32000:
            raise ValueError(f"max_tokens must be between 1 and 32000, got {max_tokens}")
        
        if timeout < 1 or timeout > 300:
            raise ValueError(f"timeout must be between 1 and 300 seconds, got {timeout}")
        
        print("⏳ Initializing Groq LLM model...")
        print(f"   Model: {model_name}")
        print(f"   Temperature: {temperature}")
        print(f"   Max tokens: {max_tokens}")
        print(f"   Timeout: {timeout}s\n")
        
        # Initialize model
        llm = ChatGroq(
            api_key=api_key,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout
        )
        
        return llm
        
    except ValueError as e:
        logger.error(f"Parameter validation failed: {str(e)}")
        raise RuntimeError(f"❌ Invalid parameters: {str(e)}")
    
    except Exception as e:
        error_str = str(e).lower()
        
        # API key errors
        if any(keyword in error_str for keyword in ['api key', 'authentication', 'unauthorized', '401']):
            error_msg = (
                "❌ API Authentication Failed\n"
                "\n"
                "Possible causes:\n"
                "1. Invalid API key\n"
                "2. Expired API key\n"
                "3. API key not activated\n"
                "\n"
                "Solutions:\n"
                "1. Verify your API key at: https://console.groq.com/keys\n"
                "2. Generate a new API key if needed\n"
                "3. Update GROQ_API_KEY in your .env file"
            )
            logger.error(f"API authentication failed: {str(e)}")
            raise RuntimeError(error_msg)
        
        # Rate limiting
        elif any(keyword in error_str for keyword in ['rate', 'limit', '429', 'quota']):
            error_msg = (
                "❌ Rate Limit Exceeded\n"
                "\n"
                "You have exceeded the API rate limit.\n"
                "Please wait a moment and try again.\n"
                "\n"
                "If this persists, check your usage at:\n"
                "https://console.groq.com/settings/limits"
            )
            logger.warning(f"Rate limit hit: {str(e)}")
            raise RuntimeError(error_msg)
        
        # Network errors
        elif any(keyword in error_str for keyword in ['timeout', 'connection', 'network']):
            error_msg = (
                "❌ Connection Failed\n"
                "\n"
                "Could not connect to Groq API.\n"
                "\n"
                "Please check:\n"
                "1. Your internet connection\n"
                "2. Firewall settings\n"
                "3. Groq API status: https://status.groq.com"
            )
            logger.error(f"Connection failed: {str(e)}")
            raise RuntimeError(error_msg)
        
        # Generic error
        else:
            error_msg = (
                f"❌ Model Loading Failed\n"
                f"\n"
                f"Error type: {type(e).__name__}\n"
                f"Error details: {str(e)}\n"
                f"\n"
                f"Please check the security.log file for more information."
            )
            logger.error(f"Model loading failed: {type(e).__name__}: {str(e)}", exc_info=True)
            raise RuntimeError(error_msg)

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function."""
    try:
        # Get API key from environment
        api_key_raw = os.getenv("GROQ_API_KEY")
        
        # Validate API key
        print("🔐 Validating API key...")
        api_key = validate_api_key(api_key_raw)
        masked_key = mask_api_key(api_key)
        print(f"   ✅ API key valid: {masked_key}\n")
        
        # Load model
        llm_model = load_llm_model(api_key)
        
        # Success message
        print("=" * 70)
        print("✅ MODEL LOADED SUCCESSFULLY")
        print("=" * 70)
        print("\n📋 Model Configuration:")
        print("   • Provider: Groq")
        print("   • Model: llama-3.3-70b-versatile")
        print("   • Type: Pre-trained (hosted)")
        print("   • Temperature: 0.1")
        print("   • Max tokens: 4096")
        print("   • Timeout: 30 seconds")
        print("\n🔒 Security Features:")
        print("   ✓ API key validated (format & length)")
        print("   ✓ API key masked in all outputs")
        print("   ✓ Secure logging with key redaction")
        print("   ✓ Comprehensive error handling")
        print("   ✓ Timeout protection enabled")
        print("   ✓ Parameter validation enforced")
        print("\n💡 Important Notes:")
        print("   • This is a PRE-TRAINED model from Groq")
        print("   • No training occurs - you connect to hosted model")
        print("   • API key is never logged in plain text")
        print("   • All requests are timeout-protected")
        print("=" * 70 + "\n")
        
        print("✅ You can now use the model in your application\n")
        print("Next steps:")
        print("   1. Run: python test_model.py (to verify system)")
        print("   2. Run: python main.py (to start chat interface)\n")
        
        print("Or import in your code:")
        print("   from load_model import llm_model\n")
        
        # Log success (key will be redacted by filter)
        logger.info(f"Model loaded successfully with key: {masked_key}")
        
        return llm_model
        
    except ValueError as e:
        print(f"\n{str(e)}\n")
        logger.error(f"Validation error: {str(e)}")
        sys.exit(1)
        
    except RuntimeError as e:
        print(f"\n{str(e)}\n")
        logger.error(f"Runtime error: {str(e)}")
        sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n⚠️  Process interrupted by user\n")
        logger.warning("Process interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {type(e).__name__}")
        print(f"   {str(e)}\n")
        logger.critical(f"Unexpected error: {type(e).__name__}: {str(e)}", exc_info=True)
        sys.exit(1)

# Initialize model at module import
try:
    llm_model = main()
except SystemExit:
    # Allow clean exit without traceback
    pass

# Export for other modules
__all__ = ['llm_model']

if __name__ == "__main__":
    print("=" * 70)
    print("🔒 SECURITY BEST PRACTICES")
    print("=" * 70)
    print("\n✓ NEVER commit your .env file to version control")
    print("✓ Add .env to your .gitignore file")
    print("✓ Rotate API keys regularly")
    print("✓ Use different keys for development and production")
    print("✓ Monitor API usage at https://console.groq.com")
    print("✓ Keep your API key confidential")
    print("=" * 70 + "\n")