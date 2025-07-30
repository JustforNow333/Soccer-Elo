#!/usr/bin/env python3
"""
Script to run comprehensive team diagnostics on Render
This script runs the diagnostics and then applies the mappings automatically
"""

import os
import subprocess
import sys

def main():
    print("🚀 Running Team Diagnostics on Render")
    print("=" * 50)
    
    # Check if API key is available
    api_key = os.environ.get('API_FOOTBALL_KEY')
    if not api_key:
        print("❌ API_FOOTBALL_KEY not found")
        print("Make sure this script is running on Render with the API key configured")
        return False
    
    print("✅ API key found")
    print(f"🔍 Starting comprehensive diagnostics...")
    
    try:
        # Run the comprehensive diagnostics
        result = subprocess.run([
            sys.executable, 'comprehensive_team_diagnostics.py'
        ], capture_output=True, text=True, timeout=1800)  # 30 minute timeout
        
        if result.returncode == 0:
            print("✅ Diagnostics completed successfully!")
            print("Output:", result.stdout)
            
            # Apply the generated mappings
            print("\n🔧 Applying auto-generated mappings...")
            apply_result = subprocess.run([
                sys.executable, 'apply_team_mappings.py'
            ], capture_output=True, text=True)
            
            if apply_result.returncode == 0:
                print("✅ Mappings applied successfully!")
                print("Output:", apply_result.stdout)
                
                # Show final status
                print("\n📊 Final Status:")
                print("Files generated:")
                print("  • team_search_diagnostics.csv")
                print("  • auto_generated_team_mappings.json")
                print("  • team_mapping_summary.csv")
                
                return True
            else:
                print("❌ Error applying mappings:")
                print("Error:", apply_result.stderr)
                return False
        else:
            print("❌ Diagnostics failed:")
            print("Error:", result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Diagnostics timed out (took longer than 30 minutes)")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Complete! You can now run your regular import process.")
        print("The team mappings should be significantly improved.")
    else:
        print("\n💡 If diagnostics failed, you can:")
        print("1. Check the Render logs for more details")
        print("2. Run the diagnostics locally with your API key")
        print("3. Use the existing manual mappings as a fallback")
    
    sys.exit(0 if success else 1)