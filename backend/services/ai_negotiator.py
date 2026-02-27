"""
InvoX — Chat-Based AI Negotiator Agent
═══════════════════════════════════════════════════
Lender initiates a chat → places an offer → AI agent (representing vendor)
negotiates back and forth in real-time chat messages.

Flow:
  1. Lender opens chat on a marketplace listing
  2. AI sends a welcome message with listing context
  3. Lender sends offer (rate + amount)
  4. AI evaluates and counters / accepts / rejects
  5. Back and forth up to max_rounds
  6. Vendor can view all negotiations on their listings

The AI agent is smart:
  - Knows the fair market rate from vendor's credit score
  - Sees competing negotiations on the same listing
  - Applies pressure tactics and leverages competing offers
  - Accepts when the offer is good enough
"""

import random
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models import (
    MarketplaceListing, Invoice, Vendor, Lender, User,
    NegotiationSession, NegotiationMessage,
    CreditScore,
)
from services.credit_scoring import compute_credit_score


# ═══════════════════════════════════════════════
#  RATE INTELLIGENCE
# ═══════════════════════════════════════════════

def _risk_based_rate(vendor_credit_score: float, risk_grade: str) -> float:
    """Calculate the 'fair' interest rate from the vendor's risk profile."""
    grade_rates = {
        "AAA": 8.5, "AA": 10.0, "A": 12.0, "BBB": 14.0,
        "BB": 16.5, "B": 19.0, "C": 22.0, "D": 28.0,
    }
    base = grade_rates.get(risk_grade, 18.0)
    adjustment = (70 - vendor_credit_score) / 100
    return round(max(6.0, base + adjustment), 2)


def _score_offer(
    offered_rate: float,
    offered_amount: float,
    invoice_amount: float,
    max_interest_rate: float,
) -> float:
    """Score an offer 0-100. Higher = better for vendor."""
    # Rate score (60%) — lower is better
    if max_interest_rate > 0:
        if offered_rate <= max_interest_rate * 0.7:
            rate_score = 100
        elif offered_rate <= max_interest_rate:
            rate_score = 100 - ((offered_rate - max_interest_rate * 0.7) / (max_interest_rate * 0.3)) * 50
        else:
            rate_score = max(0, 50 - (offered_rate - max_interest_rate) * 5)
    else:
        rate_score = 50

    # Amount score (40%) — in Community Pot mode, any valid slice is fine
    amount_pct = (offered_amount / invoice_amount * 100) if invoice_amount > 0 else 0
    if amount_pct >= 90:
        amount_score = 100
    elif amount_pct >= 80:
        amount_score = 80
    elif amount_pct >= 70:
        amount_score = 65
    elif amount_pct >= 3:  # Fractional: even small slices are valid
        amount_score = 55
    else:
        amount_score = max(30, amount_pct * 2)

    return round(rate_score * 0.6 + amount_score * 0.4, 1)


# ═══════════════════════════════════════════════
#  AI AGENT RESPONSE LOGIC
# ═══════════════════════════════════════════════

def _get_competing_offers(db: Session, listing_id: int, exclude_session_id: int) -> list:
    """Get rates from other active/accepted negotiations on same listing."""
    sessions = db.query(NegotiationSession).filter(
        NegotiationSession.listing_id == listing_id,
        NegotiationSession.id != exclude_session_id,
        NegotiationSession.status.in_(["active", "accepted"]),
    ).all()
    rates = []
    for s in sessions:
        last_offer = db.query(NegotiationMessage).filter(
            NegotiationMessage.session_id == s.id,
            NegotiationMessage.sender == "lender",
            NegotiationMessage.offered_rate.isnot(None),
        ).order_by(NegotiationMessage.id.desc()).first()
        if last_offer and last_offer.offered_rate:
            rates.append(last_offer.offered_rate)
    return sorted(rates)


