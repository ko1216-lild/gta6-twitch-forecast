"""Entry for make.fun's gta6-twitch-ccu-forecast-01 (Python 3.13, standard library only).

The program reads one case file per run from the input directory and writes,
for each case, the five quantiles (5%, 25%, 50%, 75%, 95%) of the Twitch
viewer count of the case's game category for hours 2..24 of its release day.

Method, in one paragraph: a launch day's shape is forecast as a ratio to the
day's first hour, whose count the case gives. Every case carries the hourly
curves of dozens of past big launches ("comparables"); from the ones whose
first hour was already a real launch hour (a rolling midnight unlock like
this game's, not a single worldwide unlock time still hours away) and whose
launch this game actually resembles (no early access — this game has none,
and an early-access launch's release day is flattened by days of prior
access; not the case's own research's "weak" analogues either) the program
builds, for each hour h, the distribution of ln(viewers_h / viewers_1)
across launches. The forecast for hour h is the case's own hour-1 count times
a lognormal with that distribution's weighted mean and spread, the spread
floored so no hour is ever forecast more confidently than launches ever
agree, and both curves smoothed over neighbouring hours. Everything is a
pure function of the case file: two runs on the same case write the same
bytes.

Run by the grader as `python3 /bot/main.py` with the case in /input and the
forecast going to /output; MAKEFUN_INPUT_DIR / MAKEFUN_OUTPUT_DIR override
the two directories for a local run.
"""

import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
# Standard normal quantiles at LEVELS.
Z = [-1.644854, -0.674490, 0.0, 0.674490, 1.644854]

# A comparable whose release-day peak is more than this many times its own
# hour-1 count did not really launch in its hour 1 (a single simultaneous
# unlock later in the UTC day, with hour 1 a pre-launch trickle): its ratios
# describe a different event, so it leaves the library.
PEAK_RATIO_CAP = 20.0
# Log-ratios are winsorised to this band before their mean and spread are
# taken, so one freak launch cannot drag an hour's whole distribution.
LOG_RATIO_BAND = (-1.6, 2.6)
# Per-tier library weights, read from the tier the case's own research notes
# stamp on each comparable ("Tier: ..." inside its unlock text).
TIER_WEIGHTS = {
    "comparable": 1.0,
    "early-access-contaminated": 0.0,
    "weak": 0.0,
    "target-history": 0.0,
}
DEFAULT_TIER_WEIGHT = 0.7
# No hour's spread is narrower than this, however well launches agree there:
# the target launch is bigger than every comparable and its day is one draw.
SIGMA_FLOOR = 0.35
SIGMA_CAP = 1.15


def tier_of(comp: dict) -> str:
    """The tier word the case's research stamped on a comparable, if any."""
    text = comp.get("unlock") or ""
    marker = "Tier:"
    at = text.find(marker)
    if at < 0:
        return ""
    word = text[at + len(marker):].strip().split(" ", 1)[0].strip(".").lower()
    return word


def release_day_curve(comp: dict) -> dict:
    """{hour 1..24: viewers} of a comparable's own release day (UTC)."""
    day = (comp.get("day_start") or "")[:10]
    curve = {}
    for point in comp.get("hourly") or []:
        stamp = point.get("from") or ""
        if stamp[:10] == day and point.get("viewers"):
            curve[int(stamp[11:13]) + 1] = float(point["viewers"])
    return curve


def build_library(case: dict) -> list:
    """Weighted log-ratio curves ln(viewers_h / viewers_1) of usable launches.

    Returns a list of (weight, {hour: log ratio}) — one entry per comparable
    whose release day is complete enough and whose first hour was a launch
    hour. The case's own game and the target's pre-release history (a
    "comparable" whose day is not a launch at all) never enter the library.
    """
    own_name = (case.get("game") or {}).get("name")
    library = []
    for comp in case.get("comparables") or []:
        if comp.get("name") == own_name:
            continue
        weight = TIER_WEIGHTS.get(tier_of(comp), DEFAULT_TIER_WEIGHT)
        if weight <= 0.0:
            continue
        curve = release_day_curve(comp)
        first = curve.get(1)
        if not first or len(curve) < 18:
            continue
        if max(curve.values()) / first > PEAK_RATIO_CAP:
            continue
        log_first = math.log(first)
        ratios = {h: math.log(v) - log_first for h, v in curve.items() if v > 0}
        library.append((weight, ratios))
    return library


def hour_stats(library: list, hour: int) -> tuple:
    """Weighted (mean, sd) of the library's log-ratios at one hour."""
    xs, ws = [], []
    lo, hi = LOG_RATIO_BAND
    for weight, ratios in library:
        if hour in ratios:
            xs.append(min(hi, max(lo, ratios[hour])))
            ws.append(weight)
    if not xs:
        return 0.0, 0.15 * math.sqrt(hour - 1)
    total = sum(ws)
    mean = sum(w * x for w, x in zip(ws, xs)) / total
    var = sum(w * (x - mean) ** 2 for w, x in zip(ws, xs)) / total
    return mean, math.sqrt(var)


def smoothed(values: list) -> list:
    """A 3-wide moving average over the hour axis (edges keep their value)."""
    out = []
    for i, v in enumerate(values):
        near = [values[j] for j in (i - 1, i, i + 1) if 0 <= j < len(values)]
        out.append(sum(near) / len(near))
    return out


def round2(x: float) -> float:
    """Round to 2 decimals, half up; whole numbers stay whole in the JSON."""
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if float(value).is_integer() else value


def forecast_case(case: dict) -> dict:
    first = next((k for k in case["known"] if k["hour"] == 1), None)
    if first is None:
        raise ValueError("case has no hour-1 print")
    p1 = max(1.0, float(first["viewers"]))
    hours = [row["hour"] for row in case["forecast"]]
    library = build_library(case)
    means, spreads = [], []
    for h in hours:
        mean, sd = hour_stats(library, h)
        means.append(mean)
        spreads.append(min(SIGMA_CAP, max(SIGMA_FLOOR, sd)))
    means = smoothed(means)
    spreads = smoothed(spreads)
    rows = []
    for h, mean, sd in zip(hours, means, spreads):
        centre = math.log(p1) + mean
        q = [round2(math.exp(centre + z * sd)) for z in Z]
        q = [min(1_000_000_000.0, max(0.01, float(v))) for v in q]
        q.sort()
        rows.append({"hour": h, "q": q})
    return {"hours": rows}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        result = forecast_case(case)
        text = json.dumps(result, separators=(",", ":")) + "\n"
        (OUTPUT_DIR / f"{path.stem}.out").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
