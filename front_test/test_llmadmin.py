import requests
import json
from typing import Any, Dict

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
    """Test all llmadmin API endpoints"""
    try:
        # 1. Test /users endpoint
        response = requests.get(f"{BASE_URL}/users")
        print_response("/users", response)
        
        if response.status_code == 200 and response.json():
            # Test for each user
            for user_id in response.json():
                # 2. Test /sessions/{user_id} endpoint
                response = requests.get(f"{BASE_URL}/sessions/{user_id}")
                print_response(f"/sessions/{user_id}", response)
                
                if response.status_code == 200 and response.json():
                    # Test for each session
                    for session in response.json():
                        session_id = session['session_id']
                        
                        # 3. Test /chains/{session_id} endpoint
                        response = requests.get(f"{BASE_URL}/chains/{session_id}")
                        print_response(f"/chains/{session_id}", response)
                        
                        if response.status_code == 200 and response.json():
                            # Test for each chain until we find one with traces
                            for chain in response.json():
                                chain_id = chain['id']
                                
                                # 4. Test /traces/{chain_id} endpoint
                                response = requests.get(f"{BASE_URL}/traces/{chain_id}")
                                print_response(f"/traces/{chain_id}", response)
                                
                                if response.status_code == 200:
                                    trace_data = response.json()
                                    if trace_data.get('traces'):  # Found a chain with traces
                                        trace_id = trace_data['traces'][0].get('id')
                                        
                                        # 5. Test /qnas/{trace_id} endpoint
                                        response = requests.get(f"{BASE_URL}/qnas/{trace_id}")
                                        print_response(f"/qnas/{trace_id}", response)
                                        
                                        # 6. Test /states/{trace_id} endpoint
                                        response = requests.get(f"{BASE_URL}/states/{trace_id}")
                                        print_response(f"/states/{trace_id}", response)
                                        
                                        # Found and tested a chain with traces, no need to continue
                                        return
                            
                            # If we get here, we've checked all chains in this session and found no traces
                            print("\nNo traces found in any chains for this session, trying next session...")
                
                # If we get here, we've checked all sessions for this user and found no traces
                print("\nNo traces found in any sessions for this user, trying next user...")

        print("\nCompleted testing all available users, sessions, and chains.")

    except requests.RequestException as e:
        print(f"Connection Error: {e}")
        print("Make sure the FastAPI server is running on http://localhost:8000")
    except Exception as e:
        print(f"Error during testing: {e}")

if __name__ == "__main__":
    print("Starting API tests...")
    print("Make sure the FastAPI server is running on http://localhost:8000")
    test_llmadmin_api()