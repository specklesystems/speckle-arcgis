import inspect
import os
import threading
from PyQt5 import QtWidgets, uic
from specklepy.logging.exceptions import SpeckleException

from speckle.speckle.utils.panel_logging import logToUser
import speckle.specklepy_qt_ui.qt_ui
from speckle.specklepy_qt_ui.qt_ui.mainWindow import (
    SpeckleGISDialog as SpeckleGISDialog_UI,
)

ui_file_path = os.path.join(
    os.path.dirname(speckle.specklepy_qt_ui.qt_ui.__file__),
    os.path.join("ui", "mainWindow_main.ui"),
)


class SpeckleGISDialog(SpeckleGISDialog_UI):
    def __init__(self, parent=None):
        """Constructor."""
        super(SpeckleGISDialog, self).__init__(
            parent
        )  # , QtCore.Qt.WindowStaysOnTopHint)
        uic.loadUi(ui_file_path, self)  # Load the .ui file
        # self.show()
        self.runAllSetup()

    def populateProjectStreams(self, plugin):
        try:
            from speckle.speckle.utils.project_vars import set_project_streams

            if not self:
                return
            self.streamList.clear()
            for stream in plugin.current_streams:
                self.streamList.addItems(
                    [
                        (
                            f"Stream not accessible - {stream[0].stream_id}"
                            if stream[1] is None
                            or isinstance(stream[1], SpeckleException)
                            else f"{stream[1].name}, {stream[1].id} | {stream[0].stream_url.split('/streams')[0].split('/projects')[0]}"
                        )
                    ]
                )
            if len(plugin.current_streams) == 0:
                self.streamList.addItems([""])
            self.streamList.addItems(["Create New Stream"])
            set_project_streams(plugin)
            index = self.streamList.currentIndex()
            if index == -1:
                self.streams_remove_button.setEnabled(False)
            else:
                self.streams_remove_button.setEnabled(True)

            if len(plugin.current_streams) > 0:
                plugin.active_stream = plugin.current_streams[0]
        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=self)
            return

    def completeStreamSection(self, plugin):
        try:
            self.streams_remove_button.clicked.connect(
                lambda: self.onStreamRemoveButtonClicked(plugin)
            )
            self.streamList.currentIndexChanged.connect(
                lambda: self.onActiveStreamChanged(plugin)
            )
            self.streamBranchDropdown.currentIndexChanged.connect(
                lambda: self.populateActiveCommitDropdown(plugin)
            )
            return
        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=self)
            return

    def onStreamRemoveButtonClicked(self, plugin):
        try:
            from speckle.speckle.utils.project_vars import set_project_streams

            if not self:
                return
            index = self.streamList.currentIndex()
            if len(plugin.current_streams) > 0:
                plugin.current_streams.pop(index)
            plugin.active_stream = None
            self.streamBranchDropdown.clear()
            self.commitDropdown.clear()

            set_project_streams(plugin)
            self.populateProjectStreams(plugin)
        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=self)
            return

    def populateProjectStreams(self, plugin):
        try:
            from speckle.speckle.utils.project_vars import set_project_streams

            if not self:
                return
            self.streamList.clear()
            for stream in plugin.current_streams:
                self.streamList.addItems(
                    [
                        (
                            f"Speckle Project not accessible - {stream[0].stream_id}"
                            if stream[1] is None
                            or isinstance(stream[1], SpeckleException)
                            else f"{stream[1].name}, {stream[1].id} | {stream[0].stream_url.split('/streams')[0].split('/projects')[0]}"
                        )
                    ]
                )
            if len(plugin.current_streams) == 0:
                self.streamList.addItems([""])
            self.streamList.addItems(["Create New Project"])
            set_project_streams(plugin)
            index = self.streamList.currentIndex()
            if index == -1:
                self.streams_remove_button.setEnabled(False)
            else:
                self.streams_remove_button.setEnabled(True)

            if len(plugin.current_streams) > 0:
                plugin.active_stream = plugin.current_streams[0]
        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=self)
            return

    def cancelOperations(self):
        for t in threading.enumerate():
            if "speckle_" in t.name:
                t.kill()
                t.join()
