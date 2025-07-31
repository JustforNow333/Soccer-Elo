#!/usr/bin/env python3
"""
Initialize Only - Non-Interactive
Runs complete system initialization without daily operations
Perfect for one-time setup or manual initialization
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    """Run initialization only"""
    print("🔧 SOCCER ELO SYSTEM - INITIALIZATION ONLY")
    print("=" * 55)
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check API key
    api_key = os.environ.get('API_FOOTBALL_KEY')
    if not api_key:
        print("❌ API_FOOTBALL_KEY environment variable not found")
        return False
    
    print("✅ API key found")
    print(f"🔑 Key: {api_key[:10]}...{api_key[-4:]}")
    print()
    
    print("🚀 This will run INITIALIZATION ONLY:")
    print("   1️⃣  Import 250+ teams using league-based discovery")
    print("   2️⃣  Import comprehensive match history (2010-2025)")
    print("   3️⃣  Calculate enhanced ELO ratings with adaptive K-factors")
    print("   4️⃣  Fetch upcoming fixtures for next 7 days")
    print("   ⏹️  NO daily operations (run separately if needed)")
    print()
    print("⏱️  Estimated time: 45-90 minutes")
    print("📊 API usage: ~6,000 requests (within 7,500 daily limit)")
    print()
    
    try:
        # Import and run initialization
        from initialize_and_run import SoccerEloSystemManager
        
        manager = SoccerEloSystemManager()
        
        # Validate environment first
        if not manager.validate_environment():
            return False
        
        # Run complete initialization
        success = manager.run_complete_initialization()
        
        if success:
            print("\n🎉 INITIALIZATION COMPLETE!")
            print("=" * 55)
            print("✅ Your soccer ELO system is now initialized!")
            print()
            print("🔄 To start daily operations:")
            print("   python3 initialize_and_run.py --skip-init")
            print("   OR")
            print("   python3 scheduler_manager.py --daemon")
            print()
            print("📊 To check system status:")
            print("   python3 system_status.py")
        else:
            print("\n❌ INITIALIZATION FAILED")
            print("💡 Check the error messages above for details")
        
        return success
        
    except Exception as e:
        print(f"\n❌ Initialization error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)