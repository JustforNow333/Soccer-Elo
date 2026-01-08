import os
from typing import Optional


class Config:
    @staticmethod
    def get_api_key() -> Optional[str]:
        return os.environ.get('API_FOOTBALL_KEY')

    @staticmethod
    def get_database_url() -> Optional[str]:
        return os.environ.get('DATABASE_URL')

    @staticmethod
    def get_stripe_secret_key() -> Optional[str]:
        return os.environ.get('STRIPE_SECRET_KEY')

    @staticmethod
    def get_stripe_webhook_secret() -> Optional[str]:
        return os.environ.get('STRIPE_WEBHOOK_SECRET')

    @staticmethod
    def get_frontend_url() -> str:
        return os.environ.get("FRONTEND_URL", "http://localhost:3000")

    @staticmethod
    def validate_api_key() -> bool:
        api_key = Config.get_api_key()
        if not api_key:
            print("❌ API_FOOTBALL_KEY environment variable not found")
            return False
        return True

    @staticmethod
    def get_api_headers() -> dict:
        return {
            "x-apisports-key": Config.get_api_key(),
            "x-apisports-host": "v3.football.api-sports.io"
        }

    @staticmethod
    def get_api_base_url() -> str:
        return "https://v3.football.api-sports.io"


config = Config()
