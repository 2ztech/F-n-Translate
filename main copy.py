import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QLabel, QTextEdit, QComboBox,
    QFileDialog, QDialog, QLineEdit, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QIcon, QFont, QPalette, QColor, QLinearGradient, QPixmap

class FnTranslateApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("F(n)Translate")
        self.setMinimumSize(QSize(1000, 750))
        
        # Main container
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main layout
        self.main_layout = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create UI components
        self.create_header()
        self.create_language_bar()
        self.create_modules()
        self.create_footer()
        
        # Set initial module
        self.stacked_widget.setCurrentIndex(0)
        
        # Connect signals
        self.connect_signals()
        
    def create_header(self):
        # App header
        self.header = QWidget()
        self.header.setStyleSheet("""
            background-color: #1ba1e2;
            padding: 15px 30px;
        """)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        self.header.setLayout(header_layout)
        
        # Logo
        self.logo = QLabel("F(n)Translate")
        self.logo.setStyleSheet("""
            color: white;
            font-size: 24px;
            font-weight: bold;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        
        # Navigation buttons
        self.nav_buttons = QWidget()
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(0)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_buttons.setLayout(nav_layout)
        self.nav_buttons.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.2);
            border-radius: 25px;
        """)
        
        # Create nav buttons
        self.text_btn = QPushButton("Translate Text")
        self.file_btn = QPushButton("Translate File")
        self.capture_btn = QPushButton("Screen Capture")
        
        button_style = """
            QPushButton {
                background: transparent;
                border: none;
                color: white;
                padding: 10px 25px;
                font-size: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-weight: 500;
                border-radius: 25px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.3);
            }
            QPushButton.active {
                background: white;
                color: #1ba1e2;
            }
        """
        
        for btn in [self.text_btn, self.file_btn, self.capture_btn]:
            btn.setStyleSheet(button_style)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            nav_layout.addWidget(btn)
        
        self.text_btn.setChecked(True)
        self.text_btn.setProperty("class", "active")
        
        # Add widgets to header
        header_layout.addWidget(self.logo)
        header_layout.addStretch()
        header_layout.addWidget(self.nav_buttons)
        
        self.main_layout.addWidget(self.header)
    
    def create_language_bar(self):
        # Language selection bar
        self.lang_bar = QWidget()
        self.lang_bar.setStyleSheet("""
            background-color: #dae8fc;
            padding: 15px 30px;
            border-bottom: 1px solid #b8d1f0;
        """)
        lang_layout = QHBoxLayout()
        lang_layout.setContentsMargins(0, 0, 0, 0)
        lang_layout.setSpacing(20)
        self.lang_bar.setLayout(lang_layout)
        
        # Source language
        source_lang = QWidget()
        source_layout = QHBoxLayout()
        source_layout.setContentsMargins(0, 0, 0, 0)
        source_layout.setSpacing(15)
        source_lang.setLayout(source_layout)
        
        source_label = QLabel("Source:")
        source_label.setStyleSheet("""
            font-weight: 600;
            color: #2a5298;
            font-size: 16px;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        
        self.source_combo = QComboBox()
        self.source_combo.addItems(["English", "Malay", "Spanish", "French", "German", "Chinese", "Japanese"])
        self.source_combo.setStyleSheet("""
            QComboBox {
                padding: 10px 15px;
                border: 1px solid #b8d1f0;
                border-radius: 8px;
                background: white;
                color: #2a5298;
                font-weight: 500;
                font-size: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
                min-width: 180px;
            }
            QComboBox:hover {
                border: 1px solid #1ba1e2;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #b8d1f0;
                border-radius: 8px;
                padding: 8px;
                background: white;
                selection-background-color: #e1f0ff;
                selection-color: #1ba1e2;
                font-size: 16px;
                outline: none;
            }
        """)
        
        source_layout.addWidget(source_label)
        source_layout.addWidget(self.source_combo)
        
        # Target language
        target_lang = QWidget()
        target_layout = QHBoxLayout()
        target_layout.setContentsMargins(0, 0, 0, 0)
        target_layout.setSpacing(15)
        target_lang.setLayout(target_layout)
        
        target_label = QLabel("Target:")
        target_label.setStyleSheet(source_label.styleSheet())
        
        self.target_combo = QComboBox()
        self.target_combo.addItems(["Malay", "English", "Spanish", "French", "German", "Chinese", "Japanese"])
        self.target_combo.setStyleSheet(self.source_combo.styleSheet())
        
        target_layout.addWidget(target_label)
        target_layout.addWidget(self.target_combo)
        
        # Add to language bar
        lang_layout.addStretch()
        lang_layout.addWidget(source_lang)
        lang_layout.addWidget(target_lang)
        lang_layout.addStretch()
        
        self.main_layout.addWidget(self.lang_bar)
    
    def create_modules(self):
        # Stacked widget for modules
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("""
            background-color: white;
        """)
        
        # Create modules
        self.create_text_module()
        self.create_file_module()
        self.create_capture_module()
        
        self.main_layout.addWidget(self.stacked_widget)
    
    def create_text_module(self):
        # Text translation module
        text_widget = QWidget()
        text_layout = QHBoxLayout()
        text_layout.setContentsMargins(30, 30, 30, 30)
        text_layout.setSpacing(30)
        text_widget.setLayout(text_layout)
        
        # Input box
        input_box = QWidget()
        input_layout = QVBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(20)
        input_box.setLayout(input_layout)
        
        input_label = QLabel("Source Text")
        input_label.setStyleSheet("""
            color: #2a5298;
            font-weight: 600;
            font-size: 20px;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Type to translate...")
        self.text_input.setStyleSheet("""
            QTextEdit {
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                padding: 15px;
                background: #f9fbfd;
                font-size: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
                color: #333;
                min-height: 400px;
            }
            QTextEdit:focus {
                border: 1px solid #1ba1e2;
            }
        """)
        
        input_layout.addWidget(input_label)
        input_layout.addWidget(self.text_input)
        
        # Output box
        output_box = QWidget()
        output_layout = QVBoxLayout()
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.setSpacing(20)
        output_box.setLayout(output_layout)
        
        output_label = QLabel("Translation")
        output_label.setStyleSheet(input_label.styleSheet())
        
        self.text_output = QTextEdit()
        self.text_output.setReadOnly(True)
        self.text_output.setStyleSheet("""
            QTextEdit {
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                padding: 15px;
                background: #f9fbfd;
                font-size: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
                color: #333;
                min-height: 400px;
            }
        """)
        
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.text_output)
        
        # Add to module
        text_layout.addWidget(input_box)
        text_layout.addWidget(output_box)
        
        self.stacked_widget.addWidget(text_widget)
    
    def create_file_module(self):
        # File translation module
        file_widget = QWidget()
        file_layout = QHBoxLayout()
        file_layout.setContentsMargins(30, 30, 30, 30)
        file_layout.setSpacing(30)
        file_widget.setLayout(file_layout)
        
        # Left panel - File upload
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(20)
        left_panel.setLayout(left_layout)
        
        upload_title = QLabel("Upload File")
        upload_title.setStyleSheet("""
            color: #2a5298;
            font-weight: 600;
            font-size: 20px;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        
        self.upload_area = QFrame()
        self.upload_area.setFrameShape(QFrame.StyledPanel)
        self.upload_area.setStyleSheet("""
            QFrame {
                border: 2px dashed #b8d1f0;
                border-radius: 12px;
                background: #f9fbfd;
            }
            QFrame:hover {
                border: 2px dashed #1ba1e2;
                background: #f0f7ff;
            }
        """)
        self.upload_area.setFixedHeight(400)
        
        upload_content = QVBoxLayout()
        upload_content.setContentsMargins(40, 40, 40, 40)
        upload_content.setSpacing(20)
        
        upload_icon = QLabel()
        upload_icon.setPixmap(QIcon.fromTheme("document-open").pixmap(64, 64))
        upload_icon.setAlignment(Qt.AlignCenter)
        
        upload_label = QLabel("Drag & Drop Files Here")
        upload_label.setStyleSheet("""
            color: #2a5298;
            font-weight: 600;
            font-size: 18px;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        upload_label.setAlignment(Qt.AlignCenter)
        
        upload_subtext = QLabel("or click to browse files\n\nSupported formats: PDF, DOCX, TXT\nMax file size: 10MB")
        upload_subtext.setStyleSheet("""
            color: #666;
            font-size: 14px;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        upload_subtext.setAlignment(Qt.AlignCenter)
        
        upload_button = QPushButton("Browse Files")
        upload_button.setStyleSheet("""
            QPushButton {
                background-color: #1ba1e2;
                color: white;
                padding: 12px 25px;
                border-radius: 6px;
                font-weight: 500;
                font-size: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
                border: none;
            }
            QPushButton:hover {
                background-color: #0d8bc9;
            }
        """)
        upload_button.setCursor(Qt.PointingHandCursor)
        
        upload_content.addStretch()
        upload_content.addWidget(upload_icon)
        upload_content.addWidget(upload_label)
        upload_content.addWidget(upload_subtext)
        upload_content.addWidget(upload_button, 0, Qt.AlignCenter)
        upload_content.addStretch()
        
        self.upload_area.setLayout(upload_content)
        
        left_layout.addWidget(upload_title)
        left_layout.addWidget(self.upload_area)
        
        # Right panel - Translation preview
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(20)
        right_panel.setLayout(right_layout)
        
        preview_title = QLabel("Translation Preview")
        preview_title.setStyleSheet(upload_title.styleSheet())
        
        self.translation_preview = QTextEdit()
        self.translation_preview.setReadOnly(True)
        self.translation_preview.setStyleSheet("""
            QTextEdit {
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                padding: 15px;
                background: #f9fbfd;
                font-size: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
                color: #333;
            }
        """)
        self.translation_preview.setFixedHeight(400)
        
        # Action buttons
        action_buttons = QWidget()
        action_layout = QHBoxLayout()
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(15)
        action_buttons.setLayout(action_layout)
        
        self.translate_btn = QPushButton("Translate")
        self.translate_btn.setIcon(QIcon.fromTheme("edit-find"))
        self.translate_btn.setStyleSheet(upload_button.styleSheet())
        self.translate_btn.setCursor(Qt.PointingHandCursor)
        
        self.save_btn = QPushButton("Save Translation")
        self.save_btn.setIcon(QIcon.fromTheme("document-save"))
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 12px 25px;
                border-radius: 6px;
                font-weight: 500;
                font-size: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
                border: none;
            }
            QPushButton:hover {
                background-color: #3d8b40;
            }
        """)
        self.save_btn.setCursor(Qt.PointingHandCursor)
        
        action_layout.addStretch()
        action_layout.addWidget(self.translate_btn)
        action_layout.addWidget(self.save_btn)
        
        right_layout.addWidget(preview_title)
        right_layout.addWidget(self.translation_preview)
        right_layout.addWidget(action_buttons)
        
        # Add panels to module
        file_layout.addWidget(left_panel)
        file_layout.addWidget(right_panel)
        
        self.stacked_widget.addWidget(file_widget)
    
    def create_capture_module(self):
        # Screen capture module
        capture_widget = QWidget()
        capture_layout = QVBoxLayout()
        capture_layout.setContentsMargins(30, 30, 30, 30)
        capture_layout.setSpacing(25)
        capture_widget.setLayout(capture_layout)
        
        # Capture header
        header = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header.setLayout(header_layout)
        
        # Monitor selector
        monitor_selector = QWidget()
        monitor_layout = QHBoxLayout()
        monitor_layout.setContentsMargins(0, 0, 0, 0)
        monitor_layout.setSpacing(15)
        monitor_selector.setLayout(monitor_layout)
        
        monitor_label = QLabel("Select Monitor:")
        monitor_label.setStyleSheet("""
            font-weight: 600;
            color: #2a5298;
            font-size: 16px;
            font-family: 'Segoe UI', Arial, sans-serif;
            min-width: 120px;
        """)
        
        self.monitor_combo = QComboBox()
        self.monitor_combo.addItems(["Monitor 1", "Monitor 2", "Full Screen", "Custom Region"])
        self.monitor_combo.setStyleSheet("""
            QComboBox {
                padding: 10px 15px;
                border: 1px solid #b8d1f0;
                border-radius: 8px;
                background: white;
                color: #2a5298;
                font-weight: 500;
                font-size: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
                min-width: 200px;
            }
            QComboBox:hover {
                border: 1px solid #1ba1e2;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #b8d1f0;
                border-radius: 8px;
                padding: 8px;
                background: white;
                selection-background-color: #e1f0ff;
                selection-color: #1ba1e2;
                font-size: 16px;
                outline: none;
            }
        """)
        
        monitor_layout.addWidget(monitor_label)
        monitor_layout.addWidget(self.monitor_combo)
        
        # Capture buttons
        button_group = QWidget()
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(15)
        button_group.setLayout(button_layout)
        
        self.start_btn = QPushButton("Start Capture")
        self.start_btn.setIcon(QIcon.fromTheme("media-record"))
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #1ba1e2;
                color: white;
                padding: 12px 25px;
                border-radius: 6px;
                font-weight: 500;
                font-size: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
                border: none;
            }
            QPushButton:hover {
                background-color: #0d8bc9;
            }
            QPushButton:disabled {
                background-color: #b0b0b0;
            }
        """)
        self.start_btn.setCursor(Qt.PointingHandCursor)
        
        self.stop_btn = QPushButton("Stop Capture")
        self.stop_btn.setIcon(QIcon.fromTheme("media-playback-stop"))
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 12px 25px;
                border-radius: 6px;
                font-weight: 500;
                font-size: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
                border: none;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #b0b0b0;
            }
        """)
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setEnabled(False)
        
        button_layout.addStretch()
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        
        header_layout.addWidget(monitor_selector)
        header_layout.addStretch()
        header_layout.addWidget(button_group)
        
        # Preview area
        self.preview_area = QLabel()
        self.preview_area.setAlignment(Qt.AlignCenter)
        self.preview_area.setStyleSheet("""
            QLabel {
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                background: #f0f7ff;
                min-height: 400px;
            }
        """)
        
        # Preview placeholder
        preview_placeholder = QWidget()
        preview_placeholder_layout = QVBoxLayout()
        preview_placeholder_layout.setContentsMargins(0, 0, 0, 0)
        preview_placeholder_layout.setSpacing(15)
        preview_placeholder.setLayout(preview_placeholder_layout)
        
        placeholder_icon = QLabel()
        placeholder_icon.setPixmap(QIcon.fromTheme("camera-photo").pixmap(64, 64))
        placeholder_icon.setAlignment(Qt.AlignCenter)
        
        placeholder_text = QLabel("Screen preview will appear here")
        placeholder_text.setStyleSheet("""
            color: #666;
            font-size: 16px;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        placeholder_text.setAlignment(Qt.AlignCenter)
        
        preview_placeholder_layout.addStretch()
        preview_placeholder_layout.addWidget(placeholder_icon)
        preview_placeholder_layout.addWidget(placeholder_text)
        preview_placeholder_layout.addStretch()
        
        self.preview_area.setLayout(preview_placeholder_layout)
        
        # Add to module
        capture_layout.addWidget(header)
        capture_layout.addWidget(self.preview_area)
        
        self.stacked_widget.addWidget(capture_widget)
    
    def create_footer(self):
        # App footer
        self.footer = QWidget()
        self.footer.setStyleSheet("""
            background-color: #f5f5f5;
            padding: 15px 30px;
            border-top: 1px solid #e0e0e0;
        """)
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 0, 0, 0)
        self.footer.setLayout(footer_layout)
        
        # Settings button
        self.settings_btn = QPushButton()
        self.settings_btn.setIcon(QIcon.fromTheme("preferences-system"))
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #666;
                font-size: 24px;
                padding: 8px;
                border-radius: 50%;
            }
            QPushButton:hover {
                background: #eaeaea;
                color: #1ba1e2;
            }
        """)
        self.settings_btn.setToolTip("API Settings")
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        
        # API key info
        self.api_info = QLabel("API Status: <span style='color:#1ba1e2;'>Connected</span> | Key: <span style='color:#1ba1e2;'>ds-********************</span>")
        self.api_info.setStyleSheet("""
            font-size: 14px;
            color: #666;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        
        # Add to footer
        footer_layout.addWidget(self.settings_btn)
        footer_layout.addStretch()
        footer_layout.addWidget(self.api_info)
        
        self.main_layout.addWidget(self.footer)
    
    def connect_signals(self):
        # Connect navigation buttons
        self.text_btn.clicked.connect(lambda: self.switch_module(0))
        self.file_btn.clicked.connect(lambda: self.switch_module(1))
        self.capture_btn.clicked.connect(lambda: self.switch_module(2))
        
        # Connect file module signals
        self.upload_area.mousePressEvent = self.handle_file_upload
        self.translate_btn.clicked.connect(self.translate_file)
        self.save_btn.clicked.connect(self.save_translation)
        
        # Connect capture module signals
        self.start_btn.clicked.connect(self.start_capture)
        self.stop_btn.clicked.connect(self.stop_capture)
        
        # Connect settings button
        self.settings_btn.clicked.connect(self.show_settings_dialog)
    
    def switch_module(self, index):
        # Update navigation buttons
        self.text_btn.setChecked(index == 0)
        self.file_btn.setChecked(index == 1)
        self.capture_btn.setChecked(index == 2)
        
        # Update active class for styling
        self.text_btn.setProperty("class", "active" if index == 0 else "")
        self.file_btn.setProperty("class", "active" if index == 1 else "")
        self.capture_btn.setProperty("class", "active" if index == 2 else "")
        
        # Refresh styles
        self.text_btn.style().polish(self.text_btn)
        self.file_btn.style().polish(self.file_btn)
        self.capture_btn.style().polish(self.capture_btn)
        
        # Switch to selected module
        self.stacked_widget.setCurrentIndex(index)
    
    def handle_file_upload(self, event):
        # Show file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select File", "", 
            "Supported Files (*.pdf *.docx *.txt);;All Files (*)"
        )
        
        if file_path:
            # Update UI to show processing
            self.upload_area.clear()
            processing_layout = QVBoxLayout()
            processing_layout.setContentsMargins(0, 0, 0, 0)
            processing_layout.setSpacing(15)
            
            spinner = QLabel()
            spinner.setPixmap(QIcon.fromTheme("process-working").pixmap(64, 64))
            spinner.setAlignment(Qt.AlignCenter)
            
            processing_text = QLabel("Processing File...")
            processing_text.setStyleSheet("""
                color: #2a5298;
                font-weight: 600;
                font-size: 18px;
                font-family: 'Segoe UI', Arial, sans-serif;
            """)
            processing_text.setAlignment(Qt.AlignCenter)
            
            processing_subtext = QLabel("Your document is being prepared for translation")
            processing_subtext.setStyleSheet("""
                color: #666;
                font-size: 14px;
                font-family: 'Segoe UI', Arial, sans-serif;
            """)
            processing_subtext.setAlignment(Qt.AlignCenter)
            
            processing_layout.addStretch()
            processing_layout.addWidget(spinner)
            processing_layout.addWidget(processing_text)
            processing_layout.addWidget(processing_subtext)
            processing_layout.addStretch()
            
            processing_widget = QWidget()
            processing_widget.setLayout(processing_layout)
            self.upload_area.setLayout(processing_layout)
            
            # Simulate file processing
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(1500, lambda: self.show_upload_complete(file_path))
    
    def show_upload_complete(self, file_path):
        # Update UI to show completion
        self.upload_area.clear()
        complete_layout = QVBoxLayout()
        complete_layout.setContentsMargins(0, 0, 0, 0)
        complete_layout.setSpacing(15)
        
        check_icon = QLabel()
        check_icon.setPixmap(QIcon.fromTheme("dialog-ok").pixmap(64, 64))
        check_icon.setAlignment(Qt.AlignCenter)
        
        complete_text = QLabel("Document Ready for Translation")
        complete_text.setStyleSheet("""
            color: #2a5298;
            font-weight: 600;
            font-size: 18px;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        complete_text.setAlignment(Qt.AlignCenter)
        
        # Get filename and size (simulated)
        from os.path import basename
        filename = basename(file_path)
        file_size = "2.4MB"  # In a real app, calculate actual size
        
        complete_subtext = QLabel(f"{filename} ({file_size})")
        complete_subtext.setStyleSheet("""
            color: #666;
            font-size: 14px;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        complete_subtext.setAlignment(Qt.AlignCenter)
        
        complete_layout.addStretch()
        complete_layout.addWidget(check_icon)
        complete_layout.addWidget(complete_text)
        complete_layout.addWidget(complete_subtext)
        complete_layout.addStretch()
        
        self.upload_area.setLayout(complete_layout)
        
        # Update translation preview with sample content
        self.translation_preview.setPlainText(f"Translated content from {filename} will appear here...")
    
    def translate_file(self):
        # Simulate translation
        self.translation_preview.setPlainText("This is a simulated translation of your document content.\n\nIn a real application, this would show the actual translated text from the API.")
        QMessageBox.information(self, "Translation", "File translation started!")
    
    def save_translation(self):
        # Show save dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Translation", "", 
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            QMessageBox.information(self, "Success", f"Translation saved to {file_path}")
    
    def start_capture(self):
        # Simulate screen capture
        self.preview_area.clear()
        
        # Create a mock screen capture preview
        preview_widget = QWidget()
        preview_layout = QVBoxLayout()
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_widget.setLayout(preview_layout)
        
        # Add a sample screen image (in a real app, this would be the actual capture)
        screen_label = QLabel()
        screen_label.setPixmap(QPixmap("sample_screen.png").scaled(800, 450, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        screen_label.setAlignment(Qt.AlignCenter)
        
        # Add overlay text
        overlay = QLabel()
        overlay.setText("""
            <div style="background-color: rgba(0,0,0,0.7); color: white; padding: 10px; border-radius: 4px;">
                <h3 style="margin:0;font-size:16px;font-family:'Segoe UI',Arial,sans-serif;">Sample Screen Content</h3>
                <p style="margin:0;font-size:14px;font-family:'Segoe UI',Arial,sans-serif;">This is a preview of captured screen content</p>
            </div>
        """)
        overlay.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        preview_layout.addWidget(screen_label)
        preview_layout.addWidget(overlay)
        
        self.preview_area.setLayout(preview_layout)
        
        # Update button states
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
    
    def stop_capture(self):
        # Reset preview area
        self.preview_area.clear()
        
        # Recreate placeholder
        preview_placeholder = QVBoxLayout()
        preview_placeholder.setContentsMargins(0, 0, 0, 0)
        preview_placeholder.setSpacing(15)
        
        placeholder_icon = QLabel()
        placeholder_icon.setPixmap(QIcon.fromTheme("camera-photo").pixmap(64, 64))
        placeholder_icon.setAlignment(Qt.AlignCenter)
        
        placeholder_text = QLabel("Screen preview will appear here")
        placeholder_text.setStyleSheet("""
            color: #666;
            font-size: 16px;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        placeholder_text.setAlignment(Qt.AlignCenter)
        
        preview_placeholder.addStretch()
        preview_placeholder.addWidget(placeholder_icon)
        preview_placeholder.addWidget(placeholder_text)
        preview_placeholder.addStretch()
        
        self.preview_area.setLayout(preview_placeholder)
        
        # Update button states
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
    
    def show_settings_dialog(self):
        # Create settings dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("API Key Settings")
        dialog.setModal(True)
        dialog.setFixedSize(500, 250)
        
        layout = QVBoxLayout()
        dialog.setLayout(layout)
        
        # Title
        title = QLabel("API Key Settings")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            font-family: 'Segoe UI', Arial, sans-serif;
            margin-bottom: 20px;
            color: #2a5298;
        """)
        
        # API key input
        api_input = QWidget()
        api_layout = QVBoxLayout()
        api_layout.setContentsMargins(0, 0, 0, 0)
        api_layout.setSpacing(10)
        api_input.setLayout(api_layout)
        
        api_label = QLabel("DeepSeek API Key:")
        api_label.setStyleSheet("""
            font-size: 16px;
            font-family: 'Segoe UI', Arial, sans-serif;
            color: #333;
        """)
        
        api_field = QLineEdit()
        api_field.setPlaceholderText("Enter your API key")
        api_field.setEchoMode(QLineEdit.Password)
        api_field.setStyleSheet("""
            QLineEdit {
                padding: 12px 15px;
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                font-size: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLineEdit:focus {
                border: 1px solid #1ba1e2;
            }
        """)
        
        api_layout.addWidget(api_label)
        api_layout.addWidget(api_field)
        
        # Save button
        save_btn = QPushButton("Save Key")
        save_btn.setIcon(QIcon.fromTheme("document-save"))
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #1ba1e2;
                color: white;
                padding: 12px 25px;
                border-radius: 6px;
                font-weight: 500;
                font-size: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
                border: none;
            }
            QPushButton:hover {
                background-color: #0d8bc9;
            }
        """)
        save_btn.setCursor(Qt.PointingHandCursor)
        
        # Add widgets to dialog
        layout.addWidget(title)
        layout.addWidget(api_input)
        layout.addStretch()
        layout.addWidget(save_btn, alignment=Qt.AlignRight)
        
        # Connect save button
        def save_api_key():
            key = api_field.text()
            if key:
                masked = f"ds-{key[-4:]}" if len(key) > 4 else "ds-****"
                self.api_info.setText(
                    f"API Status: <span style='color:#1ba1e2;'>Connected</span> | "
                    f"Key: <span style='color:#1ba1e2;'>{masked}</span>"
                )
                QMessageBox.information(self, "Success", "API key saved successfully!")
                dialog.close()
            else:
                QMessageBox.warning(self, "Error", "Please enter a valid API key")

        save_btn.clicked.connect(save_api_key)
        
        # Show the dialog
        dialog.exec_()

    def closeEvent(self, event):
        """Handle application close event"""
        reply = QMessageBox.question(
            self, "Exit",
            "Are you sure you want to exit?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

def main():
    app = QApplication(sys.argv)
    
    # Set application style and font
    app.setStyle("Fusion")
    
    # Create and show main window
    window = FnTranslateApp()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

