from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import yaml
import os
from asgiref.wsgi import WsgiToAsgi

app = Flask(__name__)
CORS(app)
asgi_app = WsgiToAsgi(app)

# REPLACE THIS with your actual raw LL.yaml link
BASE_CONFIG_URL = "https://raw.githubusercontent.com/alireza-rasouli/VPN/refs/heads/main/LL.yaml"

@app.route('/process', methods=['POST'])
def process_config():
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        # 1. Fetch LL.yaml Structure
        base_res = requests.get(BASE_CONFIG_URL, timeout=10)
        base_res.raise_for_status()
        final_config = yaml.safe_load(base_res.text)

        # Wipe old proxies from the template to keep it clean
        final_config["proxies"] = []

        # 2. Fetch New Nodes (Detect YAML vs TXT)
        nodes_res = requests.get(url, timeout=15)
        nodes_res.raise_for_status()
        content = nodes_res.text

        new_nodes = []
        new_node_names = []

        if "proxies:" in content:
            # ORIGINAL YAML LOGIC
            parsed = yaml.safe_load(content)
            new_nodes = parsed.get('proxies', [])
            new_node_names = [n.get('name', 'unnamed') for n in new_nodes]
        else:
            # TXT CONVERSION LOGIC
            raw_lines = content.splitlines()
            for line in raw_lines:
                clean = line.strip()
                if clean and not clean.startswith('#'):
                    new_nodes.append(clean)
                    # For TXT, we use the string as the name so groups can reference it
                    new_node_names.append(clean)

        if not new_nodes:
            return jsonify({"error": "No nodes found"}), 400

        # 3. Inject new nodes into the proxies list
        final_config["proxies"] = new_nodes

        # 4. UNIVERSAL GROUP UPDATE (Original Style)
        # This replaces proxies in EVERY group based on what was there before
        if "proxy-groups" in final_config:
            for group in final_config["proxy-groups"]:
                current_proxies = group.get('proxies', [])
                
                # Filter out old node names but keep control keywords like DIRECT/REJECT/SELECT
                # This mirrors your original logic of 'refreshing' the group content
                non_node_items = [p for p in current_proxies if p in ["DIRECT", "REJECT", "GLOBAL"]]
                
                # Update the group with the new list of names
                group["proxies"] = non_node_items + new_node_names

        output = yaml.dump(final_config, allow_unicode=True, sort_keys=False)
        return jsonify({"output": output})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
