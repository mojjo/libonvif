#/********************************************************************
# libonvif/python/main.py 
#
# Copyright (c) 2023  Stephen Rhodes
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#*********************************************************************/

import os
import sys
import time
import importlib.util
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QSplitter, \
QTabWidget, QMessageBox
from PyQt6.QtCore import pyqtSignal, QObject, QSettings, QDir, QSize, QByteArray
from PyQt6.QtGui import QIcon
from camerapanel import CameraPanel
from filepanel import FilePanel
from settingspanel import SettingsPanel
from modulepanel import ModulePanel
from glwidget import GLWidget
from loguru import logger

sys.path.append("../build/libavio")
sys.path.append("../build/libavio/Release")
import avio

class MainWindowSignals(QObject):
    started = pyqtSignal(int)
    stopped = pyqtSignal()
    progress = pyqtSignal(float)
    error = pyqtSignal(str)

class ViewLabel(QLabel):
    def __init__(self):
        super().__init__()

    def sizeHint(self):
        return QSize(640, 480)

class MainWindow(QMainWindow):
    def __init__(self, clear_settings=False):
        super().__init__()
        QDir.addSearchPath('image', 'resources/')
        self.style()
        self.program_name = "onvif gui version 2.0.0"
        self.setWindowTitle(self.program_name)
        self.setWindowIcon(QIcon('image:onvif-gui.png'))
        self.settings = QSettings("onvif", "gui")
        if clear_settings:
            self.settings.clear()
        self.volumeKey = "MainWindow/volume"
        self.muteKey = "MainWindow/mute"
        self.geometryKey = "MainWindow/geometry"
        self.tabIndexKey = "MainWindow/tabIndex"
        self.splitKey = "MainWindow/split"

        self.player = None
        self.playing = False
        self.connecting = False
        self.volume = self.settings.value(self.volumeKey, 80)

        if self.settings.value(self.muteKey, 0) == 0:
            self.mute = False
        else:
            self.mute = True

        self.signals = MainWindowSignals()

        self.tab = QTabWidget()
        self.cameraPanel = CameraPanel(self)
        self.signals.started.connect(self.cameraPanel.onMediaStarted)
        self.signals.stopped.connect(self.cameraPanel.onMediaStopped)
        self.filePanel = FilePanel(self)
        self.signals.started.connect(self.filePanel.onMediaStarted)
        self.signals.stopped.connect(self.filePanel.onMediaStopped)
        self.signals.progress.connect(self.filePanel.onMediaProgress)
        self.modulePanel = ModulePanel(self)
        self.signals.stopped.connect(self.onMediaStopped)
        self.signals.error.connect(self.onError)
        self.settingsPanel = SettingsPanel(self)
        self.tab.addTab(self.cameraPanel, "Cameras")
        self.tab.addTab(self.filePanel, "Files")
        self.tab.addTab(self.settingsPanel, "Settings")
        self.tab.addTab(self.modulePanel, "Modules")
        self.tab.setCurrentIndex(int(self.settings.value(self.tabIndexKey, 0)))

        if self.settings.value(self.settingsPanel.renderKey, 0) == 0:
            self.glWidget = GLWidget()
        else:
            self.glWidget = ViewLabel()

        self.split = QSplitter()
        self.split.addWidget(self.glWidget)
        self.split.addWidget(self.tab)
        self.split.setStretchFactor(0, 10)
        self.split.splitterMoved.connect(self.splitterMoved)
        splitterState = self.settings.value(self.splitKey)
        self.setCentralWidget(self.split)

        rect = self.settings.value(self.geometryKey)
        if rect is not None:
            if rect.width() > 0 and rect.height() > 0 and rect.x() > 0 and rect.y() > 0:
                self.setGeometry(rect)

        if self.settingsPanel.chkAutoDiscover.isChecked():
            self.cameraPanel.btnDiscoverClicked()

        self.hook = None
        self.worker = None
        self.configure = None
        workerName = self.modulePanel.cmbWorker.currentText()
        if len(workerName) > 0:
            self.loadWorker(workerName)
            self.loadConfigure(workerName)

        if splitterState is not None:
            self.split.restoreState(splitterState)

    def loadConfigure(self, workerName):
        spec = importlib.util.spec_from_file_location("Configure", "modules/" + workerName)
        hook = importlib.util.module_from_spec(spec)
        sys.modules["Configure"] = hook
        spec.loader.exec_module(hook)
        self.configure = hook.Configure(self)
        self.modulePanel.setPanel(self.configure)

    def loadWorker(self, workerName):
        spec = importlib.util.spec_from_file_location("Worker", "modules/" + workerName)
        self.hook = importlib.util.module_from_spec(spec)
        sys.modules["Worker"] = self.hook
        spec.loader.exec_module(self.hook)
        self.worker = None

    def pythonCallback(self, F):
        if self.modulePanel.chkEngage.isChecked():
            if self.hook is not None:
                if self.worker is None:
                    self.worker = self.hook.Worker(self)
                start = time.time()
                self.worker(F)
                finish = time.time()
                elapsed = int((finish - start) * 1000)
                self.modulePanel.lblElapsed.setText("Elapsed Time (ms)  " + str(elapsed))
        else:
            self.modulePanel.lblElapsed.setText("")
        return F

    def playMedia(self, uri):
        self.stopMedia()
        self.player = avio.Player()
        self.player.uri = uri
        self.player.width = lambda : self.glWidget.width()
        self.player.height = lambda : self.glWidget.height()
        if not self.settingsPanel.chkLowLatency.isChecked():
            self.player.vpq_size = 100
            self.player.apq_size = 100
        self.player.progressCallback = lambda f : self.mediaProgress(f)

        video_filter = self.settingsPanel.txtVideoFilter.text()
        if self.settingsPanel.chkConvert2RGB.isChecked():
            self.player.video_filter = "format=rgb24"
            if len(video_filter) > 0:
                self.player.video_filter += "," + video_filter
        else:
            if len(video_filter) > 0:
                self.player.video_filter = video_filter
            else:
                self.player.video_filter = "null"
        if "fps=" in self.player.video_filter:
            self.filePanel.progress.setEnabled(False)

        if self.settings.value(self.settingsPanel.renderKey, 0) == 0:
            self.player.renderCallback = lambda F : self.glWidget.renderCallback(F)
        else:
            self.player.hWnd = self.glWidget.winId()

        self.player.disable_audio = self.settingsPanel.chkDisableAudio.isChecked()
        self.player.disable_video = self.settingsPanel.chkDisableVideo.isChecked()

        self.player.pythonCallback = lambda F : self.pythonCallback(F)
        self.player.cbMediaPlayingStarted = lambda n : self.mediaPlayingStarted(n)
        self.player.cbMediaPlayingStopped = lambda : self.mediaPlayingStopped()
        self.player.errorCallback = lambda s : self.errorCallback(s)
        self.player.infoCallback = lambda s : self.infoCallback(s)
        self.player.setVolume(int(self.volume))
        self.player.setMute(self.mute)
        self.player.keyframe_cache_size = self.settingsPanel.spnCacheSize.value()
        self.player.hw_device_type = self.settingsPanel.getDecoder()
        self.player.hw_encoding = self.settingsPanel.chkHardwareEncode.isChecked()
        self.player.post_encode = self.settingsPanel.chkPostEncode.isChecked()
        self.player.start()
        self.cameraPanel.setEnabled(False)

    def stopMedia(self):
        if self.player is not None:
            self.player.running = False
        while self.playing:
            time.sleep(0.01)

    def toggleMute(self):
        self.mute = not self.mute
        if self.mute:
            self.settings.setValue(self.muteKey, 1)
        else:
            self.settings.setValue(self.muteKey, 0)
        if self.player is not None:
            self.player.setMute(self.mute)

    def setVolume(self, value):
        self.volume = value
        self.settings.setValue(self.volumeKey, value)
        if self.player is not None:
            self.player.setVolume(value)

    def closeEvent(self, e):
        self.stopMedia()
        self.settings.setValue(self.geometryKey, self.geometry())
        self.settings.setValue(self.tabIndexKey, self.tab.currentIndex())

    def mediaPlayingStarted(self, n):
        self.playing = True
        self.connecting = False
        self.signals.started.emit(n)

    def mediaPlayingStopped(self):
        self.playing = False
        self.player = None
        self.signals.stopped.emit()

    def onMediaStopped(self):
        self.glWidget.clear()
        self.setWindowTitle(self.program_name)

    def mediaProgress(self, f):
        self.signals.progress.emit(f)

    def infoCallback(self, msg):
        print(msg)

    def errorCallback(self, s):
        self.signals.error.emit(s)

    def onError(self, msg):
        msgBox = QMessageBox(self)
        msgBox.setText(msg)
        msgBox.setWindowTitle(self.program_name)
        msgBox.setIcon(QMessageBox.Icon.Warning)
        msgBox.exec()
        self.cameraPanel.setBtnRecord()
        self.filePanel.control.setBtnRecord()
        self.cameraPanel.setEnabled(True)

    def splitterMoved(self, pos, index):
        self.settings.setValue(self.splitKey, self.split.saveState())

    def style(self):
        #blDefault = "#566170"
        blDefault = "#5B5B5B"
        #bmDefault = "#3E4754"
        bmDefault = "#4B4B4B"
        #bdDefault = "#283445"
        bdDefault = "#3B3B3B"
        flDefault = "#C6D9F2"
        fmDefault = "#9DADC2"
        fdDefault = "#808D9E"
        slDefault = "#FFFFFF"
        smDefault = "#DDEEFF"
        sdDefault = "#306294"
        strStyle = open("./resources/darkstyle.qss", "r").read()
        strStyle = strStyle.replace("background_light",  blDefault)
        strStyle = strStyle.replace("background_medium", bmDefault)
        strStyle = strStyle.replace("background_dark",   bdDefault)
        strStyle = strStyle.replace("foreground_light",  flDefault)
        strStyle = strStyle.replace("foreground_medium", fmDefault)
        strStyle = strStyle.replace("foreground_dark",   fdDefault)
        strStyle = strStyle.replace("selection_light",   slDefault)
        strStyle = strStyle.replace("selection_medium",  smDefault)
        strStyle = strStyle.replace("selection_dark",    sdDefault)
        #print(strStyle)
        self.setStyleSheet(strStyle)



if __name__ == '__main__':
    os.environ["QT_FILESYSTEMMODEL_WATCH_FILES"] = "ON"
    #if sys.platform == "win32":
    #    sys.argv += ['-platform', 'windows:darkmode=2']

    clear_settings = False
    if len(sys.argv) > 1:
        if str(sys.argv[1]) == "--clear":
            clear_settings = True

    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow(clear_settings)
    window.style()
    window.show()
    app.exec()