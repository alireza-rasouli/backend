from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import yaml
import sys

app = FastAPI()

# --- CORS SETUP ---
# This allows your GitHub Pages (frontend) to communicate with Render (backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURATION ---
# The raw link to your static template file
TEMPLATE_URL = "https://raw.githubusercontent.com/alireza-rasouli/VPN/main/LL.yaml"

class LinkRequest(BaseModel):
    url: str

@app.get("/")
def health_check():
    return {"status": "online", "message": "VPN Automation Backend is running"}

@app.post("/process")
async def process_vpn_logic(request: LinkRequest):
    try:
        # 1. Fetch nodes from the URL provided in the panel
        source_url = request.url
        print(f"Fetching nodes from: {source_url}")
        
        try:
            source_resp = requests.get(source_url, timeout=15)
            source_resp.raise_for_status()
            source_data = yaml.safe_load(source_resp.text)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to fetch source nodes: {str(e)}")

        proxies = source_data.get('proxies', [])
        if not proxies:
            return {"output": "Error: No proxies found in the source link."}

        # Deduplicate proxies by name
        all_new_proxies = []
        seen_names = set()
        for p in proxies:
            if p.get('name') not in seen_names:
                all_new_proxies.append(p)
                seen_names.add(p['name'])
        
        new_names = list(seen_names)

        # 2. Fetch your template (The old INPUT_FILE / LL.yaml)
        try:
            template_resp = requests.get(TEMPLATE_URL, timeout=15)
            template_resp.raise_for_status()
            my_config = yaml.safe_load(template_resp.text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch template LL.yaml: {str(e)}")

        # 3. Inject gathered proxies into the config
        my_config['proxies'] = all_new_proxies

        # 4. Update Proxy Groups (Content-Aware Logic)
        if 'proxy-groups' in my_config:
            # 1. Map out what is a "System" name (Groups and Tags)
            group_names = [g['name'] for g in my_config['proxy-groups']]
            special_tags = ['DIRECT', 'REJECT', 'GLOBAL']
            system_names = set(special_tags + group_names)

            for group in my_config['proxy-groups']:
                if 'proxies' in group:
                    # 2. Check the content of the current group in LL.yaml
                    original_list = group['proxies']
                    
                    # 3. Logic: Does this group contain "Real Proxies"?
                    # We assume it's a proxy if the name isn't a Group or a Special Tag.
                    contains_proxies = any(p for p in original_list if p not in system_names)
                    
                    # Also check for empty list or url-test as a fallback
                    is_auto = group.get('type') == 'url-test'
                    
                    # 4. Clean up and preserve the System names (DIRECT, etc.)
                    preserved = [p for p in original_list if p in system_names]

                    if contains_proxies or is_auto or len(original_list) == 0:
                        # This group is "Active" - populate it!
                        if is_auto:
                            # Filter DIRECT out of Auto groups
                            preserved = [p for p in preserved if p != 'DIRECT']
                        
                        group['proxies'] = preserved + new_names
                    else:
                        # This group is "Manual/Static" - leave it exactly as it is
                        group['proxies'] = original_list
        # 5. Generate clean, multi-line YAML output
        # indent=2 and default_flow_style=False ensures it looks like a real file
        final_yaml = yaml.dump(
            my_config, 
            allow_unicode=True, 
            sort_keys=False, 
            default_flow_style=False,
            indent=2,
            width=1000
        )
        
        return {"output": final_yaml}

    except Exception as e:
        return {"output": f"Backend Error: {str(e)}"}

# Start command for Render: uvicorn main:app --host 0.0.0.0 --port $PORT
