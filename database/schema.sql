-- =====================================================================
-- نظام إدارة الأعمال المتكامل (ERP) - مخطط قاعدة البيانات SQLite
-- =====================================================================
PRAGMA foreign_keys = ON;

-- =====================  1) نظام الدخول والصلاحيات  =====================
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    role_id INTEGER REFERENCES roles(id),
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id INTEGER REFERENCES roles(id),
    module TEXT NOT NULL,
    can_view INTEGER DEFAULT 0,
    can_add INTEGER DEFAULT 0,
    can_edit INTEGER DEFAULT 0,
    can_delete INTEGER DEFAULT 0,
    UNIQUE(role_id, module)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    action TEXT,          -- add / edit / delete / login / logout
    table_name TEXT,
    record_id INTEGER,
    details TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- =====================  2) إعداد الشركة  =====================
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT,
    phone TEXT,
    tax_number TEXT,
    logo_path TEXT
);

CREATE TABLE IF NOT EXISTS branches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER REFERENCES companies(id),
    name TEXT NOT NULL,
    address TEXT
);

CREATE TABLE IF NOT EXISTS warehouses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    branch_id INTEGER REFERENCES branches(id),
    name TEXT NOT NULL,
    location TEXT,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS fiscal_years (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    is_closed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS currencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    rate REAL DEFAULT 1,
    is_base INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS taxes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    rate REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- =====================  3) الدليل المحاسبي  =====================
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('asset','liability','equity','revenue','expense')),
    parent_id INTEGER REFERENCES accounts(id),
    is_control INTEGER DEFAULT 0,   -- حساب رئيسي لا تسجل عليه قيود مباشرة
    balance REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cost_centers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);

-- =====================  4) البيانات الأساسية  =====================
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category_id INTEGER REFERENCES categories(id),
    unit_id INTEGER REFERENCES units(id),
    cost_price REAL DEFAULT 0,
    sale_price REAL DEFAULT 0,
    reorder_level REAL DEFAULT 0,
    is_raw_material INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price REAL DEFAULT 0,
    account_id INTEGER REFERENCES accounts(id),
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,
    name TEXT NOT NULL,
    phone TEXT,
    address TEXT,
    account_id INTEGER REFERENCES accounts(id),
    opening_balance REAL DEFAULT 0,
    credit_limit REAL DEFAULT 0,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,
    name TEXT NOT NULL,
    phone TEXT,
    address TEXT,
    account_id INTEGER REFERENCES accounts(id),
    opening_balance REAL DEFAULT 0,
    is_active INTEGER DEFAULT 1
);

-- =====================  5) المخزون  =====================
CREATE TABLE IF NOT EXISTS inventory_stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER REFERENCES items(id),
    warehouse_id INTEGER REFERENCES warehouses(id),
    quantity REAL DEFAULT 0,
    UNIQUE(item_id, warehouse_id)
);

CREATE TABLE IF NOT EXISTS inventory_moves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER REFERENCES items(id),
    warehouse_id INTEGER REFERENCES warehouses(id),
    move_type TEXT NOT NULL,     -- in / out
    quantity REAL NOT NULL,
    unit_cost REAL DEFAULT 0,
    ref_type TEXT,               -- sales_invoice / purchase_invoice / adjustment / transfer / production ...
    ref_id INTEGER,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS stock_adjustments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT,
    date TEXT,
    item_id INTEGER REFERENCES items(id),
    warehouse_id INTEGER REFERENCES warehouses(id),
    qty_before REAL,
    qty_after REAL,
    difference REAL,
    reason TEXT,
    notes TEXT,
    created_by INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS stock_transfers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT,
    date TEXT,
    item_id INTEGER REFERENCES items(id),
    from_warehouse INTEGER REFERENCES warehouses(id),
    to_warehouse INTEGER REFERENCES warehouses(id),
    quantity REAL,
    notes TEXT,
    created_by INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

-- =====================  6) المبيعات  =====================
CREATE TABLE IF NOT EXISTS sales_invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT UNIQUE,
    date TEXT NOT NULL,
    customer_id INTEGER REFERENCES customers(id),
    warehouse_id INTEGER REFERENCES warehouses(id),
    payment_type TEXT NOT NULL CHECK(payment_type IN ('cash','credit')),
    subtotal REAL DEFAULT 0,
    discount REAL DEFAULT 0,
    tax_total REAL DEFAULT 0,
    total REAL DEFAULT 0,
    cost_total REAL DEFAULT 0,
    paid_amount REAL DEFAULT 0,
    status TEXT DEFAULT 'posted',   -- draft / posted / cancelled
    notes TEXT,
    created_by INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sales_invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER REFERENCES sales_invoices(id) ON DELETE CASCADE,
    item_id INTEGER REFERENCES items(id),
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    cost_price REAL DEFAULT 0,
    discount REAL DEFAULT 0,
    total REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS sales_returns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT,
    date TEXT,
    invoice_id INTEGER REFERENCES sales_invoices(id),
    customer_id INTEGER REFERENCES customers(id),
    warehouse_id INTEGER REFERENCES warehouses(id),
    total REAL DEFAULT 0,
    notes TEXT,
    created_by INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sales_return_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    return_id INTEGER REFERENCES sales_returns(id) ON DELETE CASCADE,
    item_id INTEGER REFERENCES items(id),
    quantity REAL,
    price REAL,
    cost_price REAL DEFAULT 0,
    total REAL
);

