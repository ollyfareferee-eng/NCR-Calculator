import json
import os
import sqlite3
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "ncr_data.db"
PORT = int(os.environ.get("PORT", "3000"))

DEFAULT_MATERIALS = [
    {"name": "Carbon Steel", "unitCost": 12.50},
    {"name": "Stainless Steel", "unitCost": 18.75},
    {"name": "Bronze", "unitCost": 16.00},
    {"name": "Alloy Steel", "unitCost": 21.50},
]

DEFAULT_SUPPLIERS = [
    {"name": "Apex Pumps", "leadDays": 12, "handling": 42.50, "delayPerDay": 9.50},
    {"name": "HydroFlow Supply", "leadDays": 18, "handling": 28.00, "delayPerDay": 7.25},
    {"name": "BearingWorks", "leadDays": 7, "handling": 20.00, "delayPerDay": 6.00},
]

DEFAULT_COMPONENTS = [
    {"name": "Air Release Filter", "classification": "factored"},
    {"name": "Bellows", "classification": "factored"},
    {"name": "Blind Flange", "classification": "factored"},
    {"name": "Bolt", "classification": "factored"},
    {"name": "Cable", "classification": "factored"},
    {"name": "Coupling", "classification": "factored"},
    {"name": "Gearbox", "classification": "factored"},
    {"name": "Instrument Panel", "classification": "factored"},
    {"name": "Journal Bearing", "classification": "factored"},
    {"name": "Mechanical Seal", "classification": "factored"},
    {"name": "Motor", "classification": "factored"},
    {"name": "Pressure Indicator", "classification": "factored"},
    {"name": "Pump Package", "classification": "factored"},
    {"name": "Valve", "classification": "factored"},
    {"name": "Variable Frequency Drive (VFD)", "classification": "factored"},
    {"name": "Vibration Probe", "classification": "factored"},
    {"name": "Balance Drum", "classification": "non-factored"},
    {"name": "Baseplate", "classification": "non-factored"},
    {"name": "Bearing Housing", "classification": "non-factored"},
    {"name": "Case", "classification": "non-factored"},
    {"name": "Diffuser", "classification": "non-factored"},
    {"name": "Discharge Cover", "classification": "non-factored"},
    {"name": "Impeller", "classification": "non-factored"},
    {"name": "Manifold", "classification": "non-factored"},
    {"name": "Pipe", "classification": "non-factored"},
    {"name": "Pump Case", "classification": "non-factored"},
    {"name": "Pump Shaft", "classification": "non-factored"},
    {"name": "Shaft", "classification": "non-factored"},
    {"name": "Suction Cover", "classification": "non-factored"},
    {"name": "Support", "classification": "non-factored"},
    {"name": "Throttle Sleeve", "classification": "non-factored"},
    {"name": "Volute Case", "classification": "non-factored"},
]


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect_db()
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            unit_cost REAL NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            lead_days REAL NOT NULL DEFAULT 0,
            handling REAL NOT NULL DEFAULT 0,
            delay_per_day REAL NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS components (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            classification TEXT NOT NULL CHECK(classification IN ('factored', 'non-factored')),
            material_id INTEGER,
            supplier_id INTEGER,
            FOREIGN KEY (material_id) REFERENCES materials(id),
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        )
        """
    )
    conn.commit()
    conn.close()


def upsert_materials(materials):
    conn = connect_db()
    for item in materials:
        conn.execute(
            "INSERT OR IGNORE INTO materials (name, unit_cost) VALUES (?, ?)",
            (item["name"], float(item.get("unitCost", 0) or 0)),
        )
        conn.execute(
            "UPDATE materials SET unit_cost = ? WHERE name = ?",
            (float(item.get("unitCost", 0) or 0), item["name"]),
        )
    conn.commit()
    conn.close()


def upsert_suppliers(suppliers):
    conn = connect_db()
    for item in suppliers:
        conn.execute(
            "INSERT OR IGNORE INTO suppliers (name, lead_days, handling, delay_per_day) VALUES (?, ?, ?, ?)",
            (
                item["name"],
                float(item.get("leadDays", 0) or 0),
                float(item.get("handling", 0) or 0),
                float(item.get("delayPerDay", 0) or 0),
            ),
        )
        conn.execute(
            "UPDATE suppliers SET lead_days = ?, handling = ?, delay_per_day = ? WHERE name = ?",
            (
                float(item.get("leadDays", 0) or 0),
                float(item.get("handling", 0) or 0),
                float(item.get("delayPerDay", 0) or 0),
                item["name"],
            ),
        )
    conn.commit()
    conn.close()


def upsert_components(components):
    conn = connect_db()
    for item in components:
        name = item["name"]
        classification = item.get("classification", "factored")
        material_name = item.get("material") or item.get("materialName")
        supplier_name = item.get("supplier") or item.get("supplierName")

        material_id = None
        if material_name:
            material_row = conn.execute("SELECT id FROM materials WHERE name = ?", (material_name,)).fetchone()
            if material_row:
                material_id = material_row["id"]

        supplier_id = None
        if supplier_name:
            supplier_row = conn.execute("SELECT id FROM suppliers WHERE name = ?", (supplier_name,)).fetchone()
            if supplier_row:
                supplier_id = supplier_row["id"]

        conn.execute(
            "INSERT OR IGNORE INTO components (name, classification, material_id, supplier_id) VALUES (?, ?, ?, ?)",
            (name, classification, material_id, supplier_id),
        )
        conn.execute(
            "UPDATE components SET classification = ?, material_id = ?, supplier_id = ? WHERE name = ?",
            (classification, material_id, supplier_id, name),
        )
    conn.commit()
    conn.close()


def seed_default_data():
    conn = connect_db()
    materials_count = conn.execute("SELECT COUNT(*) FROM materials").fetchone()[0]
    suppliers_count = conn.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0]
    components_count = conn.execute("SELECT COUNT(*) FROM components").fetchone()[0]
    conn.close()

    if materials_count == 0:
        upsert_materials(DEFAULT_MATERIALS)
    if suppliers_count == 0:
        upsert_suppliers(DEFAULT_SUPPLIERS)
    if components_count == 0:
        # assign default material/supplier matches based on original sample data
        direct_components = []
        for comp in DEFAULT_COMPONENTS:
            name = comp["name"]
            direct_components.append({
                "name": name,
                "classification": comp["classification"],
                "material": "Carbon Steel" if name not in {"Mechanical Seal", "Bellows", "Gearbox", "Pump Package", "Instrument Panel", "Motor", "Pressure Indicator", "Vibration Probe", "Valve", "Variable Frequency Drive (VFD)"} else "Stainless Steel",
                "supplier": "Apex Pumps" if name not in {"Mechanical Seal", "Bellows", "Gearbox", "Pump Package", "Instrument Panel", "Motor", "Pressure Indicator", "Vibration Probe", "Valve", "Variable Frequency Drive (VFD)"} else "HydroFlow Supply",
            })
        upsert_components(direct_components)


def fetch_master_data():
    conn = connect_db()
    materials = [
        {"name": row["name"], "unitCost": float(row["unit_cost"])}
        for row in conn.execute("SELECT name, unit_cost FROM materials ORDER BY name").fetchall()
    ]
    suppliers = [
        {
            "name": row["name"],
            "leadDays": float(row["lead_days"]),
            "handling": float(row["handling"]),
            "delayPerDay": float(row["delay_per_day"]),
        }
        for row in conn.execute("SELECT name, lead_days, handling, delay_per_day FROM suppliers ORDER BY name").fetchall()
    ]

    material_lookup = {item["name"]: index for index, item in enumerate(materials)}
    supplier_lookup = {item["name"]: index for index, item in enumerate(suppliers)}

    components = []
    for row in conn.execute(
        "SELECT c.name, c.classification, m.name AS material_name, s.name AS supplier_name FROM components c LEFT JOIN materials m ON m.id = c.material_id LEFT JOIN suppliers s ON s.id = c.supplier_id ORDER BY c.name"
    ).fetchall():
        components.append({
            "name": row["name"],
            "classification": row["classification"],
            "materialIndex": material_lookup.get(row["material_name"], 0 if materials else -1),
            "supplierIndex": supplier_lookup.get(row["supplier_name"], 0 if suppliers else -1),
        })

    conn.close()
    return {"materials": materials, "suppliers": suppliers, "components": components}


def read_json_body(handler):
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON payload")


class CalculatorHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/components":
            self._send_json(fetch_master_data())
            return
        if path == "/api/materials":
            self._send_json({"materials": fetch_master_data()["materials"]})
            return
        if path == "/api/suppliers":
            self._send_json({"suppliers": fetch_master_data()["suppliers"]})
            return
        if path == "/api/health":
            self._send_json({"status": "ok", "database": str(DB_PATH)})
            return
        if path in ("", "/"):
            target = ROOT / "calculator.html"
            content = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return
        super().do_GET()

    def do_POST(self):
        path = urlsplit(self.path).path
        if path == "/api/sync":
            try:
                payload = read_json_body(self)
                materials = payload.get("materials", [])
                suppliers = payload.get("suppliers", [])
                components = payload.get("components", [])
                if materials:
                    upsert_materials(materials)
                if suppliers:
                    upsert_suppliers(suppliers)
                if components:
                    upsert_components(components)
                self._send_json({"status": "ok", "message": "Data synced successfully", "data": fetch_master_data()})
                return
            except ValueError:
                self._send_json({"status": "error", "message": "Invalid JSON payload"}, status=400)
                return
        self._send_json({"status": "error", "message": "Unsupported endpoint"}, status=404)

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    init_db()
    seed_default_data()
    print(f"Starting NCR calculator backend on http://localhost:{PORT}")
    print(f"Component data: http://localhost:{PORT}/api/components")
    print(f"Data sync endpoint: http://localhost:{PORT}/api/sync")
    ThreadingHTTPServer(("127.0.0.1", PORT), CalculatorHandler).serve_forever()
