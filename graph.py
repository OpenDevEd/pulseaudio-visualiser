import matplotlib.pyplot as plt
import networkx as nx
import os
from datetime import datetime
import re
from textwrap import fill

def create_audio_routing_graph(state, text_wrap=30, hide_list=None, ignore_list=None, only_active=False):
    if hide_list is None:
        hide_list = []
    if ignore_list is None:
        ignore_list = []

    def is_ignored(node):
        result = any(ignore_term in node['label'] for ignore_term in ignore_list)
        # print("perform node check: ", node['label'] , " -> ", result)
        return result

    G = nx.DiGraph()

    def add_node(node_id, data):
        label = get_node_label(data, hide_list)
        if only_active and data['state'] != 'running':
            return False
        if is_ignored(data):
            return False
        G.add_node(node_id, label=label+" "+str(node_id), type=data.get('type', 'unknown'), active=data.get('active', False))
        # G.add_node(node_id, label=label, type=data.get('type', 'unknown'), active=data.get('active', False))
        # print( f"Added node: {node_id}, label: {label}, type: {data.get('type', 'unknown')}")
        return True

    node_id_map = {}
    idx = 0


    state_keys = {
        'sinks': 'Output Devices',
        'sources': 'Input Devices',
        'sink_inputs': 'Playback',
        'source_outputs': 'Recording'
    }

    for key, description in state_keys.items():
        for node, data in state[key].items():
            # print(f"{key} = {description}: ", node)
            nodekey = key + "_" + str(node)
            if (add_node(nodekey, data)):
                node_id_map[nodekey] = idx
                idx += 1

    # print(node_id_map)


    # Adding edges
    connection_keys = {
        'sink_inputs': ('input', 'sink'),
        'source_outputs': ('output', 'source')
    }

    added_edges = {}
    # print(f"Connections: {state['connections']}")
    for key, (from_key, to_key) in connection_keys.items():
        # print(f"Key: {key}, from_key: {from_key}, to_key: {to_key}")
        # Key: source_outputs, from_key: output, to_key: source
        for conn in state['connections'][key]:
            # print(f" -> Connection: {conn}")
            #  -> Connection: {'input': 996, 'sink': 23}
            #  Added edge from sink_inputs_996 to sink_inputs_23
            from_id = key + "_" + str(conn[from_key])
            to_id = to_key + "s_" + str(conn[to_key])
            if from_id is not None and to_id is not None:
                if from_id in node_id_map and to_id in node_id_map:
                    if (from_id, to_id) in added_edges:
                        print( f"Connection: Spurious edge from {from_id} to {to_id}")
                        continue
                    if (to_id, from_id) in added_edges:
                        print(f"Spurious edge from {from_id} to {to_id}")
                        continue
                    G.add_edge(from_id, to_id)
                    added_edges[(from_id, to_id)] = True
                    print(f"Connection: edge from {from_id} to {to_id}")
                else:
                    print(f"Connection: Spurious edge from {from_id} to {to_id}")
            else:
                print(f"NOT adding edge from {conn[from_key]} to {conn[to_key]}")


    allnodes = list(G.nodes)  # Convert to list to avoid runtime error
    edges_to_add = []
    checkloops = {}

    for node in allnodes:
        for target in allnodes:
            if node != target:
                node_label = re.sub(r'\S+$', '', G.nodes[node].get('label', ''))
                target_label = re.sub(r'\S+$', '', G.nodes[target].get('label', ''))
                # if 'Monitor of' in node_label and node_label.replace('Monitor of ', '') in target_label:
                if re.match(r'^Monitor of ', node_label) and node_label.replace('Monitor of ', '') == target_label:
                    print("Monitor connection: ", node, target)
                    from_id = node  # Assuming from_id is node
                    to_id = target  # Assuming to_id is target
                    edges_to_add.append((from_id, to_id))
                else:
                    pass
                    # if "sinks_139" in node and "sources_142" in target:
                    #     print("No monitor connection: ", node, target)
                    #     print(node_label, target_label)
 
                if re.match(r'^\s*L\d ', node_label): # and re.match(r'^L\d ', target_label):
                    # print("                 ", node_label, target_label)
                    #loopback = re.sub(r'^\s*(L\d) .*?$', r'\1', node_label)
                    loopback = re.sub(r'^\s*', '', node_label)
                    loopback = re.sub(r' .*$', '', loopback, flags=re.DOTALL)
                    # print("LB=",loopback,"-")
                    if loopback in checkloops:
                        pass
                    else:
                        if target_label.startswith(loopback):
                            print("Loop connection: ", node, target)
                            print("                 ", node_label, target_label)
                            from_id = node  # Assuming from_id is node
                            to_id = target  # Assuming to_id is target
                            edges_to_add.append((from_id, to_id))
                            checkloops[loopback] = True

    # Add edges after iteration
    for from_id, to_id in edges_to_add:
        G.add_edge(from_id, to_id)
                                

    # print(f"Nodes in graph: {G.nodes(data=True)}")
    # print(f"Edges in graph: {G.edges(data=True)}")

    return G