-- =====================  7) المشتريات  =====================
CREATE TABLE IF NOT EXISTS purchase_invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT UNIQUE,
    date TEXT NOT NULL,
    supplier_id INTEGER REFERENCES suppliers(id),
    warehouse_id INTEGER REFERENCES warehouses(id),
    payment_type TEXT NOT NULL CHECK(payment_type IN ('cash','credit')),
    subtotal REAL DEFAULT 0,
    discount REAL DEFAULT 0,
    tax_total REAL DEFAULT 0,
    total REAL DEFAULT 0,
    paid_amount REAL DEFAULT 0,
    status TEXT DEFAULT 'posted',
    notes TEXT,
    created_by INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS purchase_invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER REFERENCES purchase_invoices(id) ON DELETE CASCADE,
    item_id INTEGER REFERENCES items(id),
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    discount REAL DEFAULT 0,
    total REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS purchase_returns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT,
    date TEXT,
    invoice_id INTEGER REFERENCES purchase_invoices(id),
    supplier_id INTEGER REFERENCES suppliers(id),
    warehouse_id INTEGER REFERENCES warehouses(id),
    total REAL DEFAULT 0,
    notes TEXT,
    created_by INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS purchase_return_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    return_id INTEGER REFERENCES purchase_returns(id) ON DELETE CASCADE,
    item_id INTEGER REFERENCES items(id),
    quantity REAL,
    price REAL,
    total REAL
);

-- =====================  8) الصندوق / البنك / السندات  =====================
CREATE TABLE IF NOT EXISTS receipt_vouchers (   -- سند قبض
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT,
    date TEXT NOT NULL,
    customer_id INTEGER REFERENCES customers(id),
    amount REAL NOT NULL,
    method TEXT NOT NULL CHECK(method IN ('cash','bank')),
    notes TEXT,
    created_by INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS payment_vouchers (   -- سند صرف
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT,
    date TEXT NOT NULL,
    supplier_id INTEGER REFERENCES suppliers(id),
    amount REAL NOT NULL,
    method TEXT NOT NULL CHECK(method IN ('cash','bank')),
    notes TEXT,
    created_by INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT,
    date TEXT NOT NULL,
    category TEXT,
    amount REAL NOT NULL,
    method TEXT NOT NULL CHECK(method IN ('cash','bank')),
    description TEXT,
    created_by INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS revenues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT,
    date TEXT NOT NULL,
    category TEXT,
    amount REAL NOT NULL,
    method TEXT NOT NULL CHECK(method IN ('cash','bank')),
    description TEXT,
    created_by INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS bank_transfers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT,
    date TEXT NOT NULL,
    direction TEXT NOT NULL CHECK(direction IN ('cash_to_bank','bank_to_cash')),
    amount REAL NOT NULL,
    notes TEXT,
    created_by INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

-- =====================  9) الإنتاج  =====================
CREATE TABLE IF NOT EXISTS production_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT,
    date TEXT NOT NULL,
    product_item_id INTEGER REFERENCES items(id),
    warehouse_id INTEGER REFERENCES warehouses(id),
    quantity REAL NOT NULL,
    status TEXT DEFAULT 'posted',
    notes TEXT,
    created_by INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS production_materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER REFERENCES production_orders(id) ON DELETE CASCADE,
    item_id INTEGER REFERENCES items(id),
    quantity REAL NOT NULL,
    unit_cost REAL DEFAULT 0
);

-- =====================  10) المحرك المحاسبي  =====================
CREATE TABLE IF NOT EXISTS journal_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT,
    date TEXT NOT NULL,
    description TEXT,
    ref_type TEXT,
    ref_id INTEGER,
    created_by INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS journal_entry_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER REFERENCES journal_entries(id) ON DELETE CASCADE,
    account_id INTEGER REFERENCES accounts(id),
    debit REAL DEFAULT 0,
    credit REAL DEFAULT 0,
    cost_center_id INTEGER REFERENCES cost_centers(id)
);

-- =====================  فهارس لتحسين الأداء  =====================
CREATE INDEX IF NOT EXISTS idx_inv_moves_item ON inventory_moves(item_id, warehouse_id);
CREATE INDEX IF NOT EXISTS idx_jel_account ON journal_entry_lines(account_id);
CREATE INDEX IF NOT EXISTS idx_sales_customer ON sales_invoices(customer_id);
CREATE INDEX IF NOT EXISTS idx_purch_supplier ON purchase_invoices(supplier_id);
