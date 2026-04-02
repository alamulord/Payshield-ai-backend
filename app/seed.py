# app/seed.py — Realistic data seeder for PayShield
"""
Data Seeder: Generates realistic transaction, alert, investigation, and model data.
Uses Faker for realistic names/addresses and custom logic for fraud patterns.
"""
import json
import random
import asyncio
from datetime import datetime, timedelta, timezone
from faker import Faker
from sqlalchemy import text, select, func
from app.db.database import async_session, init_db
from app.db.models import User, Transaction, Alert, Investigation, ModelRegistry, Rule
from app.core.security import hash_password
from app.services.scoring_service import score_transaction
from app.services.alert_service import calculate_sla, USERNAMES

fake = Faker()

# Merchant data
MERCHANTS = [
    ("TechGizmo Inc.", "electronics", "store"),
    ("Urban Styles", "fashion", "shopping-bag"),
    ("Apple Store", "electronics", "store"),
    ("Amazon", "marketplace", "shopping-cart"),
    ("Best Buy", "electronics", "store"),
    ("Walmart", "retail", "store"),
    ("Nike", "fashion", "shopping-bag"),
    ("Starbucks", "food", "local-cafe"),
    ("Netflix", "subscription", "play-circle"),
    ("Uber", "transport", "local-taxi"),
    ("Airbnb", "travel", "hotel"),
    ("Spotify", "subscription", "music-note"),
    ("Digital Mart", "electronics", "store"),
    ("QuickPay", "fintech", "payments"),
    ("CloudShop", "marketplace", "cloud"),
    ("Luxury Watches", "luxury", "watch"),
    ("GameZone", "gaming", "sports-esports"),
    ("FoodDash", "food", "restaurant"),
    ("TravelHub", "travel", "flight"),
    ("CryptoExchange", "crypto", "currency-bitcoin"),
]

PAYMENT_METHODS = ["visa", "mastercard", "amex", "paypal"]
COUNTRIES = [
    ("US", "United States"), ("CA", "Canada"), ("GB", "United Kingdom"),
    ("FR", "France"), ("DE", "Germany"), ("AU", "Australia"),
    ("JP", "Japan"), ("CN", "China"), ("BR", "Brazil"),
    ("IN", "India"), ("NG", "Nigeria"), ("MX", "Mexico"),
    ("KR", "South Korea"), ("RU", "Russia"),
]

DEVICES = [
    "iPhone 15 Pro", "iPhone 14", "Samsung Galaxy S24", "MacBook Pro",
    "Windows PC", "iPad Pro", "Pixel 8", "Surface Pro",
    "Chrome on Windows", "Safari on Mac",
]

ALERT_TRIGGERS = [
    ["Velocity Spike", "New Device"],
    ["High Risk Country", "Unusual Time"],
    ["Large Amount", "New Merchant"],
    ["IP Mismatch", "VPN Detected"],
    ["Card Testing Pattern"],
    ["Velocity Spike", "Large Amount"],
    ["New Device", "Unusual Time"],
    ["High Risk Country", "Large Amount", "New Device"],
]


