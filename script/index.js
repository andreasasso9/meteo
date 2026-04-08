lucide.createIcons();
let map, marker, timeoutRicerca;


document.getElementById('cityInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') cercaMeteo();
});

// Chiudi suggerimenti se clicchi fuori
document.addEventListener('click', (e) => {
    if (!document.getElementById('cityInput').contains(e.target)) {
        document.getElementById('suggestions').classList.add('hidden');
    }
});

async function gestisciInput(valore) {
    const suggDiv = document.getElementById('suggestions');
    if (valore.length < 2) { suggDiv.classList.add('hidden'); return; }

    clearTimeout(timeoutRicerca);
    timeoutRicerca = setTimeout(async () => {
        try {
            const response = await fetch(`/api/search/${encodeURIComponent(valore)}`);
            const data = await response.json();
            if (data.length > 0) {
                suggDiv.innerHTML = data.map(city => `
                    <div class="suggestion-item active:bg-indigo-500/20" 
                            onclick="selezionaCitta('${city.name.replace(/'/g, "\\'")}', ${city.lat}, ${city.lon}, '${city.admin.replace(/'/g, "\\'")}', '${city.country.replace(/'/g, "\\'")}')">
                        <div class="font-bold text-base">${city.name}</div>
                        <div class="text-[11px] opacity-50">${city.admin} (${city.country})</div>
                    </div>
                `).join('');
                suggDiv.classList.remove('hidden');
            } else { suggDiv.classList.add('hidden'); }
        } catch (e) {}
    }, 300);
}

function selezionaCitta(nome, lat, lon, admin, country) {
    document.getElementById('cityInput').value = nome;
    document.getElementById('suggestions').classList.add('hidden');
    caricaMeteoDati(nome, lat, lon, admin, country);
    // Chiude la tastiera su mobile
    document.activeElement.blur();
}

async function caricaMeteoDati(nome, lat, lon, admin, country) {
    const resDiv = document.getElementById('risultato');
    const stato = document.getElementById('stato');
    stato.classList.remove('hidden');
    resDiv.classList.add('hidden');

    try {
        const response = await fetch(`/api/weather?lat=${lat}&lon=${lon}&name=${encodeURIComponent(nome)}&admin=${encodeURIComponent(admin)}&country=${encodeURIComponent(country)}`);
        const data = await response.json();

        if (response.ok) {
            document.getElementById('cityName').innerText = data.citta;
            document.getElementById('country').innerText = data.regione ? `${data.regione}, ${data.paese}` : data.paese;
            document.getElementById('temp').innerText = `${data.temp}°`;
            document.getElementById('condition').innerText = data.condizione;
            document.getElementById('percepita').innerText = `${data.percepita}°C`;
            document.getElementById('umidita').innerText = `${data.umidita}%`;
            document.getElementById('vento').innerText = `${data.vento} km/h`;
            document.getElementById('range').innerText = `${data.max}° / ${data.min}°`;
            document.getElementById('weatherIcon').innerHTML = `<i data-lucide="${data.icona}" class="w-14 h-14 text-indigo-300"></i>`;
            const hourlyContainer = document.getElementById('hourlyContainer');
            const hourlyList = document.getElementById('hourlyList');
            
            if (data.hourly && data.hourly.length > 0) {
                hourlyList.innerHTML = data.hourly.map(h => `
                    <div class="hourly-card rounded-2xl p-3 flex flex-col items-center gap-2">
                        <span class="text-[10px] text-white/50 font-medium">${h.ora}</span>
                        <i data-lucide="${h.icona}" class="w-6 h-6 text-indigo-300"></i>
                        <span class="text-sm font-bold">${h.temp}°</span>
                    </div>
                `).join('');

                hourlyContainer.classList.remove('hidden');
            }

            stato.classList.add('hidden');
            resDiv.classList.remove('hidden');
            lucide.createIcons();
            updateMap(data.lat, data.lon);

            // Gestione Consigli
            const tipsContainer = document.getElementById('tipsContainer');
            const tipsList = document.getElementById('tipsList');

            tipsList.innerHTML = ''
            
            if (data.tips && Array.isArray(data.tips)) {
                // Cicliamo su ogni elemento dell'array 'tips'
                tipsList.innerHTML = data.tips.map(tip => `
                    <div class="flex items-center gap-4 bg-white/5 p-3 rounded-2xl border border-white/5 hover:bg-white/10 transition-colors">
                        <div class="bg-indigo-500/20 p-2 rounded-lg">
                            <i data-lucide="${tip.icon}" class="w-5 h-5 text-indigo-300"></i>
                        </div>
                        <p class="text-sm font-medium text-white/90 leading-tight">${tip.text}</p>
                    </div>
                `).join('');
                
                tipsContainer.classList.remove('hidden');
                lucide.createIcons();
            }
        }
    } catch (err) { stato.innerText = "Errore di connessione"; }
}

async function cercaMeteo() {
    const query = document.getElementById('cityInput').value;
    if(!query) return;
    const response = await fetch(`/api/search/${encodeURIComponent(query)}`);
    const data = await response.json();
    if(data.length > 0) {
        const c = data[0];
        selezionaCitta(c.name, c.lat, c.lon, c.admin, c.country);
    }
}

function updateMap(lat, lon) {
    if (!map) {
        map = L.map('map', { zoomControl: false, dragging: !L.Browser.mobile, tap: !L.Browser.mobile }).setView([lat, lon], 12);
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png').addTo(map);
        marker = L.marker([lat, lon]).addTo(map);
    } else {
        map.setView([lat, lon], 12);
        marker.setLatLng([lat, lon]);
    }
    setTimeout(() => map.invalidateSize(), 500);
}

function scrollHourly(direction) {
    const list = document.getElementById('hourlyList');
    // Calcoliamo quanto scorrere (es: la larghezza di 3 card)
    const scrollAmount = 250; 
    
    if (direction === 'left') {
        list.scrollBy({ left: -scrollAmount, behavior: 'smooth' });
    } else {
        list.scrollBy({ left: scrollAmount, behavior: 'smooth' });
    }
}