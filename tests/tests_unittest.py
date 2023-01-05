from speckle_toolbox.esri.toolboxes.speckle.speckle_arcgis import Toolbox, Speckle   # The code to test
from speckle_toolbox.esri.toolboxes.speckle.ui.project_vars import speckleInputsClass, toolboxInputsClass

import arcpy 
import os

from specklepy.api.wrapper import StreamWrapper
from specklepy.api.models import Branch, Stream, Streams
from specklepy.logging.exceptions import GraphQLException, SpeckleException
from specklepy.api.credentials import Account

import unittest   # The test framework

class Test_InitializingClasses(unittest.TestCase):
    def setUp(self) -> None:
        self.toolbox_input = toolboxInputsClass()
        self.speckle_input = speckleInputsClass()
        self.toolbox = Toolbox()
        self.speckleTool = Speckle()
        self.test_stream = "https://speckle.xyz/streams/17b0b76d13"
    
    def text_all_toolbox(self):
        self.assertTrue(isinstance(self.toolbox.tools[0], Speckle))

    def test_toolbox_inputs(self):
        self.assertEqual(self.toolbox_input.lat, 0)
        self.assertEqual(self.toolbox_input.lon, 0)
        self.assertIsNone(self.toolbox_input.active_stream)
        self.assertIsNone(self.toolbox_input.active_branch)
        self.assertIsNone(self.toolbox_input.active_commit)
        self.assertEqual(len(self.toolbox_input.selected_layers), 0)
        self.assertEqual(self.toolbox_input.messageSpeckle, "")
        self.assertEqual(self.toolbox_input.action, 1)
        self.assertIsNone(self.toolbox_input.project)
        self.assertEqual(self.toolbox_input.stream_file_path, "")

    def test_toolbox_inputs_functions(self):
        self.toolbox_input.setProjectStreams(StreamWrapper(self.test_stream))
        if os.path.exists(self.toolbox_input.stream_file_path):
            f = open(self.toolbox_input.stream_file_path, "r")
            existing_content = f.read()
            f.close()
            self.assertTrue(isinstance(existing_content, str))
        
        self.toolbox_input.setProjectStreams(None)
        if os.path.exists(self.toolbox_input.stream_file_path):
            f = open(self.toolbox_input.stream_file_path, "r")
            existing_content = f.read()
            f.close()
            self.assertTrue(isinstance(existing_content, str))

        self.assertTrue( isinstance(self.toolbox_input.get_survey_point(), tuple))
        self.assertTrue( isinstance(self.toolbox_input.get_survey_point()[0], float) or isinstance(self.toolbox_input.get_survey_point()[0], int))
        self.assertTrue( isinstance(self.toolbox_input.get_survey_point()[1], float) or isinstance(self.toolbox_input.get_survey_point()[1], int))

        self.assertTrue( self.toolbox_input.set_survey_point )

    def test_speckle_inputs(self):
        self.assertTrue(isinstance(self.speckle_input.accounts, list))
        self.assertTrue(self.speckle_input.account is None or isinstance(self.speckle_input.account, Account))
        self.assertTrue(self.speckle_input.streams_default is None or isinstance(self.speckle_input.streams_default, list))
        self.assertIsNone(self.speckle_input.project)
        self.assertIsNone(self.speckle_input.active_map)
        self.assertEqual(self.speckle_input.stream_file_path, "")
        self.assertTrue(isinstance(self.speckle_input.saved_streams, list))
        self.assertTrue(isinstance(self.speckle_input.all_layers, list))
        self.assertTrue(isinstance(self.speckle_input.clients, list))
    
    def test_speckle_inputs_functions(self):    
        
        self.assertTrue(isinstance(self.speckle_input.getProjectStreams(), list))
        getStreams = self.speckle_input.getProjectStreams(self.test_stream)
        self.assertTrue(isinstance(getStreams[0][0], StreamWrapper) and isinstance(getStreams[0][1], Stream))

        self.assertTrue(isinstance(self.speckle_input.tryGetStream(StreamWrapper(self.test_stream)), Stream))
        self.assertRaises(SpeckleException, lambda: self.speckle_input.tryGetStream(None))

    def test_parameters(self):
        actual = len(self.speckleTool.getParameterInfo())
        expected = 15
        self.assertEqual(actual, expected)

if __name__ == '__main__':
    unittest.main()