def _generate_ai_response(
    db: Session,
    session: NegotiationSession,
    lender_rate: float,
    lender_amount: float,
    lender_message: str,
) -> dict:
    """
    Core AI logic: evaluate lender's offer and generate a response.
    Community Pot aware — understands fractional investments.
    Returns: { message, message_type, counter_rate, counter_amount }
    """
    fair_rate = session.fair_market_rate or 14.0
    max_rate = session.max_interest_rate or 16.0
    invoice_amount = session.invoice_amount or 0
    round_num = session.current_round
    max_rounds = session.max_rounds

    # Community Pot context — get remaining amount from the listing
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == session.listing_id).first()
    total_funded = (listing.total_funded_amount or 0) if listing else 0
    remaining_amount = round(invoice_amount - total_funded, 2)
    total_investors = (listing.total_investors or 0) if listing else 0
    min_investment = (listing.min_investment or 500) if listing else 500

    # Target: agent wants rate between fair_rate and fair_rate + small buffer
    target_rate = fair_rate + 1.5  # Ideal rate the AI is aiming for
    acceptable_rate = fair_rate + 3.0  # Will accept at this level
    good_rate = fair_rate + 0.5  # Great deal

    # Get competing offers for leverage
    competing = _get_competing_offers(db, session.listing_id, session.id)
    best_competing = min(competing) if competing else None

    # Score the offer — use remaining amount as reference for fractional
    eval_amount = remaining_amount if remaining_amount > 0 else invoice_amount
    score = _score_offer(lender_rate, lender_amount, eval_amount, max_rate)

    # Funding percentage (of remaining, not total)
    funding_pct = round((lender_amount / eval_amount * 100), 1) if eval_amount > 0 else 80

    # ── Decision tree ──

    # REJECT: Rate way too high
    if lender_rate > max_rate * 1.3:
        return {
            "message": (
                f"I appreciate your interest, but {lender_rate:.1f}% is significantly above "
                f"our maximum cap of {max_rate:.1f}%. This vendor has a "
                f"**{session.vendor_risk_grade}** credit rating ({session.vendor_credit_score:.0f}/100). "
                f"We'd need you to come down substantially — ideally below {max_rate:.1f}%. "
                f"Can you reconsider?"
            ),
            "message_type": "counter",
            "counter_rate": round(max_rate - 0.5, 1),
            "counter_amount": round(min(lender_amount, remaining_amount), 2),
            "score": score,
            "funding_pct": funding_pct,
        }

    # Valid amount check — must be at least min_investment (Community Pot)
    amount_is_valid = lender_amount >= min_investment or lender_amount >= remaining_amount

    # ACCEPT: Rate is excellent
    if lender_rate <= good_rate and amount_is_valid:
        pot_note = f" This brings the community pot to {total_investors + 1} investor(s)." if total_investors > 0 else ""
        return {
            "message": (
                f"**Excellent offer!** {lender_rate:.1f}% is a fantastic rate for this vendor. "
                f"Investment of ₹{lender_amount:,.0f} ({funding_pct:.0f}% of remaining) looks great.{pot_note} "
                f"I'm recommending this deal to the vendor. **Deal accepted!**"
            ),
            "message_type": "accept",
            "counter_rate": lender_rate,
            "counter_amount": lender_amount,
            "score": score,
            "funding_pct": funding_pct,
        }

    # ACCEPT: After many rounds, rate is decent
    if round_num >= max_rounds - 1 and lender_rate <= acceptable_rate and amount_is_valid:
        savings = round(max_rate - lender_rate, 1)
        return {
            "message": (
                f"After our negotiation, {lender_rate:.1f}% is acceptable. "
                f"That saves the vendor **{savings}%** vs the {max_rate:.1f}% cap. "
                f"₹{lender_amount:,.0f} funding is workable. **Deal accepted!**"
            ),
            "message_type": "accept",
            "counter_rate": lender_rate,
            "counter_amount": lender_amount,
            "score": score,
            "funding_pct": funding_pct,
        }

    # ACCEPT: Good enough and at last round
    if round_num >= max_rounds and lender_rate <= max_rate and amount_is_valid:
        return {
            "message": (
                f"We've had a good negotiation. {lender_rate:.1f}% is within the acceptable range. "
                f"**Deal accepted** — I'll recommend this to the vendor."
            ),
            "message_type": "accept",
            "counter_rate": lender_rate,
            "counter_amount": lender_amount,
            "score": score,
            "funding_pct": funding_pct,
        }

    # REJECT: Final round and rate still too high
    if round_num >= max_rounds and lender_rate > max_rate:
        return {
            "message": (
                f"Unfortunately we couldn't reach an agreement. {lender_rate:.1f}% exceeds "
                f"the vendor's {max_rate:.1f}% cap even after {round_num} rounds. "
                f"Thank you for your time. The vendor may consider other offers."
            ),
            "message_type": "reject",
            "counter_rate": None,
            "counter_amount": None,
            "score": score,
            "funding_pct": funding_pct,
        }

    # ── COUNTER-OFFER: Focused 2-round negotiation ──

    # How far from target?
    gap = lender_rate - target_rate

    # Suggest a rate — be aggressive in 2-round format
    if lender_rate > max_rate:
        suggested = round(max_rate - random.uniform(0.3, 1.0), 1)
        urgency = "high"
    elif lender_rate > acceptable_rate:
        suggested = round(target_rate + random.uniform(0.0, 0.5), 1)
        urgency = "medium"
    else:
        suggested = round(max(good_rate, lender_rate - gap * 0.5), 1)
        urgency = "low"

    # Build substantive message for 2-round format
    parts = []

    if round_num == 1:
        parts.append(
            f"Thank you for your offer of **{lender_rate:.1f}%** for ₹{lender_amount:,.0f}."
        )
        parts.append(
            f"This vendor has a **{session.vendor_risk_grade}** credit rating "
            f"({session.vendor_credit_score:.0f}/100) with a fair market rate of **{fair_rate:.1f}%**."
        )
    else:
        parts.append(f"Your revised offer of **{lender_rate:.1f}%** for ₹{lender_amount:,.0f} is noted.")

    # Competing offer leverage
    if best_competing and best_competing < lender_rate:
        parts.append(
            f"Note: another lender is offering **{best_competing:.1f}%** on this invoice. "
            f"You'll need to beat that to win this deal."
        )

    # Amount commentary
    if lender_amount < min_investment and lender_amount < remaining_amount:
        parts.append(
            f"Your investment of ₹{lender_amount:,.0f} is below our minimum of ₹{min_investment:,.0f}."
        )
    elif total_investors > 0:
        parts.append(
            f"Your ₹{lender_amount:,.0f} ({funding_pct:.0f}% of remaining ₹{remaining_amount:,.0f}) "
            f"joins **{total_investors}** existing investor(s) in the community pot."
        )

    # Rate push
    if urgency == "high":
        parts.append(
            f"Your rate exceeds the vendor's **{max_rate:.1f}% cap**. "
            f"**I need you at {suggested:.1f}%** or below. This is a verified invoice with blockchain security."
        )
    elif urgency == "medium":
        parts.append(
            f"Given the vendor's strong credit profile and verified invoice, "
            f"**{suggested:.1f}%** would be fair. Can you match that?"
        )
    else:
        parts.append(
            f"You're close! **{suggested:.1f}%** would make this a win-win. "
            f"The vendor has a solid repayment history."
        )

    # Round pressure
    rounds_left = max_rounds - round_num
    if rounds_left == 1:
        parts.append("⚠️ **This is your last chance** — next round is final.")
    elif rounds_left == 0:
        parts.append("⚠️ **Final round** — make your best offer now.")

    return {
        "message": " ".join(parts),
        "message_type": "counter",
        "counter_rate": suggested,
        "counter_amount": round(min(max(lender_amount, min_investment), remaining_amount), 2),
        "score": score,
        "funding_pct": funding_pct,
    }


