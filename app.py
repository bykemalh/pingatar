import sys  
import logging
import os
from scapy.all import srp, Ether, ARP
import time as time_module
import time
import socket
import platform
import subprocess
from PySide6.QtCore import Signal, QObject, QRunnable, QThreadPool, QTimer, Slot, Qt,QSize,QThread
from PySide6.QtGui import QIcon, QColor, QFont, QDesktopServices,QStandardItemModel, QStandardItem
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMenu,
    QMenuBar,
    QPushButton,
    QHBoxLayout,
    QWidget,
    QSizePolicy,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QLineEdit,
    QTextEdit,
    QSpinBox,
    QGridLayout,
    QCheckBox,
    QSpacerItem,
    QTableView,
    QFileDialog,
)
import requests
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

DEFAULT_SETTINGS = {
    "ipAdress": "8.8.8.8 Google DNS\n1.1.1.1 Cloudflare DNS\nbykemalh.me Kemal\n192.168.1.1 Local",
    "timeout": 1000,
    "ping_time": 1000,
    "size": 32,
    "send_mail": False,
    "email": "",
    "time_send_mail": 60
}

class PingWorker(QObject, QRunnable):
    finished = Signal(str, str, str, str, str, str, str)  # 7 parametre için
    ping_result = Signal(str)

    def __init__(self, ip, name):
        QObject.__init__(self)
        QRunnable.__init__(self)
        self.ip = ip
        self.name = name
        self._is_running = True

    def run(self):
        try:
            if not self._is_running:
                return
            
            # Windows için ping komutu
            if platform.system().lower() == "windows":
                ping_cmd = ['ping', '-n', '1', '-w', '1000', self.ip]
            else:
                # Unix-tabanlı sistemler için ping komutu
                ping_cmd = ['ping', '-c', '1', '-W', '1', self.ip]
            
            ping = subprocess.run(ping_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            
            if not self._is_running:
                return
            
            if ping.returncode == 0:
                # Başarılı ping işlemi
                ip_reply, time_ms, ttl, status = "", "", "", "success"
                for line in ping.stdout.split('\n'):
                    if 'bytes from' in line or 'bytes de' in line:  # Windows için 'bytes de'
                        parts = line.split()
                        ip_reply = parts[2].strip(':')  # Windows'ta IP reply farklı bir konumda olabilir
                    if 'TTL=' in line.upper():  # Windows'ta 'TTL=' olarak geçer
                        ttl = line.upper().split('TTL=')[1].split()[0]
                        time_ms = line.split('time=')[1].split()[0].replace('ms', '')  # 'ms' ifadesini kaldır
                        break
                try:
                    host_name = socket.gethostbyaddr(self.ip)[0]
                except Exception:
                    host_name = "N/A"
                self.finished.emit(self.name, self.ip, ip_reply, status, time_ms, ttl, host_name)
            else:
                # Başarısız ping işlemi
                status = "timeout" if "timed out" in ping.stdout.lower() or "zaman aşımına uğradı" in ping.stdout.lower() else "no such host"
                self.finished.emit(self.name, self.ip, "-", status, "-", "-", "-")
        except Exception as e:
            # Genel hata durumu
            status = "Error"
            self.finished.emit(self.name, self.ip, "-", status, "-", "-", "-")

    def stop(self):
        self._is_running = False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.email_thread = None

        self.notified_ips = set()
        
        # Ayarları yükle
        self.load_settings()

        self.edit_form = EditForm(self)
        self.setWindowTitle("PingATAR")  # Title App
        self.setWindowIcon(QIcon('1212.ico'))  # App Icon
        self.resize(920, 550)  # Window Size

        self.failed_ips = {}
        self.last_email_sent_time = 0
        self.email_cooldown = 300

        self.thread = None
        self.worker = None

        self.last_ping_time = {}
        self.pool = QThreadPool()
        self.ping_timer = QTimer()
        self.ping_timer.timeout.connect(self.start_ping)
        self.workers = []

        # Menü Çubuğu
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        edit_menu = menubar.addMenu("Edit")
        view_menu = menubar.addMenu("View")
        help_menu = menubar.addMenu("Help")

        # File Menu Actions
        import_address_action = file_menu.addAction("Import Address")
        export_address_action = file_menu.addAction("Export Address")
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(QApplication.quit)  # Connect Exit action to quit the application
        export_address_action.triggered.connect(self.export_address)
        import_address_action.triggered.connect(self.import_address)

        # Edit Menu Actions
        self.edit_ip_action = edit_menu.addAction("Edit IP")
        self.edit_ip_action.triggered.connect(self.open_edit_form)
        self.start_action = edit_menu.addAction("Start")
        self.start_action.triggered.connect(self.start_ping)
        self.stop_action = edit_menu.addAction("Stop")
        self.stop_action.triggered.connect(self.stopPing)
        self.stop_action.setEnabled(False)
        self.reset_action = edit_menu.addAction("Reset")
        self.reset_action.triggered.connect(self.resetPing)

        # View Menu Actions
        enlarge_text_action = view_menu.addAction("Enlarge Text")
        shrink_text_action = view_menu.addAction("Shrink Text")
        enlarge_text_action.triggered.connect(self.enlarge_text)
        shrink_text_action.triggered.connect(self.shrink_text)

        # Help Menu Actions
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self.open_about_form)

        # Düğmeler
        self.button1 = QPushButton("Start")
        self.button2 = QPushButton("Stop")
        self.button3 = QPushButton("Edit IP")
        self.button4 = QPushButton("Save")

        self.button2.setEnabled(False)
        self.button1.setEnabled(True)
        self.button1.clicked.connect(self.start_ping)
        self.button2.clicked.connect(self.stopPing)
        self.button4.clicked.connect(self.save_settings_to_json)

        # Düğme Boyutu
        button_size = QSize(100, 30)
        self.button1.setFixedSize(button_size)
        self.button2.setFixedSize(button_size)
        self.button3.setFixedSize(button_size)
        self.button4.setFixedSize(button_size)
        self.button1.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Düğme Düzeni
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.button1)
        button_layout.addWidget(self.button2)
        button_layout.addWidget(self.button3)
        button_layout.addWidget(self.button4)
        button_layout.setAlignment(Qt.AlignLeft)

        self.button3.clicked.connect(self.open_edit_form)

        self.result_table = QTableView()
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.result_table.setEditTriggers(QTableView.NoEditTriggers)

        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Name", "IP/URL", "IP Reply", "Status", "Time", "TTL", "Host Name", "MAC Address", "Failed"])
        self.result_table.setModel(self.model)

        labelLink = QLabel('<a href="https://www.bykemalh.me">www.bykemalh.me</a>')
        labelLink.setOpenExternalLinks(True)

        # Yatay Panel Layout'u Oluştur
        linkPanel_layout = QHBoxLayout()
        linkPanel_layout.addWidget(labelLink)
        linkPanel_layout.addStretch()  # Link'i sola yaslamak için boşluk ekle

        # Link Panel Widget'ı Oluştur
        linkPanel_widget = QWidget()
        linkPanel_widget.setLayout(linkPanel_layout)

        # Main Layout'a Link Panel'i Ekle
        main_layout = QVBoxLayout()
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.result_table)
        main_layout.addWidget(linkPanel_widget)

        # Central Widget
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.pool = QThreadPool()
        self.ping_timer = QTimer()
        self.ping_timer.timeout.connect(self.start_ping)
        self.workers = []

    def __del__(self):
        self.cleanup()

    def cleanup(self):
        self.ping_timer.stop()
        if self.email_thread:
            self.email_thread.stop()
            self.email_thread.wait()
        for worker in self.workers:
            if isinstance(worker, QThread):
                worker.stop()
                worker.wait()  # Thread'in tamamen durmasını bekle
            elif isinstance(worker, QRunnable):
                worker.stop()
        self.pool.clear()  # ThreadPool'u temizle
        self.workers.clear()

    def closeEvent(self, event):
        self.cleanup()
        event.accept()

    def load_settings(self):
        settings_file = "pingatar_settings.json"

        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    
                # Ayarları yükle
                global ipAdress, timeout, ping_time, size, send_mail, email, time_send_mail
                ipAdress = settings.get("ipAdress", DEFAULT_SETTINGS["ipAdress"])
                timeout = settings.get("timeout", DEFAULT_SETTINGS["timeout"])
                ping_time = settings.get("ping_time", DEFAULT_SETTINGS["ping_time"])
                size = settings.get("size", DEFAULT_SETTINGS["size"])
                send_mail = settings.get("send_mail", DEFAULT_SETTINGS["send_mail"])
                email = settings.get("email", DEFAULT_SETTINGS["email"])
                time_send_mail = settings.get("time_send_mail", DEFAULT_SETTINGS["time_send_mail"])
                
            except json.JSONDecodeError:
                QMessageBox.warning(self, "Warning", "Settings file is corrupted. Using default settings.")
                self.use_default_settings()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error loading settings: {str(e)}")
                self.use_default_settings()
        else:
            # Ayar dosyası yoksa varsayılan ayarlarla çalış
            self.use_default_settings()

    def use_default_settings(self):
        global ipAdress, timeout, ping_time, size, send_mail, email, time_send_mail
        ipAdress = DEFAULT_SETTINGS["ipAdress"]
        timeout = DEFAULT_SETTINGS["timeout"]
        ping_time = DEFAULT_SETTINGS["ping_time"]
        size = DEFAULT_SETTINGS["size"]
        send_mail = DEFAULT_SETTINGS["send_mail"]
        email = DEFAULT_SETTINGS["email"]
        time_send_mail = DEFAULT_SETTINGS["time_send_mail"]

    def import_address(self):
        # Dosya seçme penceresini aç
        file_dialog = QFileDialog(self)
        file_path, _ = file_dialog.getOpenFileName(
            self,
            "Import Address",
            "",
            "JSON Files (*.json)"
        )

        if file_path:
            try:
                # JSON dosyasını oku ve ayarları yükle
                with open(file_path, 'r') as json_file:
                    settings = json.load(json_file)

                # Global değişkenlere ayarları ata
                global ipAdress, timeout, ping_time, size, send_mail, email, time_send_mail

                ipAdress = settings.get("ipAdress", ipAdress)
                timeout = settings.get("timeout", timeout)
                ping_time = settings.get("ping_time", ping_time)
                size = settings.get("size", size)
                send_mail = settings.get("send_mail", send_mail)
                email = settings.get("email", email)
                time_send_mail = settings.get("time_send_mail", time_send_mail)

                QMessageBox.information(self, "Success", "Settings imported successfully")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error importing settings: {str(e)}")

    def save_settings_to_json(self):
        global ipAdress, timeout, ping_time, size, send_mail, email, time_send_mail

        settings = {
            "ipAdress": ipAdress,
            "timeout": timeout,
            "ping_time": ping_time,
            "size": size,
            "send_mail": send_mail,
            "email": email,
            "time_send_mail": time_send_mail
        }

        # Uygulamanın çalıştığı dizine kaydetme
        json_file_path = os.path.join(os.getcwd(), 'pingatar_settings.json')

        try:
            with open(json_file_path, 'w') as json_file:
                json.dump(settings, json_file, indent=4)
            QMessageBox.information(self, "Success", f"Settings saved to {json_file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving settings: {str(e)}")

    def export_address(self):
        global ipAdress, timeout, ping_time, size, send_mail, email, time_send_mail

        settings = {
            "ipAdress": ipAdress,
            "timeout": timeout,
            "ping_time": ping_time,
            "size": size,
            "send_mail": send_mail,
            "email": email,
            "time_send_mail": time_send_mail
        }

        # Dosya kaydetme penceresini aç
        file_dialog = QFileDialog(self)
        save_path, _ = file_dialog.getSaveFileName(self, "Save Address", "pingatar_settings.json", "JSON Files (*.json)")

        if save_path:
            try:
                with open(save_path, 'w') as json_file:
                    json.dump(settings, json_file, indent=4)
                QMessageBox.information(self, "Success", f"Settings exported to {save_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error exporting settings: {str(e)}")

    def enlarge_text(self):
        self.change_font_size(1)

    def shrink_text(self):
        self.change_font_size(-1)

    def change_font_size(self, delta):
        for row in range(self.model.rowCount()):
            for column in range(self.model.columnCount()):
                item = self.model.item(row, column)
                if item:
                    font = item.font()
                    new_size = max(1, font.pointSize() + delta)
                    font.setPointSize(new_size)
                    item.setFont(font)
        self.result_table.resizeRowsToContents()  # Satır yüksekliğini içeriklere göre yeniden boyutlandırma

    # About Form
    def open_about_form(self):
        self.about_form = AboutForm()
        self.show_form_centered(self.about_form)

    def open_edit_form(self):
        self.edit_form = EditForm(self)
        self.show_form_centered(self.edit_form)

    def show_form_centered(self, form):
        form.show()
        x = self.pos().x() + (self.width() - form.width()) // 2
        y = self.pos().y() + (self.height() - form.height()) // 2
        form.move(x, y)

    def start_ping(self):
        self.button2.setEnabled(True)
        self.button1.setEnabled(False)
        self.stop_action.setEnabled(True)
        self.start_action.setEnabled(False)
        input_text = ipAdress
        input_lines = input_text.split("\n")

        for line in input_lines:
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    ip, name = parts[0], " ".join(parts[1:])
                    if not self.is_ip_in_table(ip, name):
                        self.add_ip_to_table(ip, name)
                    self.last_ping_time[ip] = time.time()
                    worker = PingWorker(ip, name)
                    worker.finished.connect(self.update_table)
                    self.workers.append(worker)
                    self.pool.start(worker)

        if not self.ping_timer.isActive():
            self.ping_timer.start(ping_time)

    def is_ip_in_table(self, ip, name):
        for row in range(self.model.rowCount()):
            if self.model.item(row, 1).text() == ip and self.model.item(row, 0).text() == name:
                return True
        return False

    def add_ip_to_table(self, ip, name):
        row_count = self.model.rowCount()
        self.model.insertRow(row_count)
        self.model.setItem(row_count, 0, QStandardItem(name))
        self.model.setItem(row_count, 1, QStandardItem(ip))
        self.model.setItem(row_count, 2, QStandardItem(""))
        self.model.setItem(row_count, 3, QStandardItem(""))
        self.model.setItem(row_count, 4, QStandardItem(""))
        self.model.setItem(row_count, 5, QStandardItem(""))
        self.model.setItem(row_count, 6, QStandardItem(""))
        self.model.setItem(row_count, 7, QStandardItem(""))
        self.model.setItem(row_count, 8, QStandardItem("0"))

    @Slot(str, str, str, str, str, str, str)
    def update_table(self, name, ip, ip_reply, status, ping_time, ttl, host_name):
        for row in range(self.model.rowCount()):
            if self.model.item(row, 1).text() == ip and self.model.item(row, 0).text() == name:
                print(f"Updating table for {ip}: status={status}")
                current_time = time.time()
                elapsed_time = current_time - self.last_ping_time.get(ip, current_time)
                self.last_ping_time[ip] = current_time

                self.set_row_items(row, ip, ip_reply, status, ping_time, ttl, host_name)
                failed_time_item = self.model.item(row, 8)
                if status == "success":
                    self.model.setItem(row, 8, QStandardItem("0s"))
                    if ip in self.notified_ips:
                        self.notified_ips.remove(ip)
                else:
                    failed_time_text = failed_time_item.text()
                    if 'm' in failed_time_text:
                        minutes, seconds = map(int, failed_time_text.replace('m', '').replace('s', '').split())
                        failed_count = minutes * 60 + seconds
                    else:
                        failed_count = int(failed_time_text.replace('s', ''))
                    
                    failed_count += int(elapsed_time)
                    failed_time_str = self.format_failed_time(failed_count)
                    self.model.setItem(row, 8, QStandardItem(failed_time_str))
                break
        else:
            print(f"IP not found in table: {ip}")

        self.check_and_send_email()

    def check_and_send_email(self):
        current_time = time.time()
        if send_mail and email:
            newly_failed_ips = []
            for row in range(self.model.rowCount()):
                ip = self.model.item(row, 1).text()
                failed_time_text = self.model.item(row, 8).text()
                failed_time = self.parse_failed_time(failed_time_text)
                
                if failed_time >= time_send_mail:
                    if ip not in self.failed_ips and ip not in self.notified_ips:
                        self.failed_ips[ip] = failed_time
                        newly_failed_ips.append((ip, failed_time))
                        self.notified_ips.add(ip)
                elif ip in self.failed_ips:
                    del self.failed_ips[ip]  # IP artık başarılı, listeden çıkar

            if newly_failed_ips:
                subject = "PingATAR - Başarısız Ping Bildirimi"
                
                if self.email_thread:
                    self.email_thread.stop()
                    self.email_thread.wait()
                
                self.email_thread = EmailSenderThread(email, subject, newly_failed_ips)
                self.email_thread.email_sent.connect(self.on_email_sent)
                self.email_thread.start()
                
                self.last_email_sent_time = current_time

    def parse_failed_time(self, failed_time_text):
        if 'm' in failed_time_text:
            minutes, seconds = map(int, failed_time_text.replace('m', '').replace('s', '').split())
            return minutes * 60 + seconds
        else:
            return int(failed_time_text.replace('s', ''))

    def on_email_sent(self, success, message):
        if success:
            QMessageBox.information(self, "E-posta Gönderildi", "Başarısız ping bildirimi e-postası gönderildi.")
            print(message)
        else:
            QMessageBox.warning(self, "E-posta Hatası", f"E-posta gönderimi başarısız: {message}")
            print(f"E-posta gönderimi başarısız: {message}")

    def format_failed_time(self, failed_count):
        if failed_count >= 60:
            minutes = int(failed_count // 60)
            seconds = int(failed_count % 60)
            return f"{minutes}m {seconds}s"
        else:
            return f"{int(failed_count)}s"

    def set_row_items(self, row, ip, ip_reply, status, time, ttl, host_name):
        font = self.model.item(row, 0).font()  # Mevcut yazı tipini al

        failed_time_item = self.model.item(row, 8)
        if failed_time_item:
            failed_time_text = failed_time_item.text()
            if 'm' in failed_time_text:
                minutes, seconds = map(int, failed_time_text.replace('m', '').replace('s', '').split())
                failed_time = minutes * 60 + seconds
            else:
                failed_time = int(float(failed_time_text.replace('s', '')))
        else:
            failed_time = 0

        items = [
            QStandardItem(ip_reply),
            QStandardItem(status),
            QStandardItem(time),
            QStandardItem(ttl),
            QStandardItem(host_name),
            QStandardItem("-"),  # MAC adresini başlangıçta "-" olarak ayarla
        ]

        if status == "success":
            failed_time = 0
        else:
            failed_time += ping_time / 1000  # ping_time milisaniyeden saniyeye dönüştürülüyor

        failed_time_str = self.format_failed_time(failed_time)
        items.append(QStandardItem(failed_time_str))

        color = QColor("green") if status == "success" else QColor("red")
        for i, item in enumerate(items):
            item.setForeground(color)
            item.setFont(font)  # Aynı yazı tipi boyutunu ayarla
            self.model.setItem(row, i + 2, item)

        # MAC adresini asenkron olarak bul
        worker = MacAddressWorker(ip)
        worker.finished.connect(lambda ip, mac: self.update_mac_address(row, ip, mac))
        self.workers.append(worker)  # Worker'ı listeye ekle
        worker.start()

    def update_mac_address(self, row, ip, mac):
        for i in range(self.model.rowCount()):
            if self.model.item(i, 1).text() == ip:
                self.model.setItem(i, 7, QStandardItem(mac or "-"))

    def stopPing(self):
        self.button2.setEnabled(False)
        self.button1.setEnabled(True)
        self.stop_action.setEnabled(False)
        self.start_action.setEnabled(True)
        self.ping_timer.stop()
        for worker in self.workers:
            if isinstance(worker, QThread):
                worker.stop()
                worker.wait()  # Thread'in tamamen durmasını bekle
            elif isinstance(worker, QRunnable):
                worker.stop()
        self.pool.clear()  # ThreadPool'u temizle
        self.workers.clear()
        self.model.clear()
        self.model.setHorizontalHeaderLabels(["Name", "IP/URL", "IP Reply", "Status", "Time", "TTL", "Host Name", "MAC Address", "Failed"])
        self.result_table.setModel(self.model)

    def resetPing(self):
        self.button2.setEnabled(False)
        self.button1.setEnabled(True)
        self.stop_action.setEnabled(False)
        self.start_action.setEnabled(True)
        self.ping_timer.stop()
        for worker in self.workers:
            worker.stop()
        self.pool.clear()
        self.model.clear()
        self.model.setHorizontalHeaderLabels(["Name", "IP/URL", "IP Reply", "Status", "Time", "TTL", "Host Name", "MAC Address", "Failed"])
        self.result_table.setModel(self.model)
        global ipAdress
        ipAdress = ""
        self.edit_form.resetClear

    def closeEvent(self, event):
        self.ping_timer.stop()
        for worker in self.workers:
            worker.stop()  # stop metodunu çağır
        self.workers.clear()
        event.accept()

class EditForm(QWidget):
    def __init__(self, main_window):
        super().__init__()
        global ipAdress
        global timeout
        global ping_time
        global size
        global send_mail
        global email
        time_send_mail
        self.main_window = main_window
        self.setWindowTitle("Edit IP")
        self.setWindowIcon(QIcon('1212.ico'))
        self.setFixedSize(500, 500)
        
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setWindowModality(Qt.ApplicationModal)
        
        label_ip = QLabel("IP Address:")
        self.edit_ip = QTextEdit()
        self.edit_ip.setText(ipAdress)
        layout_address = QVBoxLayout()
        button_layout = QHBoxLayout()
        layout_other = QGridLayout()
        layout_address.addWidget(label_ip)
        layout_address.addWidget(self.edit_ip)
        
        # Timeout
        self.timeout_spinbox = self.add_spinbox(layout_other, "Timeout(ms):", 1, 100, 10000, 100, timeout)
        # Ping Time
        self.ping_time_spinbox = self.add_spinbox(layout_other, "Ping Time (ms):", 2, 1000, 10000, 100, ping_time)
        # Size
        self.size_spinbox = self.add_spinbox(layout_other, "Size (byte):", 3, 8, 8196, 8,size)
        
        # Send Mail
        self.send_mail_checkbox = QCheckBox("Send Mail upon error")
        self.send_mail_checkbox.setChecked(send_mail)
        email_label = QLabel("Email:")
        self.email_edit = QLineEdit()
        self.email_edit.setText(email)
        layout_other.addWidget(self.send_mail_checkbox, 4, 1)
        layout_other.addWidget(email_label, 4, 2)
        layout_other.addWidget(self.email_edit, 4, 3)
        
        # Time Send Mail
        self.time_send_mail_spinbox = self.add_spinbox(layout_other, "Time send Mail (S):", 5, 30, 1800, 30, time_send_mail)
        
        # OK ve Cancel Butonları
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        ok_button.clicked.connect(self.update_data)
        cancel_button.clicked.connect(self.close)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        
        # Ana Layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(layout_address)
        main_layout.addLayout(layout_other)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
    
    def add_spinbox(self, layout, label_text, row, min_value, max_value, step, default_value):
        label = QLabel(label_text)
        spinbox = QSpinBox()
        spinbox.setFixedSize(100, 30)
        spinbox.setRange(min_value, max_value)
        spinbox.setSingleStep(step)
        spinbox.setValue(default_value)
        layout.addWidget(label, row, 1)
        layout.addWidget(spinbox, row, 2)
        return spinbox
    
    def update_data(self):
        global ipAdress, timeout, ping_time, size, send_mail, email, time_send_mail
        ipAdress = self.edit_ip.toPlainText()
        timeout = self.timeout_spinbox.value()
        ping_time = self.ping_time_spinbox.value()
        self.main_window.ping_time = ping_time  # MainWindow'daki ping_time'ı güncelle
        size = self.size_spinbox.value()
        send_mail = self.send_mail_checkbox.isChecked()
        email = self.email_edit.text()
        time_send_mail = self.time_send_mail_spinbox.value()
        self.close()
    
    def resetClear(self):
        self.edit_ip.clear()
        self.email_edit.clear()
        

class AboutForm(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("About") # App Title
        self.setWindowIcon(QIcon('1212.ico')) # App Icon
        self.setFixedSize(450, 300) # App Size 

        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowCloseButtonHint) # Disable Maximize and Minimize Button
        self.setWindowModality(Qt.ApplicationModal) # Use Form Modal (First Plan)

        # App Name Label
        label_name = QLabel("PingATAR")
        label_name.setStyleSheet("""
                            color: #cc0000;
                            font-size: 28pt;
                            font-weight: bold;
                            font-family: 'Segoe UI', sans-serif;
                            """)
        # Version Label
        label_version = QLabel("V1.0.1")
        label_version.setStyleSheet("""
                            font-size: 14pt;
                            font-style: italic;
                            font-family: 'Segoe UI', sans-serif;
                            """)

        # Creators Message
        label_message = QLabel("""<p>This application was developed by <b>Kemal Hafızoğlu</b> and shared on the internet free of charge for everyone's use.</p>
                                 <p>Additionally, the application is shared on <b>GitHub</b> as open source and has a <b>GNU GPL V3</b> license.</p>
                                 <p>Everyone is free to use, modify, and distribute this software under the terms of the GNU GPL V3 license.</p>""")
        label_message.setStyleSheet("""
                            font-size: 12pt;
                            font-family: 'Segoe UI', sans-serif;
                            """)
        label_message.setWordWrap(True)

        # Link WebSite
        link_web_site = QLabel('<a href="https://www.bykemalh.me">Website</a>')
        link_web_site.setOpenExternalLinks(True)
        link_web_site.setStyleSheet("font-size: 12pt; color: #0066cc; text-decoration: underline; font-family: 'Segoe UI', sans-serif;")

        # Link Github
        link_github = QLabel('<a href="https://www.github.com/bykemalh/pingatar">GitHub</a>')
        link_github.setOpenExternalLinks(True)
        link_github.setStyleSheet("font-size: 12pt; color: #0066cc; text-decoration: underline; font-family: 'Segoe UI', sans-serif;")

        # Check Update
        self.request_button = QPushButton("Check for Updates")
        self.request_button.clicked.connect(self.check_update)
        self.request_button.setStyleSheet("""
                            padding: 8px 16px;
                            """)
        
        # Layout Name and Version
        layout_name = QHBoxLayout()
        layout_name.addWidget(label_name)
        layout_name.addWidget(label_version)
        layout_name.addSpacerItem(QSpacerItem(10, 0, QSizePolicy.Fixed, QSizePolicy.Minimum))
        layout_name.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        layout_name.setAlignment(Qt.AlignLeft)

        # Layout Creators Message
        layout_message = QHBoxLayout()
        layout_message.addWidget(label_message)
        layout_message.addSpacerItem(QSpacerItem(10, 0, QSizePolicy.Fixed, QSizePolicy.Minimum))
        layout_message.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        layout_message.setAlignment(Qt.AlignLeft)

        # Link Layout
        layout_links = QHBoxLayout()
        layout_links.addWidget(link_web_site)
        layout_links.addWidget(link_github)
        layout_links.addWidget(self.request_button)
        layout_links.addSpacerItem(QSpacerItem(10, 0, QSizePolicy.Fixed, QSizePolicy.Minimum))
        layout_links.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        layout_links.setAlignment(Qt.AlignLeft)

        # Main Layout
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignTop)
        main_layout.addLayout(layout_name)
        main_layout.addLayout(layout_message)
        main_layout.addLayout(layout_links)
        self.setLayout(main_layout)

    def check_update(self):
        self.update_thread = CheckUpdateThread("1.0.1")
        self.update_thread.update_available.connect(self.show_update_available)
        self.update_thread.error_occurred.connect(self.show_error)
        self.update_thread.start()

    def show_update_available(self, message):
        QMessageBox.information(self, "Check Update", message)

    def show_error(self, error_message):
        QMessageBox.critical(self, "Check Update", error_message)

