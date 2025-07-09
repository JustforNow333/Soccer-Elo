#!/bin/bash

# API-Football Import Runner
# Example usage of the new API-Football import system

echo "🚀 API-Football Import System"
echo "============================="

# Check if API key is set
if [ -z "$API_FOOTBALL_KEY" ]; then
    echo "❌ Error: API_FOOTBALL_KEY environment variable is not set!"
    echo "Please set your API-Football API key:"
    echo "export API_FOOTBALL_KEY='your_api_key_here'"
    exit 1
fi

echo "✅ API key found"

# Run database migration first
echo "🔄 Running database migration..."
python3 migrate_db.py

if [ $? -ne 0 ]; then
    echo "❌ Database migration failed!"
    exit 1
fi

echo ""
echo "🔄 Starting API-Football import..."
echo "Choose an option:"
echo "1. Full import (100 leagues, production)"
echo "2. Test import (5 leagues, 3 teams each)"
echo "3. Dry run (show what would be imported)"
echo "4. Custom import"

read -p "Enter choice (1-4): " choice

case $choice in
    1)
        echo "🚀 Running full production import..."
        python3 api_import.py --max-leagues 100 --delay 0.5
        ;;
    2)
        echo "🧪 Running test import..."
        python3 api_import.py --max-leagues 5 --max-teams 3 --delay 0.2
        ;;
    3)
        echo "🔍 Running dry run..."
        python3 api_import.py --max-leagues 20 --dry-run
        ;;
    4)
        read -p "Max leagues: " max_leagues
        read -p "Max teams per league (or press enter for all): " max_teams
        read -p "Request delay in seconds (default 0.5): " delay
        
        # Set defaults
        max_leagues=${max_leagues:-10}
        delay=${delay:-0.5}
        
        cmd="python3 api_import.py --max-leagues $max_leagues --delay $delay"
        
        if [ ! -z "$max_teams" ]; then
            cmd="$cmd --max-teams $max_teams"
        fi
        
        echo "🚀 Running: $cmd"
        eval $cmd
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "🎉 Import completed!"
echo "📊 Check your database for imported teams and fixtures." 