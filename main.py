from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import yaml
import os
from asgiref.wsgi import WsgiToAsgi  # The "Translator"

app = Flask(__name__)
CORS(app)

# Wrap the app for Uvicorn/ASGI compatibility
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
        # 1. Fetch Base Config (LL.yaml)
        try:
            base_res = requests.get(BASE_CONFIG_URL, timeout=10)
            base_res.raise_for_status()
            final_config = yaml.safe_load(base_res.text)
        except Exception:
            # Fallback if LL.yaml fails
            final_config = {"proxies": [], "proxy-groups": [{"name": "Manual", "type": "select", "proxies": ["DIRECT"]}]}

        # 2. Fetch Nodes (YAML or TXT)
        nodes_res = requests.get(url, timeout=15)
        nodes_res.raise_for_status()
        content = nodes_res.text

        nodes = []
        if "proxies:" in content:
            parsed = yaml.safe_load(content)
            nodes = parsed.get('proxies', [])
        else:
            # Handle .txt node lists
            nodes = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith('#')]

        if not nodes:
            return jsonify({"error": "No nodes found"}), 400

        # 3. Merge into Base
        if "proxies" not in final_config or not final_config["proxies"]:
            final_config["proxies"] = []
        
        final_config["proxies"].extend(nodes)

        # 4. Update Proxy Groups
        if "proxy-groups" in final_config:
            names = []
            for n in nodes:
                if isinstance(n, dict):
                    names.append(n.get('name', 'node'))
                else:
                    names.append(n[:30] + "...")
            final_config["proxy-groups"][0]["proxies"].extend(names)

        output = yaml.dump(final_config, allow_unicode=True, sort_keys=False)
        return jsonify({"output": output})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Keep this for local testing
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
