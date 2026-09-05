"""Dataset 02: investor-level GL -> loader migration.

A fund-accounting-system migration with, until now, zero code checking it. See
`02-investor-level-gl-to-loader/README.md` (in the hackathon data folder, not this repo)
for what the migration actually did and the gaps its own administrator already flagged.

`load.py` reads the two source workbooks into plain lists-of-dicts. `analyze.py` turns
those into `Flag`s using the same contract as `src/checks/`.
"""
