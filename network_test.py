#!/usr/bin/env python3
"""
Network connectivity test script for the Telegram AI Companion bot.
Run this script to diagnose network connectivity issues.
"""

import socket
import time
import requests
from dotenv import load_dotenv
import os

load_dotenv()

def test_dns_resolution():
    """Test DNS resolution."""
    print("🔍 Testing DNS resolution...")
    try:
        socket.gethostbyname("google.com")
        print("✅ DNS resolution: OK")
        return True
    except socket.gaierror as e:
        print(f"❌ DNS resolution failed: {e}")
        return False

def test_internet_connectivity():
    """Test basic internet connectivity."""
    print("🌐 Testing internet connectivity...")
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        print("✅ Internet connectivity: OK")
        return True
    except OSError as e:
        print(f"❌ Internet connectivity failed: {e}")
        return False

def test_telegram_api():
    """Test Telegram API connectivity."""
    print("📱 Testing Telegram API connectivity...")
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in environment")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print("✅ Telegram API: OK")
            bot_info = response.json()
            print(f"   Bot name: {bot_info['result']['first_name']}")
            print(f"   Bot username: @{bot_info['result']['username']}")
            return True
        else:
            print(f"❌ Telegram API returned status {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"❌ Telegram API connection failed: {e}")
        return False

def test_xai_api():
    """Test xAI API connectivity."""
    print("🤖 Testing xAI API connectivity...")
    xai_key = os.environ.get("XAI_API_KEY")
    if not xai_key:
        print("⚠️  XAI_API_KEY not found in environment")
        return False
    
    try:
        # Simple connectivity test (we can't easily test the actual API without making a request)
        socket.gethostbyname("api.x.ai")
        print("✅ xAI API domain resolution: OK")
        return True
    except socket.gaierror as e:
        print(f"❌ xAI API domain resolution failed: {e}")
        return False

def main():
    """Run all network tests."""
    print("🚀 Telegram AI Companion - Network Connectivity Test")
    print("=" * 50)
    
    tests = [
        test_dns_resolution,
        test_internet_connectivity,
        test_telegram_api,
        test_xai_api
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
        print()
        time.sleep(1)
    
    print("📊 Test Summary:")
    print("=" * 50)
    if all(results):
        print("✅ All tests passed! Your network connectivity looks good.")
        print("   If you're still having issues, they might be temporary.")
        print("   Try running the bot again.")
    else:
        print("❌ Some tests failed. Network connectivity issues detected.")
        print("   Please check your internet connection and try again.")
        print("   If problems persist, contact your network administrator.")
    
    print("\n💡 Tips:")
    print("   - Make sure you have a stable internet connection")
    print("   - Check if your firewall allows outbound connections")
    print("   - Verify your API keys are correct in the .env file")
    print("   - Try running the bot again after fixing network issues")

if __name__ == "__main__":
    main()
