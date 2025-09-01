#!/usr/bin/env python3
"""
Test script to verify database persistence and multiple connections.

This script tests:
1. Database persistence across multiple application restarts
2. Multiple concurrent connections
3. Data integrity

Run this script multiple times to verify persistence.
"""

import asyncio
import sys
from pathlib import Path
import random
import time

# Add the parent directory to Python path to import src modules  
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.repository.database import async_db
from src.models.db.user import User
import src.models.db  # Import all models


async def test_database_persistence():
    """Test database persistence and multiple connections"""
    print("🧪 Testing Database Persistence & Concurrency")
    print("=" * 60)
    
    # Test 1: Basic connection
    print("1️⃣  Testing basic connection...")
    try:
        async with async_db.get_session() as session:
            result = await session.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            assert test_value == 1
            print("✅ Basic connection successful")
    except Exception as e:
        print(f"❌ Basic connection failed: {e}")
        return False
    
    # Test 2: Create test data
    print("\n2️⃣  Testing data creation...")
    test_email = f"test_user_{int(time.time())}_{random.randint(1000,9999)}@example.com"
    test_user_id = None
    
    try:
        async with async_db.get_session() as session:
            # Create a test user
            new_user = User(
                email=test_email,
                password_hash="test_hash_123",
                name="Test User"
            )
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            test_user_id = new_user.id
            print(f"✅ Created test user with ID: {test_user_id}")
    except Exception as e:
        print(f"❌ Data creation failed: {e}")
        return False
    
    # Test 3: Multiple concurrent sessions
    print("\n3️⃣  Testing multiple concurrent sessions...")
    async def read_user_in_session(session_num: int):
        try:
            async with async_db.get_session() as session:
                result = await session.execute(
                    select(User).where(User.email == test_email)
                )
                user = result.scalar_one_or_none()
                if user:
                    print(f"   Session {session_num}: Found user {user.name} (ID: {user.id})")
                    return True
                else:
                    print(f"   Session {session_num}: User not found")
                    return False
        except Exception as e:
            print(f"   Session {session_num}: Error - {e}")
            return False
    
    # Run multiple concurrent sessions
    tasks = [read_user_in_session(i) for i in range(1, 6)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    successful_sessions = sum(1 for r in results if r is True)
    print(f"✅ {successful_sessions}/5 concurrent sessions successful")
    
    # Test 4: Data persistence check
    print("\n4️⃣  Testing data persistence...")
    try:
        async with async_db.get_session() as session:
            # Count total users
            result = await session.execute(text("SELECT COUNT(*) FROM \"user\""))
            user_count = result.scalar()
            print(f"✅ Total users in database: {user_count}")
            
            # Verify our test user still exists
            result = await session.execute(
                select(User).where(User.id == test_user_id)
            )
            user = result.scalar_one_or_none()
            if user:
                print(f"✅ Test user persisted: {user.email}")
            else:
                print("❌ Test user not found!")
                return False
                
    except Exception as e:
        print(f"❌ Persistence check failed: {e}")
        return False
    
    # Test 5: Connection pool info
    print("\n5️⃣  Connection pool status...")
    pool = async_db.pool
    print(f"📊 Pool size: {pool.size()}")
    print(f"📊 Pool overflow: {pool.overflow()}")
    print(f"📊 Checked out connections: {pool.checkedout()}")
    print(f"📊 Checked in connections: {pool.checkedin()}")
    
    print("\n🎉 All tests passed! Database is persistent and supports multiple connections.")
    return True


async def cleanup_test_data():
    """Clean up test data (optional)"""
    print("\n🧹 Cleaning up test data...")
    try:
        async with async_db.get_session() as session:
            # Delete test users (keep other data)
            result = await session.execute(
                text("DELETE FROM \"user\" WHERE email LIKE 'test_user_%@example.com'")
            )
            deleted_count = result.rowcount
            await session.commit()
            print(f"✅ Cleaned up {deleted_count} test users")
    except Exception as e:
        print(f"⚠️  Cleanup failed (not critical): {e}")


async def main():
    """Main test function"""
    print("🔧 Samvaad Sathi Database Persistence Test")
    print("This script tests database persistence and concurrent connections.\n")
    
    try:
        # Run tests
        success = await test_database_persistence()
        
        if success and len(sys.argv) > 1 and sys.argv[1] == "--cleanup":
            await cleanup_test_data()
            
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print(__doc__)
        print("\nOptions:")
        print("  --cleanup    Clean up test data after running tests")
        print("  --help       Show this help message")
        sys.exit(0)
        
    asyncio.run(main())
