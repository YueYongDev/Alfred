
import sys
import os
from pprint import pprint

# Add project root to path
sys.path.append(os.getcwd())

from agents.main_chat_agent import get_agent_metadata

try:
    metadata = get_agent_metadata()
    print("--- Agents Metadata ---")
    for agent in metadata['agents']:
        print(f"Agent: {agent['name']}")
        print(f"Tools found: {len(agent['tools'])}")
        for t in agent['tools']:
            print(f"  - {t['name']}")
        print("-" * 20)
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