async def seed_data():
    """Seed the database with realistic data"""
    await init_db()

    async with async_session() as db:
        # Check if already seeded
        try:
            result = await db.execute(select(func.count()).select_from(User.__table__))
            count = result.scalar() or 0
            if count > 0:
                print("⚡ Database already seeded, skipping...")
                return
        except Exception:
            pass  # Table might not exist yet

        print("🌱 Seeding PayShield database...")

        # --- USERS ---
        print("  👤 Creating users...")
        users = [
            User(
                email="admin@payshield.ai",
                name="Admin User",
                hashed_password=hash_password("admin123"),
                role="admin",
                avatar_url="https://ui-avatars.com/api/?name=Admin+User&background=144bb8&color=fff",
            ),
            User(
                email="analyst@payshield.ai",
                name="Sarah Chen",
                hashed_password=hash_password("analyst123"),
                role="analyst",
                avatar_url="https://ui-avatars.com/api/?name=Sarah+Chen&background=10b981&color=fff",
            ),
            User(
                email="analyst2@payshield.ai",
                name="Marcus Williams",
                hashed_password=hash_password("analyst123"),
                role="analyst",
                avatar_url="https://ui-avatars.com/api/?name=Marcus+Williams&background=8b5cf6&color=fff",
            ),
        ]
        for user in users:
            db.add(user)
        await db.flush()
        print(f"    ✅ Created {len(users)} users")

        # --- TRANSACTIONS ---
        print("  💳 Creating transactions...")
        transactions = []
        now = datetime.now(timezone.utc)

        for i in range(200):
            merchant = random.choice(MERCHANTS)
            country = random.choice(COUNTRIES)
            payment = random.choice(PAYMENT_METHODS)
            amount = round(random.lognormvariate(4.5, 1.5), 2)  # Realistic distribution
            amount = min(amount, 25000)  # Cap at 25k

            # Score it
            risk_score, risk_level, risk_factors = score_transaction(
                amount=amount,
                country=country[0],
                merchant_category=merchant[1],
                payment_method=payment,
            )

            # Status based on risk
            if risk_level == "high":
                status = random.choice(["blocked", "flagged", "fraud", "review"])
                status_color = "red"
            elif risk_level == "medium":
                status = random.choice(["review", "pending", "completed"])
                status_color = "yellow" if status != "completed" else "green"
            else:
                status = "completed"
                status_color = "green"

            # Spread timestamps over last 7 days
            timestamp = now - timedelta(
                hours=random.randint(0, 168),
                minutes=random.randint(0, 59),
                seconds=random.randint(0, 59),
            )

            tx = Transaction(
                tx_id=f"TRX-{90000 + i}-{random.choice('ABCDEFGH')}{random.choice('ABCDEFGH')}",
                amount=amount,
                currency="USD",
                merchant_name=merchant[0],
                merchant_category=merchant[1],
                merchant_icon=merchant[2],
                payment_method=payment,
                card_last4=f"{random.randint(1000, 9999)}",
                country=country[0],
                country_name=country[1],
                ip_address=fake.ipv4(),
                device=random.choice(DEVICES),
                user_agent=fake.user_agent(),
                risk_score=risk_score,
                risk_level=risk_level,
                risk_factors=json.dumps(risk_factors),
                status=status,
                status_color=status_color,
                timestamp=timestamp,
                processed_at=timestamp + timedelta(milliseconds=random.randint(50, 500)),
            )
            transactions.append(tx)
            db.add(tx)

        await db.flush()
        print(f"    ✅ Created {len(transactions)} transactions")

        # --- ALERTS ---
        print("  🚨 Creating alerts...")
        high_risk_txs = [tx for tx in transactions if tx.risk_level in ("high", "medium") and tx.risk_score > 55]
        alerts = []

        for i, tx in enumerate(high_risk_txs[:50]):
            sla_text, sla_color, sla_delta = calculate_sla(tx.risk_score)
            triggers = random.choice(ALERT_TRIGGERS)

            status = random.choice(["New", "New", "In Review", "Resolved"])
            alert = Alert(
                case_id=f"CASE-{1000 + i:04d}",
                transaction_id=tx.id,
                amount=tx.amount,
                merchant=tx.merchant_name,
                category=tx.merchant_category,
                username=random.choice(USERNAMES),
                country=tx.country_name,
                country_code=tx.country,
                risk_score=tx.risk_score,
                triggers=json.dumps(triggers),
                status=status,
                sla=sla_text,
                sla_color=sla_color,
                sla_deadline=tx.timestamp + sla_delta,
                payment_method=f"{tx.payment_method.upper()} •••• {tx.card_last4}",
                ip_address=tx.ip_address,
                device=tx.device,
                user_agent=tx.user_agent,
                verdict="fraud_confirmed" if status == "Resolved" and random.random() > 0.4 else (
                    "false_positive" if status == "Resolved" else None
                ),
                resolved_at=tx.timestamp + timedelta(hours=random.randint(1, 24)) if status == "Resolved" else None,
                timestamp=tx.timestamp,
            )
            alerts.append(alert)
            db.add(alert)

        await db.flush()
        print(f"    ✅ Created {len(alerts)} alerts")

        # --- INVESTIGATIONS ---
        print("  🔍 Creating investigations...")
        investigations = []

        for i, alert in enumerate(alerts[:15]):
            inv_status = random.choice(["open", "in_progress", "pending_review", "closed"])
            timeline = [
                {
                    "id": f"evt-{random.randint(1000, 9999)}",
                    "timestamp": alert.timestamp.isoformat() if alert.timestamp else now.isoformat(),
                    "action": "Investigation opened from alert",
                    "user": "System",
                    "details": f"Auto-created from {alert.case_id}",
                    "type": "system",
                },
                {
                    "id": f"evt-{random.randint(1000, 9999)}",
                    "timestamp": (alert.timestamp + timedelta(minutes=random.randint(5, 60))).isoformat() if alert.timestamp else now.isoformat(),
                    "action": "Assigned to analyst",
                    "user": random.choice(["Sarah Chen", "Marcus Williams"]),
                    "details": "Case assigned for review",
                    "type": "action",
                },
            ]

            if inv_status in ("pending_review", "closed"):
                timeline.append({
                    "id": f"evt-{random.randint(1000, 9999)}",
                    "timestamp": (alert.timestamp + timedelta(hours=random.randint(1, 12))).isoformat() if alert.timestamp else now.isoformat(),
                    "action": "Analysis completed",
                    "user": random.choice(["Sarah Chen", "Marcus Williams"]),
                    "details": "Transaction patterns reviewed, device fingerprint analyzed",
                    "type": "action",
                })

            inv = Investigation(
                case_id=f"INV-{10000 + i}",
                alert_id=alert.id,
                analyst_id=users[1].id if random.random() > 0.5 else users[2].id,
                title=f"Suspicious activity: {alert.merchant} - ${alert.amount:,.2f}",
                description=f"Investigating potential fraud at {alert.merchant}. Risk score: {alert.risk_score}. Triggers: {', '.join(json.loads(alert.triggers) if alert.triggers else [])}",
                severity="high" if alert.risk_score >= 80 else ("medium" if alert.risk_score >= 50 else "low"),
                status=inv_status,
                verdict="fraud_confirmed" if inv_status == "closed" and random.random() > 0.4 else (
                    "false_positive" if inv_status == "closed" else None
                ),
                timeline=json.dumps(timeline),
                closed_at=now - timedelta(hours=random.randint(1, 48)) if inv_status == "closed" else None,
            )
            investigations.append(inv)
            db.add(inv)

        await db.flush()
        print(f"    ✅ Created {len(investigations)} investigations")

        # --- MODEL REGISTRY ---
        print("  🤖 Creating model registry...")
        models = [
            ModelRegistry(
                name="PayShield LightGBM",
                version="v2.4.1",
                model_type="lightgbm",
                description="Primary gradient boosting model for transaction fraud scoring. Trained on 2M+ labeled transactions.",
                accuracy=0.9542,
                precision_score=0.8923,
                recall=0.8671,
                f1_score=0.8795,
                auc_roc=0.9734,
                false_positive_rate=0.0187,
                latency_ms=23.4,
                status="deployed",
                is_active=True,
                training_samples=2150000,
                feature_count=48,
                training_duration_sec=342.5,
                last_trained_at=now - timedelta(days=3),
                drift_score=0.012,
                last_drift_check=now - timedelta(hours=6),
                deployed_at=now - timedelta(days=2),
            ),
            ModelRegistry(
                name="PayShield Anomaly Detector",
                version="v1.8.0",
                model_type="pytorch_anomaly",
                description="PyTorch autoencoder for detecting anomalous transaction patterns. Unsupervised learning.",
                accuracy=0.9213,
                precision_score=0.8456,
                recall=0.8312,
                f1_score=0.8383,
                auc_roc=0.9567,
                false_positive_rate=0.0312,
                latency_ms=45.2,
                status="deployed",
                is_active=True,
                training_samples=1800000,
                feature_count=32,
                training_duration_sec=1250.8,
                last_trained_at=now - timedelta(days=7),
                drift_score=0.018,
                last_drift_check=now - timedelta(hours=12),
                deployed_at=now - timedelta(days=5),
            ),
            ModelRegistry(
                name="PayShield River Online",
                version="v3.1.0",
                model_type="river_online",
                description="Incremental online learning model using River. Updates in real-time with analyst feedback.",
                accuracy=0.9089,
                precision_score=0.8234,
                recall=0.8567,
                f1_score=0.8397,
                auc_roc=0.9412,
                false_positive_rate=0.0234,
                latency_ms=8.1,
                status="deployed",
                is_active=True,
                training_samples=500000,
                feature_count=24,
                training_duration_sec=0.5,
                last_trained_at=now - timedelta(hours=1),
                drift_score=0.008,
                last_drift_check=now - timedelta(hours=1),
                deployed_at=now - timedelta(days=14),
            ),
            ModelRegistry(
                name="PayShield Ensemble",
                version="v2.0.0",
                model_type="ensemble",
                description="Weighted ensemble combining LightGBM (60%), PyTorch Anomaly (25%), and River Online (15%).",
                accuracy=0.9678,
                precision_score=0.9123,
                recall=0.8945,
                f1_score=0.9033,
                auc_roc=0.9856,
                false_positive_rate=0.0145,
                latency_ms=52.3,
                status="deployed",
                is_active=True,
                training_samples=2150000,
                feature_count=48,
                training_duration_sec=1600.0,
                last_trained_at=now - timedelta(days=1),
                drift_score=0.009,
                last_drift_check=now - timedelta(hours=3),
                deployed_at=now - timedelta(hours=18),
            ),
            ModelRegistry(
                name="PayShield LightGBM",
                version="v2.3.0",
                model_type="lightgbm",
                description="Previous version. Retired after v2.4.1 deployment.",
                accuracy=0.9478,
                precision_score=0.8834,
                recall=0.8523,
                f1_score=0.8676,
                auc_roc=0.9689,
                false_positive_rate=0.0213,
                latency_ms=25.1,
                status="retired",
                is_active=False,
                training_samples=2000000,
                feature_count=45,
                training_duration_sec=310.2,
                last_trained_at=now - timedelta(days=14),
                deployed_at=now - timedelta(days=14),
            ),
        ]
        for model in models:
            db.add(model)

        await db.flush()
        print(f"    ✅ Created {len(models)} model registry entries")

        # --- RULES ---
        print("  📏 Creating decision rules...")
        rules = [
            Rule(name="High Amount Threshold", description="Flag transactions above $5000",
                 condition=json.dumps({"field": "amount", "operator": ">", "value": 5000}),
                 action="flag", threshold=5000, priority=1, category="amount", is_active=True, times_triggered=1234),
            Rule(name="Velocity Check", description="Block if >10 transactions in 5 minutes",
                 condition=json.dumps({"field": "velocity_5min", "operator": ">", "value": 10}),
                 action="block", threshold=10, priority=2, category="velocity", is_active=True, times_triggered=89),
            Rule(name="High Risk Country", description="Review transactions from high-risk countries",
                 condition=json.dumps({"field": "country", "operator": "in", "value": list({"NG", "RU", "CN"})}),
                 action="review", priority=3, category="geo", is_active=True, times_triggered=567),
            Rule(name="New Device Alert", description="Flag transactions from unrecognized devices",
                 condition=json.dumps({"field": "device_known", "operator": "==", "value": False}),
                 action="flag", priority=4, category="device", is_active=True, times_triggered=234),
            Rule(name="Cross-border Transaction", description="Review transactions with country mismatch",
                 condition=json.dumps({"field": "country_mismatch", "operator": "==", "value": True}),
                 action="review", priority=5, category="geo", is_active=True, times_triggered=456),
            Rule(name="Card Testing Pattern", description="Block rapid micro-transactions ($0.50-$2.00)",
                 condition=json.dumps({"field": "amount", "operator": "between", "value": [0.5, 2.0]}),
                 action="block", threshold=2, priority=1, category="velocity", is_active=True, times_triggered=45),
        ]
        for rule in rules:
            db.add(rule)

        await db.flush()
        print(f"    ✅ Created {len(rules)} decision rules")

        await db.commit()
        print("\n✅ Database seeded successfully!")
        print(f"   📊 {len(transactions)} transactions")
        print(f"   🚨 {len(alerts)} alerts")
        print(f"   🔍 {len(investigations)} investigations")
        print(f"   🤖 {len(models)} models")
        print(f"   📏 {len(rules)} rules")
        print(f"   👤 {len(users)} users")
        print("\n   Login credentials:")
        print("   Admin:   admin@payshield.ai / admin123")
        print("   Analyst: analyst@payshield.ai / analyst123")


if __name__ == "__main__":
    asyncio.run(seed_data())
