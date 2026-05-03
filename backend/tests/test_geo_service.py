import pytest
from unittest.mock import patch, MagicMock
from app.services.geo_service import get_geo_features

def test_get_geo_features_fallback_unbound_local_error_fix():
    # Test that fallback_used correctly processes without UnboundLocalError
    # We mock _overpass_api.query and _geocoder to force a fallback
    
    with patch("app.services.geo_service._overpass_api.query") as mock_query, \
         patch("app.services.geo_service._geocoder.reverse") as mock_reverse:
         
         # Force fallback by raising exception in Overpass API
         mock_query.side_effect = Exception("OSM 406 Not Acceptable")
         
         # Provide a dummy location so it doesn't fail on reverse geocoding completely
         mock_loc = MagicMock()
         mock_loc.raw = {"address": {"city": "TestCity", "state": "TestState"}}
         mock_reverse.return_value = mock_loc
         
         # Call get_geo_features
         result = get_geo_features(12.9716, 77.5946)
         
         assert result is not None
         assert result.fallback_used == True
         assert result.competition_adjustment == 1.0

def test_get_geo_features_happy_path():
    with patch("app.services.geo_service._overpass_api.query") as mock_query, \
         patch("app.services.geo_service._geocoder.reverse") as mock_reverse:
         
         def side_effect_query(query):
             mock_response = MagicMock()
             if "amenity" in query or "shop" in query and "highway" not in query:
                 # mock nodes
                 mock_response.nodes = [MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()] # 6 items
                 for n in mock_response.nodes:
                     n.tags = {"shop": "convenience"}
                     n.lat = 12.9716
                     n.lon = 77.5946
             else:
                 mock_response.nodes = []
                 
             if "highway" in query:
                 mock_way = MagicMock()
                 mock_way.tags = {"highway": "primary"}
                 mock_response.ways = [mock_way]
             else:
                 mock_response.ways = []
             return mock_response
             
         mock_query.side_effect = side_effect_query
         
         mock_loc = MagicMock()
         mock_loc.raw = {"address": {"city": "TestCity", "state": "TestState"}}
         mock_reverse.return_value = mock_loc
         
         result = get_geo_features(12.9716, 77.5946)
         
         assert result is not None
         assert result.fallback_used == False
         assert result.competition_count_500m == 6 # from our mock
         assert result.competition_adjustment == 0.85 # 6 >= 5, so 0.85
