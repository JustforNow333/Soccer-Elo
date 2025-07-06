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
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
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

@app.route("/wipe-db/", methods=["POST"])
def wipe_db():
    from sqlalchemy import text

    try:
        db.session.execute(text("DROP SCHEMA public CASCADE;"))
        db.session.execute(text("CREATE SCHEMA public;"))
        db.session.commit()
        return jsonify({"status": "Database wiped successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
    try:
        date = datetime.strptime(body["date"], "%Y-%m-%d").date()
        match = Match(
            date=date,
            home_team_id=body["home_team_id"],
            away_team_id=body["away_team_id"],
            home_score=body.get("home_score", 0),
            away_score=body.get("away_score", 0),
        )
        db.session.add(match)
        db.session.flush()
        update_elo_after_match(match.id)
        db.session.commit()
        return jsonify({"id": match.id}), 201
    except Exception as e:
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
    """Debug endpoint to check environment variables (REMOVE IN PRODUCTION!)"""
    return jsonify({
        "stripe_secret_key_exists": bool(os.environ.get("STRIPE_SECRET_KEY")),
        "stripe_secret_key_length": len(os.environ.get("STRIPE_SECRET_KEY", "")),
        "stripe_secret_key_starts_with": os.environ.get("STRIPE_SECRET_KEY", "")[:7] + "...",
        "database_url_exists": bool(os.environ.get("DATABASE_URL")),
        "all_env_vars": list(os.environ.keys())
    })

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
    
def update_elo_after_match(match_id, k=20):
    match = Match.query.get(match_id)
    if not match:
        return jsonify({"error": "Match not found"}), 404

    home_team = Team.query.get(match.home_team_id)
    away_team = Team.query.get(match.away_team_id)

    if home_team is None or away_team is None:
        return {"error": "Home or away team not found"}, 400

    home_rating = EloRating.query.filter_by(team_id=home_team.id).order_by(EloRating.date.desc()).first()
    away_rating = EloRating.query.filter_by(team_id=away_team.id).order_by(EloRating.date.desc()).first()

    home_score, away_score = get_match_result(match.home_score, match.away_score)
    home_rating_val = home_rating.rating if home_rating else 1000
    away_rating_val = away_rating.rating if away_rating else 1000

    db.session.add(EloRating(team_id=home_team.id, date=match.date, rating=update_elo(home_rating_val, away_rating_val, home_score, k)))
    db.session.add(EloRating(team_id=away_team.id, date=match.date, rating=update_elo(away_rating_val, home_rating_val, away_score, k)))
    db.session.commit()
    return {"message": "Elo updated"}, 200

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
            
            # Categorize based on Elo difference
            category = None
            confidence_level = None
            
            if 191 <= elo_diff <= 239:
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

if __name__ == "__main__":
    from apscheduler.schedulers.background import BackgroundScheduler
    from import_data import import_matches_from_csv, generate_football_data_urls

    # Background scheduler removed - scheduled tasks now run in scheduled_import.py

    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0",  port=int(os.environ.get("PORT", 5000)))


