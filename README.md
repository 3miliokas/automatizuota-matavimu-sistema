# Automatizuota matavimų sistema (Bakalauro baigiamasis darbas)

Tai Python (PyQt6) pagrindu sukurta programinė įranga, skirta laboratorinių matavimo prietaisų valdymui, sinchronizavimui ir duomenų surinkimui realiu laiku. Sistema naudoja daugiagijiškumą (Multithreading) ir MVC (Model-View-Controller) architektūrą, apjungdama SCPI komandas per VISA protokolą bei serijinį (RS-232) ryšį.

## Palaikoma aparatūra

Sistema sukonfigūruota ir ištestuota dirbti su šiais prietaisais:
* **Oscilografas:** Rigol MSO1074Z / DS serija (USB/LAN-TMC sąsaja)
* **Signalų generatorius:** Siglent SDG serija (USB/LAN-TMC sąsaja)
* **Skaitmeninis multimetras 1:** TTi 1604 (RS-232 sąsaja per virtualų COM prievadą)
* **Skaitmeninis multimetras 2:** Escort 3136A (RS-232 sąsaja per virtualų COM prievadą)

## Pagrindinis funkcionalumas

1. **Bazinė kontrolė:** Signalų parametrų nustatymas generatoriuje, realaus laiko oscilogramos atvaizdavimas ir aparatūrinių matavimų (Vpp, Freq, Rise time) nuskaitymas iš oscilografo.
2. **Dažninės charakteristikos braižymas (Bode Plot):** Uždaro ciklo automatizacija, savarankiškai keičianti generatoriaus dažnį ir matuojanti grandinės atsaką (stiprinimą dB).
3. **Ilgalaikis duomenų registravimas (Data Logger):** Periodinis multimetrų duomenų fiksavimas į CSV failą lėtų procesų (pvz., baterijos iškrovimo ar komponentų kaitimo) stebėjimui.
4. **Spektrinė analizė (FFT):** Kompiuterinis laiko srities signalo konvertavimas į dažnių sritį naudojant `numpy.fft` biblioteką, harmonikų išskyrimas ir pagrindinio dažnio paieška.
5. **PDF protokolų generavimas:** Automatinis oficialios matavimų ataskaitos suformavimas, įtraukiant oscilogramos nuotrauką, prietaiso serijos numerį ir matavimų rezultatus.

## Sistemos reikalavimai

* **Operacinė sistema:** Windows 10/11
* **VISA tvarkyklės:** rekomenduojama „NI-VISA“ (reikalinga USB-TMC ryšiui užtikrinti)
* **Python:** 3.10 ar naujesnė versija (reikalinga *tik* norint modifikuoti ar kompiliuoti kodą)

## Greitas paleidimas (Galutiniams vartotojams)

Jei nenorite diegti programavimo aplinkos, galite atsisiųsti paruoštą vykdomąjį failą:
1. Eikite į šios repozitorijos skyrių **Releases**.
2. Atsisiųskite naujausią sukompiliuotą `.exe` failą.
3. Prijunkite prietaisus ir paleiskite programą (papildomas diegimas nereikalingas).
4. Valdymo skydelyje paspauskite „Skenuoti VISA ir COM“ ir priskirkite rastus prievadus.

## Diegimo instrukcija (Kūrėjams)

1. Sukurkite virtualią „Python“ aplinką projekto aplanke:
```bash
python -m venv venv
```

2. Aktyvuokite virtualią aplinką:
```bash
.\venv\Scripts\Activate.ps1
```
*(Jei naudojate CMD: `.\venv\Scripts\activate.bat`)*

3. Įdiekite reikiamas bibliotekas:
```bash
pip install -r requirements.txt
```

## Naudojimas iš kodo ir Kompiliavimas

**Paleidimas programavimo aplinkoje:**
1. Prijunkite matavimo prietaisus prie kompiuterio USB ir RS-232 jungtimis.
2. Paleiskite pagrindinį programos failą:
```bash
python main.py
```

**Kompiliavimas į vykdomąjį (.exe) failą:**
Norint sugeneruoti savarankišką failą, aktyvioje virtualioje aplinkoje įvykdykite:
```bash
pyinstaller --onefile --windowed main.py
```
*(Sukompiliuotas failas bus automatiškai patalpintas `dist` kataloge).*