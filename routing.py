import pulsectl
import json
from datetime import datetime
import os
import re

def fetch_node_state(string):
    return str(string).split( '=')[-1].strip('>') 

def get_node_data(node, node_type):
    # Extract properties from node
    active = node.state == pulsectl.PulseStateEnum.running if hasattr(node, 'state') else False
    
    # Prioritize application name if available
    app_name = node.proplist.get('application.name', None) if hasattr(node, 'proplist') else None
    label = app_name if app_name else (getattr(node, 'description', '') or getattr(node, 'name', 'Unnamed Node'))
    
    # Extract the actual state without the EnumValue representation
    state = "unknown"
    if hasattr(node, 'state'):
        if hasattr(node.state, 'name'): 
            state = fetch_node_state(node.state.name) 
        else:
            state = str(node.state)
    else:
        state = "unknown"
        active = True
    
    # Include more detailed information if available
    additional_info = {}
    if hasattr(node, 'proplist'):
        for key, value in node.proplist.items():
            additional_info[key] = value

    return {
        "active": active,
        "type": node_type,
        "label": label,
        "state": state,
        "additional_info": additional_info  # Store additional info if available
    }


def get_audio_routing(pulse):
    sinks = pulse.sink_list()
    sources = pulse.source_list()
    sink_inputs = pulse.sink_input_list()
    source_outputs = pulse.source_output_list()

    return sinks, sources, sink_inputs, source_outputs


def normalize_state(state):
    normalized = {
        "sinks": {idx: get_node_data(sink, "sink") for idx, sink in state["sinks"].items()},
        "sources": {idx: get_node_data(source, "source") for idx, source in state["sources"].items()},
        "sink_inputs": {idx: get_node_data(sink_input, "sink_input") for idx, sink_input in state["sink_inputs"].items()},
        "source_outputs": {idx: get_node_data(source_output, "source_output") for idx, source_output in state["source_outputs"].items()},
        "connections": {
            "sink_inputs": [{"input": conn["input"], "sink": conn["sink"]} for conn in state["connections"]["sink_inputs"]],
            "source_outputs": [{"output": conn["output"], "source": conn["source"]} for conn in state["connections"]["source_outputs"]]
        }
    }
    return normalized


def generate_audio_state_json(pulse, previous_state=None, directory="./graphs"):
    sinks, sources, sink_inputs, source_outputs = get_audio_routing(pulse)

    state = {
        "sinks": {sink.index: get_node_data(sink, "sink") for sink in sinks},
        "sources": {source.index: get_node_data(source, "source") for source in sources},
        "sink_inputs": {sink_input.index: get_node_data(sink_input, "sink_input") for sink_input in sink_inputs},
        "source_outputs": {source_output.index: get_node_data(source_output, "source_output") for source_output in source_outputs},
        "connections": {
            "sink_inputs": [{"input": sink_input.index, "sink": sink_input.sink} for sink_input in sink_inputs],
            "source_outputs": [{"output": source_output.index, "source": source_output.source} for source_output in source_outputs]
        }
    }

    normalized_state = normalize_state(state)
    has_changed = previous_state is None or normalized_state != normalize_state(previous_state)

    state["has_changed"] = has_changed
    state["changed_items"] = {
        "sinks": [idx for idx in state["sinks"] if previous_state is None or previous_state["sinks"].get(idx) != state["sinks"][idx]],
        "sources": [idx for idx in state["sources"] if previous_state is None or previous_state["sources"].get(idx) != state["sources"][idx]],
        "sink_inputs": [idx for idx in state["sink_inputs"] if previous_state is None or previous_state["sink_inputs"].get(idx) != state["sink_inputs"][idx]],
        "source_outputs": [idx for idx in state["source_outputs"] if previous_state is None or previous_state["source_outputs"].get(idx) != state["source_outputs"][idx]]
    }


    loopbacks = ['sink_inputs', 'source_outputs']
    for key in loopbacks:
        i=0
        for idx in state[key]:
            if re.match("^Loopback", state[key][idx]['label']):
                i += 1
                #print(f"Loopback detected: {state[key][idx]['label']}")
                state[key][idx]['label'] = "L" + str(i) + " " + state[key][idx]['label']

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    json_path = os.path.join(directory, f'state_{timestamp}.json')

    # with open(json_path, 'w') as f:
    #     json.dump(state, f, indent=4)

    # print(f"Saved state to {json_path}")

    return state


if __name__ == "__main__":
    pulse = pulsectl.Pulse('audio-routing-visualizer')
    generate_audio_state_json(pulse)
