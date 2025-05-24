# main.py

import sys
from PyQt5.QtWidgets import QApplication
# --- Added imports for localization ---
from PyQt5.QtCore import QTranslator, QLibraryInfo, QLocale

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # --- Attempt to load Qt translations for localization ---
    translator = QTranslator()
    # Try loading translation file based on system locale from standard Qt translation paths
    if translator.load("qt_%s" % QLocale.system().name(), QLibraryInfo.location(QLibraryInfo.TranslationsPath)):
         app.installTranslator(translator)
    # You might need to specify a fallback path or try specific languages too
    # Example for Chinese:
    # if translator.load("qt_zh_CN", QLibraryInfo.location(QLibraryInfo.TranslationsPath)):
    #     app.installTranslator(translator)

    from gui.main_window import MainWindow

    main_window = MainWindow()
    main_window.show()

    sys.exit(app.exec_())