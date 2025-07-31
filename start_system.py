#!/usr/bin/env python3
"""
Start System - Simple One-Command Setup
Complete soccer ELO system setup and operation in one command
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    """One-command system startup"""
    print("⚽ SOCCER ELO SYSTEM - ONE-COMMAND STARTUP")
    print("=" * 50)
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check API key
    api_key = os.environ.get('API_FOOTBALL_KEY')
    if not api_key:
        print("❌ API_FOOTBALL_KEY not found!")
        print()
        print("💡 Set your API key first:")
        print("   export API_FOOTBALL_KEY='your_api_key_here'")
        print()
        print("🔑 Get your API key from: https://api-football.com/")
        return False
    
    print("✅ API key found")
    print(f"🔑 Key: {api_key[:10]}...{api_key[-4:]}")
    print()
    
    # Show what will happen
    print("🚀 This will:")
    print("   1️⃣  Import 250+ top teams using league-based discovery")
    print("   2️⃣  Import comprehensive match history (2010-2025)")
    print("   3️⃣  Calculate enhanced ELO ratings with adaptive K-factors")
    print("   4️⃣  Fetch upcoming fixtures for next 7 days")
    print("   5️⃣  Start daily operations:")
    print("      • Match updates every 3 hours ⚽")
    print("      • Weekly fixture refresh 📅")
    print("      • Daily ELO maintenance 🏆")
    print()
    print("⏱️  Estimated time: 45-90 minutes for initial setup")
    print("📊 API usage: ~6,000 requests (within 7,500 daily limit)")
    print()
    
    # Get user confirmation
    try:
        confirm = input("🚀 Start complete system setup? (y/N): ").strip().lower()
        if confirm != 'y':
            print("🛑 Setup cancelled")
            return False
    except KeyboardInterrupt:
        print("\n🛑 Setup cancelled")
        return False
    
    print("\n" + "="*50)
    print("🚀 STARTING COMPLETE SYSTEM SETUP...")
    print("="*50)
    
    try:
        # Import and run the complete system
        from initialize_and_run import SoccerEloSystemManager
        
        manager = SoccerEloSystemManager()
        success = manager.run_full_cycle(skip_initialization=False)
        
        if success:
            print("\n🎉 SYSTEM SETUP COMPLETE!")
            print("✅ Your soccer ELO system is now running!")
        else:
            print("\n❌ SYSTEM SETUP FAILED")
            print("💡 Check the error messages above")
        
        return success
        
    except KeyboardInterrupt:
        print("\n🛑 Setup interrupted by user")
        return True
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)