import argparse
import json
import os
from datetime import datetime
import matplotlib.pyplot as plt
import pulsectl
from routing import get_audio_routing, generate_audio_state_json
from graph import create_audio_routing_graph, update_graph, save_graph_figure
import time
import sys
import signal

def signal_handler(sig, frame):
    print('You pressed Ctrl-C! Exiting gracefully...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)


def save_audio_state_to_file(state, directory):
    if not os.path.exists(directory):
        os.makedirs(directory)
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    file_path = os.path.join(directory, f'state_{timestamp}.json')
    with open(file_path, 'w') as f:
        json.dump(state, f, indent=4)
    return file_path


def main():
    parser = argparse.ArgumentParser( description="Visualize PulseAudio routing.")
    parser.add_argument('--text_wrap', type=int, default=30,
                        help='Number of characters after which to wrap text labels.')
    parser.add_argument('--hide', nargs='+', default=[],
                        help='List of strings to hide from graph labels.')
    parser.add_argument('--ignore', nargs='+', default=[],
                        help='List of strings to ignore from audio sources and sinks.')
    parser.add_argument('--active', action='store_true',
                        help='Only show active elements in the graph.')
    parser.add_argument('--alpha', action='store_true',
                        help='Sort nodes alphabetically, rather than with minimised edge crossings.', default=False)
    args = parser.parse_args()

    print(f"Ignoring applications containing: {args.ignore}")
    print(f"Hiding strings: {args.hide}")

    plt.ion()
    # Double the size of the initial window
    fig, ax = plt.subplots(figsize=(20, 10))
    pos = None
    last_update_time = datetime.now()
    previous_state = None

    with pulsectl.Pulse('pulseaudio-routing-visualizer') as pulse:
        while True:
            current_state = generate_audio_state_json(pulse, previous_state=previous_state)

            # Only update the graph if the audio configuration changes
            if current_state["has_changed"]:
                # Save the state to a file
                state_file_path = save_audio_state_to_file(current_state, './graphs')
                print(f"Saved state to {state_file_path}")

                G = create_audio_routing_graph(current_state, text_wrap=args.text_wrap, hide_list=args.hide, ignore_list=args.ignore, only_active=args.active)

                pos = update_graph( G, ax, fig, pos, datetime.now(), only_active=args.active, spring_layout=not(args.alpha))
                save_graph_figure(G, pos, './graphs')

                previous_state = current_state
                last_update_time = datetime.now()

            # Update every second without bringing the window to the front
            fig.canvas.start_event_loop(1)


if __name__ == "__main__":
    main()
