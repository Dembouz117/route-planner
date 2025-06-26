from models.schemas import LocationPoint



MOCK_LOCATIONS = {
    "warehouses": [
        LocationPoint(id="WH001", name="Singapore Hub", lat=1.3521, lng=103.8198, type="warehouse", capacity=10000),
        LocationPoint(id="WH002", name="Shanghai Center", lat=31.2304, lng=121.4737, type="warehouse", capacity=15000),
        LocationPoint(id="WH003", name="Austin Facility", lat=30.2672, lng=-97.7431, type="warehouse", capacity=8000),
        LocationPoint(id="WH004", name="Dublin Hub", lat=53.3498, lng=-6.2603, type="warehouse", capacity=12000),
        LocationPoint(id="WH005", name="Tokyo Distribution", lat=35.6762, lng=139.6503, type="warehouse", capacity=9000),
        LocationPoint(id="WH006", name="Tel Aviv Warehouse", lat=32.0853, lng=34.7818, type="warehouse", capacity=7000),
    ],
    "ports": [
        LocationPoint(id="PORT001", name="Port of Singapore", lat=1.2659, lng=103.8072, type="port"),
        LocationPoint(id="PORT002", name="Port of Shanghai", lat=31.3056, lng=121.6489, type="port"),
        LocationPoint(id="PORT003", name="Port of Long Beach", lat=33.7701, lng=-118.2437, type="port"),
        LocationPoint(id="PORT004", name="Port of Rotterdam", lat=51.9225, lng=4.47917, type="port"),
        LocationPoint(id="PORT005", name="Port of Dubai", lat=25.2769, lng=55.3264, type="port"),
        LocationPoint(id="PORT006", name="Port of Haifa", lat=32.8191, lng=34.9983, type="port"),
    ],
    "airports": [
        LocationPoint(id="AIR001", name="Changi Airport", lat=1.3644, lng=103.9915, type="airport"),
        LocationPoint(id="AIR002", name="Pudong Airport", lat=31.1443, lng=121.8083, type="airport"),
        LocationPoint(id="AIR003", name="LAX", lat=33.9425, lng=-118.4081, type="airport"),
        LocationPoint(id="AIR004", name="Heathrow Airport", lat=51.4700, lng=-0.4543, type="airport"),
        LocationPoint(id="AIR005", name="Narita Airport", lat=35.7720, lng=140.3929, type="airport"),
        LocationPoint(id="AIR006", name="Ben Gurion Airport", lat=32.0114, lng=34.8867, type="airport"),
        LocationPoint(id="AIR007", name="Ramon Airport", lat=29.7281, lng=35.0128, type="airport"),
    ]
}
# API Configuration
API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"

# External Service Configuration (in production, use environment variables)
PINECONE_CONFIG = {
    "api_key": "your-pinecone-api-key",
    "environment": "your-pinecone-environment",
    "index_name": "dell-supply-chain-kb"
}

TAVILY_CONFIG = {
    "api_key": "your-tavily-api-key"
}

OPENAI_CONFIG = {
    "api_key": "your-openai-api-key",
    "model": "gpt-4"
}