# ═══════════════════════════════════════════════
#  PUBLIC API FUNCTIONS
# ═══════════════════════════════════════════════

def start_chat(db: Session, listing_id: int, lender_user: User) -> dict:
    """
    Lender opens a negotiation chat on a listing.
    Creates session + welcome message.
    """
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if not listing:
        raise ValueError("Listing not found")
    if listing.listing_status not in ("open", "partially_funded"):
        raise ValueError(f"Listing is '{listing.listing_status}', must be open for negotiation")

    lender = db.query(Lender).filter(Lender.id == lender_user.lender_id).first()
    if not lender:
        raise ValueError("You must be a registered lender")

    # Check if lender already has an active session on this listing
    existing = db.query(NegotiationSession).filter(
        NegotiationSession.listing_id == listing_id,
        NegotiationSession.lender_id == lender.id,
        NegotiationSession.status == "active",
    ).first()
    if existing:
        return format_chat(db, existing)

    # Gather context
    invoice = db.query(Invoice).filter(Invoice.id == listing.invoice_id).first()
    vendor = db.query(Vendor).filter(Vendor.id == listing.vendor_id).first()
    if not invoice or not vendor:
        raise ValueError("Invoice or vendor data not found")

    # Credit score
    try:
        score_data = compute_credit_score(db, vendor.id)
        vendor_score = score_data["total_score"]
        risk_grade = score_data["risk_grade"]
    except Exception:
        vendor_score = 55.0
        risk_grade = "BB"

    fair_rate = _risk_based_rate(vendor_score, risk_grade)
    invoice_amount = listing.requested_amount
    tenure_days = listing.repayment_period_days or 90

    # Community Pot context
    total_funded = listing.total_funded_amount or 0
    remaining_amount = round(invoice_amount - total_funded, 2)
    total_investors = listing.total_investors or 0
    min_investment = listing.min_investment or 500

    # Count competing negotiations
    competing_count = db.query(NegotiationSession).filter(
        NegotiationSession.listing_id == listing_id,
        NegotiationSession.status.in_(["active", "accepted"]),
    ).count()

    # Create session
    session = NegotiationSession(
        listing_id=listing_id,
        vendor_id=vendor.id,
        lender_id=lender.id,
        lender_user_id=lender_user.id,
        invoice_amount=invoice_amount,
        vendor_credit_score=vendor_score,
        vendor_risk_grade=risk_grade,
        fair_market_rate=fair_rate,
        max_interest_rate=listing.max_interest_rate,
        tenure_days=tenure_days,
        current_round=0,
        max_rounds=2,
        status="active",
    )
    db.add(session)
    db.flush()

    # Welcome message — Community Pot aware
    compete_text = ""
    if competing_count > 0:
        compete_text = f" **{competing_count} other lender(s)** are also negotiating."

    pot_text = ""
    if total_funded > 0:
        progress_pct = round((total_funded / invoice_amount) * 100, 1)
        pot_text = (
            f"\n\n🏺 **Community Pot Status:**\n"
            f"- Already funded: **₹{total_funded:,.0f}** ({progress_pct}%) by **{total_investors}** investor(s)\n"
            f"- Remaining: **₹{remaining_amount:,.0f}**\n"
            f"- Min. investment: **₹{min_investment:,.0f}**"
        )

    welcome = NegotiationMessage(
        session_id=session.id,
        sender="ai_agent",
        message=(
            f"Welcome to the negotiation for **Invoice #{invoice.invoice_number}**!\n\n"
            f"**Listing details:**\n"
            f"- Full invoice ask: **₹{invoice_amount:,.0f}**\n"
            f"- Remaining to fund: **₹{remaining_amount:,.0f}**\n"
            f"- Repayment: **{tenure_days} days**\n"
            f"- Vendor rating: **{risk_grade}** ({vendor_score:.0f}/100)\n"
            f"- Max rate cap: **{listing.max_interest_rate:.1f}%**"
            f"{pot_text}\n\n"
            f"I'm the AI agent representing the vendor.{compete_text} "
            f"You can invest any amount from **₹{min_investment:,.0f}** up to **₹{remaining_amount:,.0f}**. "
            f"Please make your first offer — enter a rate (%) and your investment amount."
        ),
        message_type="welcome",
    )
    db.add(welcome)
    db.commit()
    db.refresh(session)

    return format_chat(db, session)


