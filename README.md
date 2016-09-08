ImpCommander
=================================

The helper script to perform bulk Imp device operations.

## Requirements

The script requires Python 3.0+

## Usage

Please define BUILD_API_KEY constant with your Electric Imp Build API Key.

### Command Line Options

```
Usage:
imp-commander ( -L
              | -l --model=<model-name>
              | -p --model=<model-name> --agent=<agent-file> --device=<device-file>
              | -m --model=<model-name> --device_ids-file=<device-ids>
              | -M --model=<model-name>
              | -c --model=<model-name> --query=<query> )
  Where command options are:
    -L: list all the unassigned device ids
    -l: list all the device ids for the model specified
    -p: push the code to the model
    -m: move the specified devices to the model
    -M: move all the unassigned devices to the model
    -c: do HTTP request to all the agents of the specified model with the query specified
```
