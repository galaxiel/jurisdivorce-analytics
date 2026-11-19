"""Endpoint de paiement Freemium : crée une session Stripe Checkout (mode payment)
si STRIPE_SECRET_KEY est configurée ; sinon bascule sur la simulation de paiement.

Règle d'Or N°5 : l'offre porte sur un OUTIL STATISTIQUE, jamais sur un conseil juridique.
"""
import os

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..schemas import CheckoutResult

router = APIRouter(prefix="/api/checkout", tags=["checkout"])

TIER_DAYS = {"diagnostic_29": 30, "pack_avocat_49": 30, "pass_decisions_19": 7}
TIER_PRICES = {"diagnostic_29": 29, "pack_avocat_49": 49, "pass_decisions_19": 19}


class CheckoutRequest(BaseModel):
    tier: str = Field(pattern="^(diagnostic_29|pack_avocat_49|pass_decisions_19)$")


class CheckoutResult(BaseModel):
    simulation: bool
    redirect_url: str
    tier: str
    price_eur: int
    days: int


@router.post("/create-session", response_model=CheckoutResult)
def create_session(req: CheckoutRequest):
    stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
    base = os.getenv("SITE_URL", "http://localhost:3100")
    days = TIER_DAYS.get(req.tier, 30)
    price = TIER_PRICES.get(req.tier, 29)

    if stripe_key:
        # Production : Stripe Checkout (import paresseux pour ne pas l'exiger en dev)
        try:
            import stripe

            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "eur",
                        "product_data": {"name": f"JurisDivorce Analytics — {req.tier}"},
                        "unit_amount": price * 100,
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url=f"{base}/checkout/simulation?tier={req.tier}&days={days}&paid=1&session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{base}/simulateur?cancelled=1",
            )
            return CheckoutResult(
                simulation=False, redirect_url=session.url,
                tier=req.tier, price_eur=price, days=days,
            )
        except Exception:
            pass  # repli sur la simulation si Stripe échoue

    return CheckoutResult(
        simulation=True,
        redirect_url=f"/checkout/simulation?tier={req.tier}&days={days}",
        tier=req.tier, price_eur=price, days=days,
    )
