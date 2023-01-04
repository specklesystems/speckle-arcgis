from speckle_toolbox.esri.toolboxes.speckle.speckle_arcgis import Speckle   # The code to test
from speckle_toolbox.esri.toolboxes.speckle.ui.project_vars import speckleInputsClass, toolboxInputsClass
import unittest   # The test framework

class Test_TestIncrementDecrement(unittest.TestCase):
    def setUp(self) -> None:
        self.speckle_input = speckleInputsClass()
        self.toolbox_input = toolboxInputsClass()
        self.speckleTool = Speckle()

    def test_speckle_inputs(self):
        actual = len(self.speckleTool.getParameterInfo())
        expected = 15
        self.assertEqual(actual, expected)

    def test_parameters(self):
        actual = len(self.speckleTool.getParameterInfo())
        expected = 15
        self.assertEqual(actual, expected)

    #def test_decrement(self):
    #    self.assertEqual(inc_dec.decrement(3), 4)

if __name__ == '__main__':
    unittest.main()

