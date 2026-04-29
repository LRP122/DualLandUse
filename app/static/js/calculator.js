'use strict';

// ── State ──────────────────────────────────────────────────────────────────
const state = {
  lat: null, lon: null,
  ghi: null, pvout: null,
  locationPicked: false,
};

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

const CROP_INFO = {
  lettuce_herbs:  'High shade tolerance. Yield may slightly improve under partial shade. Low hail risk.',
  potatoes:       'Medium-high shade tolerance. Yield impact is minimal. Very suitable for agrivoltaics.',
  wheat_barley:   'Medium shade tolerance. Expect ~15% yield reduction — offset by strong PV revenue.',
  maize:          'Low shade tolerance (C4 plant). Significant yield loss expected. PV revenue compensates well.',
  strawberries:   'Shade-tolerant with major hail protection benefit. Often net positive with agrivoltaics.',
  apples_fruit:   'Good shade tolerance. Hail protection is critical and very valuable for this crop.',
  grapes:         'Medium tolerance. Site-dependent yield impact. High hail protection value.',
  vegetables:     'Medium-high tolerance. Slight yield reduction, partially offset by protection benefits.',
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

  // Custom green marker icon
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

    // Fetch GHI from server
    document.getElementById('loc-ghi').textContent = '…';
    document.getElementById('loc-pvout').textContent = '…';
    document.getElementById('location-info').classList.remove('hidden');
    document.getElementById('loc-fallback-notice').classList.add('hidden');
    document.getElementById('loc-coords').textContent =
      `${lat.toFixed(4)}°N, ${lng.toFixed(4)}°E`;

    try {
      const res = await fetch(`/api/ghi-at-location?lat=${lat}&lon=${lng}`);
      const data = await res.json();

      if (data.ghi !== null && data.ghi !== undefined) {
        state.ghi = data.ghi;
        state.pvout = data.pvout;
        document.getElementById('loc-ghi').textContent = data.ghi.toFixed(2);
        document.getElementById('loc-pvout').textContent =
          data.pvout ? data.pvout.toFixed(2) : '—';
      } else {
        state.ghi = 3.5;
        state.pvout = null;
        document.getElementById('loc-ghi').textContent = '3.50 (avg)';
        document.getElementById('loc-pvout').textContent = '—';
        document.getElementById('loc-fallback-notice').classList.remove('hidden');
      }
    } catch (_) {
      state.ghi = 3.5;
      document.getElementById('loc-ghi').textContent = '3.50 (avg)';
    }

    state.locationPicked = true;
    document.getElementById('btn-next-1').disabled = false;
  });
}

// ── Step navigation ────────────────────────────────────────────────────────
function goToStep(n) {
  document.querySelectorAll('.step-card').forEach(c => c.classList.remove('active'));
  document.getElementById(`step-${n}`).classList.add('active');

  // Update step indicators
  document.querySelectorAll('.step-dot').forEach(dot => {
    const s = parseInt(dot.dataset.step);
    const circle = dot.querySelector('.step-circle');
    const label  = dot.querySelector('.step-label');
    circle.classList.remove('active-circle', 'done-circle', 'bg-gray-200', 'text-gray-500', 'bg-brand-500', 'text-white', 'bg-green-100', 'text-green-700');

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
  }
}

// ── Run calculation ────────────────────────────────────────────────────────
async function runCalculation() {
  const area     = parseFloat(document.getElementById('input-area').value) || 10;
  const crop     = document.getElementById('input-crop').value;
  const tariff   = parseFloat(document.getElementById('input-tariff').value) || 0.08;
  const irrigates = document.getElementById('input-irrigates').checked;

  goToStep(3);
  document.getElementById('results-loading').classList.remove('hidden');
  document.getElementById('results-content').classList.add('hidden');

  try {
    const res = await fetch('/api/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        area_ha: area,
        crop,
        ghi: state.ghi || 3.5,
        irrigates,
        tariff,
      }),
    });
    const d = await res.json();

    document.getElementById('results-loading').classList.add('hidden');
    document.getElementById('results-content').classList.remove('hidden');

    renderResults(d);
  } catch (err) {
    document.getElementById('results-loading').innerHTML =
      '<p class="text-red-500 p-8">Error: could not connect to server.</p>';
  }
}

