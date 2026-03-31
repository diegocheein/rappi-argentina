"""Taste profile computation and smart recommendations engine."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone

import aiosqlite

from rappi.models.intelligence import (
    CategoryPreference,
    PriceRange,
    Recommendation,
    RecommendationSet,
    SpendingSummary,
    StoreTypePreference,
    TasteProfile,
    TimePattern,
    TopProduct,
    TopStore,
    ToppingPreference,
)

HOUR_SLOTS = {
    "morning": (6, 11),
    "lunch": (11, 14),
    "afternoon": (14, 17),
    "evening": (17, 21),
    "night": (21, 6),  # wraps around midnight
}

DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _hour_to_slot(hour: int) -> str:
    if 6 <= hour < 11:
        return "morning"
    elif 11 <= hour < 14:
        return "lunch"
    elif 14 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"


class IntelligenceEngine:
    """Computes taste profiles and recommendations from order history."""

    def __init__(self, db: aiosqlite.Connection):
        self._db = db

    async def compute_taste_profile(
        self,
        dietary_restrictions: list[str] | None = None,
        allergies: list[str] | None = None,
        include_taste_vector: bool = False,
    ) -> TasteProfile:
        """Compute the full taste profile from order history."""
        return TasteProfile(
            category_preferences=await self._category_preferences(),
            store_type_preferences=await self._store_type_preferences(),
            price_range=await self._price_range(),
            time_patterns=await self._time_patterns(),
            topping_preferences=await self._topping_preferences(),
            top_products=await self._top_products(),
            top_stores=await self._top_stores(),
            spending=await self._spending_summary(),
            taste_vector=await self._taste_vector() if include_taste_vector else None,
            dietary_restrictions=dietary_restrictions or [],
            allergies=allergies or [],
            computed_at=datetime.now(timezone.utc).isoformat(),
        )

    async def get_recommendations(self, context: dict | None = None) -> RecommendationSet:
        """Get smart recommendations based on taste profile and current context."""
        recs: list[Recommendation] = []
        now = datetime.now()
        current_slot = _hour_to_slot(now.hour)
        current_day = DAY_NAMES[now.weekday()]

        # "The usual" recommendations
        recs.extend(await self._usual_recommendations())

        # Time-based recommendations
        recs.extend(await self._time_based_recommendations(now.hour))

        # Embedding-powered: "similar to what you like" (if enabled)
        recs.extend(await self._similar_product_recommendations())

        # New store discovery
        recs.extend(await self._new_store_recommendations())

        # Sort by confidence
        recs.sort(key=lambda r: r.confidence, reverse=True)

        # Generate profile summary
        summary = await self.get_taste_summary()

        return RecommendationSet(
            recommendations=recs[:10],
            context={"time_slot": current_slot, "day": current_day, "hour": now.hour},
            profile_summary=summary,
        )

    async def get_usual_order(self, store_id: int) -> list[dict] | None:
        """Get the user's usual order from a specific store (items ordered 2+ times)."""
        cursor = await self._db.execute(
            """SELECT oi.product_id, oi.product_name, oi.quantity,
                      COUNT(*) as times_ordered
               FROM orders o
               JOIN order_items oi ON o.id = oi.order_id
               WHERE o.store_id = ?
               GROUP BY oi.product_id
               HAVING times_ordered >= 2
               ORDER BY times_ordered DESC""",
            (store_id,),
        )
        rows = await cursor.fetchall()
        if not rows:
            return None
        return [
            {
                "product_id": row["product_id"],
                "name": row["product_name"],
                "quantity": row["quantity"],
                "times_ordered": row["times_ordered"],
            }
            for row in rows
        ]

    async def get_taste_summary(self) -> str:
        """One-line summary of the user's taste profile."""
        cursor = await self._db.execute("SELECT COUNT(*) FROM orders")
        row = await cursor.fetchone()
        if not row or row[0] == 0:
            return "No order history yet."

        parts = []

        # Top categories
        cats = await self._category_preferences()
        if cats:
            top_cats = [c.category_name for c in cats[:2]]
            parts.append(f"Loves {' and '.join(top_cats)}")

        # Top store
        stores = await self._top_stores()
        if stores:
            parts.append(f"orders most from {stores[0].store_name}")

        # Time pattern
        patterns = await self._time_patterns()
        if patterns.peak_hour_slot:
            parts.append(f"usually at {patterns.peak_hour_slot}")

        # Spending
        spending = await self._spending_summary()
        if spending.avg_per_order > 0:
            from rappi.utils.pricing import format_cop
            parts.append(f"avg {format_cop(spending.avg_per_order)} per order")

        if not parts:
            return f"{row[0]} orders in history."

        return ", ".join(parts) + "."

    # --- Private computation methods ---

    async def _category_preferences(self) -> list[CategoryPreference]:
        cursor = await self._db.execute(
            """SELECT pc.category_name, COUNT(*) as cnt
               FROM order_items oi
               LEFT JOIN product_cache pc
                 ON CAST(oi.product_id AS TEXT) = CAST(pc.product_id AS TEXT)
               WHERE pc.category_name IS NOT NULL
               GROUP BY pc.category_name
               ORDER BY cnt DESC
               LIMIT 20"""
        )
        rows = await cursor.fetchall()
        total = sum(row["cnt"] for row in rows) if rows else 1
        return [
            CategoryPreference(
                category_name=row["category_name"],
                order_count=row["cnt"],
                percentage=round(row["cnt"] / total * 100, 1),
            )
            for row in rows
        ]

    async def _store_type_preferences(self) -> list[StoreTypePreference]:
        cursor = await self._db.execute(
            """SELECT COALESCE(o.store_type, sc.store_type, 'restaurant') as stype,
                      COUNT(*) as cnt
               FROM orders o
               LEFT JOIN store_cache sc ON o.store_id = sc.store_id
               GROUP BY stype
               ORDER BY cnt DESC"""
        )
        rows = await cursor.fetchall()
        total = sum(row["cnt"] for row in rows) if rows else 1
        return [
            StoreTypePreference(
                store_type=row["stype"],
                order_count=row["cnt"],
                percentage=round(row["cnt"] / total * 100, 1),
            )
            for row in rows
        ]

    async def _price_range(self) -> PriceRange:
        cursor = await self._db.execute(
            """SELECT AVG(total) as avg_total, MIN(total) as min_total, MAX(total) as max_total
               FROM orders WHERE total > 0"""
        )
        order_row = await cursor.fetchone()

        cursor = await self._db.execute(
            "SELECT AVG(unit_price) as avg_item FROM order_items WHERE unit_price > 0"
        )
        item_row = await cursor.fetchone()

        return PriceRange(
            avg_order_total=round(order_row["avg_total"] or 0, 0),
            min_order_total=order_row["min_total"] or 0,
            max_order_total=order_row["max_total"] or 0,
            avg_item_price=round(item_row["avg_item"] or 0, 0),
        )

    async def _time_patterns(self) -> TimePattern:
        cursor = await self._db.execute(
            """SELECT CAST(strftime('%H', placed_at) AS INTEGER) as hour,
                      CAST(strftime('%w', placed_at) AS INTEGER) as dow,
                      COUNT(*) as cnt
               FROM orders
               WHERE placed_at IS NOT NULL
               GROUP BY hour, dow"""
        )
        rows = await cursor.fetchall()
        if not rows:
            return TimePattern()

        hour_dist: Counter[str] = Counter()
        day_dist: Counter[str] = Counter()

        for row in rows:
            slot = _hour_to_slot(row["hour"])
            hour_dist[slot] += row["cnt"]
            # SQLite %w: 0=Sunday, 1=Monday...
            day_idx = (row["dow"] - 1) % 7  # shift so 0=Monday
            day_dist[DAY_NAMES[day_idx]] += row["cnt"]

        peak_slot = hour_dist.most_common(1)[0][0] if hour_dist else None
        peak_day = day_dist.most_common(1)[0][0] if day_dist else None

        return TimePattern(
            hour_distribution=dict(hour_dist),
            day_distribution=dict(day_dist),
            peak_hour_slot=peak_slot,
            peak_day=peak_day,
        )

    async def _topping_preferences(self) -> list[ToppingPreference]:
        cursor = await self._db.execute(
            "SELECT toppings_json FROM order_items WHERE toppings_json IS NOT NULL AND toppings_json != '[]'"
        )
        rows = await cursor.fetchall()

        counts: Counter[str] = Counter()
        for row in rows:
            try:
                toppings = json.loads(row["toppings_json"])
                for t in toppings:
                    desc = t.get("description", "") if isinstance(t, dict) else str(t)
                    if desc:
                        counts[desc] += 1
            except (json.JSONDecodeError, TypeError):
                continue

        return [
            ToppingPreference(topping_description=desc, count=cnt)
            for desc, cnt in counts.most_common(15)
        ]

    async def _top_products(self) -> list[TopProduct]:
        cursor = await self._db.execute(
            """SELECT oi.product_id, oi.product_name,
                      SUM(oi.quantity) as total_qty,
                      COUNT(DISTINCT oi.order_id) as order_count,
                      o.store_name
               FROM order_items oi
               JOIN orders o ON oi.order_id = o.id
               GROUP BY oi.product_id
               ORDER BY total_qty DESC
               LIMIT 15"""
        )
        rows = await cursor.fetchall()
        return [
            TopProduct(
                product_id=str(row["product_id"]),
                product_name=row["product_name"],
                total_quantity=row["total_qty"],
                order_count=row["order_count"],
                store_name=row["store_name"],
            )
            for row in rows
        ]

    async def _top_stores(self) -> list[TopStore]:
        cursor = await self._db.execute(
            """SELECT o.store_id,
                      COALESCE(o.store_name, sc.name) as store_name,
                      COALESCE(o.store_type, sc.store_type) as store_type,
                      COUNT(*) as order_count,
                      MAX(o.placed_at) as last_ordered
               FROM orders o
               LEFT JOIN store_cache sc ON o.store_id = sc.store_id
               GROUP BY o.store_id
               ORDER BY order_count DESC
               LIMIT 10"""
        )
        rows = await cursor.fetchall()
        return [
            TopStore(
                store_id=row["store_id"],
                store_name=row["store_name"],
                store_type=row["store_type"],
                order_count=row["order_count"],
                last_ordered=row["last_ordered"],
            )
            for row in rows
        ]

    async def _spending_summary(self) -> SpendingSummary:
        cursor = await self._db.execute(
            """SELECT SUM(total) as total_spent, COUNT(*) as cnt,
                      AVG(total) as avg_total, AVG(tip) as avg_tip,
                      MIN(placed_at) as first_order, MAX(placed_at) as last_order
               FROM orders"""
        )
        row = await cursor.fetchone()
        if not row or row["cnt"] == 0:
            return SpendingSummary()

        # Compute orders per week
        orders_per_week = 0.0
        if row["first_order"] and row["last_order"] and row["cnt"] > 1:
            try:
                first = datetime.fromisoformat(row["first_order"].replace("Z", "+00:00"))
                last = datetime.fromisoformat(row["last_order"].replace("Z", "+00:00"))
                weeks = max((last - first).days / 7, 1)
                orders_per_week = round(row["cnt"] / weeks, 1)
            except (ValueError, TypeError):
                pass

        return SpendingSummary(
            total_spent=row["total_spent"] or 0,
            order_count=row["cnt"],
            avg_per_order=round(row["avg_total"] or 0, 0),
            avg_tip=round(row["avg_tip"] or 0, 0),
            orders_per_week=orders_per_week,
        )

    async def _taste_vector(self) -> list[float] | None:
        """Average embedding of all ordered products (requires embeddings enabled)."""
        try:
            from rappi.memory.embeddings import bytes_to_vector

            cursor = await self._db.execute(
                """SELECT e.vector
                   FROM order_items oi
                   JOIN orders o ON oi.order_id = o.id
                   JOIN embeddings e ON e.entity_type = 'product'
                     AND e.entity_id = CAST(o.store_id AS TEXT) || ':' || oi.product_id"""
            )
            rows = await cursor.fetchall()
            if not rows:
                return None

            vectors = [bytes_to_vector(row["vector"]) for row in rows]
            dim = len(vectors[0])
            avg = [sum(v[i] for v in vectors) / len(vectors) for i in range(dim)]
            return avg
        except Exception:
            return None

    # --- Recommendation generators ---

    async def _usual_recommendations(self) -> list[Recommendation]:
        """Find 'the usual' — products ordered 3+ times from the same store."""
        cursor = await self._db.execute(
            """SELECT o.store_id, o.store_name, oi.product_id, oi.product_name,
                      oi.quantity, COUNT(*) as times_ordered
               FROM orders o
               JOIN order_items oi ON o.id = oi.order_id
               GROUP BY o.store_id, oi.product_id
               HAVING times_ordered >= 3
               ORDER BY times_ordered DESC
               LIMIT 20"""
        )
        rows = await cursor.fetchall()
        if not rows:
            return []

        # Group by store
        store_items: dict[int, list] = {}
        store_names: dict[int, str] = {}
        for row in rows:
            sid = row["store_id"]
            if sid not in store_items:
                store_items[sid] = []
                store_names[sid] = row["store_name"] or "Store"
            store_items[sid].append({
                "product_id": row["product_id"],
                "name": row["product_name"],
                "quantity": row["quantity"],
                "times_ordered": row["times_ordered"],
            })

        recs = []
        for sid, items in store_items.items():
            top_item = items[0]
            item_names = [it["name"] for it in items[:3]]
            confidence = min(top_item["times_ordered"] / 10, 1.0)
            recs.append(Recommendation(
                type="usual",
                title=f"Your usual from {store_names[sid]}",
                description=", ".join(item_names),
                store_id=sid,
                store_name=store_names[sid],
                confidence=confidence,
                items=items,
            ))

        return recs[:5]

    async def _time_based_recommendations(self, current_hour: int) -> list[Recommendation]:
        """Stores the user orders from at this time of day."""
        slot = _hour_to_slot(current_hour)
        start, end = HOUR_SLOTS.get(slot, (0, 24))

        if slot == "night":
            # Night wraps: 21-23 and 0-5
            where = "(CAST(strftime('%H', placed_at) AS INTEGER) >= 21 OR CAST(strftime('%H', placed_at) AS INTEGER) < 6)"
            params: tuple = ()
        else:
            where = "CAST(strftime('%H', placed_at) AS INTEGER) BETWEEN ? AND ?"
            params = (start, end - 1)

        cursor = await self._db.execute(
            f"""SELECT store_id, store_name, COUNT(*) as cnt
                FROM orders
                WHERE {where}
                GROUP BY store_id
                ORDER BY cnt DESC
                LIMIT 5""",
            params,
        )
        rows = await cursor.fetchall()

        # Get total orders for confidence scoring
        cursor2 = await self._db.execute("SELECT COUNT(*) FROM orders")
        total_row = await cursor2.fetchone()
        total = total_row[0] if total_row else 1

        recs = []
        for row in rows:
            confidence = min(row["cnt"] / total * 5, 1.0)
            recs.append(Recommendation(
                type="time_based",
                title=f"{store_names}" if False else f"{row['store_name'] or 'Store'} — your {slot} spot",
                description=f"You've ordered from here {row['cnt']} times around this time",
                store_id=row["store_id"],
                store_name=row["store_name"],
                confidence=confidence,
            ))

        return recs

    async def _new_store_recommendations(self) -> list[Recommendation]:
        """Stores the user hasn't tried that match their preferred store types."""
        cursor = await self._db.execute(
            """SELECT sc.store_id, sc.name, sc.store_type
               FROM store_cache sc
               WHERE sc.store_id NOT IN (SELECT DISTINCT store_id FROM orders)
               LIMIT 10"""
        )
        rows = await cursor.fetchall()

        return [
            Recommendation(
                type="new_store",
                title=f"Try {row['name'] or 'a new store'}",
                description=f"You haven't ordered from here yet ({row['store_type'] or 'store'})",
                store_id=row["store_id"],
                store_name=row["name"],
                confidence=0.3,
            )
            for row in rows[:3]
        ]

    async def _similar_product_recommendations(self) -> list[Recommendation]:
        """Find products similar to what the user likes, using embeddings.

        Computes the user's taste vector (average of ordered product embeddings),
        then finds cached products most similar to it that the user hasn't ordered.
        Only works when embeddings are enabled.
        """
        try:
            taste_vec = await self._taste_vector()
            if not taste_vec:
                return []

            from rappi.memory.embeddings import bytes_to_vector, cosine_similarity

            # Get all product embeddings
            cursor = await self._db.execute(
                "SELECT entity_id, text_content, vector FROM embeddings WHERE entity_type = 'product'"
            )
            rows = await cursor.fetchall()
            if not rows:
                return []

            # Get products the user has already ordered
            cursor2 = await self._db.execute(
                """SELECT DISTINCT CAST(o.store_id AS TEXT) || ':' || oi.product_id as eid
                   FROM order_items oi JOIN orders o ON oi.order_id = o.id"""
            )
            ordered_ids = {row[0] for row in await cursor2.fetchall()}

            # Score unordered products against taste vector
            scored = []
            for row in rows:
                if row["entity_id"] in ordered_ids:
                    continue
                vec = bytes_to_vector(row["vector"])
                score = cosine_similarity(taste_vec, vec)
                if score > 0.7:  # only recommend strong matches
                    scored.append((row["entity_id"], row["text_content"], score))

            scored.sort(key=lambda x: x[2], reverse=True)

            recs = []
            for entity_id, text, score in scored[:3]:
                parts = entity_id.split(":", 1)
                store_id = int(parts[0]) if len(parts) == 2 else None
                # Look up store name
                store_name = None
                if store_id:
                    sc = await self._db.execute(
                        "SELECT name FROM store_cache WHERE store_id = ?", (store_id,)
                    )
                    sr = await sc.fetchone()
                    if sr:
                        store_name = sr["name"]

                recs.append(Recommendation(
                    type="similar_product",
                    title=f"You might like: {text}",
                    description=f"Similar to what you usually order" + (f" — from {store_name}" if store_name else ""),
                    store_id=store_id,
                    store_name=store_name,
                    product_name=text,
                    confidence=round(score, 2),
                ))

            return recs
        except Exception:
            return []

    async def score_menu_items(
        self, store_id: int, products: list
    ) -> list[dict]:
        """Score menu items against the user's taste vector.

        Returns products sorted by how well they match the user's taste,
        with a match_score field. Only works with embeddings enabled.
        Falls back to order-frequency scoring without embeddings.
        """
        # Try embedding-based scoring first
        taste_vec = await self._taste_vector()
        if taste_vec:
            try:
                from rappi.memory.embeddings import bytes_to_vector, cosine_similarity

                scored = []
                for p in products:
                    pid = getattr(p, "id", getattr(p, "product_id", 0))
                    entity_id = f"{store_id}:{pid}"
                    cursor = await self._db.execute(
                        "SELECT vector FROM embeddings WHERE entity_type = 'product' AND entity_id = ?",
                        (entity_id,),
                    )
                    row = await cursor.fetchone()
                    if row:
                        vec = bytes_to_vector(row["vector"])
                        score = cosine_similarity(taste_vec, vec)
                    else:
                        score = 0.0
                    scored.append({"product": p, "match_score": round(score, 3), "source": "embedding"})

                scored.sort(key=lambda x: x["match_score"], reverse=True)
                return scored
            except Exception:
                pass

        # Fallback: score by how often the user has ordered each product
        scored = []
        for p in products:
            pid = str(getattr(p, "id", getattr(p, "product_id", 0)))
            cursor = await self._db.execute(
                "SELECT SUM(quantity) as qty FROM order_items WHERE product_id = ?",
                (pid,),
            )
            row = await cursor.fetchone()
            qty = row["qty"] if row and row["qty"] else 0
            score = min(qty / 5, 1.0)  # 5 orders = max score
            scored.append({"product": p, "match_score": round(score, 3), "source": "history"})

        scored.sort(key=lambda x: x["match_score"], reverse=True)
        return scored
