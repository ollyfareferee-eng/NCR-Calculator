const http = require('http');
const fs = require('fs');
const path = require('path');

const HOST = '0.0.0.0';
const PORT = Number(process.env.PORT || 3000);
const ROOT = __dirname;
const CSV_PATH = path.join(ROOT, 'sap_master_template.csv');

function parseCsvRows(csvText) {
  const rows = [];
  let current = '';
  let row = [];
  let inQuotes = false;

  const commitCell = () => {
    if (inQuotes && current.endsWith('"')) {
      current = current.slice(0, -1);
    }
    row.push(current);
    current = '';
  };

  const commitRow = () => {
    commitCell();
    rows.push(row);
    row = [];
  };

  for (let i = 0; i < csvText.length; i += 1) {
    const ch = csvText[i];
    const next = csvText[i + 1];

    if (ch === '"') {
      if (inQuotes && next === '"') {
        current += '"';
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (ch === ',' && !inQuotes) {
      commitCell();
      continue;
    }

    if ((ch === '\n' || ch === '\r') && !inQuotes) {
      if (ch === '\r' && next === '\n') {
        i += 1;
      }
      commitRow();
      continue;
    }

    current += ch;
  }

  if (current.length > 0 || row.length > 0) {
    commitRow();
  }

  return rows.filter((values) => values.some((value) => String(value).trim() !== ''));
}

function buildFallbackData() {
  return {
    materials: [
      { name: 'Carbon Steel', unitCost: 12.50 },
      { name: 'Stainless Steel', unitCost: 18.75 },
      { name: 'Bronze', unitCost: 16.00 },
      { name: 'Alloy Steel', unitCost: 21.50 }
    ],
    suppliers: [
      { name: 'Apex Pumps', leadDays: 12, handling: 42.50, delayPerDay: 9.50 },
      { name: 'HydroFlow Supply', leadDays: 18, handling: 28.00, delayPerDay: 7.25 },
      { name: 'BearingWorks', leadDays: 7, handling: 20.00, delayPerDay: 6.00 }
    ],
    components: [
      { name: 'Air Release Filter', classification: 'factored', materialIndex: 0, supplierIndex: 0 },
      { name: 'Bellows', classification: 'factored', materialIndex: 1, supplierIndex: 1 },
      { name: 'Blind Flange', classification: 'factored', materialIndex: 0, supplierIndex: 0 },
      { name: 'Bolt', classification: 'factored', materialIndex: 0, supplierIndex: 0 },
      { name: 'Coupling', classification: 'factored', materialIndex: 0, supplierIndex: 0 },
      { name: 'Gearbox', classification: 'factored', materialIndex: 1, supplierIndex: 2 },
      { name: 'Instrument Panel', classification: 'factored', materialIndex: 0, supplierIndex: 1 },
      { name: 'Journal Bearing', classification: 'factored', materialIndex: 0, supplierIndex: 2 },
      { name: 'Mechanical Seal', classification: 'factored', materialIndex: 1, supplierIndex: 2 },
      { name: 'Motor', classification: 'factored', materialIndex: 0, supplierIndex: 0 },
      { name: 'Pressure Indicator', classification: 'factored', materialIndex: 0, supplierIndex: 0 },
      { name: 'Pump Package', classification: 'factored', materialIndex: 1, supplierIndex: 1 },
      { name: 'Valve', classification: 'factored', materialIndex: 0, supplierIndex: 1 },
      { name: 'Variable Frequency Drive (VFD)', classification: 'factored', materialIndex: 0, supplierIndex: 0 },
      { name: 'Vibration Probe', classification: 'factored', materialIndex: 0, supplierIndex: 1 },
      { name: 'Balance Drum', classification: 'non-factored', materialIndex: 2, supplierIndex: 0 },
      { name: 'Baseplate', classification: 'non-factored', materialIndex: 0, supplierIndex: 1 },
      { name: 'Bearing Housing', classification: 'non-factored', materialIndex: 1, supplierIndex: 2 },
      { name: 'Case', classification: 'non-factored', materialIndex: 0, supplierIndex: 0 },
      { name: 'Diffuser', classification: 'non-factored', materialIndex: 1, supplierIndex: 0 },
      { name: 'Discharge Cover', classification: 'non-factored', materialIndex: 0, supplierIndex: 1 },
      { name: 'Impeller', classification: 'non-factored', materialIndex: 2, supplierIndex: 1 },
      { name: 'Manifold', classification: 'non-factored', materialIndex: 0, supplierIndex: 0 },
      { name: 'Pipe', classification: 'non-factored', materialIndex: 0, supplierIndex: 1 },
      { name: 'Pump Case', classification: 'non-factored', materialIndex: 0, supplierIndex: 0 },
      { name: 'Pump Shaft', classification: 'non-factored', materialIndex: 1, supplierIndex: 0 },
      { name: 'Shaft', classification: 'non-factored', materialIndex: 1, supplierIndex: 0 },
      { name: 'Suction Cover', classification: 'non-factored', materialIndex: 0, supplierIndex: 1 },
      { name: 'Support', classification: 'non-factored', materialIndex: 0, supplierIndex: 0 },
      { name: 'Throttle Sleeve', classification: 'non-factored', materialIndex: 0, supplierIndex: 1 },
      { name: 'Volute Case', classification: 'non-factored', materialIndex: 0, supplierIndex: 0 }
    ]
  };
}

function loadSapData() {
  if (!fs.existsSync(CSV_PATH)) {
    return buildFallbackData();
  }

  try {
    const csvText = fs.readFileSync(CSV_PATH, 'utf8');
    const rows = parseCsvRows(csvText);

    if (rows.length < 2) {
      return buildFallbackData();
    }

    const headers = rows[0].map((header) => String(header).trim());
    const suppliers = [];
    const materials = [];
    const components = [];
    const supplierMap = new Map();
    const materialMap = new Map();

    rows.slice(1).forEach((values) => {
      const row = Object.fromEntries(headers.map((header, index) => [header, values[index] !== undefined && values[index] !== null ? values[index] : '']));
      const vendorName = String(row.VendorName || 'Unknown Vendor').trim();
      const vendorCode = String(row.VendorCode || '').trim();
      const materialCode = String(row.MaterialCode || '').trim();
      const materialName = String(row.MaterialDescription || materialCode || 'Unknown material').trim();
      const classification = String(row.Classification || 'non-factored').trim() || 'non-factored';
      const unitCost = Number(row.NetPrice) || 0;
      const leadDays = Number(row.LeadDays) || 0;
      const handling = Number(row.Handling || row.HandlingCost || row.SupplierHandling || row.HandlingCostGBP || 0) || 0;
      const delayPerDay = Number(row.DelayPerDay || row.DelayCostPerDay || row.DelayDaysPerDay || 0) || 0;
      const dataCurrency = String(row.Currency || 'GBP').trim();

      if (!supplierMap.has(vendorName)) {
        const supplierIndex = suppliers.length;
        supplierMap.set(vendorName, supplierIndex);
        suppliers.push({
          name: vendorName,
          vendorCode,
          leadDays,
          handling,
          delayPerDay,
          currency: dataCurrency
        });
      }

      if (!materialMap.has(materialCode || materialName)) {
        const materialIndex = materials.length;
        materialMap.set(materialCode || materialName, materialIndex);
        materials.push({
          name: materialName,
          materialCode,
          unitCost,
          currency: dataCurrency,
          vendorName,
          vendorCode,
          classification,
          leadDays
        });
      }

      components.push({
        name: materialName,
        materialCode,
        vendorCode,
        vendorName,
        classification,
        materialIndex: materialMap.get(materialCode || materialName) !== undefined && materialMap.get(materialCode || materialName) !== null ? materialMap.get(materialCode || materialName) : 0,
        supplierIndex: supplierMap.get(vendorName) !== undefined && supplierMap.get(vendorName) !== null ? supplierMap.get(vendorName) : 0,
        unitCost,
        leadDays,
        currency: dataCurrency
      });
    });

    return {
      materials,
      suppliers,
      components: components.length ? components : buildFallbackData().components
    };
  } catch (error) {
    console.warn('Unable to load SAP CSV, using built-in fallback data instead:', error.message);
    return buildFallbackData();
  }
}

const mimeTypes = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.ico': 'image/x-icon'
};

function sendJson(res, data) {
  res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(data, null, 2));
}

