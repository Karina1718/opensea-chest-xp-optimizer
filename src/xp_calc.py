import yaml
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class ActionResult:
    action: str
    xp: int
    txs: int
    volume_usd: float
    cost_usd: float

class XPCalculator:
    def __init__(self, params: Dict):
        self.p = params

    def level_xp(self, target_level:int) -> int:
        table = {row["level"]: row["xp"] for row in self.p["levels"]}
        if target_level not in table:
            raise ValueError("Unknown target level")
        return table[target_level]

    def base_quests_xp(self) -> int:
        return sum(q["xp"] for q in self.p["xp"]["base_quests"])

    def simulate_swaps(self, swaps:int, avg_volume_usd:float) -> ActionResult:
        xp_per_tx = self.p["xp"]["repeatables"]["swap_per_tx"]["xp_per_tx"]
        xp = swaps * xp_per_tx

        l2gas = self.p["fees"]["l2_gas_per_tx_usd"] * swaps
        dex_fee = avg_volume_usd * self.p["fees"]["dex_fee_pct"] * swaps
        price_impact = avg_volume_usd * self.p["fees"]["price_impact_pct"] * swaps
        cost = l2gas + dex_fee + price_impact

        volume = avg_volume_usd * swaps
        return ActionResult("swaps", xp, swaps, volume, cost)

    def volume_bonus_xp(self, daily_volume_usd:float) -> int:
        tiers = sorted(self.p["xp"]["repeatables"]["volume_bonus"]["tiers"], key=lambda t: t["min_usd"])
        xp = 0
        for t in tiers:
            if daily_volume_usd >= t["min_usd"]:
                xp = t["xp"]
        return xp

    def plan_to_reach(self, target_level:int, budget_usd:float, avg_swap_usd:float) -> Dict:
        target_xp = self.level_xp(target_level)
        base = self.base_quests_xp()
        remain = max(0, target_xp - base)

        swaps = 0
        actions: List[ActionResult] = []
        cost_total = 0.0
        xp_total = base

        max_per_day = self.p["xp"]["repeatables"]["swap_per_tx"]["max_per_day"]

        while xp_total < target_xp and cost_total <= budget_usd:
            batch = max_per_day
            ar = self.simulate_swaps(batch, avg_swap_usd)
            day_bonus = self.volume_bonus_xp(ar.volume_usd)
            bonus_ar = ActionResult("daily_volume_bonus", day_bonus, 0, ar.volume_usd, 0.0)

            if cost_total + ar.cost_usd > budget_usd:
                for s in range(batch-1, 0, -1):
                    ar_try = self.simulate_swaps(s, avg_swap_usd)
                    if cost_total + ar_try.cost_usd <= budget_usd:
                        ar = ar_try
                        bonus_ar = ActionResult("daily_volume_bonus",
                                                self.volume_bonus_xp(ar.volume_usd),
                                                0, ar.volume_usd, 0.0)
                        break
                else:
                    break

            actions.append(ar)
            actions.append(bonus_ar)
            cost_total += ar.cost_usd
            xp_total += ar.xp + bonus_ar.xp
            swaps += ar.txs

        return {
            "target_level": target_level,
            "target_xp": target_xp,
            "base_xp": base,
            "xp_total": xp_total,
            "swaps": swaps,
            "avg_swap_usd": avg_swap_usd,
            "cost_total_usd": round(cost_total, 2),
            "actions": [a.__dict__ for a in actions],
            "reached": xp_total >= target_xp
        }