# def add_dotted_edges(G):
#     dotted_edges = []
#     for node in G.nodes:
#         for target in G.nodes:
#             if node != target:
#                 if 'Monitor of' in G.nodes[node].get('label', '') and G.nodes[node].get('label').replace('Monitor of ', '') in G.nodes[target].get('label', ''):
#                     print("Dotted: ",node, target)
#                     dotted_edges.append((node, target))
#     return dotted_edges


def update_graph(G, ax, fig, pos, last_update_time, only_active=False, spring_layout = True):
    labeloffset = 0.5
    ax.clear()
    node_labels = nx.get_node_attributes(G, 'label')
    wrapped_labels = wrap_labels(node_labels, 30)  # Adjust the width as needed

    node_colors = [
        'grey' if not G.nodes[node].get('active', False) else get_node_color(
            G.nodes[node].get('type', 'unknown'))
        for node in G.nodes
    ]
    node_sizes = [
        500 if G.nodes[node].get('active', False) else 200
        for node in G.nodes
    ]

    # Generate initial positions using spring layout
    initial_pos = nx.spring_layout(G, seed=42)

    pos = {}
    x_offset = {'sink_input': 0, 'sink': 1,
                'source': 2, 'source_output': 3, 'unknown': 4}

    # Collect nodes by type and sort them alphabetically by label
    nodes_by_type = {'sink_input': [], 'sink': [],
                     'source': [], 'source_output': [], 'unknown': []}
    for node, data in G.nodes(data=True):
        node_type = data.get('type', 'unknown')
        nodes_by_type[node_type].append((node, data))

    for node_type in nodes_by_type:
        nodes_by_type[node_type].sort(key=lambda x: x[1].get('label', ''))

    y_positions = {node_type: 0 for node_type in nodes_by_type.keys()}
    placed_positions = set()

    def get_unique_position(x, y):
        while (x, y) in placed_positions:
            y -= 1
        placed_positions.add((x, y))
        return (x, y)

    
    for node_type, nodes in nodes_by_type.items():
        for node, data in nodes:
            if spring_layout and node in initial_pos:
                x = x_offset[node_type]
                # Scale the y-coordinate to avoid overlaps
                y = initial_pos[node][1] * 10
                pos[node] = get_unique_position(x, y)
            else:
                pos[node] = get_unique_position( x_offset[node_type], y_positions[node_type])
                y_positions[node_type] -= 1

    if spring_layout:
        for node_type, nodes in nodes_by_type.items():
            column_nodes = [node for node, _ in nodes]
            if column_nodes:
                min_y = min(pos[node][1] for node in column_nodes)
                max_y = max(pos[node][1] for node in column_nodes)
                step = (max_y - min_y) / (len(column_nodes) - 1) if len(column_nodes) > 1 else 0
                for i, node in enumerate(sorted(column_nodes, key=lambda n: pos[n][1])):
                    # print(x_offset[node_type], min_y + i * step)
                    pos[node] = (x_offset[node_type], min_y + i * step)
                
    # nx.draw(G, pos, ax=ax, labels=wrapped_labels, node_color=node_colors,
    #         node_size=node_sizes, font_size=14, font_weight='bold', edge_color='gray', edgelist=[])

    # Draw the nodes with custom positioning
    nx.draw(G, pos, ax=ax, node_color=node_colors, node_size=node_sizes, font_size=14, font_weight='bold', edge_color='gray', edgelist=[])
    # Draw the labels with an offset
    label_pos = {node: (pos[node][0], pos[node][1] + labeloffset) for node in G.nodes()}
    nx.draw_networkx_labels( G, label_pos, labels=wrapped_labels, font_size=14, font_weight='bold')

    # Draw edges with specific styles
    edge_colors = []
    edges_to_reverse = []

    for source, target in G.edges:
        source_x, _ = pos[source]
        target_x, _ = pos[target]
        if (source_x == 3 and target_x == 2) or (source_x == 2 and target_x == 1) or (source_x == 0 and target_x == 3):
            edges_to_reverse.append((source, target))

    for source, target in edges_to_reverse:
        G.remove_edge(source, target)
        G.add_edge(target, source)

    for source, target in G.edges:
        source_x, _ = pos[source]
        target_x, _ = pos[target]
        if source_x == 0 and target_x == 1:
            edge_colors.append('red')
        elif source_x == 1 and target_x == 2:
            edge_colors.append('green')
        elif source_x == 2 and target_x == 3:
            edge_colors.append('orange')
        else:
            edge_colors.append('lightgray')

    # print(G.nodes(data=True))
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color=edge_colors, width=2, connectionstyle='arc3, rad=0.2', arrows=True, arrowsize=30)

    update_text = f"Last update: {last_update_time.strftime('%Y-%m-%d %H:%M:%S')}"
    ax.text(0.95, 0.01, update_text, horizontalalignment='right', verticalalignment='bottom', transform=ax.transAxes, fontsize=10, color='gray')

    column_labels = [
        ("Playback\n(Sink Inputs)", 0),
        ("Output Devices\n(Sinks)", 1),
        ("Input Devices\n(Sources)", 2),
        ("Recording\n(Source Outputs)", 3)
    ]

    top_edge_y, top_edge_y = ax.get_ylim()
    for label, x in column_labels:
        ax.text(x, top_edge_y, label, horizontalalignment='center', verticalalignment='top', fontsize=12, color='black')

    for x in range(4):
        ax.axvline(x=x, color='gray', linestyle='--', linewidth=0.5)
        # ax.text(x, top_edge_y-1, f"{x}", horizontalalignment='center', verticalalignment='top', fontsize=24, color='black')

    fig.canvas.draw_idle()
    return pos


