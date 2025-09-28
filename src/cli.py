import argparse, yaml
from tabulate import tabulate
from xp_calc import XPCalculator

def load_params(path="config/params.yml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def simulate(target_level:int, budget_usd:float, avg_swap_usd:float, params_path:str):
    p = load_params(params_path)
    calc = XPCalculator(p)
    result = calc.plan_to_reach(target_level, budget_usd, avg_swap_usd)

    headers = ["Action","XP","TXs","Volume USD","Cost USD"]
    rows = [[a["action"], a["xp"], a["txs"], round(a["volume_usd"],2), round(a["cost_usd"],2)]
            for a in result["actions"]]
    print(tabulate(rows, headers=headers, tablefmt="github"))
    print()
    print(tabulate([[
        result["target_level"], result["target_xp"],
        result["base_xp"], result["xp_total"], result["swaps"],
        result["avg_swap_usd"], result["cost_total_usd"], result["reached"]
    ]], headers=["Target Lvl","Target XP","Base XP","XP Total","Swaps",
                 "Avg Swap USD","Cost Total USD","Reached"], tablefmt="github"))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd")

    s = sp.add_parser("simulate", help="simulate plan to reach target level under budget")
    s.add_argument("--target-level", type=int, required=True)
    s.add_argument("--budget-usd", type=float, default=None)
    s.add_argument("--avg-swap-usd", type=float, default=1.00)
    s.add_argument("--params", type=str, default="config/params.yml")

    args = ap.parse_args()
    if args.cmd == "simulate":
        if args.budget_usd is None:
            p = load_params(args.params)
            args.budget_usd = float(p["usd_ref"]["default_budget_usd"])
        simulate(args.target_level, args.budget_usd, args.avg_swap_usd, args.params)
    else:
        print("Use: simulate --target-level 10 --budget-usd 50 --avg-swap-usd 1.0")
