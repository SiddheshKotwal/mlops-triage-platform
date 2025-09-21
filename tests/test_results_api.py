# tests/test_results_api.py

import pytest
import uuid
from httpx import AsyncClient, ASGITransport 
from unittest.mock import patch, MagicMock

from services.results_api.app import app as results_app

@pytest.mark.asyncio
async def test_get_ticket_result_found():
    """
    Tests the GET /tickets/{ticket_id} endpoint when a ticket is found.
    """
    # Arrange: Create a fake ticket ID and a mock database response
    test_ticket_id = uuid.uuid4()
    
    # This mock represents the data returned from a successful database query
    mock_db_row = MagicMock()
    mock_db_row._asdict.return_value = {
        "ticket_id": test_ticket_id,
        "status": "COMPLETED",
        "subject": "Test Subject",
        "description": "Test Description",
        "predicted_category": "Finance & Billing",
        "predicted_priority": "P2",
        "final_category": "Finance & Billing",
        "final_priority": "P2",
        "created_at": "2025-09-19T10:00:00Z",
        "prediction_confidence_category": 0.95,
        "prediction_confidence_priority": 0.99
    }

    # Patch the 'engine.connect' method to avoid a real database call
    with patch('services.results_api.app.engine.connect') as mock_connect:
        # Configure the mock to return our fake data
        mock_connection = MagicMock()
        mock_connection.execute.return_value.first.return_value = mock_db_row
        mock_connect.return_value.__enter__.return_value = mock_connection

        async with AsyncClient(transport=ASGITransport(app=results_app), base_url="http://test") as client:
            response = await client.get(f"/tickets/{test_ticket_id}")

            assert response.status_code == 200
            response_json = response.json()
            assert response_json["status"] == "COMPLETED"
            assert response_json["ticket_id"] == str(test_ticket_id)