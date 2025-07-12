import unittest
import numpy as np
from flai.api import projects


class UtilsTests(unittest.TestCase):

    def test_get_projects(self):
        flaiProjectApi = projects.FlaiProject()
        self.assertIsNotNone(flaiProjectApi.get_projects())

if __name__ == '__main__':
    unittest.main()
