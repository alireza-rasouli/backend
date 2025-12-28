from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import yaml
import os
from asgiref.wsgi import WsgiToAsgi
import urllib.parse

app = Flask(__name__)
CORS(app)
asgi_app = WsgiToAsgi(app)

# Use your actual raw LL.yaml link here
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
        final_config["proxies"] = []

        # 2. Fetch New Nodes
        nodes_res = requests.get(url, timeout=15)
        nodes_res.raise_for_status()
        content = nodes_res.text

        new_nodes = []
        new_node_names = []

        if "proxies:" in content:
            # Standard YAML parsing
            parsed = yaml.safe_load(content)
            new_nodes = parsed.get('proxies', [])
            new_node_names = [n.get('name', 'unnamed') for n in new_nodes]
        else:
            # TXT CONVERSION LOGIC (Handles those long vless/ss links)
            raw_lines = content.splitlines()
            for line in raw_lines:
                clean = line.strip()
                if clean and (clean.startswith('vless://') or clean.startswith('ss://') or clean.startswith('vmess://')):
                    # Extract name from the # fragment
                    if '#' in clean:
                        # Split at # and take the second part. Decode URL encoding (like %20 to space)
                        parts = clean.split('#', 1)
                        name = urllib.parse.unquote(parts[1])
                    else:
                        name = f"Node-{len(new_node_names)+1}"
                    
                    # Store the full link in the proxies list
                    new_nodes.append(clean)
                    # Store ONLY the name for the groups
                    new_node_names.append(name)

        if not new_nodes:
            return jsonify({"error": "No nodes found"}), 400

        # 3. Update the Proxies list
        final_config["proxies"] = new_nodes

        # 4. Universal Group Update (Blind referencing)
        if "proxy-groups" in final_config:
            for group in final_config["proxy-groups"]:
                current_proxies = group.get('proxies', [])
                # Keep DIRECT/REJECT/SELECT, replace everything else with new names
                non_node_items = [p for p in current_proxies if p in ["DIRECT", "REJECT", "GLOBAL"]]
                group["proxies"] = non_node_items + new_node_names

        output = yaml.dump(final_config, allow_unicode=True, sort_keys=False)
        return jsonify({"output": output})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
