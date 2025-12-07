
import unittest
import sys
import os
import json

# Add src to sys.path
sys.path.append(os.path.abspath("src"))

from fyodoros.kernel.syscalls import SyscallHandler
from fyodoros.bin import explorer

class TestExplorer(unittest.TestCase):
    def setUp(self):
        self.handler = SyscallHandler()
        # Setup clean environment
        # We assume /home/guest exists from FileSystem init
        self.handler.sys_write("/home/guest/source.txt", "content")

    def test_copy_file_to_new_path(self):
        result = explorer.main(["copy", "/home/guest/source.txt", "/home/guest/dest.txt"], self.handler)
        result_json = json.loads(result)

        self.assertEqual(result_json.get("status"), "copied")
        self.assertEqual(result_json.get("dst"), "/home/guest/dest.txt")
        self.assertEqual(self.handler.sys_read("/home/guest/dest.txt"), "content")

    def test_copy_file_to_directory(self):
        # Create directory
        self.handler.fs.mkdir("/home/guest/subdir")

        result = explorer.main(["copy", "/home/guest/source.txt", "/home/guest/subdir"], self.handler)
        result_json = json.loads(result)

        self.assertEqual(result_json.get("status"), "copied")
        self.assertEqual(result_json.get("dst"), "/home/guest/subdir/source.txt")
        self.assertEqual(self.handler.sys_read("/home/guest/subdir/source.txt"), "content")

    def test_move_file_to_new_path(self):
        result = explorer.main(["move", "/home/guest/source.txt", "/home/guest/moved.txt"], self.handler)
        result_json = json.loads(result)

        self.assertEqual(result_json.get("status"), "moved")
        self.assertEqual(result_json.get("dst"), "/home/guest/moved.txt")
        self.assertEqual(self.handler.sys_read("/home/guest/moved.txt"), "content")

        # Verify source is gone
        with self.assertRaises(Exception):
            self.handler.sys_read("/home/guest/source.txt")

    def test_move_file_to_directory(self):
        self.handler.fs.mkdir("/home/guest/subdir_move")

        result = explorer.main(["move", "/home/guest/source.txt", "/home/guest/subdir_move"], self.handler)
        result_json = json.loads(result)

        self.assertEqual(result_json.get("status"), "moved")
        self.assertEqual(result_json.get("dst"), "/home/guest/subdir_move/source.txt")
        self.assertEqual(self.handler.sys_read("/home/guest/subdir_move/source.txt"), "content")

        # Verify source is gone
        with self.assertRaises(Exception):
            self.handler.sys_read("/home/guest/source.txt")

    def test_copy_non_existent_source(self):
        result = explorer.main(["copy", "/home/guest/missing.txt", "/home/guest/dest.txt"], self.handler)
        result_json = json.loads(result)

        self.assertIn("error", result_json)

if __name__ == '__main__':
    unittest.main()