def process_offer(
    db: Session,
    session_id: int,
    lender_user: User,
    offered_rate: float,
    offered_amount: float,
    message: str = "",
) -> dict:
    """
    Lender sends an offer in the chat. AI responds.
    """
    session = db.query(NegotiationSession).filter(NegotiationSession.id == session_id).first()
    if not session:
        raise ValueError("Negotiation session not found")
    if session.lender_user_id != lender_user.id:
        raise ValueError("This is not your negotiation")
    if session.status != "active":
        raise ValueError(f"Negotiation is '{session.status}', cannot send offers")

    # Validate
    if offered_rate <= 0 or offered_rate > 50:
        raise ValueError("Rate must be between 0.1% and 50%")
    if offered_amount <= 0:
        raise ValueError("Amount must be positive")

    # Validate against remaining amount
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == session.listing_id).first()
    if listing:
        remaining = (listing.requested_amount or 0) - (listing.total_funded_amount or 0)
        if offered_amount > remaining + 0.01:
            raise ValueError(f"Amount ₹{offered_amount:,.0f} exceeds remaining ₹{remaining:,.0f}")

    # Increment round
    session.current_round += 1

    # Lender message — show as % of remaining, not total
    remaining_ref = remaining if listing else (session.invoice_amount or 0)
    funding_pct = round((offered_amount / remaining_ref * 100), 1) if remaining_ref > 0 else 80
    lender_text = message.strip() if message.strip() else (
        f"I'm offering **{offered_rate:.1f}%** annual rate for ₹{offered_amount:,.0f} ({funding_pct:.0f}% of remaining)."
    )

    lender_msg = NegotiationMessage(
        session_id=session.id,
        sender="lender",
        message=lender_text,
        message_type="offer",
        offered_rate=offered_rate,
        offered_amount=offered_amount,
        funding_percentage=funding_pct,
        offer_score=_score_offer(offered_rate, offered_amount, session.invoice_amount, session.max_interest_rate or 16),
    )
    db.add(lender_msg)
    db.flush()

    # AI response
    ai_resp = _generate_ai_response(db, session, offered_rate, offered_amount, lender_text)

    ai_msg = NegotiationMessage(
        session_id=session.id,
        sender="ai_agent",
        message=ai_resp["message"],
        message_type=ai_resp["message_type"],
        offered_rate=ai_resp.get("counter_rate"),
        offered_amount=ai_resp.get("counter_amount"),
        funding_percentage=ai_resp.get("funding_pct"),
        offer_score=ai_resp.get("score"),
    )
    db.add(ai_msg)

    # Update session status
    if ai_resp["message_type"] == "accept":
        session.status = "accepted"
        session.final_rate = offered_rate
        session.final_amount = offered_amount
        session.final_score = ai_resp["score"]
        session.completed_at = datetime.now(timezone.utc)
    elif ai_resp["message_type"] == "reject":
        session.status = "rejected"
        session.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(session)

    return format_chat(db, session)


