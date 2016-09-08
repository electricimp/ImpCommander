#
# Helper script to perform bulk Imp device operations
#

import base64
import getopt
import json
import os
import sys

import requests

BUILD_API_KEY = ""
BUILD_API_URL = "https://build.electricimp.com/v4/"
IMP_AGENT_URL = "https://agent.electricimp.com/{}?{}"


def usage():
    print "Usage:                                                                                       \n" \
          "imp-commander ( -L                                                                           \n" \
          "              | -l --model=<model-name>                                                      \n" \
          "              | -p --model=<model-name> --agent=<agent-file> --device=<device-file>          \n" \
          "              | -m --model=<model-name> --device_ids-file=<device-ids>)                      \n" \
          "              | -M --model=<model-name>                                                      \n" \
          "              | -c --model=<model-name> --query=<query>                                      \n" \
          "  Where command options are:                                                                 \n" \
          "    -L: list all the unassigned device ids                                                   \n" \
          "    -l: list all the device ids for the model specified                                      \n" \
          "    -p: push the code to the model                                                           \n" \
          "    -m: move the specified devices to the model                                              \n" \
          "    -M: move all the unassigned devices to the model                                         \n" \
          "    -c: do HTTP request to all the agents of the specified model with the query specified    \n"


def base64encode(string):
    return base64.b64encode(string.encode()).decode()


def is_response_valid(response):
    return response.status_code in [
        requests.codes.ok,
        requests.codes.created,
        requests.codes.accepted
    ]


def get_http_headers():
    return {
        "Authorization": "Basic " + base64encode(BUILD_API_KEY),
        "Content-Type": "application/json"
    }


def get_model_by_name(model_name):
    return requests.get(BUILD_API_URL + "models?name=" + model_name, headers=get_http_headers())


def __get_model_device_ids(model_name):
    device_ids = []
    response = get_model_by_name(model_name)
    if is_response_valid(response):
        json_model = response.json()
        if len(json_model["models"]):
            for id in json_model["models"][0]["devices"]:
                device_ids.append(id)
        else:
            print("Found no model with name: " + model_name)

    else:
        print("Request to list models failed: " + response.status_code)

    return device_ids


def list_model_devices(model_name):
    check_model_name(model_name)
    device_ids = __get_model_device_ids(model_name)
    for id in device_ids:
        print(id)


def __get_unassigned_device_ids():
    result = []
    response = requests.get(BUILD_API_URL + "devices", headers=get_http_headers())
    if is_response_valid(response):
        devices_json = response.json()
        if len(devices_json["devices"]):
            devices = devices_json["devices"]
            for d in devices:
                # List only devices that have no model_id set
                if not d["model_id"]:
                    result.append(d["id"])
    else:
        print("Request retrieving the list of devices: " + response.status_code)
    return result


def list_unassigned_devices():
    device_ids = __get_unassigned_device_ids()
    for id in device_ids:
        print(id)


def check_file_exists(file_name, message):
    if not file_name or not os.path.exists(file_name):
        usage()
        print(message)
        exit(3)


def check_model_name(model_name):
    if not model_name:
        usage()
        print("Model name is not specified")
        exit(2)


def read_file(filename):
    with open(filename, 'r') as f:
        s = f.read()
    return s


def push_code(model_name, agent_code_file, device_code_file):
    check_model_name(model_name)
    check_file_exists(agent_code_file, "Please specify a valid agent code file")
    check_file_exists(device_code_file, "Please specify a valid device code file")

    agent_code = read_file(agent_code_file)
    device_code = read_file(device_code_file)

    model_json = get_model_by_name(model_name).json()
    if not len(model_json["models"]):
        print("Model not found")
        return

    model_id = model_json["models"][0]["id"]

    url = BUILD_API_URL + "models/" + model_id + "/revisions"
    data = '{"agent_code": ' + json.dumps(agent_code) + ', "device_code" : ' + json.dumps(device_code) + ' }'
    response = requests.post(url, data, headers=get_http_headers())

    if is_response_valid(response):
        print("Created new revision: " + str(response.json()["revision"]["version"]))
        # Restart the model
        requests.post(BUILD_API_URL + "models/" + model_id + "/restart", headers=get_http_headers())
    else:
        print("Code push failed: " + str(response.json()["error"]))


def get_existing_or_create_model(model_name):
    model_json = get_model_by_name(model_name).json()
    if not len(model_json["models"]):
        response = requests.post(BUILD_API_URL + "models/", '{"name" : "' + model_name + '" }',
                                 headers=get_http_headers())
        if not is_response_valid(response):
            print("Failed to create model: " + str(response))
            return
        model_id = response.json()["model"]["id"]
    else:
        model_id = model_json["models"][0]["id"]
    return model_id


def __move_devices_to_model(model_id, device_ids):
    for device_id in device_ids:
        response = requests.put(BUILD_API_URL + "devices/" + device_id, '{"model_id": "' + model_id + '"}',
                                headers=get_http_headers())
        if not is_response_valid(response):
            print("Failed to move device {} to model {}".format(device_id, model_id))


def move_devices_to_model(model_name, device_list_file):
    check_model_name(model_name)
    check_file_exists(device_list_file, "Please specify file with device ids")
    with open(device_list_file) as f:
        ids_read = [line.rstrip('\n') for line in f]
    __move_devices_to_model(get_existing_or_create_model(model_name), ids_read)


def move_unassigned_devices_to_model(model_name):
    check_model_name(model_name)
    __move_devices_to_model(get_existing_or_create_model(model_name), __get_unassigned_device_ids())


def call_agents(model_name, query):
    check_model_name(model_name)
    device_ids = __get_model_device_ids(model_name)

    for d_id in device_ids:
        response = requests.get(BUILD_API_URL + "devices/" + d_id, headers=get_http_headers()).json()
        agent_id = response["device"]["agent_id"]
        agent_url = IMP_AGENT_URL.format(agent_id, query)
        # call the agent
        print("Calling the agent: " + agent_url)
        requests.get(agent_url)


def main(args):
    opts = None
    try:
        opts, args = getopt.getopt(args, "lLpmMc", ["model=", "agent=", "device=", "device_ids-file=", "command="])
    except getopt.GetoptError as err:
        print str(err)
        usage()
        exit(2)

    if not BUILD_API_KEY:
        print("Please provide the Build API key (define BUILD_API_KEY constant)")
        exit(2)

    opts = dict(opts)

    model_name = opts["--model"] if "--model" in opts else None
    agent_code = opts["--agent"] if "--agent" in opts else None
    device_code = opts["--device"] if "--device" in opts else None
    device_list_file = opts["--device_ids-file"] if "--device_ids-file" in opts else None
    query = opts["--query"] if "--query" in opts else None

    if "-l" in opts:
        list_model_devices(model_name)
    elif "-L" in opts:
        list_unassigned_devices()
    elif "-p" in opts:
        push_code(model_name, agent_code, device_code)
    elif "-m" in opts:
        move_devices_to_model(model_name, device_list_file)
    elif "-M" in opts:
        move_unassigned_devices_to_model(model_name)
    elif "-c" in opts:
        call_agents(model_name, query)
    else:
        print("No command options specified")
        exit(2)

    exit(0)


if __name__ == "__main__":
    main(sys.argv[1:])
