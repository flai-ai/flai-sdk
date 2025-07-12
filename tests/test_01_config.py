import unittest
import numpy as np
from flai.config import Config


class UtilsTests(unittest.TestCase):

    def test_get_config(self):
        config = Config()
        config.load()
        self.assertIsNotNone(config.flai_host)


    def test_set_config(self):
        config = Config()
        new_key_id = 'MY_ID'
        config.set(aws_access_key_id=new_key_id)
        self.assertEqual(new_key_id, config.aws_access_key_id)

if __name__ == '__main__':
    unittest.main()
