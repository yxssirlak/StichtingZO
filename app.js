// --- JOUW FIREBASE CONFIGURATIE ---
const firebaseConfig = {
    apiKey: "AIzaSyC_2cDXedKEjz14lSGgEPRDGoSSfxsikOU",
    authDomain: "stichtingzo-c2e4b.firebaseapp.com",
    databaseURL: "https://stichtingzo-c2e4b-default-rtdb.europe-west1.firebasedatabase.app",
    projectId: "stichtingzo-c2e4b",
    storageBucket: "stichtingzo-c2e4b.firebasestorage.app",
    messagingSenderId: "316298935855",
    appId: "1:316298935855:web:9a92633f927fbc060210da",
    measurementId: "G-55TD3F28YE"
};

firebase.initializeApp(firebaseConfig);
const db = firebase.database();

const urlParams = new URLSearchParams(window.location.search);
const templateId = urlParams.get('id');
let huidigeTemplate = null;

// Leeftijd dropdown vullen
const leeftijdSelect = document.getElementById('leeftijd');
for (let i = 12; i <= 27; i++) {
    let option = document.createElement('option');
    option.value = i;
    option.text = i;
    leeftijdSelect.add(option);
}
let optionOuder = document.createElement('option');
optionOuder.value = "> 27";
optionOuder.text = "> 27";
leeftijdSelect.add(optionOuder);

function haalVragenlijstOp() {
    if (!templateId) {
        document.getElementById('vragenlijst-container').innerHTML = `<h2>Fout</h2><p>Geen geldige vragenlijst link gevonden.</p>`;
        return;
    }
    db.ref('templates/' + templateId).once('value').then((snapshot) => {
        const data = snapshot.val();
        if (data) {
            huidigeTemplate = data;
            bouwFormulier(data);
        } else {
            document.getElementById('vragenlijst-container').innerHTML = `<h2>Niet gevonden</h2><p>Deze vragenlijst bestaat niet (meer).</p>`;
        }
    }).catch((error) => {
        document.getElementById('vragenlijst-container').innerHTML = `<h2>Fout bij laden</h2><p>${error.message}</p>`;
    });
}

function berekenInvulTijd(vragen) {
    let seconden = 10; 
    vragen.forEach(v => {
        if (v.type === "Open Vraag") seconden += 40;
        else if (v.type === "Meerkeuze (Checkboxes)" || v.type === "Keuze (Radiobuttons)") seconden += 20;
        else seconden += 15; 
    });
    return Math.max(1, Math.round(seconden / 60)); 
}