class CheckUpdateThread(QThread):
    update_available = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, version):
        super().__init__()
        self.version = version

    def run(self):
        url = 'http://127.0.0.1:6000/api/version'
        data = {"version": self.version}

        try:
            response = requests.post(url, json=data)

            if response.status_code == 200:
                response_data = response.json()
                message_from_api = response_data.get("message")
                if message_from_api:
                    self.update_available.emit(message_from_api)
            else:
                self.error_occurred.emit("Could not connect to the server")
        except Exception as e:
            self.error_occurred.emit("Could not connect to the server to check for updates")

class MacAddressWorker(QThread):
    finished = Signal(str, str)  # İşlem bittiğinde IP ve MAC adresi sinyali gönderecek

    def __init__(self, ip):
        super().__init__()
        self.ip = ip
        self.is_running = True

    def run(self):
        try:
            if not self.is_running:
                return
            mac_address = self.get_mac_address(self.ip)  # MAC adresini al
            if not self.is_running:  # Thread çalışıyorsa
                return

            # MAC adresi bulunduysa veya bulunamadıysa 'finished' sinyalini gönder
            self.finished.emit(self.ip, mac_address)

        except Exception as e:
            print(f"Error retrieving MAC for {self.ip}: {e}")
            if self.is_running:
                self.finished.emit(self.ip, 'Not Found')

    def stop(self):
        self.is_running = False
        self.wait()

    def get_mac_address(self, ip):
        """
        IP adresi için MAC adresini alır
        """
        # 1. Adım: İlk olarak ARP tablosundan sorgula
        mac_address = self.get_mac_from_arp_table(ip)
        if mac_address:
            return mac_address

        # 2. Adım: Eğer ARP tablosunda yoksa, cihaza ping at
        if self.ping_device(ip):
            mac_address = self.get_mac_from_arp_table(ip)
            if mac_address:
                return mac_address

        # 3. Adım: Hala bulunamadıysa, scapy kullanarak doğrudan sorgu yap
        mac_address = self.get_mac_from_ip_scapy(ip)
        if mac_address:
            return mac_address

        # 4. Adım: Hala MAC bulunamadıysa
        return "Not Found"

    def ping_device(self, ip_address):
        try:
            # Ping komutunu işletim sistemine göre çalıştır
            if sys.platform == "win32":
                subprocess.run(["ping", "-n", "1", ip_address], capture_output=True)
            else:
                subprocess.run(["ping", "-c", "1", ip_address], capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def get_mac_from_arp_table(self, ip_address):
        """ARP tablosundan MAC adresini alır"""
        try:
            # Windows için ARP komutu farklı, diğer işletim sistemleri için standart
            if sys.platform == "win32":
                result = subprocess.run(["arp", "-a", ip_address], capture_output=True, text=True)
                return result.stdout.split()[-1] if result.returncode == 0 else None
            else:
                result = subprocess.run(["arp", "-n", ip_address], capture_output=True, text=True)
                # ARP çıktısından MAC adresini bulma
                mac_address = self.extract_mac_address(result.stdout, ip_address)
                return mac_address if result.returncode == 0 else None
        except subprocess.CalledProcessError:
            return None

    def extract_mac_address(self, arp_output, ip_address):
        """ARP tablosu çıktısından MAC adresini çıkarır"""
        import re
        # MAC adresleri için regex deseni
        pattern = r"{}.*?((?:[0-9a-fA-F]{{2}}[:-]){{5}}[0-9a-fA-F]{{2}})".format(ip_address)
        match = re.search(pattern, arp_output)
        return match.group(1) if match else None

    def get_mac_from_ip_scapy(self, ip_address):
        """Scapy kullanarak IP adresinin MAC adresini alır"""
        try:
            ans, _ = srp(Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=ip_address), timeout=2, verbose=False)
            return ans[0][1].hwsrc if ans else None
        except PermissionError as e:
            print(f"Permission error while accessing network resources: {e}")
            return None