def format_chat(db: Session, session: NegotiationSession) -> dict:
    """Format a session into the chat response — Community Pot aware."""
    messages = db.query(NegotiationMessage).filter(
        NegotiationMessage.session_id == session.id,
    ).order_by(NegotiationMessage.created_at).all()

    lender = db.query(Lender).filter(Lender.id == session.lender_id).first()
    vendor = db.query(Vendor).filter(Vendor.id == session.vendor_id).first()
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == session.listing_id).first()

    # Community Pot context
    total_funded = (listing.total_funded_amount or 0) if listing else 0
    remaining_amount = round((session.invoice_amount or 0) - total_funded, 2)
    total_investors = (listing.total_investors or 0) if listing else 0
    min_investment = (listing.min_investment or 500) if listing else 500

    return {
        "session_id": session.id,
        "listing_id": session.listing_id,
        "status": session.status,
        "current_round": session.current_round,
        "max_rounds": session.max_rounds,

        # Parties
        "lender": {
            "id": lender.id if lender else None,
            "name": lender.name if lender else None,
            "type": lender.lender_type if lender else None,
            "organization": lender.organization if lender else None,
        },
        "vendor": {
            "id": vendor.id if vendor else None,
            "business_name": vendor.business_name if vendor else None,
        },

        # Context
        "invoice_amount": session.invoice_amount,
        "remaining_amount": remaining_amount,
        "total_funded": total_funded,
        "total_investors": total_investors,
        "min_investment": min_investment,
        "vendor_credit_score": session.vendor_credit_score,
        "vendor_risk_grade": session.vendor_risk_grade,
        "fair_market_rate": session.fair_market_rate,
        "max_interest_rate": session.max_interest_rate,
        "tenure_days": session.tenure_days,

        # Result
        "final_rate": session.final_rate,
        "final_amount": session.final_amount,
        "final_score": session.final_score,

        # Messages
        "messages": [
            {
                "id": m.id,
                "sender": m.sender,
                "message": m.message,
                "message_type": m.message_type,
                "offered_rate": m.offered_rate,
                "offered_amount": m.offered_amount,
                "funding_percentage": m.funding_percentage,
                "offer_score": m.offer_score,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],

        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "created_at": session.created_at.isoformat() if session.created_at else None,
    }


def get_chat(db: Session, session_id: int):
    """Get a specific chat session."""
    session = db.query(NegotiationSession).filter(NegotiationSession.id == session_id).first()
    if not session:
        return None
    return format_chat(db, session)


def get_listing_negotiations(db: Session, listing_id: int) -> list:
    """Get all negotiation chats for a listing (for vendor view)."""
    sessions = db.query(NegotiationSession).filter(
        NegotiationSession.listing_id == listing_id,
    ).order_by(NegotiationSession.created_at.desc()).all()
    return [format_chat(db, s) for s in sessions]


def get_vendor_negotiations(db: Session, vendor_id: int) -> list:
    """Get all negotiations across all of a vendor's listings."""
    sessions = db.query(NegotiationSession).filter(
        NegotiationSession.vendor_id == vendor_id,
    ).order_by(NegotiationSession.created_at.desc()).all()

    results = []
    for s in sessions:
        listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == s.listing_id).first()
        invoice = db.query(Invoice).filter(Invoice.id == listing.invoice_id).first() if listing else None
        chat = format_chat(db, s)
        chat["invoice_number"] = invoice.invoice_number if invoice else None
        chat["listing_status"] = listing.listing_status if listing else None
        results.append(chat)

    return results


