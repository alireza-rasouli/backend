from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import yaml

app = Flask(__name__)
CORS(app)

# The template for your final YAML output
BASE_CONFIG = {
    "port": 7890,
    "socks-port": 7891,
    "allow-lan": True,
    "mode": "rule",
    "log-level": "info",
    "external-controller": "127.0.0.1:9090",
    "proxies": [],
    "proxy-groups": [
        {"name": "🚀 Manual Select", "type": "select", "proxies": ["DIRECT"]},
    ],
    "rules": ["MATCH,🚀 Manual Select"]
}

@app.route('/process', methods=['POST'])
def process_config():
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        # 1. Fetch the content
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        raw_content = response.text

        # 2. Detect Format: Is it YAML or Raw Text?
        if "proxies:" in raw_content:
            # Handle as YAML
            parsed_data = yaml.safe_load(raw_content)
            nodes = parsed_data.get('proxies', [])
        else:
            # Handle as Raw Node List (Albania.txt style)
            # We clean up the strings and ignore empty lines
            nodes = [line.strip() for line in raw_content.splitlines() if line.strip()]

        if not nodes:
            return jsonify({"error": "No proxy nodes found in the link"}), 400

        # 3. Build the final Config
        final_config = BASE_CONFIG.copy()
        
        # If nodes are already dictionaries (YAML), use them. 
        # If they are strings (Raw), we keep them as strings for the client to handle
        final_config["proxies"] = nodes
        
        # Update Proxy Groups with node names
        node_names = []
        for node in nodes:
            if isinstance(node, dict):
                node_names.append(node.get('name', 'Unknown'))
            else:
                node_names.append(node) # Keep raw string
                
        final_config["proxy-groups"][0]["proxies"].extend(node_names)

        # 4. Return as YAML string
        output = yaml.dump(final_config, allow_unicode=True, sort_keys=False)
        return jsonify({"output": output})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
