#!/usr/bin/env python3
"""
Test script to verify the bot setup and dependencies.
Run this before starting the bot to check if everything is configured correctly.
"""

import os
import sys
from dotenv import load_dotenv

def test_environment():
    """Test environment variables."""
    print("🔧 Testing environment variables...")
    
    load_dotenv()
    
    required_vars = ['TELEGRAM_BOT_TOKEN', 'XAI_API_KEY']
    optional_vars = ['OPENAI_API_KEY', 'YT_API_KEY', 'DB_FILENAME']
    
    missing_required = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_required.append(var)
        else:
            print(f"  ✅ {var}: Set")
    
    for var in optional_vars:
        if os.environ.get(var):
            print(f"  ✅ {var}: Set")
        else:
            print(f"  ⚠️  {var}: Not set (optional)")
    
    if missing_required:
        print(f"  ❌ Missing required variables: {', '.join(missing_required)}")
        return False
    
    return True

def test_dependencies():
    """Test required dependencies."""
    print("\n📦 Testing dependencies...")
    
    dependencies = [
        ('telegram', 'python-telegram-bot'),
        ('openai', 'openai'),
        ('xai_sdk', 'xai-sdk'),
        ('requests', 'requests'),
        ('bs4', 'beautifulsoup4'),
        ('linkpreview', 'linkpreview'),
        ('moviepy.editor', 'moviepy'),
        ('dotenv', 'python-dotenv')
    ]
    
    missing_deps = []
    for module, package in dependencies:
        try:
            __import__(module)
            print(f"  ✅ {package}: Available")
        except ImportError:
            print(f"  ❌ {package}: Missing")
            missing_deps.append(package)
    
    if missing_deps:
        print(f"\n  Install missing dependencies with:")
        print(f"  pip install {' '.join(missing_deps)}")
        return False
    
    return True

def test_ai_apis():
    """Test AI API connectivity."""
    print("\n🤖 Testing AI API connectivity...")
    
    # Test OpenAI
    openai_key = os.environ.get('OPENAI_API_KEY')
    if openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            # Just test client creation, not actual API call
            print("  ✅ OpenAI: Client initialized")
        except Exception as e:
            print(f"  ❌ OpenAI: Error - {e}")
    else:
        print("  ⚠️  OpenAI: API key not set")
    
    # Test xAI
    xai_key = os.environ.get('XAI_API_KEY')
    if xai_key:
        try:
            from xai_sdk import Client as XAIClient
            client = XAIClient(api_key=xai_key)
            print("  ✅ xAI: Client initialized")
        except Exception as e:
            print(f"  ❌ xAI: Error - {e}")
    else:
        print("  ❌ xAI: API key not set (required)")
        return False
    
    return True

def test_prompts():
    """Test prompt files."""
    print("\n📝 Testing prompt files...")
    
    prompts_dir = "prompts"
    if not os.path.exists(prompts_dir):
        print(f"  ❌ Prompts directory '{prompts_dir}' not found")
        return False
    
    expected_prompts = ['dan.txt', 'friendly.txt', 'professional.txt', 'creative.txt', 'sarcastic.txt', 'concise.txt']
    missing_prompts = []
    
    for prompt_file in expected_prompts:
        prompt_path = os.path.join(prompts_dir, prompt_file)
        if os.path.exists(prompt_path):
            print(f"  ✅ {prompt_file}: Found")
        else:
            print(f"  ❌ {prompt_file}: Missing")
            missing_prompts.append(prompt_file)
    
    if missing_prompts:
        print(f"  Missing prompt files: {', '.join(missing_prompts)}")
        return False
    
    return True

def main():
    """Run all tests."""
    print("🚀 Telegram AI Companion - Setup Test\n")
    
    tests = [
        ("Environment Variables", test_environment),
        ("Dependencies", test_dependencies),
        ("AI APIs", test_ai_apis),
        ("Prompt Files", test_prompts)
    ]
    
    all_passed = True
    for test_name, test_func in tests:
        try:
            if not test_func():
                all_passed = False
        except Exception as e:
            print(f"  ❌ {test_name}: Error - {e}")
            all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("🎉 All tests passed! The bot should work correctly.")
        print("Run 'python bot.py' to start the bot.")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