def get_lender_negotiations(db: Session, lender_user_id: int) -> list:
    """Get all negotiations for a specific lender."""
    sessions = db.query(NegotiationSession).filter(
        NegotiationSession.lender_user_id == lender_user_id,
    ).order_by(NegotiationSession.created_at.desc()).all()

    results = []
    for s in sessions:
        listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == s.listing_id).first()
        invoice = db.query(Invoice).filter(Invoice.id == listing.invoice_id).first() if listing else None
        chat = format_chat(db, s)
        chat["invoice_number"] = invoice.invoice_number if invoice else None
        chat["listing_status"] = listing.listing_status if listing else None
        results.append(chat)

    return results


def lock_price_accept(db: Session, listing_id: int, lender_user: User, amount: float) -> dict:
    """
    Lender accepts the listed max_interest_rate without negotiation.
    Creates a session that is immediately 'accepted'.
    """
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if not listing:
        raise ValueError("Listing not found")
    if listing.listing_status not in ("open", "partially_funded"):
        raise ValueError(f"Listing is '{listing.listing_status}', must be open")

    lender = db.query(Lender).filter(Lender.id == lender_user.lender_id).first()
    if not lender:
        raise ValueError("You must be a registered lender")

    remaining = round((listing.requested_amount or 0) - (listing.total_funded_amount or 0), 2)
    if amount > remaining + 0.01:
        raise ValueError(f"Amount exceeds remaining amount of the listing")
    min_inv = listing.min_investment or 500
    if amount < min_inv and amount < remaining:
        raise ValueError(f"Minimum investment is {min_inv}")

    try:
        score_data = compute_credit_score(db, listing.vendor_id)
        vendor_score = score_data["total_score"]
        risk_grade = score_data["risk_grade"]
    except Exception:
        vendor_score = 55.0
        risk_grade = "BB"

    session = NegotiationSession(
        listing_id=listing_id,
        vendor_id=listing.vendor_id,
        lender_id=lender.id,
        lender_user_id=lender_user.id,
        invoice_amount=listing.requested_amount,
        vendor_credit_score=vendor_score,
        vendor_risk_grade=risk_grade,
        fair_market_rate=_risk_based_rate(vendor_score, risk_grade),
        max_interest_rate=listing.max_interest_rate,
        tenure_days=listing.repayment_period_days or 90,
        current_round=0,
        max_rounds=0,
        status="accepted",
        final_rate=listing.max_interest_rate,
        final_amount=amount,
        final_score=100,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(session)
    db.flush()

    msg = NegotiationMessage(
        session_id=session.id,
        sender="ai_agent",
        message=(
            f"**Price Locked!**\n\n"
            f"The lender has accepted the listed rate of **{listing.max_interest_rate:.1f}%** "
            f"for an investment of **₹{amount:,.0f}**.\n\n"
            f"No negotiation needed — deal is confirmed at the vendor's listed terms. "
            f"**Deal accepted!**"
        ),
        message_type="accept",
        offered_rate=listing.max_interest_rate,
        offered_amount=amount,
        funding_percentage=round((amount / remaining * 100), 1) if remaining > 0 else 100,
        offer_score=100,
    )
    db.add(msg)
    db.commit()
    db.refresh(session)

    return format_chat(db, session)