// ── Render results ─────────────────────────────────────────────────────────
function renderResults(d) {
  // Score circle
  const circle = document.getElementById('score-circle');
  const circumference = 2 * Math.PI * 40; // r=40
  const scoreEl = document.getElementById('score-number');
  const labelEl = document.getElementById('score-label');
  const subtitleEl = document.getElementById('score-subtitle');

  const colorMap = { green: '#16a34a', amber: '#d97706', red: '#dc2626' };
  circle.style.stroke = colorMap[d.color] || '#16a34a';
  scoreEl.className = `text-5xl font-black score-${d.color}`;
  scoreEl.textContent = d.score;
  labelEl.className = `text-sm font-bold uppercase tracking-wide score-${d.color}`;
  labelEl.textContent = d.label + ' Potential';
  subtitleEl.textContent =
    `${d.area_ha} ha · ${d.crop_label} · ${d.ghi_daily} kWh/m²/day solar`;

  // Animate ring after a short delay
  setTimeout(() => {
    const offset = circumference - (d.score / 100) * circumference;
    circle.style.strokeDasharray = circumference;
    circle.style.strokeDashoffset = offset;
  }, 100);

  // Location / context
  document.getElementById('res-location').textContent =
    state.lat ? `${state.lat.toFixed(3)}°N, ${state.lon.toFixed(3)}°E` : 'Austria (average)';
  document.getElementById('res-ghi').textContent = d.ghi_daily;
  document.getElementById('res-crop').textContent = d.crop_label;

  // Energy
  set('res-pv-yield',    d.pv_yield_mwh.toLocaleString());
  set('res-pv-revenue',  d.pv_revenue.toLocaleString());
  set('res-pv-kwp',      d.pv_capacity_kwp.toLocaleString());

  // Financial
  set('res-total-benefit', d.total_benefit.toLocaleString());
  set('res-payback',  d.payback < 50 ? `${d.payback} years` : '> 50 years');
  set('res-lcoe',     `${d.lcoe_ct} ct/kWh`);
  set('res-capex',    `€${d.capex.toLocaleString()}`);

  // LER
  set('res-ler', d.ler);
  setTimeout(() => {
    const lerBar = document.getElementById('ler-bar');
    lerBar.style.width = `${Math.min((d.ler / 2) * 100, 100)}%`;
  }, 300);

  // Water
  if (d.water_saved_m3 > 0) {
    set('res-water', d.water_saved_m3.toLocaleString());
    set('res-water-label', `m³ per year saved  ·  ≈ €${d.water_value.toLocaleString()}`);
  } else {
    set('res-water', '—');
    set('res-water-label', 'Enable irrigation above to see savings');
  }
  set('res-irr-pct', d.irr_reduction_pct);

  // Crop yield
  const deltaColor = d.yield_delta_pct >= 0 ? 'text-brand-600' : 'text-red-500';
  document.getElementById('res-yield-delta').className = `text-3xl font-bold mb-1 ${deltaColor}`;
  set('res-yield-delta', (d.yield_delta_pct >= 0 ? '+' : '') + d.yield_delta_pct + '%');
  set('res-shade', d.shade_tolerance);
  const deltaAgriVal = d.delta_agri >= 0
    ? `+€${d.delta_agri.toLocaleString()}`
    : `−€${Math.abs(d.delta_agri).toLocaleString()}`;
  const deltaAgriEl = document.getElementById('res-delta-agri');
  deltaAgriEl.textContent = deltaAgriVal;
  deltaAgriEl.className = `font-semibold ${d.delta_agri >= 0 ? 'text-brand-600' : 'text-red-500'}`;

  // Hail
  set('res-hail',     d.hail_value.toLocaleString());
  set('res-risk-pct', d.risk_pct);

  // Monthly chart
  renderMonthlyChart(d.monthly_mwh);

  // Benefit breakdown
  renderBenefitBreakdown(d);

  // Animate result cards in
  setTimeout(() => {
    document.querySelectorAll('.result-card').forEach(c => c.classList.add('visible'));
  }, 50);
}

function set(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function renderMonthlyChart(monthly) {
  const container = document.getElementById('monthly-bars');
  const labelsEl  = document.getElementById('monthly-labels');
  const maxVal    = Math.max(...monthly);

  container.innerHTML = '';
  labelsEl.innerHTML  = '';

  monthly.forEach((val, i) => {
    const col = document.createElement('div');
    col.className = 'month-col';

    const bar = document.createElement('div');
    bar.className = 'month-bar';
    bar.style.height = '0px';
    bar.title = `${MONTHS[i]}: ${val} MWh`;

    col.appendChild(bar);
    container.appendChild(col);

    const lbl = document.createElement('div');
    lbl.className = 'month-col';
    lbl.innerHTML = `<span class="month-label">${MONTHS[i]}</span>`;
    labelsEl.appendChild(lbl);

    setTimeout(() => {
      bar.style.height = `${(val / maxVal) * 112}px`;
    }, 100 + i * 40);
  });
}

function renderBenefitBreakdown(d) {
  const container = document.getElementById('benefit-breakdown');
  container.innerHTML = '';

  const items = [
    { label: 'PV Revenue',        value: d.pv_revenue,   color: '#eab308' },
    { label: 'Agri margin change', value: d.delta_agri,   color: d.delta_agri >= 0 ? '#16a34a' : '#ef4444' },
    { label: 'Water savings',      value: d.water_value,  color: '#3b82f6' },
    { label: 'Hail protection',    value: d.hail_value,   color: '#f97316' },
  ];

  const maxVal = Math.max(...items.map(i => Math.abs(i.value)), 1);

  items.forEach(item => {
    const isNeg = item.value < 0;
    const row = document.createElement('div');
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
  state.locationPicked = false;

  if (marker) { map.removeLayer(marker); marker = null; }
  document.getElementById('location-info').classList.add('hidden');
  document.getElementById('loc-fallback-notice').classList.add('hidden');
  document.getElementById('btn-next-1').disabled = true;
  document.querySelectorAll('.result-card').forEach(c => c.classList.remove('visible'));

  goToStep(1);
}

// ── Init ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initMap();
  document.getElementById('input-crop').addEventListener('change', updateCropInfo);
  updateCropInfo();
});
