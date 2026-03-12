# Automatizuota matavimų sistema

Tai programinė įranga, skirta laboratorinių matavimo prietaisų valdymui, sinchronizavimui ir duomenų surinkimui realiu laiku, naudojant SCPI komandas per VISA protokolą.

## Palaikoma aparatūra
Sistema sukonfigūruota dirbti su šiais prietaisais:
* **Oscilografas:** Rigol MSO1070 (USB-TMC sąsaja)
* **Signalų generatorius:** Siglent (USB-TMC sąsaja)
* **Skaitmeninis multimetras 1:** TTi 1604 (RS-232 sąsaja per virtualų COM prievadą)
* **Skaitmeninis multimetras 2:** Escort 3136A (RS-232 sąsaja per virtualų COM prievadą)

## Sistemos reikalavimai
* Operacinė sistema: Windows 10/11
* Python 3.10 ar naujesnė versija
* VISA tvarkyklės: rekomenduojama „NI-VISA“ (arba alternatyvus `pyvisa-py` priedas testavimui)

## Diegimo instrukcija
1. Sukurkite virtualią „Python“ aplinką projekto aplanke:
   python -m venv venv
2. Aktyvuokite virtualią aplinką („Windows“):
   .\venv\Scripts\activate
3. Įdiekite reikiamas bibliotekas iš `requirements.txt` failo:
   pip install -r requirements.txt

## Naudojimas
1. Prijunkite matavimo prietaisus prie kompiuterio.
2. Paleiskite pagrindinį programos failą:
   python main.py
3. Grafinėje sąsajoje paspauskite „Ieškoti prietaisų (Scan)“.
4. Įveskite norimus signalo parametrus ir pradėkite matavimą. Surinkti duomenys automatiškai eksportuojami `.csv` formatu tolimesnei analizei.