class EmailSenderThread(QThread):
    email_sent = Signal(bool, str)

    def __init__(self, receiver_email, subject, failed_ips):
        super().__init__()
        self.receiver_email = receiver_email
        self.subject = subject
        self.failed_ips = failed_ips
        self._is_running = True

    def run(self):
        if not self._is_running:
            return

        try:
            yandex_smtp_server = ""
            port = 587
            email_sender = ""
            password = ""

            message = MIMEMultipart("alternative")
            message["From"] = email_sender
            message["To"] = self.receiver_email
            message["Subject"] = self.subject

            html = self.create_html_content()

            text_part = MIMEText("Bu e-posta istemciniz HTML içeriği görüntüleyemiyorsa görünür.", "plain")
            html_part = MIMEText(html, "html")

            message.attach(text_part)
            message.attach(html_part)

            with smtplib.SMTP(yandex_smtp_server, port, timeout=30) as server:
                server.starttls()
                server.login(email_sender, password)
                server.sendmail(email_sender, self.receiver_email, message.as_string())

            if self._is_running:
                self.email_sent.emit(True, "E-posta başarıyla gönderildi.")
        except Exception as e:
            if self._is_running:
                self.email_sent.emit(False, f"E-posta gönderiminde hata oluştu: {e}")

    def stop(self):
        self._is_running = False

    def create_html_content(self):
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 600px; margin: auto; padding: 20px; }}
                h1 {{ color: #333366; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>PingATAR - Başarısız Ping Bildirimi</h1>
                <p>Aşağıdaki IP adreslerinde ping başarısız oldu:</p>
                <table>
                    <tr>
                        <th>IP Adresi</th>
                        <th>Başarısız Süre</th>
                    </tr>
                    {''.join(f"<tr><td>{ip}</td><td>{self.format_failed_time(failed_time)}</td></tr>" for ip, failed_time in self.failed_ips)}
                </table>
            </div>
        </body>
        </html>
        """
        return html

    def format_failed_time(self, failed_time):
        if failed_time >= 60:
            minutes = int(failed_time // 60)
            seconds = int(failed_time % 60)
            return f"{minutes} dakika {seconds} saniye"
        else:
            return f"{int(failed_time)} saniye"

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    logging.getLogger().setLevel(logging.ERROR)
    window.show()
    exit_code = app.exec()
    window.cleanup()
    sys.exit(exit_code)