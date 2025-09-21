# tests/test_ingestion_api.py

import pytest
from httpx import AsyncClient, ASGITransport 
from unittest.mock import patch, MagicMock

# Import the FastAPI app instance from your service
from services.ingestion_api.app import app as ingestion_app

@pytest.mark.asyncio
async def test_create_ticket_endpoint():
    """
    Tests the POST /tickets endpoint of the ingestion API.
    It should return a 200 OK status and a ticket_id.
    """
    # Arrange: Mock the Redis client's 'xadd' method so we don't need a real Redis server
    with patch('services.ingestion_api.app.r.xadd', MagicMock()) as mock_xadd:
        async with AsyncClient(transport=ASGITransport(app=ingestion_app), base_url="http://test") as client:
            ticket_data = {
                "subject": "My printer is on fire",
                "description": "The printer is literally on fire. Please send help."
            }
            response = await client.post("/tickets", json=ticket_data)
            
            assert response.status_code == 200
            response_json = response.json()
            assert "ticket_id" in response_json
            assert isinstance(response_json["ticket_id"], str)
            mock_xadd.assert_called_once()