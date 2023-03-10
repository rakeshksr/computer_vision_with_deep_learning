import sys
from pathlib import Path

import cv2

from PySide6.QtCore import Qt, QSize, QThread, Signal, Slot
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (QApplication, QComboBox, QHBoxLayout,
                               QLabel, QMainWindow, QPushButton,
                               QVBoxLayout, QWidget)

from ml_applications import MlApplications

# For PyInstaller 
PWD = Path(getattr(sys, "_MEIPASS", Path.cwd()))

def convert_snake_case_to_title_case(snake_case_str: str) -> str:
    """
    Converts a string from snake_case to Title Case.
    """
    # Split the string into individual words
    words = snake_case_str.split("_")

    # Capitalize the first letter of each word and join them with a space
    title_case_str = " ".join(word.capitalize() for word in words)

    return title_case_str


ML_FUNCTIONS = {
    convert_snake_case_to_title_case(attribute): attribute
    for attribute in dir(MlApplications)
    if callable(getattr(MlApplications, attribute)) and attribute.startswith('__') is False
}


class Thread(QThread):
    updateFrame = Signal(QImage)

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.detect_function = None
        self.status = True
        self.cap = True
        self.mla = MlApplications()

    def set_detect_function(self, fname):
        self.detect_function = ML_FUNCTIONS[fname]

    def run(self):
        self.cap = cv2.VideoCapture(0)
        while self.status:
            ret, frame = self.cap.read()
            if not ret:
                continue
            func = getattr(self.mla, self.detect_function)
            output_image = func(frame)

            # Creating and scaling QImage
            h, w, ch = output_image.shape
            img = QImage(output_image.data, w, h, ch * w, QImage.Format_RGB888)
            scaled_img = img.scaled(640, 480, Qt.KeepAspectRatio)

            # Emit signal
            self.updateFrame.emit(scaled_img)
        sys.exit(-1)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Title and dimensions
        self.setWindowTitle("AI Vision")
        # self.setGeometry(0, 0, 800, 500)
        wIcon = QIcon(str(PWD/"assets/app_icon.png"))
        self.setWindowIcon(wIcon)

        # Create a label for the display camera
        self.label = QLabel(self)
        self.label.setFixedSize(640, 480)

        # Thread in charge of updating the image
        self.th = Thread(self)
        self.th.finished.connect(self.close)
        self.th.updateFrame.connect(self.setImage)

        self.combobox = QComboBox()
        self.combobox.addItems(ML_FUNCTIONS.keys())
        qcb_icon = str(PWD).replace("\\", "/") + "/assets/downarrow.png" # QT CSS only accepting path with "/" seperator
        self.combobox.setStyleSheet(f"""QComboBox::down-arrow {{
            image: url({qcb_icon});
            }}"""
        )

        self.start_pause_button = QPushButton()
        self.handle_click()

        right_layout = QHBoxLayout()
        right_layout.addWidget(self.combobox, stretch=3)
        right_layout.addWidget(self.start_pause_button, stretch=1)

        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(self.label, alignment=Qt.AlignCenter)
        layout.addLayout(right_layout)

        # Central widget
        widget = QWidget(self)
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        # Interactions
        self.start_pause_button.clicked.connect(self.handle_click)
        self.combobox.currentTextChanged.connect(self.set_model)

        # Load the style sheet
        with open(PWD/"styles.css") as f:
            self.setStyleSheet(f.read())

    @Slot()
    def set_model(self, text):
        self.th.set_detect_function(text)

    @Slot()
    def handle_click(self):
        if self.start_pause_button.text() == "Start":
            self.start_detection()
            text = "Pause"
            bg_color = "#bb85f1"
            icon = PWD / "assets/pause_circle.png"
            cb = True
        else:
            if self.start_pause_button.text() != "":
                self.pause_detection()
            text = "Start"
            bg_color = "#47c2a7"
            icon = PWD / "assets/play_circle.png"
            cb = False
        self.start_pause_button.setText(text)
        self.start_pause_button.setStyleSheet(f"background-color: {bg_color};")
        self.start_pause_button.setIcon(QIcon(str(icon)))
        self.start_pause_button.setIconSize(QSize(25, 25))
        self.combobox.setEnabled(cb)

    @Slot()
    def pause_detection(self):
        # print("Finishing...")
        self.th.set_detect_function("No Detection")

    @Slot()
    def start_detection(self):
        # print("Starting...")
        self.th.set_detect_function(self.combobox.currentText())
        if not self.th.isRunning():
            self.th.start()

    @Slot(QImage)
    def setImage(self, image):
        self.label.setPixmap(QPixmap.fromImage(image))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
