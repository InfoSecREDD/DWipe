import importlib.util
import os
import sys
import types
import unittest
from collections import namedtuple
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "dwipe.py"


def load_dwipe_module():
    os.environ["DWIPE_SKIP_VENV_BOOTSTRAP"] = "1"

    psutil_stub = types.ModuleType("psutil")
    psutil_stub.disk_partitions = lambda all=False: []
    psutil_stub.disk_usage = lambda path: namedtuple("Usage", "total free")(0, 0)

    tqdm_stub = types.ModuleType("tqdm")
    tqdm_stub.tqdm = lambda *args, **kwargs: None

    colorama_stub = types.ModuleType("colorama")
    colorama_stub.init = lambda **kwargs: None
    colorama_stub.Fore = types.SimpleNamespace(
        RED="",
        GREEN="",
        YELLOW="",
        BLUE="",
        MAGENTA="",
        CYAN="",
        WHITE="",
    )
    colorama_stub.Style = types.SimpleNamespace(RESET_ALL="", BRIGHT="")

    with mock.patch.dict(
        sys.modules,
        {
            "psutil": psutil_stub,
            "tqdm": tqdm_stub,
            "colorama": colorama_stub,
        },
    ):
        spec = importlib.util.spec_from_file_location("dwipe_under_test", MODULE_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


class CrossPlatformTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dwipe = load_dwipe_module()
        cls.Completed = namedtuple("Completed", "returncode stdout stderr")
        cls.Partition = namedtuple("Partition", "device mountpoint fstype opts")
        cls.Usage = namedtuple("Usage", "total free")

    def test_parse_windows_disk_number_accepts_multiple_forms(self):
        self.assertEqual(self.dwipe.parse_windows_disk_number(r"\\.\PhysicalDrive7"), "7")
        self.assertEqual(self.dwipe.parse_windows_disk_number("PhysicalDrive3"), "3")
        self.assertEqual(self.dwipe.parse_windows_disk_number("9"), "9")
        self.assertIsNone(self.dwipe.parse_windows_disk_number("not-a-disk"))

    def test_disk_path_exists_accepts_windows_raw_disks(self):
        self.assertTrue(self.dwipe.disk_path_exists("Windows", r"\\.\PhysicalDrive4"))
        self.assertTrue(self.dwipe.disk_path_exists("Windows", "4"))
        self.assertFalse(self.dwipe.disk_path_exists("Windows", "diskX"))

    def test_get_device_path_for_mount_uses_parent_linux_disk(self):
        with mock.patch.object(
            self.dwipe.subprocess,
            "check_output",
            return_value=b"Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/nvme0n1p1 1 1 1 1% /mnt\n",
        ), mock.patch.object(self.dwipe, "command_exists", return_value=False):
            device = self.dwipe.get_device_path_for_mount("/mnt", system="Linux")

        self.assertEqual(device, "/dev/nvme0n1")

    def test_get_device_path_for_mount_uses_windows_disk_number(self):
        with mock.patch.object(
            self.dwipe,
            "run_windows_powershell",
            return_value=self.Completed(0, "3\n", ""),
        ):
            device = self.dwipe.get_device_path_for_mount(r"C:\\", system="Windows")

        self.assertEqual(device, r"\\.\PhysicalDrive3")

    def test_find_writable_path_can_refuse_cross_volume_fallback(self):
        with mock.patch.object(self.dwipe, "find_writable_path_for_volume", return_value="/locked"), mock.patch.object(
            self.dwipe, "is_path_writable", return_value=False
        ):
            path, free_space = self.dwipe.find_writable_path("/locked", allow_cross_volume_fallback=False)

        self.assertIsNone(path)
        self.assertEqual(free_space, 0)

    def test_get_windows_physical_drives_parses_inventory(self):
        payload = (
            '[{"DiskNumber":1,"Device":"\\\\\\\\.\\\\PhysicalDrive1","FriendlyName":"USB","MountPoint":"E:\\\\",'
            '"FileSystem":"exFAT","Size":64000,"Free":32000}]'
        )
        with mock.patch.object(
            self.dwipe,
            "run_windows_powershell",
            return_value=self.Completed(0, payload, ""),
        ):
            drives = self.dwipe.get_windows_physical_drives()

        self.assertEqual(len(drives), 1)
        self.assertEqual(drives[0]["device"], r"\\.\PhysicalDrive1")
        self.assertEqual(drives[0]["mountpoint"], "E:\\")
        self.assertEqual(drives[0]["fstype"], "exFAT")

    def test_get_physical_drives_windows_uses_windows_helper(self):
        expected = [{"id": 0, "device": r"\\.\PhysicalDrive2"}]
        with mock.patch.object(self.dwipe.platform, "system", return_value="Windows"), mock.patch.object(
            self.dwipe, "get_windows_physical_drives", return_value=expected
        ):
            drives = self.dwipe.get_physical_drives()

        self.assertEqual(drives, expected)

    def test_get_physical_drives_linux_filters_non_block_devices(self):
        partitions = [
            self.Partition("/dev/nvme0n1p1", "/mnt/data", "ext4", ""),
            self.Partition("overlay", "/", "overlay", ""),
        ]
        with mock.patch.object(self.dwipe.platform, "system", return_value="Linux"), mock.patch.object(
            self.dwipe.psutil, "disk_partitions", return_value=partitions
        ), mock.patch.object(
            self.dwipe.psutil, "disk_usage", return_value=self.Usage(1024, 512)
        ), mock.patch.object(
            self.dwipe, "get_linux_base_device", return_value="/dev/nvme0n1"
        ):
            drives = self.dwipe.get_physical_drives()

        self.assertEqual(len(drives), 1)
        self.assertEqual(drives[0]["device"], "/dev/nvme0n1")
        self.assertEqual(drives[0]["mountpoint"], "/mnt/data")


if __name__ == "__main__":
    unittest.main()
