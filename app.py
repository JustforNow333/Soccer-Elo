from flask import Flask, request, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from db import db, Team, Match, EloRating, User, Fixture
from datetime import datetime, timedelta
from flask_cors import CORS
import os
import requests
from sqlalchemy import or_, and_
from elo_utils import expected_result, update_elo, get_match_result
from fixture_import import fetch_next_48_hours_fixtures

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": [
    "http://localhost:3000", 
     r"https://.*\.vercel\.app"
]}})

# Environment variable validation with proper error handling
def validate_environment():
    """Validate required environment variables"""
    required_vars = {
        "DATABASE_URL": "Database connection string",
        "API_FOOTBALL_KEY": "API-Football API key", 
        "STRIPE_SECRET_KEY": "Stripe secret key",
        "STRIPE_WEBHOOK_SECRET": "Stripe webhook secret"
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        if not os.environ.get(var):
            missing_vars.append(f"{var} ({description})")
    
    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        print(f"❌ CONFIGURATION ERROR: {error_msg}")
        # In production, you might want to exit or disable certain features
        # For now, we'll continue but log the error
        return False
    
    print("✅ All required environment variables are configured")
    return True

# Validate environment on startup
validate_environment()

# Safe database URL configuration
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    print("❌ CRITICAL: DATABASE_URL not configured - using SQLite fallback")
    database_url = "sqlite:///fallback.db"

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = False

# Initialize Stripe once at startup
print("Initializing Stripe...")
try:
    import stripe
    stripe_module = stripe
    print("✅ Stripe module imported successfully")
    
    def get_stripe():
        try:
            key = os.environ.get("STRIPE_SECRET_KEY")
            if not key:
                print("❌ STRIPE_SECRET_KEY is missing!")
                return None
            
            # Validate the key format
            if not key.startswith(('sk_test_', 'sk_live_')):
                print(f"❌ Invalid STRIPE_SECRET_KEY format")
                return None
                
            stripe_module.api_key = key
            print(f"✅ Stripe configured successfully")
            return stripe_module
        except Exception as e:
            print(f"❌ Error configuring Stripe: {e}")
            return None
            
except ImportError as e:
    print(f"❌ Failed to import stripe: {e}")
    stripe_module = None
    
    def get_stripe():
        print("❌ Stripe module not available")
        return None

db.init_app(app)

# API Debug on startup
def debug_api_on_startup():
    """Debug API connection on app startup"""
    print("\n" + "="*60)
    print("🔍 API DEBUG CHECK ON STARTUP")
    print("="*60)
    
    api_key = os.environ.get("API_FOOTBALL_KEY")
    print(f"API Key present: {'Yes' if api_key else 'No'}")
    if api_key:
        print(f"API Key length: {len(api_key)}")
        print(f"API Key prefix: {api_key[:8]}...")
    else:
        print("❌ API_FOOTBALL_KEY environment variable not found!")
        return
    
    # Test API status
    url = "https://v3.football.api-sports.io/status"
    headers = {
        "x-apisports-key": api_key,
        "x-apisports-host": "v3.football.api-sports.io"
    }
    
    try:
        print("🔄 Testing API connection...")
        import requests
        response = requests.get(url, headers=headers, timeout=15)
        
        print(f"HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API Status Response:")
            print(f"   Account: {data.get('response', {}).get('account', {})}")
            print(f"   Requests: {data.get('response', {}).get('requests', {})}")
            
            # Test simple team request
            team_url = "https://v3.football.api-sports.io/teams"
            team_params = {"league": "39", "season": "2024"}  # Premier League
            team_response = requests.get(team_url, headers=headers, params=team_params, timeout=15)
            
            if team_response.status_code == 200:
                team_data = team_response.json()
                teams = team_data.get("response", [])
                print(f"✅ Team data test: Found {len(teams)} Premier League teams")
                print("🎉 API is working correctly!")
            else:
                print(f"❌ Team request failed: {team_response.status_code}")
                print(f"   Response: {team_response.text}")
        else:
            print(f"❌ API Status Error:")
            print(f"   Headers: {dict(response.headers)}")
            print(f"   Body: {response.text}")
            
    except Exception as e:
        print(f"❌ API Connection Error: {e}")
    
    print("="*60)

# Run API debug check on startup
debug_api_on_startup()

@app.before_request
def log_request_info():
    if request.path.startswith('/api/') and request.method == 'POST':
        print(f"API Request: {request.method} {request.path}")

@app.after_request
def log_response_info(response):
    if request.path.startswith('/api/') and request.method == 'POST':
        print(f"API Response: {response.status_code}")
    return response

@app.route("/debug/teams/")
def debug_teams():
    try:
        teams = Team.query.all()
        return jsonify({
            "count": len(teams),
            "teams": [team.name for team in teams]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/debug/team-names/")
def debug_team_names():
    """Show actual team names in database for debugging fixture matching"""
    try:
        teams = Team.query.limit(20).all()  # Limit to first 20 teams
        return jsonify({
            "count": len(teams),
            "sample_teams": [
                {
                    "id": team.id,
                    "name": team.name,
                    "league": team.league
                } for team in teams
            ],
            "message": "Sample team names from database (normalized format)"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/debug/fixtures/")
def debug_fixtures():
    """Check fixture status and team matching"""
    try:
        from sqlalchemy import func
        
        # Get fixture counts
        total_fixtures = Fixture.query.count()
        fixtures_with_both_teams = Fixture.query.filter(
            Fixture.home_team_id.isnot(None),
            Fixture.away_team_id.isnot(None)
        ).count()
        fixtures_with_no_teams = Fixture.query.filter(
            Fixture.home_team_id.is_(None),
            Fixture.away_team_id.is_(None)
        ).count()
        fixtures_with_one_team = total_fixtures - fixtures_with_both_teams - fixtures_with_no_teams
        
        # Get sample unmatched fixtures
        unmatched_fixtures = Fixture.query.filter(
            Fixture.home_team_id.is_(None),
            Fixture.away_team_id.is_(None)
        ).limit(5).all()
        
        return jsonify({
            "total_fixtures": total_fixtures,
            "fixtures_with_both_teams": fixtures_with_both_teams,
            "fixtures_with_one_team": fixtures_with_one_team,
            "fixtures_with_no_teams": fixtures_with_no_teams,
            "sample_unmatched_fixtures": [
                {
                    "id": f.id,
                    "date": f.date.isoformat(),
                    "home_team_name": f.home_team_name,
                    "away_team_name": f.away_team_name,
                    "league_name": f.league_name
                } for f in unmatched_fixtures
            ],
            "recommendation": "If you have many fixtures_with_no_teams, you should re-run the fixture import after deploying the fix."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/data-status")
def data_status():
    """Check database status with more details"""
    try:
        total_teams = Team.query.count()
        total_matches = Match.query.count()
        total_elo_ratings = EloRating.query.count()
        total_fixtures = Fixture.query.count() if 'Fixture' in globals() else 0
        
        # Sample team data to see what's in there
        sample_teams = Team.query.limit(5).all()
        sample_team_data = [{"id": t.id, "name": t.name, "league": t.league} for t in sample_teams]
        
        return jsonify({
            "total_teams": total_teams,
            "total_matches": total_matches,
            "total_elo_ratings": total_elo_ratings,
            "total_fixtures": total_fixtures,
            "sample_teams": sample_team_data,
            "diagnosis": "You have teams but no matches - this means the match import failed or wasn't run"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/wipe-db/", methods=["POST"])
def wipe_db():
    """Fast database wipe with proper transaction handling"""
    try:
        print("🧹 Starting fast database wipe...", flush=True)

        # CRITICAL FIX: Use single atomic transaction for entire wipe
        with db.session.begin():
            # Delete in reverse dependency order to avoid foreign key violations
            batch_size = 1000
            
            # ELO Ratings (no dependencies)
            total_deleted = 0
            while True:
                batch = EloRating.query.limit(batch_size).all()
                if not batch:
                    break
                for item in batch:
                    db.session.delete(item)
                total_deleted += len(batch)
                print(f"Deleted {len(batch)} ELO ratings (total: {total_deleted})", flush=True)
            
            # Matches (depends on teams)
            total_deleted = 0
            while True:
                batch = Match.query.limit(batch_size).all()
                if not batch:
                    break
                for item in batch:
                    db.session.delete(item)
                total_deleted += len(batch)
                print(f"Deleted {len(batch)} matches (total: {total_deleted})", flush=True)
            
            # Fixtures (depends on teams)
            fixture_count = Fixture.query.count()
            Fixture.query.delete()
            print(f"Deleted {fixture_count} fixtures", flush=True)
            
            # Teams (referenced by matches, fixtures, elo_ratings)
            total_deleted = 0
            while True:
                batch = Team.query.limit(batch_size).all()
                if not batch:
                    break
                for item in batch:
                    db.session.delete(item)
                total_deleted += len(batch)
                print(f"Deleted {len(batch)} teams (total: {total_deleted})", flush=True)
            
            # Users (no dependencies on our main data)
            user_count = User.query.count()
            User.query.delete()
            print(f"Deleted {user_count} users", flush=True)
            
            # Reset auto-increment sequences within the same transaction
            print("🔄 Resetting ID sequences...", flush=True)
            db.session.execute(db.text("ALTER SEQUENCE teams_id_seq RESTART WITH 1;"))
            db.session.execute(db.text("ALTER SEQUENCE matches_id_seq RESTART WITH 1;"))
            db.session.execute(db.text("ALTER SEQUENCE elo_ratings_id_seq RESTART WITH 1;"))
            db.session.execute(db.text("ALTER SEQUENCE fixtures_id_seq RESTART WITH 1;"))
            db.session.execute(db.text("ALTER SEQUENCE users_id_seq RESTART WITH 1;"))
            print("✅ All ID sequences reset to start at 1", flush=True)
            
            # Transaction commits automatically when exiting 'with' block
            
        print("✅ Complete database wipe finished!", flush=True)
        return jsonify({
            "status": "Complete database wipe finished",
            "message": "All data deleted and IDs reset to start at 1"
        }), 200
        
    except Exception as e:
        print(f"❌ Database wipe failed: {str(e)}", flush=True)
        db.session.rollback()
        return jsonify({"error": f"Database wipe failed: {str(e)}"}), 500

@app.route("/clear-fixtures/", methods=["POST"])
def clear_fixtures():
    """Clear only the fixtures table (preserves teams and matches with Elo ratings)"""
    try:
        deleted_count = Fixture.query.count()
        Fixture.query.delete()
        db.session.commit()
        return jsonify({
            "status": "Fixtures cleared successfully",
            "deleted_count": deleted_count
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route("/create-tables/")
def create_tables():
    db.create_all()
    return "Tables created!"

@app.route("/api/teams/", methods=["GET"])
def get_teams():
    # Get latest Elo rating per team in one batch
    from sqlalchemy.sql import func

    subquery = db.session.query(
        EloRating.team_id,
        func.max(EloRating.date).label("latest_date")
    ).group_by(EloRating.team_id).subquery()

    elo_map = {
        row.team_id: row.rating
        for row in db.session.query(EloRating).join(
            subquery,
            (EloRating.team_id == subquery.c.team_id) &
            (EloRating.date == subquery.c.latest_date)
        )
    }

    teams = Team.query.all()
    return jsonify({
        "teams": [
            {
                "id": team.id,
                "name": team.name,
                "league": team.league,
                "elo": round(elo_map.get(team.id, 1000), 1)
            }
            for team in teams
        ]
    })


@app.route("/api/teams/", methods=["POST"])
def create_team():
    body = request.get_json()
    if not body.get("name") or not body.get("league"):
        return jsonify({"error": "Missing name or league"}), 400
    team = Team(name=body["name"], league=body["league"])
    db.session.add(team)
    db.session.commit()
    return jsonify(team.serialize()), 201

@app.route("/api/matches/", methods=["POST"])
def create_match():
    body = request.get_json()
    
    # Input validation
    if not body:
        return jsonify({"error": "Request body is required"}), 400
    
    # Validate required fields
    required_fields = ["date", "home_team_id", "away_team_id", "home_score", "away_score"]
    for field in required_fields:
        if field not in body:
            return jsonify({"error": f"Field '{field}' is required"}), 400
    
    try:
        # Validate and parse date
        try:
            date = datetime.strptime(body["date"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
        
        # Validate team IDs
        home_team_id = body["home_team_id"]
        away_team_id = body["away_team_id"]
        
        if not isinstance(home_team_id, int) or not isinstance(away_team_id, int):
            return jsonify({"error": "Team IDs must be integers"}), 400
        
        if home_team_id == away_team_id:
            return jsonify({"error": "Home and away teams must be different"}), 400
        
        # Validate teams exist
        home_team = Team.query.get(home_team_id)
        away_team = Team.query.get(away_team_id)
        
        if not home_team:
            return jsonify({"error": f"Home team with ID {home_team_id} not found"}), 400
        if not away_team:
            return jsonify({"error": f"Away team with ID {away_team_id} not found"}), 400
        
        # Validate scores
        home_score = body.get("home_score", 0)
        away_score = body.get("away_score", 0)
        
        if not isinstance(home_score, int) or not isinstance(away_score, int):
            return jsonify({"error": "Scores must be integers"}), 400
        
        if home_score < 0 or away_score < 0:
            return jsonify({"error": "Scores cannot be negative"}), 400
        
        if home_score > 50 or away_score > 50:
            return jsonify({"error": "Scores above 50 are not realistic"}), 400
        
        # Create match after all validations pass
        match = Match(
            date=date,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_score=home_score,
            away_score=away_score,
        )
        db.session.add(match)
        db.session.flush()
        
        # Fixed: Wrap Elo update in same transaction to prevent race condition
        try:
            update_elo_result = update_elo_after_match(match.id)
            if "error" in update_elo_result or not update_elo_result.get("success"):
                db.session.rollback()
                return jsonify(update_elo_result), 400
            
            db.session.commit()
            return jsonify({"id": match.id}), 201
        except Exception as elo_error:
            db.session.rollback()
            return jsonify({"error": f"Elo calculation failed: {str(elo_error)}"}), 400
            
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route("/api/elo-ratings/", methods=["GET"])
def get_elo_ratings():
    # Option A: Get only latest ratings per team
    from sqlalchemy import func
    latest_ratings = db.session.query(
        EloRating.team_id,
        func.max(EloRating.date).label('latest_date')
    ).group_by(EloRating.team_id).subquery()
    
    ratings = db.session.query(EloRating)\
        .join(latest_ratings, 
              (EloRating.team_id == latest_ratings.c.team_id) & 
              (EloRating.date == latest_ratings.c.latest_date))\
        .all()
    
    return jsonify({
        "elo_ratings": [{
            "team_id": r.team_id,
            "rating": r.rating,
            "date": r.date.isoformat()
        } for r in ratings]
    })

@app.route("/api/user/premium-status", methods=["POST"])
def check_premium_status():
    """Check if a user has premium access"""
    data = request.get_json()
    email = data.get("email")
    
    if not email:
        return jsonify({"error": "Email is required"}), 400
    
    try:
        user = User.query.filter_by(email=email).first()
        if user:
            return jsonify({
                "has_premium": user.is_premium_active(),
                "subscription_status": user.subscription_status,
                "subscription_start_date": user.subscription_start_date.isoformat() if user.subscription_start_date else None
            })
        else:
            return jsonify({
                "has_premium": False,
                "subscription_status": "none",
                "subscription_start_date": None
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def health():
    return jsonify({"status": "ok"})

@app.route("/debug/config")
def debug_config():
    """Debug endpoint to check configuration (remove in production!)"""
    return jsonify({
        "stripe_configured": bool(os.environ.get("STRIPE_SECRET_KEY")),
        "database_url_set": bool(os.environ.get("DATABASE_URL")),
        "stripe_webhook_secret_set": bool(os.environ.get("STRIPE_WEBHOOK_SECRET")),
        "stripe_publishable_key_set": bool(os.environ.get("STRIPE_PUBLISHABLE_KEY")),
        "environment_variables": list(os.environ.keys())
    })
# def show_teams():
#     from sqlalchemy.orm import joinedload

#     teams = Team.query.options(joinedload(Team.elo_ratings)).all()
#     team_elos = []
#     for team in teams:
#         latest = max(team.elo_ratings, key=lambda r: r.date, default=None)
#         team_elos.append({
#             "name": team.name,
#             "league": team.league,
#             "elo": round(latest.rating, 1) if latest else "N/A"
#         })
#     team_elos.sort(key=lambda x: x["elo"] if isinstance(x["elo"], float) else 0, reverse=True)
#     return render_template("team_elos.html", teams=team_elos)




# Set your secret key
@app.route("/debug/env-check")
def debug_env_check():
    """Debug endpoint to check environment variables (SECURED FOR PRODUCTION)"""
    # Only show basic status without exposing sensitive information
    return jsonify({
        "stripe_configured": bool(os.environ.get("STRIPE_SECRET_KEY")),
        "database_configured": bool(os.environ.get("DATABASE_URL")),
        "api_football_configured": bool(os.environ.get("API_FOOTBALL_KEY")),
        "status": "Environment check completed - sensitive details hidden for security"
    })

@app.route("/debug/api-check")
def debug_api_check():
    """Debug endpoint to check API-Football connection"""
    api_key = os.environ.get("API_FOOTBALL_KEY")
    
    result = {
        "api_key_present": bool(api_key),
        "api_key_length": len(api_key) if api_key else 0,
        "api_key_prefix": api_key[:8] + "..." if api_key else "N/A"
    }
    
    if not api_key:
        result["error"] = "API_FOOTBALL_KEY environment variable not found"
        return jsonify(result), 500
    
    # Test API status
    url = "https://v3.football.api-sports.io/status"
    headers = {
        "x-apisports-key": api_key,
        "x-apisports-host": "v3.football.api-sports.io"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        result["status_code"] = response.status_code
        
        if response.status_code == 200:
            data = response.json()
            result["api_status"] = "working"
            result["account_info"] = data.get("response", {}).get("account", {})
            result["requests_info"] = data.get("response", {}).get("requests", {})
            
            # Test team request
            team_url = "https://v3.football.api-sports.io/teams"
            team_params = {"league": "39", "season": "2024"}
            team_response = requests.get(team_url, headers=headers, params=team_params, timeout=15)
            
            if team_response.status_code == 200:
                team_data = team_response.json()
                teams = team_data.get("response", [])
                result["team_test"] = f"Success - Found {len(teams)} Premier League teams"
            else:
                result["team_test"] = f"Failed - {team_response.status_code}: {team_response.text}"
        else:
            result["api_status"] = "error"
            result["error_response"] = response.text
            
    except Exception as e:
        result["api_status"] = "connection_error"
        result["error"] = str(e)
    
    return jsonify(result)

@app.route("/debug/leagues-structure")
def debug_leagues_structure():
    """Debug endpoint to examine actual leagues API response structure"""
    api_key = os.environ.get("API_FOOTBALL_KEY")
    
    if not api_key:
        return jsonify({"error": "API_FOOTBALL_KEY not found"}), 500
    
    # Test leagues endpoint
    url = "https://v3.football.api-sports.io/leagues"
    headers = {
        "x-apisports-key": api_key,
        "x-apisports-host": "v3.football.api-sports.io"
    }
    
    current_season = datetime.now().year
    params = {
        "season": str(current_season)
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            leagues = data.get("response", [])
            
            result = {
                "total_leagues": len(leagues),
                "sample_leagues": leagues[:3] if leagues else [],
                "analysis": {}
            }
            
            if leagues:
                # Analyze structure
                first_league = leagues[0]
                league = first_league.get("league", {})
                country = first_league.get("country", {})
                seasons = first_league.get("seasons", [])
                
                result["structure"] = {
                    "league_keys": list(league.keys()),
                    "country_keys": list(country.keys()),
                    "has_seasons": len(seasons) > 0
                }
                
                if seasons:
                    current_season_data = None
                    for season in seasons:
                        if season.get("year") == current_season:
                            current_season_data = season
                            break
                    
                    if current_season_data:
                        coverage = current_season_data.get("coverage", {})
                        result["current_season_structure"] = {
                            "season_keys": list(current_season_data.keys()),
                            "coverage_keys": list(coverage.keys()),
                            "coverage_values": coverage
                        }
                
                # Count leagues by type and coverage
                league_types = {}
                coverage_odds = 0
                world_leagues = 0
                valid_leagues = 0
                
                for league_data in leagues:
                    league = league_data.get("league", {})
                    country = league_data.get("country", {})
                    seasons = league_data.get("seasons", [])
                    
                    league_type = league.get("type", "unknown")
                    league_types[league_type] = league_types.get(league_type, 0) + 1
                    
                    if country.get("name") == "World":
                        world_leagues += 1
                    
                    # Check if it would pass our new filter
                    league_type = league.get("type", "").lower()
                    if (league_type in ["league", "cup"] and
                        country.get("name") not in ["World", None] and
                        league.get("name") and league.get("id")):
                        valid_leagues += 1
                    
                    # Check coverage
                    for season in seasons:
                        if season.get("year") == current_season:
                            coverage = season.get("coverage", {})
                            if coverage.get("odds", False):
                                coverage_odds += 1
                            break
                
                result["analysis"] = {
                    "league_types": league_types,
                    "leagues_with_odds_coverage": coverage_odds,
                    "world_leagues": world_leagues,
                    "leagues_passing_new_filter": valid_leagues,
                    "leagues_passing_old_filter": 0  # We know this was 0
                }
            
            return jsonify(result)
        else:
            return jsonify({
                "error": f"API Error: {response.status_code}",
                "response": response.text
            }), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/create-checkout-session", methods=["POST"])
def create_checkout_session():
    try:
        print("Creating checkout session...")
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data received"}), 400
            
        email = data.get("email")
        if not email:
            return jsonify({"error": "Email is required"}), 400

        print(f"Creating session for email: {email}")
        
        stripe_client = get_stripe()
        if not stripe_client:
            return jsonify({"error": "Payment system not configured"}), 500
        
        # Get frontend URL from environment variable
        frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
        
        session = stripe_client.checkout.Session.create(
            customer_email=email,
            payment_method_types=["card"],
            line_items=[{
                "price": "price_1RfE3RFQ0X76CRQWSNsdAb5Q",
                "quantity": 1,
            }],
            mode="subscription",
            success_url=f"{frontend_url}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{frontend_url}/cancel",
            metadata={
                "email": email
            }
        )
        
        print(f"✅ Checkout session created: {session.id}")
        return jsonify({"url": session.url})
        
    except Exception as e:
        print(f"❌ Checkout session error: {str(e)}")
        return jsonify({"error": str(e)}), 400

@app.route("/api/stripe-webhook", methods=["POST"])
def stripe_webhook():
    # Get stripe module first
    stripe = get_stripe()
    if not stripe:
        return jsonify({"error": "Payment system not configured"}), 500

    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")
    endpoint_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    
    if not endpoint_secret:
        return jsonify({"error": "Webhook secret not configured"}), 500

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError as e:
        # Invalid payload
        return jsonify({"error": "Invalid payload"}), 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return jsonify({"error": "Invalid signature"}), 400

    # Handle the event
    try:
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            handle_checkout_session_completed(session)
            
        elif event["type"] == "customer.subscription.created":
            subscription = event["data"]["object"]
            handle_subscription_created(subscription)
            
        elif event["type"] == "customer.subscription.updated":
            subscription = event["data"]["object"]
            handle_subscription_updated(subscription)
            
        elif event["type"] == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            handle_subscription_deleted(subscription)
            
        elif event["type"] == "invoice.payment_succeeded":
            invoice = event["data"]["object"]
            handle_payment_succeeded(invoice)
            
        elif event["type"] == "invoice.payment_failed":
            invoice = event["data"]["object"]
            handle_payment_failed(invoice)
            
        else:
            print(f"Unhandled event type: {event['type']}")

    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        return jsonify({"error": "Webhook processing failed"}), 500

    return jsonify({"success": True}), 200

def handle_checkout_session_completed(session):
    """Handle successful checkout session completion"""
    try:
        customer_email = session.get("customer_email")
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")
        
        if customer_email:
            user = User.query.filter_by(email=customer_email).first()
            if user:
                # Update existing user
                user.stripe_customer_id = customer_id
                user.stripe_subscription_id = subscription_id
                user.subscription_status = "active"
                user.subscription_start_date = datetime.utcnow()
                db.session.commit()
                print(f"Updated existing user {customer_email} with subscription {subscription_id}")
            else:
                # Create new user
                new_user = User(
                    email=customer_email,
                    stripe_customer_id=customer_id,
                    stripe_subscription_id=subscription_id,
                    subscription_status="active",
                    subscription_start_date=datetime.utcnow()
                )
                db.session.add(new_user)
                db.session.commit()
                print(f"Created new user {customer_email} with subscription {subscription_id}")
        else:
            print("No customer email in checkout session")
    except Exception as e:
        print(f"Error handling checkout session: {str(e)}")
        raise

def handle_subscription_created(subscription):
    """Handle subscription creation"""
    try:
        customer_id = subscription.get("customer")
        subscription_id = subscription.get("id")
        status = subscription.get("status")
        
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        if user:
            user.stripe_subscription_id = subscription_id
            user.subscription_status = status
            if status == "active":
                user.subscription_start_date = datetime.utcnow()
            db.session.commit()
            print(f"Updated user subscription status to {status}")
    except Exception as e:
        print(f"Error handling subscription created: {str(e)}")
        raise

def handle_subscription_updated(subscription):
    """Handle subscription updates"""
    try:
        subscription_id = subscription.get("id")
        status = subscription.get("status")
        
        user = User.query.filter_by(stripe_subscription_id=subscription_id).first()
        if user:
            user.subscription_status = status
            if status == "canceled":
                user.subscription_end_date = datetime.utcnow()
            db.session.commit()
            print(f"Updated subscription {subscription_id} status to {status}")
    except Exception as e:
        print(f"Error handling subscription updated: {str(e)}")
        raise

def handle_subscription_deleted(subscription):
    """Handle subscription cancellation"""
    try:
        subscription_id = subscription.get("id")
        
        user = User.query.filter_by(stripe_subscription_id=subscription_id).first()
        if user:
            user.subscription_status = "canceled"
            user.subscription_end_date = datetime.utcnow()
            db.session.commit()
            print(f"Canceled subscription for user {user.email}")
    except Exception as e:
        print(f"Error handling subscription deleted: {str(e)}")
        raise

def handle_payment_succeeded(invoice):
    """Handle successful payment"""
    try:
        subscription_id = invoice.get("subscription")
        
        user = User.query.filter_by(stripe_subscription_id=subscription_id).first()
        if user:
            user.subscription_status = "active"
            db.session.commit()
            print(f"Payment succeeded for user {user.email}")
    except Exception as e:
        print(f"Error handling payment succeeded: {str(e)}")
        raise

def handle_payment_failed(invoice):
    """Handle failed payment"""
    try:
        subscription_id = invoice.get("subscription")
        
        user = User.query.filter_by(stripe_subscription_id=subscription_id).first()
        if user:
            user.subscription_status = "past_due"
            db.session.commit()
            print(f"Payment failed for user {user.email}")
    except Exception as e:
        print(f"Error handling payment failed: {str(e)}")
        raise


@app.route("/api/cancel-subscription", methods=["POST"])
def cancel_subscription():
    data = request.get_json()
    email = data.get("email")
    if not email:
        return jsonify({"error": "Email is required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.stripe_subscription_id:
        return jsonify({"error": "Active subscription not found"}), 404

    stripe_client = get_stripe()
    if not stripe_client:
        return jsonify({"error": "Payment system not configured"}), 500

    try:
        # Cancel the Stripe subscription immediately
        stripe_client.Subscription.delete(user.stripe_subscription_id)
        user.subscription_status = "canceled"
        user.subscription_end_date = datetime.utcnow()
        db.session.commit()
        return jsonify({"message": "Subscription canceled successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
def update_elo_after_match(match_id, k=20):
    """Update Elo ratings for teams after a match with race condition protection"""
    try:
        # CRITICAL FIX: Use atomic transaction with row locking
        with db.session.begin():
            match = Match.query.get(match_id)
            if not match:
                return {"error": "Match not found"}

            home_team = Team.query.get(match.home_team_id)
            away_team = Team.query.get(match.away_team_id)

            if home_team is None or away_team is None:
                return {"error": "Home or away team not found"}

            # CRITICAL FIX: Lock rows to prevent race conditions in rating reads
            home_rating = EloRating.query.filter_by(team_id=home_team.id)\
                                        .order_by(EloRating.date.desc())\
                                        .with_for_update().first()
            away_rating = EloRating.query.filter_by(team_id=away_team.id)\
                                        .order_by(EloRating.date.desc())\
                                        .with_for_update().first()

            home_score, away_score = get_match_result(match.home_score, match.away_score)
            home_rating_val = home_rating.rating if home_rating else 1000
            away_rating_val = away_rating.rating if away_rating else 1000

            # Validate ratings before calculation
            if not (0 <= home_rating_val <= 5000) or not (0 <= away_rating_val <= 5000):
                return {"error": f"Invalid rating values: home={home_rating_val}, away={away_rating_val}"}

            # Calculate new ratings
            new_home_rating = update_elo(home_rating_val, away_rating_val, home_score, k)
            new_away_rating = update_elo(away_rating_val, home_rating_val, away_score, k)

            # Validate new ratings
            if not (0 <= new_home_rating <= 5000) or not (0 <= new_away_rating <= 5000):
                return {"error": f"Invalid calculated ratings: home={new_home_rating}, away={new_away_rating}"}

            # Check if ratings already exist for this date to prevent duplicates
            existing_home = EloRating.query.filter_by(team_id=home_team.id, date=match.date).first()
            existing_away = EloRating.query.filter_by(team_id=away_team.id, date=match.date).first()
            
            if existing_home or existing_away:
                return {"error": "Elo ratings already exist for this match date"}

            # Add new Elo ratings within the same transaction
            db.session.add(EloRating(team_id=home_team.id, date=match.date, rating=new_home_rating))
            db.session.add(EloRating(team_id=away_team.id, date=match.date, rating=new_away_rating))
            
            # Transaction commits automatically when exiting 'with' block
            
        return {"message": "Elo ratings updated successfully", "success": True}
        
    except Exception as e:
        db.session.rollback()
        return {"error": f"Elo calculation failed: {str(e)}"}

# NO scheduler runs at startup anymore

@app.route("/api/strategic-betting", methods=["POST"])
def get_strategic_betting_opportunities():
    """Get categorized betting opportunities based on Elo differences (Premium feature)"""
    data = request.get_json()
    email = data.get("email")
    
    if not email:
        return jsonify({"error": "Email is required"}), 400
    
    # Check premium status
    user = User.query.filter_by(email=email).first()
    if not user or not user.is_premium_active():
        return jsonify({"error": "Premium subscription required"}), 403
    
    try:
        from sqlalchemy import func, and_
        from datetime import date, timedelta
        
        # Get upcoming fixtures from API-Football data (more accurate than historical matches)
        today = datetime.now().date()
        upcoming_fixtures = Fixture.query.filter(
            Fixture.date >= today,
            Fixture.status == "NS"  # Not Started
        ).order_by(Fixture.date.asc()).all()
        
        # Filter to only include fixtures with teams in our database (with Elo ratings)
        relevant_fixtures = [f for f in upcoming_fixtures if f.has_elo_teams()]
        
        if not relevant_fixtures:
            return jsonify({
                "opportunities": [],
                "total_count": 0,
                "categories": {
                    "good_chance": 0,
                    "great_chance": 0,
                    "almost_certain": 0
                },
                "message": "No upcoming fixtures found with Elo-rated teams"
            })
        
        # Get latest Elo ratings for all teams involved in upcoming fixtures
        team_ids = set()
        for fixture in relevant_fixtures:
            team_ids.add(fixture.home_team_id)
            team_ids.add(fixture.away_team_id)
        
        # Get latest Elo ratings in batch
        subquery = db.session.query(
            EloRating.team_id,
            func.max(EloRating.date).label("latest_date")
        ).filter(EloRating.team_id.in_(team_ids)).group_by(EloRating.team_id).subquery()
        
        elo_map = {
            row.team_id: row.rating
            for row in db.session.query(EloRating).join(
                subquery,
                (EloRating.team_id == subquery.c.team_id) &
                (EloRating.date == subquery.c.latest_date)
            )
        }
        
        opportunities = []
        
        for fixture in relevant_fixtures:
            home_elo = elo_map.get(fixture.home_team_id, 1000)
            away_elo = elo_map.get(fixture.away_team_id, 1000)
            
            # Calculate Elo difference and determine which team is favored
            elo_diff = abs(home_elo - away_elo)
            favored_team = fixture.home_team if home_elo > away_elo else fixture.away_team
            underdog_team = fixture.away_team if home_elo > away_elo else fixture.home_team
            favored_elo = max(home_elo, away_elo)
            underdog_elo = min(home_elo, away_elo)
            
            # Calculate win probability for favored team
            from elo_utils import expected_result
            win_probability = expected_result(favored_elo, underdog_elo)
            
            # Categorize based on Elo difference (FIXED: No gaps in ranges)
            category = None
            confidence_level = None
            
            if 150 <= elo_diff <= 249:  # Fixed: Covers 150-249 range
                category = "good_chance"
                confidence_level = "Good Chance"
            elif 250 <= elo_diff <= 399:
                category = "great_chance" 
                confidence_level = "Great Chance"
            elif elo_diff >= 400:
                category = "almost_certain"
                confidence_level = "Almost Certain"
            
            # Only include fixtures that meet betting criteria
            if category:
                opportunities.append({
                    "fixture_id": fixture.id,
                    "api_fixture_id": fixture.api_football_id,
                    "date": fixture.date.isoformat(),
                    "league": fixture.league_name,
                    "venue": fixture.venue,
                    "home_team": {
                        "id": fixture.home_team.id,
                        "name": fixture.home_team.name,
                        "league": fixture.home_team.league,
                        "elo": round(home_elo, 1)
                    },
                    "away_team": {
                        "id": fixture.away_team.id,
                        "name": fixture.away_team.name,
                        "league": fixture.away_team.league,
                        "elo": round(away_elo, 1)
                    },
                    "favored_team": {
                        "id": favored_team.id,
                        "name": favored_team.name,
                        "elo": round(favored_elo, 1)
                    },
                    "underdog_team": {
                        "id": underdog_team.id,
                        "name": underdog_team.name,
                        "elo": round(underdog_elo, 1)
                    },
                    "elo_difference": round(elo_diff, 1),
                    "win_probability": round(win_probability * 100, 1),
                    "category": category,
                    "confidence_level": confidence_level,
                    "betting_recommendation": f"{favored_team.name} has a {confidence_level.lower()} to win"
                })
        
        # Sort by Elo difference (highest first) for best opportunities
        opportunities.sort(key=lambda x: x["elo_difference"], reverse=True)
        
        return jsonify({
            "opportunities": opportunities,
            "total_count": len(opportunities),
            "categories": {
                "good_chance": len([o for o in opportunities if o["category"] == "good_chance"]),
                "great_chance": len([o for o in opportunities if o["category"] == "great_chance"]),
                "almost_certain": len([o for o in opportunities if o["category"] == "almost_certain"])
            },
            "message": f"Found {len(opportunities)} betting opportunities from {len(relevant_fixtures)} upcoming fixtures"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/create-test-user", methods=["POST"])
def create_test_user():
    """Temporary endpoint to create a test user (REMOVE IN PRODUCTION!)"""
    try:
        data = request.get_json()
        email = data.get("email")
        
        if not email:
            return jsonify({"error": "Email is required"}), 400
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({"message": f"User {email} already exists", "user": existing_user.serialize()}), 200
        
        # Create new test user with active subscription
        new_user = User(
            email=email,
            stripe_customer_id="test_customer_id",
            stripe_subscription_id="test_subscription_id",
            subscription_status="active",
            subscription_start_date=datetime.utcnow()
        )
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            "message": f"Test user created successfully",
            "user": new_user.serialize()
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/fixtures", methods=["POST"])
def get_fixtures():
    """Get upcoming fixtures for premium users"""
    data = request.get_json()
    email = data.get("email")
    
    if not email:
        return jsonify({"error": "Email is required"}), 400
    
    # Check premium status
    user = User.query.filter_by(email=email).first()
    if not user or not user.is_premium_active():
        return jsonify({"error": "Premium subscription required"}), 403
    
    try:
        # Get fixtures from today onwards
        today = datetime.now().date()
        upcoming_fixtures = Fixture.query.filter(
            Fixture.date >= today,
            Fixture.status == "NS"  # Not Started
        ).order_by(Fixture.date.asc()).all()
        
        # Filter to only include fixtures with teams in our database
        relevant_fixtures = [f for f in upcoming_fixtures if f.has_elo_teams()]
        
        return jsonify({
            "fixtures": [fixture.serialize() for fixture in relevant_fixtures],
            "total_count": len(relevant_fixtures),
            "message": f"Found {len(relevant_fixtures)} upcoming fixtures"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/manual-fixture-fetch", methods=["POST"])
def manual_fixture_fetch():
    """Manual endpoint to fetch fixtures (for testing)"""
    try:
        fetch_next_48_hours_fixtures()
        return jsonify({"message": "Fixture fetch completed successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/manual-import", methods=["POST"])
def manual_import():
    """Import data from CSV sources as fallback"""
    try:
        from import_data import import_matches_from_csv
        
        # Import Premier League 2023-24 season as a quick test
        url = "https://www.football-data.co.uk/mmz4281/2324/E0.csv"
        import_matches_from_csv(url)
        
        return jsonify({
            "message": "CSV import completed (Premier League 2023-24)",
            "method": "csv"
        }), 200
    
    except Exception as e:
        return jsonify({"error": f"Import failed: {str(e)}"}), 500

@app.route("/api/recalculate-elo", methods=["POST"])
def recalculate_elo():
    """Recalculate ELO ratings for existing matches"""
    try:
        print("🔄 Starting ELO recalculation...", flush=True)
        
        # Clear existing ELO ratings
        EloRating.query.delete()
        db.session.commit()
        print("✅ Cleared existing ELO ratings", flush=True)
        
        # Get all matches ordered by date
        matches = Match.query.order_by(Match.date.asc()).all()
        print(f"📊 Found {len(matches)} matches to process", flush=True)
        
        if not matches:
            return jsonify({"error": "No matches found to process"}), 400
        
        # Track ELO ratings for each team
        team_elos = {}
        ratings_to_add = []
        
        processed = 0
        for match in matches:
            try:
                # Get current ELO for both teams (default to 1000)
                home_elo = team_elos.get(match.home_team_id, 1000)
                away_elo = team_elos.get(match.away_team_id, 1000)
                
                # Calculate match result
                from elo_utils import get_match_result, update_elo
                home_score, away_score = get_match_result(match.home_score, match.away_score)
                
                # Calculate new ELO ratings
                new_home_elo = update_elo(home_elo, away_elo, home_score)
                new_away_elo = update_elo(away_elo, home_elo, away_score)
                
                # Update tracking
                team_elos[match.home_team_id] = new_home_elo
                team_elos[match.away_team_id] = new_away_elo
                
                # Add to batch
                ratings_to_add.append(EloRating(
                    team_id=match.home_team_id, 
                    date=match.date, 
                    rating=new_home_elo
                ))
                ratings_to_add.append(EloRating(
                    team_id=match.away_team_id, 
                    date=match.date, 
                    rating=new_away_elo
                ))
                
                processed += 1
                
                # Batch commit every 100 matches
                if processed % 100 == 0:
                    db.session.add_all(ratings_to_add)
                    db.session.commit()
                    ratings_to_add = []
                    print(f"📈 Processed {processed}/{len(matches)} matches", flush=True)
                    
            except Exception as e:
                print(f"❌ Error processing match {match.id}: {e}", flush=True)
                continue
        
        # Final commit
        if ratings_to_add:
            db.session.add_all(ratings_to_add)
            db.session.commit()
        
        print(f"✅ ELO recalculation complete: {processed} matches processed", flush=True)
        
        return jsonify({
            "message": f"ELO recalculation completed successfully",
            "matches_processed": processed,
            "total_matches": len(matches),
            "teams_with_elo": len(team_elos)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ ELO recalculation failed: {str(e)}", flush=True)
        return jsonify({"error": f"Recalculation failed: {str(e)}"}), 500

@app.route("/api/import-top-250-matches", methods=["POST"])
def import_top_250_matches():
    """Import matches for the top 250 teams specifically"""
    try:
        print("🚀 Starting Top 250 teams match import...", flush=True)
        
        # Check if we have the top 250 teams system
        try:
            from top_250_teams import get_team_mapper
            from api_import import APIFootballImporter
            
            api_key = os.environ.get("API_FOOTBALL_KEY")
            if not api_key:
                return jsonify({"error": "API_FOOTBALL_KEY not configured"}), 400
            
            # Get team mapper for top 250 teams
            team_mapper = get_team_mapper()
            progress = team_mapper.get_mapping_progress()
            
            if progress['mapped'] == 0:
                return jsonify({
                    "error": "No top 250 teams mapped. Run team mapping first.",
                    "suggestion": "Use the top_250_manager.py script to map teams first"
                }), 400
            
            # Import historical data for mapped teams
            importer = APIFootballImporter(
                api_key=api_key,
                current_season=datetime.now().year,
                request_delay=0.6,
                max_requests_per_day=6000
            )
            
            print(f"📊 Importing matches for {progress['mapped']} mapped teams...", flush=True)
            importer.import_top_250_teams_historical(start_year=2020)
            
            # Check results
            total_matches = Match.query.count()
            total_elo_ratings = EloRating.query.count()
            
            return jsonify({
                "message": f"Top 250 teams import completed successfully",
                "teams_mapped": progress['mapped'],
                "total_matches": total_matches,
                "total_elo_ratings": total_elo_ratings
            }), 200
            
        except ImportError:
            # Fallback: Clean up excess teams and import basic data
            print("⚠️ Top 250 system not available, cleaning up and importing basic data...", flush=True)
            
            # Keep only teams from major leagues
            major_leagues = [
                "Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1",
                "Champions League", "Europa League", "World Cup"
            ]
            
            # Count teams in major leagues
            teams_to_keep = Team.query.filter(Team.league.in_(major_leagues)).all()
            teams_to_delete = Team.query.filter(~Team.league.in_(major_leagues)).all()
            
            print(f"🧹 Cleaning up: Keeping {len(teams_to_keep)} teams, removing {len(teams_to_delete)} teams", flush=True)
            
            # Delete excess teams
            for team in teams_to_delete:
                db.session.delete(team)
            db.session.commit()
            
            # Import matches for remaining teams using CSV
            from import_data import import_matches_from_csv
            
            urls = [
                "https://www.football-data.co.uk/mmz4281/2324/E0.csv",  # Premier League 23-24
                "https://www.football-data.co.uk/mmz4281/2324/SP1.csv", # La Liga 23-24
                "https://www.football-data.co.uk/mmz4281/2324/I1.csv",  # Serie A 23-24
                "https://www.football-data.co.uk/mmz4281/2324/D1.csv",  # Bundesliga 23-24
                "https://www.football-data.co.uk/mmz4281/2324/F1.csv",  # Ligue 1 23-24
            ]
            
            imported_count = 0
            for url in urls:
                try:
                    import_matches_from_csv(url)
                    imported_count += 1
                except Exception as e:
                    print(f"Failed to import {url}: {e}")
            
            final_teams = Team.query.count()
            final_matches = Match.query.count()
            
            return jsonify({
                "message": f"Cleanup and import completed - imported {imported_count} league seasons",
                "final_teams": final_teams,
                "final_matches": final_matches,
                "method": "csv_cleanup"
            }), 200
            
    except Exception as e:
        print(f"❌ Top 250 import failed: {str(e)}", flush=True)
        return jsonify({"error": f"Import failed: {str(e)}"}), 500

@app.route("/api/reset-and-import", methods=["POST"])
def reset_and_import():
    """Wipe database and import clean data"""
    try:
        print("🗑️  Resetting database...", flush=True)
        
        # Clear all data
        EloRating.query.delete()
        Match.query.delete()
        Team.query.delete()
        # Clear fixtures if they exist
        try:
            Fixture.query.delete()
        except:
            pass
        db.session.commit()
        print("✅ Database cleared", flush=True)
        
        # Import fresh data from CSV (major leagues only)
        from import_data import import_matches_from_csv
        
        urls = [
            "https://www.football-data.co.uk/mmz4281/2324/E0.csv",  # Premier League 23-24
            "https://www.football-data.co.uk/mmz4281/2324/SP1.csv", # La Liga 23-24
            "https://www.football-data.co.uk/mmz4281/2324/I1.csv",  # Serie A 23-24
            "https://www.football-data.co.uk/mmz4281/2324/D1.csv",  # Bundesliga 23-24
            "https://www.football-data.co.uk/mmz4281/2324/F1.csv",  # Ligue 1 23-24
            "https://www.football-data.co.uk/mmz4281/2223/E0.csv",  # Premier League 22-23
            "https://www.football-data.co.uk/mmz4281/2223/SP1.csv", # La Liga 22-23
            "https://www.football-data.co.uk/mmz4281/2223/I1.csv",  # Serie A 22-23
        ]
        
        imported_count = 0
        total_urls = len(urls)
        
        for i, url in enumerate(urls):
            try:
                print(f"📥 Importing {i+1}/{total_urls}: {url}", flush=True)
                import_matches_from_csv(url)
                imported_count += 1
            except Exception as e:
                print(f"❌ Failed to import {url}: {e}", flush=True)
                continue
        
        # Get final counts
        final_teams = Team.query.count()
        final_matches = Match.query.count()
        final_elo_ratings = EloRating.query.count()
        
        return jsonify({
            "message": f"Database reset and import completed successfully!",
            "imported_seasons": imported_count,
            "total_seasons": total_urls,
            "final_teams": final_teams,
            "final_matches": final_matches,
            "final_elo_ratings": final_elo_ratings,
            "leagues": "Premier League, La Liga, Serie A, Bundesliga, Ligue 1"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Reset and import failed: {str(e)}", flush=True)
        return jsonify({"error": f"Reset failed: {str(e)}"}), 500

if __name__ == "__main__":
    from apscheduler.schedulers.background import BackgroundScheduler
    from import_data import import_matches_from_csv, generate_football_data_urls

    # Background scheduler removed - scheduled tasks now run in scheduled_import.py

    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0",  port=int(os.environ.get("PORT", 5000)))


