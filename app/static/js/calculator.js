'use strict';

// ── State ──────────────────────────────────────────────────────────────────
const state = {
  lat: null, lon: null,
  ghi: null, pvout: null,
  locationPicked: false,
};

let scenarios = null;  // { hot_dry: {...}, cold_humid: {...} } after calculation

const CROP_INFO = {
  winter_wheat: 'Medium shade tolerance. Dominant Austrian cereal (~58 dt/ha). Expect yield loss in cold years, offset by PV revenue.',
  summer_wheat: 'Medium shade tolerance. Lower yields than winter wheat (~44 dt/ha). Same shade behaviour.',
  potatoes:     'Medium-high shade tolerance. Well suited to agrivoltaics, especially in dry years.',
  apples:       'Good shade tolerance. Partial shade can reduce sunburn damage on fruit.',
  vegetables:   'Medium-high tolerance. Small yield reduction partially offset by protection benefits.',
  maize:        'Not recommended. Maize (C4 plant) has very low shade tolerance — agrivoltaics are not profitable for this crop.',
};

// ── Map init ───────────────────────────────────────────────────────────────
let map, marker;

function initMap() {
  map = L.map('location-map', {
    center: [47.5, 13.5],
    zoom: 7,
    minZoom: 6,
    maxZoom: 14,
  });

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 19,
  }).addTo(map);

  const icon = L.divIcon({
    html: '<div class="pulse-marker"></div>',
    className: '',
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });

  map.on('click', async (e) => {
    const { lat, lng } = e.latlng;

    if (marker) map.removeLayer(marker);
    marker = L.marker([lat, lng], { icon }).addTo(map);

    state.lat = lat;
    state.lon = lng;

    document.getElementById('loc-pvout').textContent = '…';
    document.getElementById('location-info').classList.remove('hidden');
    document.getElementById('loc-fallback-notice').classList.add('hidden');
    document.getElementById('loc-coords').textContent =
      `${lat.toFixed(4)}°N, ${lng.toFixed(4)}°E`;

    try {
      const res  = await fetch(`/api/ghi-at-location?lat=${lat}&lon=${lng}`);
      const data = await res.json();

      if (data.ghi !== null && data.ghi !== undefined) {
        state.ghi   = data.ghi;
        state.pvout = data.pvout;
        document.getElementById('loc-pvout').textContent =
          data.pvout ? data.pvout.toFixed(2) : '—';
      } else {
        state.ghi = 3.5;
        state.pvout = null;
        document.getElementById('loc-pvout').textContent = '2.80 (avg)';
        document.getElementById('loc-fallback-notice').classList.remove('hidden');
      }
    } catch (_) {
      state.ghi = 3.5;
      state.pvout = null;
      document.getElementById('loc-pvout').textContent = '2.80 (avg)';
    }

    state.locationPicked = true;
    document.getElementById('btn-next-1').disabled = false;
  });
}

