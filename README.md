# gta6-twitch-forecast

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/ko1216-lild/gta6-twitch-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/ko1216-lild/gta6-twitch-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

# gta6-twitch-ccu-forecast-01 — entry

A forecasting program for make.fun's bounty *gta6-twitch-ccu-forecast-01*.
`main.py` (Python 3.13, standard library only, no network) reads one case
file from the input directory — everything recorded about a game's Twitch
category up to the end of hour 1 of its release day, that hour's viewer count
included — and writes, for each of hours 2–24 of the day (UTC), five
quantiles (5%, 25%, 50%, 75%, 95%) of that hour's concurrent live viewers.
The final case is Grand Theft Auto VI's release day, 2026-11-19; the score
is the mean pinball loss on the log scale over all hours and quantiles.

## Method

A launch day is forecast as a **ratio curve to the day's own first hour**,
whose count the case hands us. The level is therefore set by the actual
launch; the program's job is the shape and the spread.

1. **Library.** Each case carries dozens of past big launches
   ("comparables") with their hourly viewer curves from 14 days before to 3
   days after their release days (SullyGnome's hourly Twitch category
   averages, as packaged in the competition kit). From each comparable the
   program extracts its release-day curve and the log-ratios
   `ln(viewers_h / viewers_1)`.
2. **Filters, matched to this launch.** GTA VI unlocks at midnight local
   time, rolling country by country (New Zealand first, the US last), is
   console-only, and has no early access. The library keeps only launches
   whose day has that shape:
   - a comparable whose release-day peak is more than 20× its hour-1 count
     is dropped — its hour 1 was a pre-launch trickle before a single
     worldwide unlock time, a different event from a rolling launch whose
     first hour is already live in several regions;
   - comparables the case's own research stamps "early-access-contaminated"
     are dropped: their release days are flattened by days of prior access
     (Hogwarts Legacy's record audience arrived in early access, three days
     before its release day), and this game has no early access;
   - the research's "weak" analogues (a free-to-play live-service launch, a
     slow-burn launch) and the target category's own pre-release history
     are dropped, as is the case's own game;
   - a comparable needs an hour-1 count and at least 18 of the day's 24
     hours to enter.
3. **Distribution per hour.** Log-ratios are winsorised to [−1.6, +2.6],
   then each hour's weighted mean and standard deviation are taken across
   the library (weight 1.0 for the research's "comparable" tier, 0.7 for
   untiered entries), smoothed over neighbouring hours, and the spread is
   floored at 0.35 and capped at 1.15 in log units — no hour is forecast
   more confidently than big launches ever agree with each other.
4. **Quantiles.** `q_tau(h) = p1 · exp(mean_h + z_tau · sd_h)` with `p1` the
   case's hour-1 count and `z` the standard normal quantiles. The forecast
   is a pure function of the case file: two runs write identical bytes.

The resulting shape (medians, as a ratio to hour 1): a dip to ≈0.75–0.85 in
hours 2–4 (the first-hour regions rotate out before Europe's day and the US
unlocks build), a climb through the day, a peak of ≈2.5 around hour 20
(19:00–20:00 UTC, the Europe–US prime-time overlap), and a gentle decline
into hour 24 — with a wide, honest band (the 95% quantile sits ≈12× the 5%
at peak hours), because realised launches with the same first hour have
peaked anywhere from 1.3× to 9× it.

## Sources

- **Case data (what the program actually reads):** the competition kit's
  case files — SullyGnome.com hourly Twitch category averages for the
  practice launches and the 38–42 comparables, quoted with attribution in
  the kit's `input/NOTICE.txt`; the final case's history and hour-1 count
  are make.fun's own per-minute reads of Twitch's public directory count
  for the Grand Theft Auto VI category (game id 1867279146).
- **Validation answers:** SullyGnome's published hourly "Average viewers"
  for the four practice release days, fetched through the API the kit's
  NOTICE documents (four requests, one per game). Their hour-1 values
  reproduce the cases' `known` rows exactly.
- **Context for scale:** Hogwarts Legacy reached 1.28M peak concurrent
  Twitch viewers at launch — the largest single-player audience in
  Twitch's history — surpassing Cyberpunk 2077's ≈1.14M (Warner Bros.
  Games press release, 23 Feb 2023, via Business Wire; Prima Games,
  8 Feb 2023). GTA VI's own hype is larger still: Trailer 1 drew ≈93M
  YouTube views in 24 hours (a Guinness World Record) and Trailer 2 drew
  475M views in 24 hours across platforms, which Rockstar called the
  biggest video launch of all time (Rockstar via The Hollywood Reporter,
  May 2025). The forecast does not use these figures as inputs — it is
  scale-free and keys off the real hour-1 count — they are why the spread
  is kept wide rather than tuned to the comparables' typical size.

## Assumptions

- Release-day *shapes* (ratios to hour 1) transfer across big launches once
  the unlock pattern and early access are matched; the level does not need
  to transfer, because hour 1 supplies it.
- After winsorising, an hour's log-ratios across launches are close enough
  to normal that normal quantiles of their mean and spread are calibrated;
  the 0.35 floor prices in that GTA VI is bigger than every comparable.
- The hour-1 count is a clean anchor: in the final it is the mean of a
  full hour of per-minute reads, not a single sample.

## Local validation (practice cases)

Scored with the contest's own rule (mean pinball loss on the log scale)
against the SullyGnome answers above:

| case | launch | this entry | house baseline |
|---|---|---|---|
| p00 | Marvel's Wolverine (2026-09-15) | 0.405 | 0.744 |
| p01 | Red Dead Redemption 2 (2018-10-26) | 0.175 | 0.287 |
| p02 | God of War Ragnarök (2022-11-09) | 0.202 | 0.215 |
| p03 | Marvel's Spider-Man 2 (2023-10-20) | 0.222 | 0.303 |
| **mean** | | **0.251** | **0.387** |

Typical miss 47.8%; 90% coverage 0.95. The baseline figures reproduce the
kit's published practice result for the house baseline (loss ≈ 0.387),
which cross-checks the local scorer. As the rules themselves warn, a
practice score is no guide to the final: the final is one day, one draw.

## Running

```
mkdir -p out
MAKEFUN_INPUT_DIR=<dir with .in files> MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Writes one `<id>.out` per `<id>.in`, each a single `{"hours": [...]}` JSON
object of 23 rows (hours 2–24), at most 65,536 bytes. Runs in ≈0.1 s per
case on one CPU, far inside the 8-second cap, and needs nothing beyond the
Python 3.13 standard library.
