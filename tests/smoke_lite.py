from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from app.db.database import Database
from app.services.backup_service import BackupService
from app.services.products_service import ProductsService
from app.services.sales_service import SalesService
from app.services.settings_service import SettingsService


def main() -> None:
    temp = Path(tempfile.mkdtemp(prefix="cashier_lite_smoke_"))
    try:
        db = Database(temp / "smoke.sqlite")
        db.initialize()
        products = ProductsService(db)
        sales = SalesService(db)
        settings = SettingsService(db)
        settings.ensure_defaults()
        settings.save_currency_settings(
            currency_name="ليرة سورية",
            currency_symbol="ل.س",
            exchange_currency_name="دولار",
            exchange_currency_symbol="$",
            exchange_rate="14000",
        )

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

        details = sales.get_sale_details(int(result["sale_id"]))
        assert details["sale"]["exchange_rate"] == "14000.0000"

        # Change current exchange settings; old invoice must keep historical rate.
        settings.save_currency_settings(
            currency_name="ليرة سورية",
            currency_symbol="ل.س",
            exchange_currency_name="دولار",
            exchange_currency_symbol="$",
            exchange_rate="15000",
        )
        details_after_rate_change = sales.get_sale_details(int(result["sale_id"]))
        assert details_after_rate_change["sale"]["exchange_rate"] == "14000.0000"

        sale_item = details_after_rate_change["items"][0]
        sales.update_sale(
            int(result["sale_id"]),
            [
                {
                    "sale_item_id": sale_item["id"],
                    "quantity": "1",
                    "unit_price": sale_item["unit_price"],
                    "discount": "0",
                }
            ],
            payment_method="cash",
            paid_amount="15",
        )
        updated_product = products.get_product(product_id)
        assert updated_product is not None
        assert updated_product["stock_quantity"] == "4.0000"
        updated_details = sales.get_sale_details(int(result["sale_id"]))
        assert updated_details["sale"]["total_amount"] == "15.0000"
        assert int(updated_details["sale"]["edit_count"]) == 1
        assert updated_details["sale"]["exchange_rate"] == "14000.0000"

        backup = BackupService(db).create_backup(label="smoke")
        assert backup.exists()
        assert settings.get("theme_mode") == "light"
        print("SMOKE_OK", result["invoice_number"])
    finally:
        shutil.rmtree(temp, ignore_errors=True)


if __name__ == "__main__":
    main()
