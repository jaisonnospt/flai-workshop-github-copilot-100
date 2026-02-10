"""
Tests for the High School Management System API
"""
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield
    
    # Reset to original state after test
    for name, details in original_activities.items():
        if name in activities:
            activities[name]["participants"] = details["participants"].copy()


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static_index(self, client):
        """Test that root redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_success(self, client):
        """Test getting all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        
        # Check structure of first activity
        first_activity = list(data.values())[0]
        assert "description" in first_activity
        assert "schedule" in first_activity
        assert "max_participants" in first_activity
        assert "participants" in first_activity
    
    def test_activities_have_required_fields(self, client):
        """Test that all activities have required fields"""
        response = client.get("/activities")
        data = response.json()
        
        required_fields = ["description", "schedule", "max_participants", "participants"]
        
        for activity_name, activity_data in data.items():
            for field in required_fields:
                assert field in activity_data, f"Activity '{activity_name}' missing field '{field}'"
    
    def test_activities_participants_is_list(self, client):
        """Test that participants field is a list"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert isinstance(activity_data["participants"], list), \
                f"Activity '{activity_name}' participants should be a list"


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        # Use a new email not in the original participants
        response = client.post(
            "/activities/Basketball%20Team/signup?email=test.student@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "test.student@mergington.edu" in data["message"]
        assert "Basketball Team" in data["message"]
        
        # Verify the participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "test.student@mergington.edu" in activities_data["Basketball Team"]["participants"]
    
    def test_signup_duplicate_email(self, client):
        """Test that duplicate signup is rejected"""
        email = "test.duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(
            f"/activities/Basketball%20Team/signup?email={email}"
        )
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(
            f"/activities/Basketball%20Team/signup?email={email}"
        )
        assert response2.status_code == 400
        
        data = response2.json()
        assert "detail" in data
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_nonexistent_activity(self, client):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent%20Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_signup_multiple_students(self, client):
        """Test signing up multiple students for same activity"""
        emails = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        for email in emails:
            response = client.post(
                f"/activities/Art%20Club/signup?email={email}"
            )
            assert response.status_code == 200
        
        # Verify all were added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        
        for email in emails:
            assert email in activities_data["Art Club"]["participants"]


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client):
        """Test successful unregistration from an activity"""
        email = "test.unregister@mergington.edu"
        activity = "Drama Club"
        
        # First signup
        signup_response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Then unregister
        unregister_response = client.delete(
            f"/activities/{activity}/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        
        data = unregister_response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity in data["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data[activity]["participants"]
    
    def test_unregister_not_registered(self, client):
        """Test unregistering a student who is not registered"""
        response = client.delete(
            "/activities/Basketball%20Team/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        
        data = response.json()
        assert "detail" in data
        assert "not registered" in data["detail"].lower()
    
    def test_unregister_nonexistent_activity(self, client):
        """Test unregistering from non-existent activity"""
        response = client.delete(
            "/activities/Nonexistent%20Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_unregister_existing_participant(self, client):
        """Test unregistering an existing participant"""
        # Get an existing participant from activities
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        
        # Find an activity with participants
        activity_name = "Basketball Team"
        if activities_data[activity_name]["participants"]:
            email = activities_data[activity_name]["participants"][0]
            
            # Unregister
            response = client.delete(
                f"/activities/{activity_name}/unregister?email={email}"
            )
            assert response.status_code == 200
            
            # Verify removal
            activities_response = client.get("/activities")
            activities_data = activities_response.json()
            assert email not in activities_data[activity_name]["participants"]


class TestActivityCapacity:
    """Tests for activity capacity limits"""
    
    def test_activity_has_max_participants(self, client):
        """Test that activities have max_participants defined"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "max_participants" in activity_data
            assert isinstance(activity_data["max_participants"], int)
            assert activity_data["max_participants"] > 0
    
    def test_participants_count_within_limit(self, client):
        """Test that current participants don't exceed max"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            current_count = len(activity_data["participants"])
            max_count = activity_data["max_participants"]
            assert current_count <= max_count, \
                f"Activity '{activity_name}' has {current_count} participants, max is {max_count}"


class TestEmailValidation:
    """Tests for email parameter validation"""
    
    def test_signup_with_special_characters_in_email(self, client):
        """Test signup with special characters in email"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=test%2Bspecial@mergington.edu"
        )
        assert response.status_code == 200
    
    def test_signup_url_encoded_activity_name(self, client):
        """Test that URL encoding works for activity names"""
        response = client.post(
            "/activities/Programming%20Class/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200


class TestIntegrationScenarios:
    """Integration tests for complete user scenarios"""
    
    def test_complete_signup_and_unregister_flow(self, client):
        """Test complete flow: signup -> verify -> unregister -> verify"""
        email = "flow.test@mergington.edu"
        activity = "Debate Team"
        
        # 1. Signup
        signup_response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # 2. Verify participant is in list
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity]["participants"]
        
        # 3. Unregister
        unregister_response = client.delete(
            f"/activities/{activity}/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        
        # 4. Verify participant is removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data[activity]["participants"]
    
    def test_signup_multiple_activities_same_student(self, client):
        """Test student signing up for multiple activities"""
        email = "multi.activity@mergington.edu"
        activities_to_signup = ["Basketball Team", "Art Club", "Chess Club"]
        
        for activity in activities_to_signup:
            response = client.post(
                f"/activities/{activity}/signup?email={email}"
            )
            assert response.status_code == 200
        
        # Verify student is in all activities
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        
        for activity in activities_to_signup:
            assert email in activities_data[activity]["participants"]
