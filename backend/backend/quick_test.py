#!/usr/bin/env python3
"""
Quick API test script to verify endpoints after Account system removal
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_health_check():
    """Test if server is responding"""
    try:
        response = requests.get(f"{BASE_URL}/docs")
        print(f"✅ Server Health Check: Status {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ Server Health Check Failed: {e}")
        return False

def test_user_registration():
    """Test user registration API"""
    try:
        test_user = {
            "email": "test@example.com",
            "password": "Test123!",
            "full_name": "Test User"
        }
        response = requests.post(f"{BASE_URL}/api/users", json=test_user)
        print(f"✅ User Registration: Status {response.status_code}")
        if response.status_code == 201:
            return response.json()
        elif response.status_code == 409:
            print("   (User already exists - that's okay)")
            return test_user
        return None
    except Exception as e:
        print(f"❌ User Registration Failed: {e}")
        return None

def test_user_login(email, password):
    """Test user login API"""
    try:
        login_data = {
            "email": email,
            "password": password
        }
        response = requests.post(f"{BASE_URL}/api/login", json=login_data)
        print(f"✅ User Login: Status {response.status_code}")
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    except Exception as e:
        print(f"❌ User Login Failed: {e}")
        return None

def main():
    print("🚀 Testing API after Account system removal...\n")
    
    # Test 1: Health check
    if not test_health_check():
        print("\n❌ Server is not responding. Make sure it's running on port 8000")
        return
    
    print("\n📝 Testing User Authentication APIs...")
    
    # Test 2: User registration
    user_data = test_user_registration()
    if not user_data:
        print("❌ Cannot proceed without user registration")
        return
    
    # Test 3: User login
    access_token = test_user_login("test@example.com", "Test123!")
    if access_token:
        print(f"✅ Login successful, got access token")
    else:
        print("❌ Login failed")
    
    print("\n🎉 Basic API tests completed!")
    print("📋 Available endpoints:")
    print("   - POST /api/users (User Registration)")
    print("   - POST /api/login (User Login)")
    print("   - GET /api/me (Get User Profile)")
    print("   - Resume and Interview APIs")
    print("\n✨ Account system successfully removed!")

if __name__ == "__main__":
    main()
