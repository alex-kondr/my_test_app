import json
from pathlib import Path
import argparse
import os
import sys
import warnings

# python c:\Users\user\Documents\GitHub\my_test_app\product_test\format_emits.py "c:\Users\user\Documents\GitHub\my_test_app\reviews.mein-gartenexperte.de\reviews.mein-gartenexperte.de.txt" 12345
# Після цього буде створено відформатований agent-12345.json у папці product_test/emits/, готовий до використання у ваших тестах
# Add parent directory to path to import functions
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from product_test.functions import get_agent_name, get_old_agent

# --- Parser for 'EMIT: Product(...)' format ---

# Define dummy classes for eval(). Their purpose is to capture the kwargs
# from the string representation of the objects.
class ReprAsDict:
    def __init__(self, *args, **kwargs):
        self.data = kwargs

# Helper function to recursively convert the dummy objects into dictionaries.
def to_dict(obj):
    if isinstance(obj, ReprAsDict):
        return {k: to_dict(v) for k, v in obj.data.items()}
    elif isinstance(obj, list):
        return [to_dict(item) for item in obj]
    else:
        return obj

# Create aliases for all class names found in the data.
# This is necessary for the eval() call to succeed.
Product = ReprAsDict
ProductProperty = ReprAsDict
Review = ReprAsDict
Person = ReprAsDict
ReviewProperty = ReprAsDict
Grade = ReprAsDict
# Note: If other class names appear in the data, they must be added here.

def parse_emit_log(input_path: Path):
    """
    Parses a log file with lines in the format "EMIT: Product(...)".
    """
    products = []
    warnings.warn(
        "This script uses eval() to parse the input file, which is inherently insecure "
        "and can execute arbitrary code. Only run this on trusted files."
    )

    with open(input_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line.startswith("EMIT: Product("):
                continue

            line_to_eval = line[len("EMIT: "):]
            
            try:
                # WARNING: eval() is used here. It's a security risk if the input
                # is not from a trusted source.
                evaluated_obj = eval(line_to_eval)
                product_dict = to_dict(evaluated_obj)

                # Post-process fields that are string-encoded representations of other objects
                for key in ['reviews', 'prices']:
                    if key in product_dict and isinstance(product_dict[key], str):
                        try:
                            stringified_obj = eval(product_dict[key])
                            product_dict[key] = to_dict(stringified_obj)
                        except Exception as e:
                            print(f"Warning on line {i}: Could not eval string content of '{key}'. Keeping as string. Error: {e}")
                
                products.append(product_dict)

            except Exception as e:
                print(f"Error on line {i}: Could not parse line. Skipping. Error: {e}")
                print(f"Problematic line content: {line_to_eval[:200]}...")
                continue
    
    return products


def format_product_file(input_path: Path, agent_id: int):
    """
    Reads a file containing product data in 'EMIT: Product(...)' format,
    wraps it in the structure expected by test scripts, and saves it
    with the correct name in the 'product_test/emits' directory.
    """
    emits_dir = Path("product_test/emits")
    emits_dir.mkdir(exist_ok=True)
    output_path = emits_dir / f"agent-{agent_id}.json"

    products = parse_emit_log(input_path)

    if not products:
        print("No products were parsed from the file. Aborting.")
        return

    print(f"Found and parsed {len(products)} products.")

    print(f"Fetching agent name for agent_id: {agent_id}")
    try:
        # This function requires a .env file with credentials (USER-NAME, PASS)
        html = get_old_agent(agent_id)
        agent_name = get_agent_name(html)
        print(f"Agent name found: {agent_name}")
    except Exception as e:
        print(f"Could not fetch agent name automatically: {e}")
        print("You might need to create a .env file with USER-NAME and PASS.")
        agent_name = f"Agent {agent_id}"
        print(f"Using default agent name: {agent_name}")

    meta_info = {
        "agent_name": agent_name
    }

    output_data = {
        "meta": meta_info,
        "products": products
    }

    print(f"Writing formatted file to: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print("Formatting complete.")
    print(f"You can now run your test script. Make sure 'reload' is set to 0 or False to use this generated file.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Format a product data file into the JSON structure required by test_products_multiprocessing.py.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("input_file", help="Path to the input file in 'EMIT: Product(...)' log format.")
    parser.add_argument("agent_id", type=int, help="The agent ID for which the test file is being created.")
    args = parser.parse_args()

    input_p = Path(args.input_file)
    if not input_p.exists():
        print(f"Error: Input file not found at {input_p}")
    else:
        format_product_file(input_p, args.agent_id)