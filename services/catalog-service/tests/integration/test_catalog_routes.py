"""Integration smoke tests for catalog routes."""

import pytest


@pytest.mark.integration
async def test_list_products_empty(client):
    response = await client.get("/api/v1/catalog/products")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.integration
async def test_list_categories_empty(client):
    response = await client.get("/api/v1/catalog/categories")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.integration
async def test_get_product_not_found(client):
    import uuid

    response = await client.get(f"/api/v1/catalog/products/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.integration
async def test_create_product_requires_auth(client):
    import uuid

    response = await client.post(
        "/api/v1/catalog/products",
        json={"name": "Test", "category_id": str(uuid.uuid4())},
    )
    assert response.status_code == 403