function bouwFormulier(template) {
    document.getElementById('vragenlijst-container').style.display = 'none';
    document.getElementById('enquete-formulier').style.display = 'block';

    const headerCard = document.createElement('div');
    headerCard.className = 'card';
    
    const vragen = template.vragen || [];
    const minuten = berekenInvulTijd(vragen);

    let html = `
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 15px;">
            <h2 style="margin-top: 0; margin-bottom: 10px; line-height: 1.2;">${template.titel}</h2>
            <div style="background-color: var(--bg-main); color: var(--accent); padding: 5px 12px; border-radius: 20px; font-size: 13px; font-weight: bold; white-space: nowrap; border: 1px solid var(--border-color); display: flex; align-items: center; gap: 5px;">
                ⏱️ ~${minuten} min
            </div>
        </div>
    `;

    if (template.beschrijving) {
        html += `<p style="margin-top: 5px; margin-bottom: 0;">${template.beschrijving}</p>`;
    }
    
    headerCard.innerHTML = html;
    
    const form = document.getElementById('enquete-formulier');
    form.insertBefore(headerCard, form.firstChild);

    const vragenDiv = document.getElementById('dynamische-vragen');

    vragen.forEach((vraagData, index) => {
        const qCard = document.createElement('div');
        qCard.className = 'card';
        qCard.id = `vraag-card-${index}`;
        
        let qHtml = `<h3>${index + 1}. ${vraagData.vraag}</h3>`;

        // --- HIER WORDEN DE FOTO'S EN DE NAMEN GETEKEND ---
        if (vraagData.afbeeldingen && vraagData.afbeeldingen.length > 0) {
            qHtml += `<div class="afbeelding-container" style="display: flex; flex-wrap: wrap; gap: 15px; margin-top: 15px;">`;
            vraagData.afbeeldingen.forEach((imgInfo, imgIdx) => {
                let b64_data = "";
                let caption = "";

                // Controleer of het nieuwe formaat (met naam) of oude formaat (alleen foto) is
                if (typeof imgInfo === 'object' && imgInfo !== null) {
                    b64_data = imgInfo.data;
                    caption = imgInfo.caption || `Afbeelding ${imgIdx + 1}`;
                } else {
                    b64_data = imgInfo;
                    caption = `Afbeelding ${imgIdx + 1}`;
                }

                qHtml += `<div>
                            <img src="data:image/jpeg;base64,${b64_data}" alt="${caption}" 
                                 onclick="vergrootAfbeelding(this.src)" 
                                 style="cursor: zoom-in; max-width: 250px; border-radius: 8px; transition: transform 0.2s ease; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" 
                                 onmouseover="this.style.transform='scale(1.03)'" 
                                 onmouseout="this.style.transform='scale(1)'">
                            <p style="text-align:center; margin-top:8px; margin-bottom:2px; font-weight:bold; font-size:14px; color: var(--text-main);">${caption}</p>
                            <p style="text-align:center; margin-top:0px; font-size: 11px; color: var(--text-grey);">Klik om te vergroten</p>
                          </div>`;
            });
            qHtml += `</div>`;
        }

        const type = vraagData.type || "Dropdown";
        const opties = vraagData.opties || [];

        if (type === "Open Vraag") {
            qHtml += `<textarea id="antwoord-${index}" rows="3" placeholder="Typ hier je antwoord..." required></textarea>`;
        } else if (type === "Slider (1-10)") {
            qHtml += `
                <div class="slider-container">
                    <div class="slider-labels">
                        <span>1</span><span>2</span><span>3</span><span>4</span><span>5</span><span>6</span><span>7</span><span>8</span><span>9</span><span>10</span>
                    </div>
                    <input type="range" id="antwoord-${index}" min="1" max="10" value="5" step="1">
                    <p style="text-align:center; color: var(--accent); font-weight:bold; margin-top:10px;">
                        Geselecteerd: <span id="slider-val-${index}">5</span>
                    </p>
                </div>`;
        } else if (type === "Dropdown") {
            qHtml += `<select id="antwoord-${index}" required onchange="checkAnders(this, ${index})">`;
            opties.forEach(optie => {
                qHtml += `<option value="${optie}">${optie}</option>`;
            });
            qHtml += `</select><input type="text" id="anders-${index}" style="display:none; margin-top:10px;" placeholder="Typ hier je antwoord...">`;
        } else if (type === "Keuze (Radiobuttons)") {
            opties.forEach((optie) => {
                qHtml += `
                    <label class="radio-group">
                        <input type="radio" name="antwoord-${index}" value="${optie}" onchange="checkAndersRadio('${optie}', ${index})" required>
                        ${optie}
                    </label>`;
            });
            qHtml += `<input type="text" id="anders-${index}" style="display:none; margin-top:10px;" placeholder="Typ hier je antwoord...">`;
        } else if (type === "Meerkeuze (Checkboxes)") {
            opties.forEach((optie) => {
                qHtml += `
                    <label class="checkbox-group">
                        <input type="checkbox" name="antwoord-${index}" value="${optie}" onchange="checkAndersCheckbox(${index})">
                        ${optie}
                    </label>`;
            });
            qHtml += `<input type="text" id="anders-${index}" style="display:none; margin-top:10px;" placeholder="Typ hier je antwoord...">`;
        }

        qCard.innerHTML = qHtml;
        vragenDiv.appendChild(qCard);

        if (type === "Slider (1-10)") {
            document.getElementById(`antwoord-${index}`).addEventListener('input', function() {
                document.getElementById(`slider-val-${index}`).innerText = this.value;
            });
        }
    });
}

function checkAnders(selectElement, index) {
    const val = selectElement.value.toLowerCase();
    const andersVeld = document.getElementById(`anders-${index}`);
    if (val.includes('anders')) {
        andersVeld.style.display = 'block';
        andersVeld.required = true;
    } else {
        andersVeld.style.display = 'none';
        andersVeld.required = false;
    }
}

function checkAndersRadio(val, index) {
    const andersVeld = document.getElementById(`anders-${index}`);
    if (val.toLowerCase().includes('anders')) {
        andersVeld.style.display = 'block';
        andersVeld.required = true;
    } else {
        andersVeld.style.display = 'none';
        andersVeld.required = false;
    }
}

function checkAndersCheckbox(index) {
    const checkboxes = document.querySelectorAll(`input[name="antwoord-${index}"]:checked`);
    let showAnders = false;
    checkboxes.forEach(cb => {
        if (cb.value.toLowerCase().includes('anders')) {
            showAnders = true;
        }
    });
    const andersVeld = document.getElementById(`anders-${index}`);
    if (showAnders) {
        andersVeld.style.display = 'block';
        andersVeld.required = true;
    } else {
        andersVeld.style.display = 'none';
        andersVeld.required = false;
    }
}