// ── Step navigation ────────────────────────────────────────────────────────
function goToStep(n) {
  document.querySelectorAll('.step-card').forEach(c => c.classList.remove('active'));
  document.getElementById(`step-${n}`).classList.add('active');

  document.querySelectorAll('.step-dot').forEach(dot => {
    const s      = parseInt(dot.dataset.step);
    const circle = dot.querySelector('.step-circle');
    const label  = dot.querySelector('.step-label');
    circle.classList.remove('active-circle', 'done-circle', 'bg-gray-200', 'text-gray-500',
                            'bg-brand-500', 'text-white', 'bg-green-100', 'text-green-700');

    if (s < n) {
      circle.classList.add('done-circle');
      circle.innerHTML = '✓';
      if (label) { label.classList.remove('text-gray-400'); label.classList.add('text-brand-600'); }
    } else if (s === n) {
      circle.classList.add('active-circle');
      circle.innerHTML = s;
      if (label) { label.classList.remove('text-gray-400'); label.classList.add('text-brand-600'); }
    } else {
      circle.classList.add('bg-gray-200', 'text-gray-500');
      circle.innerHTML = s;
      if (label) { label.classList.add('text-gray-400'); label.classList.remove('text-brand-600'); }
    }
  });

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── Crop info box ──────────────────────────────────────────────────────────
function updateCropInfo() {
  const crop = document.getElementById('input-crop').value;
  const box  = document.getElementById('crop-info-box');
  const text = document.getElementById('crop-info-text');
  if (CROP_INFO[crop]) {
    text.textContent = '💡 ' + CROP_INFO[crop];
    box.classList.remove('hidden');
    box.className = crop === 'maize'
      ? 'mt-6 bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700'
      : 'mt-6 bg-gray-50 border border-gray-200 rounded-xl p-4 text-sm text-gray-600';
  }
}

// ── Run calculation ────────────────────────────────────────────────────────
async function runCalculation() {
  const area   = parseFloat(document.getElementById('input-area').value) || 10;
  const crop   = document.getElementById('input-crop').value;
  const tariff = parseFloat(document.getElementById('input-tariff').value) || 0.08;

  goToStep(3);
  document.getElementById('results-loading').classList.remove('hidden');
  document.getElementById('results-content').classList.add('hidden');
  document.getElementById('results-unprofitable').classList.add('hidden');

  try {
    const res = await fetch('/api/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ area_ha: area, crop, ghi: state.ghi || 3.5, pvout: state.pvout, tariff }),
    });
    const d = await res.json();

    document.getElementById('results-loading').classList.add('hidden');

    if (d.unprofitable) {
      document.getElementById('up-crop-label').textContent = d.crop_label;
      document.getElementById('up-reason').textContent     = d.reason;
      document.getElementById('results-unprofitable').classList.remove('hidden');
    } else {
      document.getElementById('results-content').classList.remove('hidden');
      renderResults(d);
    }
  } catch (err) {
    document.getElementById('results-loading').innerHTML =
      '<p class="text-red-500 p-8">Error: could not connect to server.</p>';
  }
}

// ── Render results ─────────────────────────────────────────────────────────
function renderResults(d) {
  scenarios = d;

  document.getElementById('res-location').textContent =
    state.lat ? `${state.lat.toFixed(3)}°N, ${state.lon.toFixed(3)}°E` : 'Austria (average)';
  document.getElementById('res-crop').textContent = d.crop_label;

  selectScenario('hot_dry');
}

