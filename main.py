"""
Pagrindinis programos paleidimo (Entry point) failas.
Inicijuoja PyQt6 aplikaciją, pritaiko globalią išvaizdos temą ir
sukuria pagrindinį vartotojo sąsajos langą.
"""

import sys
from PyQt6.QtWidgets import QApplication

from gui.theme import apply_dark_theme
from gui.main_window import MainWindow

def main():
    """
    Pagrindinė programos paleidimo funkcija.
    Kuria aplikacijos instanciją ir palaiko pagrindinį įvykių ciklą (Event loop).
    """
    # Sukuriama bazinė Qt aplikacijos instancija. sys.argv perduoda komandinės eilutės argumentus.
    app = QApplication(sys.argv)
    
    # Pritaikoma inžinerinė tamsioji tema iš atskiro modulio
    apply_dark_theme(app)
    
    # Inicijuojamas ir parodomas pagrindinis sistemos langas su visais valdikliais
    window = MainWindow()
    window.show()
    
    # Paleidžiamas nesibaigiantis įvykių ciklas (Event loop). 
    # app.exec() blokuoja tolesnį vykdymą iki kol langas uždaromas, tada grąžina išėjimo kodą.
    sys.exit(app.exec())

# Šis blokas užtikrina, kad kodas bus vykdomas tik paleidus failą tiesiogiai,
# o ne importuojant jį kaip modulį kitur.
if __name__ == "__main__":
    main()