document.getElementById('enquete-formulier').addEventListener('submit', function(e) {
    e.preventDefault(); 
    const naam = document.getElementById('naam').value;
    const geslacht = document.getElementById('geslacht').value;
    const leeftijd = document.getElementById('leeftijd').value;
    const opmerking = document.getElementById('opmerking').value;
    
    const d = new Date();
    const datum = ("0" + d.getDate()).slice(-2) + "-" + ("0"+(d.getMonth()+1)).slice(-2) + "-" + d.getFullYear();

    const antwoordenLijst = [];
    const vragen = huidigeTemplate.vragen || [];

    vragen.forEach((vraagData, index) => {
        const type = vraagData.type || "Dropdown";
        let gekozenAntwoord = "";

        if (type === "Open Vraag" || type === "Slider (1-10)") {
            gekozenAntwoord = document.getElementById(`antwoord-${index}`).value;
        } else if (type === "Dropdown") {
            let val = document.getElementById(`antwoord-${index}`).value;
            if (val.toLowerCase().includes('anders')) {
                let eigenText = document.getElementById(`anders-${index}`).value;
                gekozenAntwoord = eigenText ? `${val}: ${eigenText}` : `${val}: (Niets ingevuld)`;
            } else {
                gekozenAntwoord = val;
            }
        } else if (type === "Keuze (Radiobuttons)") {
            let selected = document.querySelector(`input[name="antwoord-${index}"]:checked`);
            if (selected) {
                let val = selected.value;
                if (val.toLowerCase().includes('anders')) {
                    let eigenText = document.getElementById(`anders-${index}`).value;
                    gekozenAntwoord = eigenText ? `${val}: ${eigenText}` : `${val}: (Niets ingevuld)`;
                } else {
                    gekozenAntwoord = val;
                }
            } else {
                gekozenAntwoord = "Niets geselecteerd";
            }
        } else if (type === "Meerkeuze (Checkboxes)") {
            let checked = document.querySelectorAll(`input[name="antwoord-${index}"]:checked`);
            let vals = [];
            checked.forEach(cb => {
                let val = cb.value;
                if (val.toLowerCase().includes('anders')) {
                    let eigenText = document.getElementById(`anders-${index}`).value;
                    vals.push(eigenText ? `${val}: ${eigenText}` : `${val}: (Niets ingevuld)`);
                } else {
                    vals.push(val);
                }
            });
            gekozenAntwoord = vals.length > 0 ? vals.join(", ") : "Niets geselecteerd";
        }
        antwoordenLijst.push({ vraag: vraagData.vraag, antwoord: gekozenAntwoord });
    });

    const nieuweInvoer = {
        template_id: templateId,
        template_titel: huidigeTemplate.titel,
        naam: naam,
        leeftijd: leeftijd,
        geslacht: geslacht,
        datum: datum,
        opmerking: opmerking,
        antwoorden: antwoordenLijst
    };

    db.ref('vragenlijsten').push(nieuweInvoer).then(() => {
        document.getElementById('enquete-formulier').style.display = 'none';
        document.getElementById('succes-bericht').style.display = 'block';
        window.scrollTo(0, 0);
    }).catch((error) => {
        alert("Fout bij opslaan: " + error.message);
    });
});

haalVragenlijstOp();

// --- DARK MODE LOGICA ---
const themeToggleBtn = document.getElementById('theme-toggle');
const currentTheme = localStorage.getItem('theme');

if (currentTheme === 'dark') {
    document.body.classList.add('dark-mode');
    themeToggleBtn.innerText = '☀️ Light Mode';
}

themeToggleBtn.addEventListener('click', () => {
    document.body.classList.toggle('dark-mode');
    let theme = 'light';
    if (document.body.classList.contains('dark-mode')) {
        theme = 'dark';
        themeToggleBtn.innerText = '☀️ Light Mode';
    } else {
        themeToggleBtn.innerText = '🌙 Dark Mode';
    }
    localStorage.setItem('theme', theme);
});

// ==================================================================
// --- AFBEELDING LIGHTBOX / POPUP LOGICA ---
// ==================================================================
document.body.insertAdjacentHTML('beforeend', `
    <div id="imageModal" style="display:none; position:fixed; z-index:9999; left:0; top:0; width:100%; height:100%; background-color:rgba(0,0,0,0.85); align-items:center; justify-content:center; cursor:zoom-out;" onclick="sluitAfbeelding()">
        <img id="modalImg" src="" style="max-width:90vw; max-height:90vh; border-radius:10px; box-shadow:0 10px 30px rgba(0,0,0,0.5);">
    </div>
`);

function vergrootAfbeelding(src) {
    document.getElementById('modalImg').src = src; 
    document.getElementById('imageModal').style.display = 'flex'; 
}

function sluitAfbeelding() {
    document.getElementById('imageModal').style.display = 'none'; 
    document.getElementById('modalImg').src = ''; 
}