// ── Scenario tab switcher ──────────────────────────────────────────────────
function selectScenario(key) {
  if (!scenarios) return;
  const d = scenarios[key];

  ['hot_dry', 'cold_humid'].forEach(k => {
    const btn = document.getElementById(`tab-${k}`);
    if (k === key) {
      btn.classList.add('bg-white', 'shadow-sm', 'text-gray-900');
      btn.classList.remove('text-gray-500');
    } else {
      btn.classList.remove('bg-white', 'shadow-sm', 'text-gray-900');
      btn.classList.add('text-gray-500');
    }
  });

  // Score ring
  const circle        = document.getElementById('score-circle');
  const circumference = 2 * Math.PI * 40;
  circle.style.strokeDasharray  = circumference;
  circle.style.strokeDashoffset = circumference;
  const colorMap = { green: '#16a34a', amber: '#d97706', red: '#dc2626' };
  circle.style.stroke = colorMap[d.color] || '#16a34a';

  const scoreEl    = document.getElementById('score-number');
  const labelEl    = document.getElementById('score-label');
  const subtitleEl = document.getElementById('score-subtitle');
  scoreEl.className   = `text-5xl font-black score-${d.color}`;
  scoreEl.textContent = d.score;
  labelEl.className   = `text-sm font-bold uppercase tracking-wide score-${d.color}`;
  labelEl.textContent = d.label + ' Potential';
  subtitleEl.textContent = `${d.area_ha} ha · ${d.crop_label} · ${d.pvout_daily} kWh/kWp/day PV output`;

  setTimeout(() => {
    circle.style.strokeDashoffset = circumference - (d.score / 100) * circumference;
  }, 100);

  document.getElementById('res-pvout').textContent = d.pvout_daily;

  // Energy
  set('res-pv-yield',   d.pv_yield_mwh.toLocaleString());
  set('res-pv-revenue', d.pv_revenue.toLocaleString());
  set('res-pv-kwp',     d.pv_capacity_kwp.toLocaleString());

  // Financial
  set('res-total-benefit', d.total_benefit.toLocaleString());
  set('res-water-saved',   d.water_saved_L.toLocaleString());
  set('res-payback', d.payback < 50 ? `${d.payback} years` : '> 50 years');
  set('res-lcoe',    `${d.lcoe_ct} ct/kWh`);
  set('res-capex',   `€${d.capex.toLocaleString()}`);
  set('res-opex',    `€${d.opex_annual.toLocaleString()}`);

  // Crop yield
  const deltaColor = d.yield_delta_pct >= 0 ? 'text-brand-600' : 'text-red-500';
  document.getElementById('res-yield-delta').className = `text-3xl font-bold mb-1 ${deltaColor}`;
  set('res-yield-delta', (d.yield_delta_pct >= 0 ? '+' : '') + d.yield_delta_pct + '%');
  set('res-base-revenue', `€${d.base_revenue.toLocaleString()}`);
  const deltaAgriVal = d.delta_agri >= 0
    ? `+€${d.delta_agri.toLocaleString()}`
    : `−€${Math.abs(d.delta_agri).toLocaleString()}`;
  const deltaAgriEl = document.getElementById('res-delta-agri');
  deltaAgriEl.textContent = deltaAgriVal;
  deltaAgriEl.className   = `font-semibold ${d.delta_agri >= 0 ? 'text-brand-600' : 'text-red-500'}`;

  renderBenefitBreakdown(d);

  setTimeout(() => {
    document.querySelectorAll('.result-card').forEach(c => c.classList.add('visible'));
  }, 50);
}

function set(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function renderBenefitBreakdown(d) {
  const container = document.getElementById('benefit-breakdown');
  container.innerHTML = '';

  const items = [
    { label: 'PV Revenue',         value: d.pv_revenue, color: '#eab308' },
    { label: 'O&M cost (Opex)',    value: -d.opex_annual, color: '#ef4444' },
    { label: 'Agri margin change',  value: d.delta_agri, color: d.delta_agri >= 0 ? '#16a34a' : '#ef4444' },
  ];

  const maxVal = Math.max(...items.map(i => Math.abs(i.value)), 1);

  items.forEach(item => {
    const isNeg = item.value < 0;
    const row   = document.createElement('div');
    row.className = 'benefit-row';
    row.innerHTML = `
      <div class="benefit-label">${item.label}</div>
      <div class="benefit-track">
        <div class="benefit-fill" style="background:${item.color};" data-width="${Math.abs(item.value) / maxVal * 100}"></div>
      </div>
      <div class="benefit-value" style="color:${isNeg ? '#ef4444' : '#111827'}">
        ${isNeg ? '−' : '+'}€${Math.abs(item.value).toLocaleString()}
      </div>`;
    container.appendChild(row);
  });

  setTimeout(() => {
    container.querySelectorAll('.benefit-fill').forEach(bar => {
      bar.style.width = bar.dataset.width + '%';
    });
  }, 200);
}

// ── Reset ──────────────────────────────────────────────────────────────────
function resetCalculator() {
  state.lat = null;
  state.lon = null;
  state.ghi = null;
  state.pvout = null;
  state.locationPicked = false;
  scenarios = null;

  if (marker) { map.removeLayer(marker); marker = null; }
  document.getElementById('location-info').classList.add('hidden');
  document.getElementById('loc-fallback-notice').classList.add('hidden');
  document.getElementById('btn-next-1').disabled = true;
  document.querySelectorAll('.result-card').forEach(c => c.classList.remove('visible'));
  document.getElementById('results-unprofitable').classList.add('hidden');
  document.getElementById('results-content').classList.add('hidden');

  goToStep(1);
}

// ── Init ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initMap();
  document.getElementById('input-crop').addEventListener('change', updateCropInfo);
  updateCropInfo();
});
