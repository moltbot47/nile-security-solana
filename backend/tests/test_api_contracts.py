"""Tests for contract CRUD endpoints."""

import uuid


async def test_create_contract_unauthenticated(client, sample_contract_data):
    """POST /contracts without auth returns 401."""
    response = await client.post("/api/v1/contracts", json=sample_contract_data)
    assert response.status_code == 401


async def test_create_contract(client, auth_headers, sample_contract_data):
    """POST /contracts creates a new contract and returns it."""
    response = await client.post(
        "/api/v1/contracts", json=sample_contract_data, headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == sample_contract_data["name"]
    assert data["address"] == sample_contract_data["address"]
    assert data["chain"] == "solana"
    assert "id" in data


async def test_list_contracts_empty(client):
    """GET /contracts returns empty list when no contracts exist."""
    response = await client.get("/api/v1/contracts")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_contracts_with_data(client, auth_headers, sample_contract_data):
    """GET /contracts returns contracts after creation."""
    await client.post(
        "/api/v1/contracts", json=sample_contract_data, headers=auth_headers
    )
    response = await client.get("/api/v1/contracts")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == sample_contract_data["name"]


async def test_get_contract_by_id(client, auth_headers, sample_contract_data):
    """GET /contracts/{id} returns the correct contract."""
    create_resp = await client.post(
        "/api/v1/contracts", json=sample_contract_data, headers=auth_headers
    )
    contract_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/contracts/{contract_id}")
    assert response.status_code == 200
    assert response.json()["id"] == contract_id


async def test_get_contract_not_found(client):
    """GET /contracts/{id} returns 404 for non-existent contract."""
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/contracts/{fake_id}")
    assert response.status_code == 404


async def test_get_nile_history_empty(client, auth_headers, sample_contract_data):
    """GET /contracts/{id}/nile-history returns empty list when no scores exist."""
    create_resp = await client.post(
        "/api/v1/contracts", json=sample_contract_data, headers=auth_headers
    )
    contract_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/contracts/{contract_id}/nile-history")
    assert response.status_code == 200
    assert response.json() == []


async def test_get_vulnerabilities_empty(client, auth_headers, sample_contract_data):
    """GET /contracts/{id}/vulnerabilities returns empty when none reported."""
    create_resp = await client.post(
        "/api/v1/contracts", json=sample_contract_data, headers=auth_headers
    )
    contract_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/contracts/{contract_id}/vulnerabilities")
    assert response.status_code == 200
    assert response.json() == []


async def test_contract_solana_address_accepted(client, auth_headers):
    """Contract with valid Solana address (44 chars) is accepted."""
    response = await client.post(
        "/api/v1/contracts",
        json={
            "name": "Token Program",
            "address": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            "chain": "solana",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["address"] == "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"


async def test_contract_pagination(client, auth_headers, sample_contract_data):
    """GET /contracts supports skip and limit pagination."""
    # Create 3 contracts
    for i in range(3):
        data = {**sample_contract_data, "name": f"Contract {i}"}
        await client.post("/api/v1/contracts", json=data, headers=auth_headers)

    # Paginate
    response = await client.get("/api/v1/contracts?skip=0&limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 2

    response = await client.get("/api/v1/contracts?skip=2&limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 1
