from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from app.db.database import Database
from app.services.products_service import ProductsService
from app.services.sales_service import SalesService


def main() -> None:
    temp = Path(tempfile.mkdtemp(prefix="cashier_lite_smoke_"))
    try:
        db = Database(temp / "smoke.sqlite")
        db.initialize()
        products = ProductsService(db)
        sales = SalesService(db)
        product_id = products.create_product(
            {
                "name": "منتج تجربة",
                "barcode": "TST-001",
                "unit": "قطعة",
                "purchase_price": "10",
                "retail_price": "15",
                "stock_quantity": "5",
                "min_stock_level": "1",
            }
        )
        result = sales.create_sale([{"product_id": product_id, "quantity": "2", "unit_price": "15", "discount": "0"}])
        product = products.get_product(product_id)
        assert product is not None
        assert product["stock_quantity"] == "3.0000"
        assert result["total_amount"] == "30.0000"
        print("SMOKE_OK", result["invoice_number"])
    finally:
        shutil.rmtree(temp, ignore_errors=True)


if __name__ == "__main__":
    main()
