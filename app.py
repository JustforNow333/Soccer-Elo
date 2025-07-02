from flask import Flask, request, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from db import db, Team, Match, EloRating, User
from datetime import datetime
from flask_cors import CORS
import os
from elo_utils import expected_result, update_elo, get_match_result

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": [
    "http://localhost:3000", 
     r"https://.*\.vercel\.app"
]}})
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = False

# Initialize Stripe once at startup - set to None if not configured
def get_stripe():
    try:
        import stripe
        key = os.environ.get("STRIPE_SECRET_KEY")
        if not key:
            print("❌ STRIPE_SECRET_KEY is missing!")
            print(f"Available env vars: {list(os.environ.keys())}")
            return None
        
        # Validate the key format
        if not key.startswith(('sk_test_', 'sk_live_')):
            print(f"❌ Invalid STRIPE_SECRET_KEY format: {key[:10]}...")
            return None
            
        stripe.api_key = key
        print(f"✅ Stripe configured successfully with key: {key[:10]}...")
        return stripe
    except ImportError as e:
        print(f"❌ Failed to import stripe: {e}")
        return None
    except Exception as e:
        print(f"❌ Error configuring Stripe: {e}")
        return None

db.init_app(app)

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
        print("=== DEBUG: Starting create_checkout_session ===")
        data = request.get_json()
        print(f"DEBUG: Request data: {data}")
        
        email = data.get("email")
        print(f"DEBUG: Email: {email}")

        if not email:
            print("DEBUG: No email provided")
            return jsonify({"error": "Email is required"}), 400

        print("DEBUG: Getting Stripe...")
        stripe = get_stripe()
        print(f"DEBUG: Stripe object: {stripe}")
        
        if not stripe:
            print("DEBUG: Stripe not configured")
            return jsonify({
                "error": "Payment system not configured. Please contact support.",
                "details": "Stripe secret key is missing or invalid"
            }), 500
        
        print("DEBUG: Checking database connection...")
        try:
            # Test database connection
            db.session.execute('SELECT 1')
            print("DEBUG: Database connection OK")
        except Exception as db_error:
            print(f"DEBUG: Database connection failed: {db_error}")
            return jsonify({"error": "Database connection failed"}), 500
        
        # Create or get existing user
        print("DEBUG: Querying for user...")
        try:
            user = User.query.filter_by(email=email).first()
            print(f"DEBUG: Found user: {user}")
            
            if not user:
                print("DEBUG: Creating new user...")
                user = User(email=email)
                db.session.add(user)
                db.session.commit()
                print(f"DEBUG: Created user: {user}")
        except Exception as user_error:
            print(f"DEBUG: User creation/lookup failed: {user_error}")
            return jsonify({"error": "Failed to process user data"}), 500

        print("DEBUG: Creating Stripe checkout session...")
        try:
            session = stripe.checkout.Session.create(
                customer_email=email,
                payment_method_types=["card"],
                line_items=[{
                    "price": "price_1RfE3RFQ0X76CRQWSNsdAb5Q",
                    "quantity": 1,
                }],
                mode="subscription",
                success_url="https://soccer-elo-chi.vercel.app/success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url="https://soccer-elo-chi.vercel.app/cancel",
                metadata={
                    "user_id": str(user.id),
                    "email": email
                }
            )
            print(f"DEBUG: Created session: {session.id}")
        except Exception as stripe_error:
            print(f"DEBUG: Stripe session creation failed: {stripe_error}")
            return jsonify({
                "error": "Failed to create checkout session", 
                "details": str(stripe_error)
            }), 400
        
        if not session or not session.url:
            print("DEBUG: Session creation failed - no URL")
            return jsonify({"error": "Failed to create checkout session"}), 500
        
        print(f"DEBUG: Session URL: {session.url}")
        return jsonify({"url": session.url})
        
    except Exception as e:
        print(f"DEBUG: Exception occurred: {str(e)}")
        print(f"DEBUG: Exception type: {type(e)}")
        import traceback
        print(f"DEBUG: Full traceback: {traceback.format_exc()}")
        return jsonify({
            "error": "Internal server error", 
            "details": str(e)
        }), 500

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
                user.stripe_customer_id = customer_id
                user.stripe_subscription_id = subscription_id
                user.subscription_status = "active"
                user.subscription_start_date = datetime.utcnow()
                db.session.commit()
                print(f"Updated user {customer_email} with subscription {subscription_id}")
            else:
                print(f"User not found for email: {customer_email}")
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
        
        # Get matches from today onwards (upcoming matches)
        today = date.today()
        upcoming_matches = Match.query.filter(Match.date >= today).order_by(Match.date.asc()).all()
        
        if not upcoming_matches:
            return jsonify({
                "opportunities": [],
                "message": "No upcoming matches found"
            })
        
        # Get latest Elo ratings for all teams involved in upcoming matches
        team_ids = set()
        for match in upcoming_matches:
            team_ids.add(match.home_team_id)
            team_ids.add(match.away_team_id)
        
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
        
        for match in upcoming_matches:
            home_elo = elo_map.get(match.home_team_id, 1000)
            away_elo = elo_map.get(match.away_team_id, 1000)
            
            # Calculate Elo difference and determine which team is favored
            elo_diff = abs(home_elo - away_elo)
            favored_team = match.home_team if home_elo > away_elo else match.away_team
            underdog_team = match.away_team if home_elo > away_elo else match.home_team
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
            
            # Only include matches that meet betting criteria
            if category:
                opportunities.append({
                    "match_id": match.id,
                    "date": match.date.isoformat(),
                    "home_team": {
                        "id": match.home_team.id,
                        "name": match.home_team.name,
                        "league": match.home_team.league,
                        "elo": round(home_elo, 1)
                    },
                    "away_team": {
                        "id": match.away_team.id,
                        "name": match.away_team.name,
                        "league": match.away_team.league,
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
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    from apscheduler.schedulers.background import BackgroundScheduler
    from import_data import import_matches_from_csv, generate_football_data_urls

    def scheduled_fetch():
        print("Running scheduled match import...")
        urls = generate_football_data_urls(start_season=2024, end_season=2025, include_club_world_cup=True)
        for url in urls:
            import_matches_from_csv(url)
        print("Finished scheduled fetch.")

    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_fetch, 'interval', minutes=5)
    scheduler.start()

    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0",  port=int(os.environ.get("PORT", 5000)))
