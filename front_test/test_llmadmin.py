import requests
import json
from typing import Any, Dict
from datetime import datetime

BASE_URL = "http://localhost:8000/llmadmin"

def print_response(endpoint: str, response: Dict[str, Any]) -> None:
    """Print formatted API response"""
    print(f"\n=== Testing {endpoint} ===")
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Response Data:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    else:
        print(f"Error: {response.text}")
    print("=" * 50)

def test_llmadmin_api():
    try:
        # 1. Test /users endpoint
        response = requests.get(f"{BASE_URL}/users")
        print_response("/users", response)
        
        if response.status_code == 200 and response.json():
            # Get first user_id for further tests
            first_user_id = response.json()[0]
            
            # 2. Test /sessions/{user_id} endpoint
            response = requests.get(f"{BASE_URL}/sessions/{first_user_id}")
            print_response(f"/sessions/{first_user_id}", response)
            
            if response.status_code == 200 and response.json():
                # Get first session_id for further tests
                first_session = response.json()[0]
                first_session_id = first_session['session_id']
                
                # 3. Test /chains/{session_id} endpoint
                response = requests.get(f"{BASE_URL}/chains/{first_session_id}")
                print_response(f"/chains/{first_session_id}", response)
                
                if response.status_code == 200 and response.json():
                    # Get first chain_id for further tests
                    first_chain = response.json()[0]
                    first_chain_id = first_chain['id']
                    
                    # 4. Test /traces/{chain_id} endpoint
                    response = requests.get(f"{BASE_URL}/traces/{first_chain_id}")
                    print_response(f"/traces/{first_chain_id}", response)
                    
                    if response.status_code == 200 and response.json().get('traces'):
                        # Get first trace_id for further tests
                        first_trace = response.json()['traces'][0]
                        first_trace_id = first_trace['id']
                        
                        # 5. Test /qnas/{trace_id} endpoint
                        response = requests.get(f"{BASE_URL}/qnas/{first_trace_id}")
                        print_response(f"/qnas/{first_trace_id}", response)
                        
                        # 6. Test /states/{trace_id} endpoint
                        response = requests.get(f"{BASE_URL}/states/{first_trace_id}")
                        print_response(f"/states/{first_trace_id}", response)

    except requests.RequestException as e:
        print(f"Connection Error: {e}")
        print("Make sure the FastAPI server is running on http://localhost:8000")
    except Exception as e:
        print(f"Error during testing: {e}")

if __name__ == "__main__":
    print("Starting API tests...")
    print("Make sure the FastAPI server is running on http://localhost:8000")
    test_llmadmin_api()