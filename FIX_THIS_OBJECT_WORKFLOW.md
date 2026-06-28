# Fix This Object Workflow

## Implemented in v54
- repair planning service
- `/v1/fix-object/plan` endpoint
- mobile Fix This Object screen
- quick repair actions for broken functional parts

## Purpose
Turn broken real-world objects into repair-ready, printable replacements.

## Current behavior
- identify broken part family
- infer likely failure region
- recommend replacement family
- recommend material
- create Object DNA repair record
- suggest quick actions:
  - Generate replacement
  - Strengthen automatically
  - Resize fit
  - Print nearby

## Next steps
- connect camera live detection directly into Fix This Object
- push generated repair Object DNA into draft/edit flow
- add fit-tolerance controls
- add printer quote submission
