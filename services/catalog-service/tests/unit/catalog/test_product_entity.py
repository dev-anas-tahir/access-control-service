import uuid

from app.catalog.domain.entities.product import ProductStatus
from app.catalog.domain.events import ProductPriceChanged
from tests.unit.catalog.fakes import make_product, make_variant


def test_update_variant_price_on_active_product_returns_price_changed_event():
    product = make_product(status=ProductStatus.ACTIVE)
    variant = make_variant(product_id=product.id, price=10.0)
    actor_id = uuid.uuid4()

    event = product.update_variant_price(variant, 20.0, actor_id=actor_id)

    assert isinstance(event, ProductPriceChanged)
    assert event.old_price == 10.0
    assert event.new_price == 20.0
    assert event.variant_id == variant.id
    assert event.product_id == product.id
    assert event.actor_id == actor_id


def test_update_variant_price_on_inactive_product_returns_none():
    product = make_product(status=ProductStatus.INACTIVE)
    variant = make_variant(product_id=product.id, price=10.0)

    event = product.update_variant_price(variant, 20.0, actor_id=uuid.uuid4())

    assert event is None


def test_update_variant_price_when_unchanged_returns_none():
    product = make_product(status=ProductStatus.ACTIVE)
    variant = make_variant(product_id=product.id, price=10.0)

    event = product.update_variant_price(variant, 10.0, actor_id=uuid.uuid4())

    assert event is None


def test_update_variant_price_mutates_variant():
    product = make_product(status=ProductStatus.ACTIVE)
    variant = make_variant(product_id=product.id, price=10.0)

    product.update_variant_price(variant, 25.0)

    assert variant.price == 25.0


def test_update_variant_price_inactive_still_mutates_variant():
    product = make_product(status=ProductStatus.INACTIVE)
    variant = make_variant(product_id=product.id, price=10.0)

    product.update_variant_price(variant, 30.0)

    assert variant.price == 30.0
