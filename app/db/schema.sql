PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
  version INTEGER PRIMARY KEY,
  applied_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT,
  updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS invoice_sequences (
  prefix TEXT PRIMARY KEY,
  last_number INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  barcode TEXT UNIQUE,
  name TEXT NOT NULL,
  unit TEXT NOT NULL DEFAULT 'قطعة',
  purchase_price TEXT NOT NULL DEFAULT '0.0000',
  retail_price TEXT NOT NULL DEFAULT '0.0000',
  stock_quantity TEXT NOT NULL DEFAULT '0.0000',
  min_stock_level TEXT NOT NULL DEFAULT '0.0000',
  notes TEXT,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
CREATE INDEX IF NOT EXISTS idx_products_barcode ON products(barcode);
CREATE INDEX IF NOT EXISTS idx_products_active ON products(is_active);

CREATE TABLE IF NOT EXISTS customers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  phone TEXT,
  balance TEXT NOT NULL DEFAULT '0.0000',
  notes TEXT,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS sales (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  invoice_number TEXT UNIQUE NOT NULL,
  customer_id INTEGER REFERENCES customers(id) ON DELETE SET NULL,
  subtotal TEXT NOT NULL DEFAULT '0.0000',
  discount TEXT NOT NULL DEFAULT '0.0000',
  total_amount TEXT NOT NULL DEFAULT '0.0000',
  paid_amount TEXT NOT NULL DEFAULT '0.0000',
  payment_method TEXT NOT NULL DEFAULT 'cash' CHECK (payment_method IN ('cash','card')),
  currency_name TEXT,
  currency_symbol TEXT,
  exchange_currency_name TEXT,
  exchange_currency_symbol TEXT,
  exchange_rate TEXT NOT NULL DEFAULT '1.0000',
  edit_count INTEGER NOT NULL DEFAULT 0,
  edited_at TEXT,
  last_edit_reason TEXT,
  notes TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_sales_created_at ON sales(created_at);
CREATE INDEX IF NOT EXISTS idx_sales_invoice_number ON sales(invoice_number);

CREATE TABLE IF NOT EXISTS sale_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sale_id INTEGER NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
  product_id INTEGER NOT NULL REFERENCES products(id),
  quantity TEXT NOT NULL,
  unit_price TEXT NOT NULL,
  unit_cost TEXT NOT NULL DEFAULT '0.0000',
  discount TEXT NOT NULL DEFAULT '0.0000',
  total_price TEXT NOT NULL,
  profit_amount TEXT NOT NULL DEFAULT '0.0000'
);

CREATE INDEX IF NOT EXISTS idx_sale_items_sale_id ON sale_items(sale_id);
CREATE INDEX IF NOT EXISTS idx_sale_items_product_id ON sale_items(product_id);

CREATE TABLE IF NOT EXISTS purchases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  invoice_number TEXT UNIQUE NOT NULL,
  supplier_name TEXT,
  total_amount TEXT NOT NULL DEFAULT '0.0000',
  paid_amount TEXT NOT NULL DEFAULT '0.0000',
  notes TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS purchase_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  purchase_id INTEGER NOT NULL REFERENCES purchases(id) ON DELETE CASCADE,
  product_id INTEGER NOT NULL REFERENCES products(id),
  quantity TEXT NOT NULL,
  unit_price TEXT NOT NULL,
  total_price TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stock_movements (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id INTEGER NOT NULL REFERENCES products(id),
  movement_type TEXT NOT NULL CHECK (movement_type IN (
    'initial','sale','purchase','sale_return','adjustment_in','adjustment_out'
  )),
  quantity_change TEXT NOT NULL,
  quantity_before TEXT NOT NULL,
  quantity_after TEXT NOT NULL,
  reference_id INTEGER,
  reference_type TEXT,
  note TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_stock_movements_product ON stock_movements(product_id);
CREATE INDEX IF NOT EXISTS idx_stock_movements_created ON stock_movements(created_at);
CREATE INDEX IF NOT EXISTS idx_stock_movements_ref ON stock_movements(reference_type, reference_id);

CREATE TABLE IF NOT EXISTS app_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  level TEXT NOT NULL,
  message TEXT NOT NULL,
  context TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

INSERT OR IGNORE INTO invoice_sequences(prefix, last_number) VALUES ('SALE', 0);
INSERT OR IGNORE INTO invoice_sequences(prefix, last_number) VALUES ('PUR', 0);
INSERT OR IGNORE INTO settings(key, value) VALUES ('store_name', 'Rayyan Lite');
INSERT OR IGNORE INTO settings(key, value) VALUES ('allow_negative_stock', 'false');

INSERT OR IGNORE INTO settings(key, value) VALUES ('currency_name', 'ليرة سورية');
INSERT OR IGNORE INTO settings(key, value) VALUES ('currency_symbol', 'ل.س');
INSERT OR IGNORE INTO settings(key, value) VALUES ('exchange_currency_name', 'دولار');
INSERT OR IGNORE INTO settings(key, value) VALUES ('exchange_currency_symbol', '$');
INSERT OR IGNORE INTO settings(key, value) VALUES ('exchange_rate', '1.0000');

INSERT OR IGNORE INTO settings(key, value) VALUES ('theme_mode', 'light');
