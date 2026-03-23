const BASE_URL = "https://hazard-backend.onrender.com"; 

const searchInput = document.getElementById("searchInput");
const searchBtn = document.getElementById("searchBtn");
const statusEl = document.getElementById("status");
const loader = document.getElementById("loader");
const resultsEl = document.getElementById("results");
const locationNameEl = document.getElementById("locationName");
const summaryEl = document.getElementById("summary");
const mapSection = document.getElementById("mapSection");

let map;
let marker;

/* =========================
   ELITE UTILITIES
========================= */
function fetchWithTimeout(url, options = {}, timeout = 8000) {
    return Promise.race([
        fetch(url, options),
        new Promise((_, reject) =>
            setTimeout(() => reject(new Error("Request timed out")), timeout)
        )
    ]);
}

/* =========================
   EVENT LISTENERS
========================= */
searchBtn.addEventListener("click", search);

searchInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
        e.preventDefault(); 
        search();
    }
});

document.querySelectorAll(".example").forEach(el => {
    el.addEventListener("click", () => {
        searchInput.value = el.innerText;
        search(); 
    });
});

/* =========================
   MAIN SEARCH FUNCTION
========================= */
async function search() {
    // 🔥 3. Concurrency Lock: Prevent Multiple Parallel Calls
    if (loader.classList.contains("hidden") === false) return;

    const input = searchInput.value.trim();
    if (!input) return;

    searchBtn.disabled = true;
    searchBtn.style.cursor = "not-allowed";
    searchBtn.style.opacity = "0.7";

    // Reset UI State
    statusEl.innerText = "";
    resultsEl.classList.add("hidden");
    mapSection.classList.add("hidden");
    loader.classList.remove("hidden");

    try {
        // 🔍 STEP 1: GEOCODE
        // 🔥 1. Encode URL to handle spaces and special chars securely
        const geoRes = await fetchWithTimeout(`${BASE_URL}/api/search?place=${encodeURIComponent(input)}`);
        
        // 🔥 2. Smart Error Handling: Parse backend payload
        if (!geoRes.ok) {
            const errData = await geoRes.json().catch(() => null);
            throw new Error(errData?.error || "Location not found");
        }

        const loc = await geoRes.json();

        // 📡 STEP 2: FETCH RISK
        const riskRes = await fetchWithTimeout(`${BASE_URL}/api/risk?lat=${loc.lat}&lon=${loc.lon}`);
        
        // 🔥 2. Smart Error Handling: Parse backend payload
        if (!riskRes.ok) {
            const errData = await riskRes.json().catch(() => null);
            throw new Error(errData?.error || "Risk data fetch failed");
        }

        const data = await riskRes.json();

        // 🎨 STEP 3: RENDER
        renderResults(loc, data);

    } catch (err) {
        console.error("Search Pipeline Error:", err);
        // Display the actual error message thrown from the try block
        statusEl.innerHTML = `❌ ${err.message || "Unable to retrieve data. Try another location."}`;
    } finally {
        loader.classList.add("hidden");
        searchBtn.disabled = false;
        searchBtn.style.cursor = "pointer";
        searchBtn.style.opacity = "1";
    }
}

/* =========================
   RENDER RESULTS
========================= */
function renderResults(loc, data) {
    resultsEl.classList.remove("hidden");
    locationNameEl.innerText = loc.name;

    renderCard("heatwave", "Heatwave", data.heatwave);
    renderCard("flood", "Flood", data.flood);
    renderCard("drought", "Drought", data.drought);
    renderCard("rainfall", "Extreme Rainfall", data.extreme_rainfall);
    renderCard("landslide", "Landslide", data.landslide);

    updateSummary(data);
    updateMap(loc.lat, loc.lon, loc.name, data);
}

/* =========================
   CARD RENDERING
========================= */
function renderCard(id, title, obj) {
    const el = document.getElementById(id);
    if (!el || !obj) return; 

    el.classList.remove("low", "mild", "moderate", "high", "extreme");

    const severityClass = obj.severity.toLowerCase().replace(/\s+/g, '-');
    el.classList.add(severityClass);

    el.innerHTML = `
        <h3>${title}</h3>
        <p>${obj.risk}</p>
        <p>${obj.severity}</p>
    `;
}

/* =========================
   SUMMARY GENERATOR
========================= */
function updateSummary(data) {
    const risks = [
        { name: "Heatwave", value: data.heatwave.risk },
        { name: "Flood", value: data.flood.risk },
        { name: "Drought", value: data.drought.risk },
        { name: "Extreme Rainfall", value: data.extreme_rainfall.risk },
        { name: "Landslide", value: data.landslide.risk }
    ];

    const highest = risks.sort((a, b) => b.value - a.value)[0];

    if (highest.value > 60) {
        summaryEl.innerHTML = `<strong style="color: #ff7b72;">⚠ High ${highest.name} risk detected.</strong> Take necessary precautions.`;
    } else if (highest.value > 30) {
        summaryEl.innerHTML = `<strong style="color: #d29922;">⚠ Moderate ${highest.name} risk.</strong> Stay informed.`;
    } else {
        summaryEl.innerHTML = `<span style="color: #2ea043;">✅ No extreme hazard risks detected.</span>`;
    }
}

/* =========================
   MAP HANDLING
========================= */
function updateMap(lat, lon, name, data) {
    mapSection.classList.remove("hidden");

    const maxRisk = Math.max(
        data.heatwave.risk,
        data.flood.risk,
        data.drought.risk,
        data.extreme_rainfall.risk,
        data.landslide.risk
    );

    let markerColor = "#238636"; 
    if (maxRisk > 30) markerColor = "#d29922"; 
    if (maxRisk > 60) markerColor = "#ff0000"; 

    if (!map) {
        map = L.map('map').setView([lat, lon], 7);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap'
        }).addTo(map);
    } else {
        map.flyTo([lat, lon], 7, { duration: 1.5 });
    }

    setTimeout(() => {
        map.invalidateSize();
    }, 200);

    if (marker) marker.remove();

    marker = L.circleMarker([lat, lon], {
        radius: 12,
        color: markerColor,
        fillColor: markerColor,
        fillOpacity: 0.6,
        weight: 2
    }).addTo(map).bindPopup(`<strong>${name}</strong><br>Max Risk Score: ${maxRisk}`).openPopup();
}