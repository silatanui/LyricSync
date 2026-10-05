"""Clear Premium / Stripe flags for a user email (run on the host).

Usage:
  python scratch/clear_user_premium.py tanui.kipngetichsila@students.kyu.ac.ke
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import create_app
from app.extensions import db
from app.models.user import User

EMAIL = (sys.argv[1] if len(sys.argv) > 1 else "tanui.kipngetichsila@students.kyu.ac.ke").strip().lower()


def main() -> int:
    app = create_app()
    with app.app_context():
        user = db.session.query(User).filter(db.func.lower(User.email) == EMAIL).first()
        if not user:
            print(f"No user found for {EMAIL}")
            return 1
        before = {
            "is_premium": bool(user.is_premium),
            "bonus_image_credits": int(user.bonus_image_credits or 0),
            "stripe_customer_id": user.stripe_customer_id,
        }
        user.is_premium = False
        user.bonus_image_credits = 0
        user.stripe_customer_id = None
        db.session.commit()
        print(f"Cleared premium for {user.email}")
        print(f"  before: {before}")
        print("  after:  is_premium=False bonus_image_credits=0 stripe_customer_id=None")
        print("Also cancel any active Stripe subscription for this customer in the Stripe Dashboard.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
