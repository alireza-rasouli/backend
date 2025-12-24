import requests
import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class LinkRequest(BaseModel):
    url: str

# Use the raw link to your template file on GitHub
TEMPLATE_URL = "https://raw.githubusercontent.com/alireza-rasouli/VPN/main/LL.yaml"

@app.post("/process")
async def process_vpn(request: LinkRequest):
    try:
        # 1. Gather all proxy nodes from the source URLs
        # (Using the link you paste into the panel + any hardcoded ones)
        source_urls = [request.url] 
        all_new_proxies = []
        seen_names = set()

        for url in source_urls:
            response = requests.get(url, timeout=10)
            source_data = yaml.safe_load(response.text)
            proxies = source_data.get('proxies', [])
            
            for p in proxies:
                if p['name'] not in seen_names:
                    all_new_proxies.append(p)
                    seen_names.add(p['name'])

        if not all_new_proxies:
            return {"output": "No proxies found in the provided link."}

        # 2. Fetch your template (The old INPUT_FILE)
        template_resp = requests.get(TEMPLATE_URL)
        my_config = yaml.safe_load(template_resp.text)

        # 3. Inject proxies (Your exact logic)
        my_config['proxies'] = all_new_proxies
        new_names = list(seen_names)

        # 4. Update Groups (Your exact logic)
        if 'proxy-groups' in my_config:
            group_names = [g['name'] for g in my_config['proxy-groups']]
            special_tags = ['DIRECT', 'REJECT', 'GLOBAL']
            valid_static = special_tags + group_names

            for group in my_config['proxy-groups']:
                if 'proxies' in group:
                    preserved = [p for p in group['proxies'] if p in valid_static]
                    group['proxies'] = preserved + new_names

        # 5. Return the result as YAML text
        final_yaml = yaml.dump(my_config, allow_unicode=True, sort_keys=False, default_flow_style=False)
        return {"output": final_yaml}

    except Exception as e:
        return {"output": f"Error: {str(e)}"}

@app.get("/")
def health():
    return {"status": "online"}
