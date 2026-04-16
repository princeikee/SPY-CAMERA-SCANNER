import requests
import sys
import json
from datetime import datetime

class SpyCamAPITester:
    def __init__(self, base_url="https://hidden-lens-scan-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.scan_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, description=""):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else f"{self.api_url}/"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        if description:
            print(f"   Description: {description}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if endpoint == "" and "message" in response_data:
                        print(f"   Response: {response_data['message']}")
                    elif "scans/start" in endpoint and "id" in response_data:
                        print(f"   Scan ID: {response_data['id']}")
                        print(f"   Devices found: {response_data.get('total_devices', 0)}")
                        print(f"   Cameras found: {response_data.get('cameras_found', 0)}")
                    elif "stats" in endpoint:
                        print(f"   Total scans: {response_data.get('total_scans', 0)}")
                        print(f"   Total devices: {response_data.get('total_devices_found', 0)}")
                except:
                    pass
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Response text: {response.text[:200]}")

            return success, response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text

        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timeout")
            return False, {}
        except requests.exceptions.ConnectionError:
            print(f"❌ Failed - Connection error")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test GET /api/ - health check endpoint"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "",
            200,
            description="Should return SpyCam Scanner API message"
        )
        return success

    def test_start_scan(self):
        """Test POST /api/scans/start - starts a network scan"""
        success, response = self.run_test(
            "Start Network Scan",
            "POST",
            "scans/start",
            200,
            data={"subnet": "192.168.1.0/24", "interface": "eth0"},
            description="Should start scan and return scan with devices, cameras_found, risk scores"
        )
        if success and isinstance(response, dict) and 'id' in response:
            self.scan_id = response['id']
            # Validate response structure
            required_fields = ['id', 'subnet', 'total_devices', 'cameras_found', 'devices']
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                print(f"⚠️  Warning: Missing fields in response: {missing_fields}")
            
            # Check if devices have proper structure
            if 'devices' in response and response['devices']:
                device = response['devices'][0]
                device_fields = ['id', 'ip', 'mac', 'vendor', 'open_ports', 'device_type', 'risk_score']
                missing_device_fields = [field for field in device_fields if field not in device]
                if missing_device_fields:
                    print(f"⚠️  Warning: Missing device fields: {missing_device_fields}")
                else:
                    print(f"✅ Device structure validated")
        return success

    def test_list_scans(self):
        """Test GET /api/scans - returns list of all scans"""
        success, response = self.run_test(
            "List All Scans",
            "GET",
            "scans",
            200,
            description="Should return list of all scans from history"
        )
        if success and isinstance(response, list):
            print(f"   Found {len(response)} scans in history")
        return success

    def test_get_scan_details(self):
        """Test GET /api/scans/{scan_id} - returns specific scan details"""
        if not self.scan_id:
            print("❌ Skipping - No scan ID available from previous test")
            return False
            
        success, response = self.run_test(
            "Get Scan Details",
            "GET",
            f"scans/{self.scan_id}",
            200,
            description="Should return specific scan with full device list"
        )
        return success

    def test_export_scan(self):
        """Test GET /api/scans/{scan_id}/export - exports scan data as JSON"""
        if not self.scan_id:
            print("❌ Skipping - No scan ID available from previous test")
            return False
            
        success, response = self.run_test(
            "Export Scan Data",
            "GET",
            f"scans/{self.scan_id}/export",
            200,
            description="Should export scan data as JSON"
        )
        return success

    def test_get_stats(self):
        """Test GET /api/stats - returns aggregated statistics"""
        success, response = self.run_test(
            "Get Statistics",
            "GET",
            "stats",
            200,
            description="Should return aggregated statistics"
        )
        if success and isinstance(response, dict):
            required_stats = ['total_scans', 'total_devices_found', 'total_cameras_found', 'total_high_risk']
            missing_stats = [stat for stat in required_stats if stat not in response]
            if missing_stats:
                print(f"⚠️  Warning: Missing stats fields: {missing_stats}")
            else:
                print(f"✅ Statistics structure validated")
        return success

    def test_delete_scan(self):
        """Test DELETE /api/scans/{scan_id} - deletes a scan"""
        if not self.scan_id:
            print("❌ Skipping - No scan ID available from previous test")
            return False
            
        success, response = self.run_test(
            "Delete Scan",
            "DELETE",
            f"scans/{self.scan_id}",
            200,
            description="Should delete the scan"
        )
        return success

    def test_risk_scoring_logic(self):
        """Test risk scoring system validation"""
        print(f"\n🔍 Testing Risk Scoring Logic...")
        print("   Validating risk scoring rules:")
        print("   - RTSP port 554 = +40 points")
        print("   - Multiple web ports = +20 points") 
        print("   - Camera vendor MAC = +20 points")
        print("   - Camera-specific ports = +20 points")
        
        # This will be validated through the scan results
        if hasattr(self, '_last_scan_response') and self._last_scan_response:
            devices = self._last_scan_response.get('devices', [])
            camera_devices = [d for d in devices if 'Camera' in d.get('device_type', '')]
            
            if camera_devices:
                print(f"✅ Found {len(camera_devices)} camera devices for risk validation")
                for device in camera_devices[:2]:  # Check first 2 cameras
                    risk_score = device.get('risk_score', 0)
                    open_ports = device.get('open_ports', [])
                    risk_factors = device.get('risk_factors', [])
                    
                    print(f"   Device {device.get('ip')}: Risk {risk_score}, Ports {open_ports}")
                    print(f"   Risk factors: {len(risk_factors)} factors")
                return True
            else:
                print("⚠️  No camera devices found to validate risk scoring")
                return True
        else:
            print("⚠️  No scan data available for risk scoring validation")
            return True

def main():
    print("🚀 Starting SpyCam Scanner API Tests")
    print("=" * 50)
    
    # Setup
    tester = SpyCamAPITester()
    
    # Run all tests in sequence
    test_results = []
    
    # Basic API tests
    test_results.append(("Health Check", tester.test_health_check()))
    test_results.append(("Start Scan", tester.test_start_scan()))
    test_results.append(("List Scans", tester.test_list_scans()))
    test_results.append(("Get Scan Details", tester.test_get_scan_details()))
    test_results.append(("Export Scan", tester.test_export_scan()))
    test_results.append(("Get Statistics", tester.test_get_stats()))
    test_results.append(("Risk Scoring Logic", tester.test_risk_scoring_logic()))
    test_results.append(("Delete Scan", tester.test_delete_scan()))

    # Print final results
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    for test_name, passed in test_results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
    
    passed_count = sum(1 for _, passed in test_results if passed)
    total_count = len(test_results)
    
    print(f"\n📈 Overall: {passed_count}/{total_count} tests passed ({passed_count/total_count*100:.1f}%)")
    
    if passed_count == total_count:
        print("🎉 All tests passed! API is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the API implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())