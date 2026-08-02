from httpx import AsyncClient


async def authenticate_demo_client(
    client: AsyncClient,
    *,
    subject: str = "demo-admin",
) -> None:
    response = await client.post("/auth/demo-login", json={"subject": subject})
    response.raise_for_status()
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