function serveStaticFile(requestPath, res) {
  const requestedPath = requestPath === '/' ? '/calculator.html' : requestPath;
  const safePath = decodeURIComponent(path.normalize(requestedPath).replace(/^\.+/, ''));
  const filePath = path.resolve(ROOT, safePath.replace(/^\/+/, ''));
  const rootPath = path.resolve(ROOT);
  const relativePath = path.relative(rootPath, filePath);

  if (relativePath.startsWith('..') || path.isAbsolute(relativePath)) {
    res.writeHead(403, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end('Forbidden');
    return;
  }

  fs.readFile(filePath, (error, contents) => {
    if (error) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('Not found');
      return;
    }

    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, { 'Content-Type': mimeTypes[ext] || 'application/octet-stream' });
    res.end(contents);
  });
}

const masterData = loadSapData();

function startServer(port) {
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, `http://${HOST}`);

    if (url.pathname === '/api/components') {
      sendJson(res, masterData);
      return;
    }

    serveStaticFile(url.pathname, res);
  });

  server.on('error', (error) => {
    if (error.code === 'EADDRINUSE') {
      const nextPort = port + 1;
      console.warn(`Port ${port} is already in use. Trying http://localhost:${nextPort} instead.`);
      startServer(nextPort);
      return;
    }

    console.error('Unable to start the server:', error);
    process.exitCode = 1;
  });

  server.listen(port, HOST, () => {
    console.log(`NCR cost calculator backend is running at http://${HOST}:${port}`);
    console.log('Data source available at http://' + HOST + ':' + port + '/api/components');
  });
}

startServer(PORT);