def wrap_text(text, width):
    return '\n'.join(text[i:i+width] for i in range(0, len(text), width))


def remove_strings_from_labels(label, hide_list):
    for hide_str in hide_list:
        label = label.replace(hide_str, '')
    return label

def get_node_label(node, hide_list):
    if isinstance(node, dict):
        label = node.get('label', 'Unknown')
    else:
        label = node.proplist.get('application.name', 'Unknown') if hasattr(
            node, 'proplist') else node.description
    label = remove_strings_from_labels(label, hide_list)
    return label

def shortLabel(string):
    string = re.sub(r'sources_(\d+)$', r'sr.\1', string)
    string = re.sub(r'sinks_(\d+)$', r'sn.\1', string)
    string = re.sub(r'sink_inputs_(\d+)$', r'SI.\1', string)
    string = re.sub(r'source_outputs_(\d+)$', r'SO.\1', string)
    return string

def wrap_labels(labels, width):
    return {node: fill(shortLabel(label), width) for node, label in labels.items()}

# def apply_spring_layout(G):
#     # Generate initial positions using spring layout
#     pos = nx.spring_layout(G, seed=42)

#     # Ensure nodes are placed in specific columns based on their types
#     x_offset = {'sink_input': 0, 'sink': 1,
#                 'source': 2, 'source_output': 3, 'unknown': 4}
#     y_positions = {node_type: 0 for node_type in x_offset.keys()}
#     placed_positions = set()

#     def get_unique_position(x, y):
#         while (x, y) in placed_positions:
#             y -= 1
#         placed_positions.add((x, y))
#         return (x, y)

#     nodes_by_type = {'sink_input': [], 'sink': [],
#                      'source': [], 'source_output': [], 'unknown': []}

#     for node, data in G.nodes(data=True):
#         node_type = data.get('type', 'unknown')
#         nodes_by_type[node_type].append((node, data))

#     for node_type in nodes_by_type:
#         nodes_by_type[node_type].sort(key=lambda x: x[1].get('label', ''))

#     for node_type, nodes in nodes_by_type.items():
#         for node, data in nodes:
#             pos[node] = get_unique_position(
#                 x_offset[node_type], y_positions[node_type])
#             y_positions[node_type] -= 1

#     return pos


def save_graph_figure(G, pos, directory):
    if not os.path.exists(directory):
        os.makedirs(directory)
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    plt.savefig(os.path.join(directory, f'graph_{timestamp}.png'))


def get_node_color(node_type):
    return {
        'sink': 'lightblue',
        'source': 'lightgreen',
        'sink_input': 'lightcoral',
        'source_output': 'yellow',
        'unknown': 'grey'
    }.get(node_type, 'grey')



if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Visualize PulseAudio routing.")
    parser.add_argument('--text_wrap', type=int, default=30,
                        help='Number of characters after which to wrap text labels.')
    parser.add_argument('--hide', nargs='+', default=[],
                        help='List of strings to hide from graph labels.')
    parser.add_argument('--ignore', nargs='+', default=[],
                        help='List of strings to ignore from audio sources and sinks.')
    parser.add_argument('--active', action='store_true',
                        help='Only show active elements in the graph.')
    args = parser.parse_args()

    plt.ion()
    # Double the size of the initial window
    fig, ax = plt.subplots(figsize=(20, 10))
    pos = None

    latest_json_file = sorted([f for f in os.listdir(
        './graphs') if f.startswith('state_')], reverse=True)[0]
    with open(os.path.join('./graphs', latest_json_file), 'r') as f:
        state = json.load(f)

    G = create_audio_routing_graph(state, text_wrap=args.text_wrap,
                                   hide_list=args.hide, ignore_list=args.ignore, only_active=args.active)
    pos = update_graph(G, ax, fig, pos, datetime.now(), only_active=args.active)
    save_graph_figure(G, pos, './graphs')
    plt.show()

