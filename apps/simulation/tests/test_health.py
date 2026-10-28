from app.config import get_settings
from app.services.health_service import HealthService, get_health_service
from psycopg import AsyncConnection


async def test_health_ok_with_a_reachable_database(client) -> None:
    http, _ = client
    response = await http.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": True}


async def test_health_reports_503_when_the_connection_is_dead(client) -> None:
    http, app = client
    connection = await AsyncConnection.connect(get_settings().simulation_database_url)
    await connection.close()
    app.dependency_overrides[get_health_service] = lambda: HealthService(connection)
    response = await http.get("/health")
    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": False}


async def test_health_needs_no_credentials(client) -> None:
    http, _ = client
    response = await http.get("/health")
    assert response.status_code == 200
    assert "authorization" not in response.request.headers
