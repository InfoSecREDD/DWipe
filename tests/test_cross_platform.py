import errno
import importlib.util
import os
import sys
import tempfile
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

    def _capture_single_wipe_chunk(self, pattern, block_size=10):
        writes = []

        class FakeProgressBar:
            disable = False

            def update(self, amount):
                return None

            def close(self):
                return None

        class FakeFile:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def write(self, chunk):
                writes.append(chunk)
                raise OSError(errno.ENOSPC, "disk full")

            def flush(self):
                return None

            def fileno(self):
                return 1

        time_values = iter([0, 1, 2])

        with mock.patch.object(self.dwipe, "find_writable_path", return_value=("/mnt", block_size)), mock.patch.object(
            self.dwipe, "get_device_path_for_mount", return_value=None
        ), mock.patch.object(
            self.dwipe, "tqdm", return_value=FakeProgressBar()
        ), mock.patch.object(
            self.dwipe.time, "time", side_effect=lambda: next(time_values)
        ), mock.patch.object(
            self.dwipe.os, "urandom", return_value=b"R" * block_size
        ), mock.patch.object(
            self.dwipe.atexit, "register"
        ), mock.patch.object(
            self.dwipe.atexit, "unregister"
        ), mock.patch.object(
            self.dwipe.signal, "signal"
        ), mock.patch.object(
            self.dwipe.os.path, "exists", return_value=False
        ), mock.patch.object(
            self.dwipe.os, "remove"
        ), mock.patch.object(
            self.dwipe.os, "sync"
        ), mock.patch.object(
            self.dwipe.os, "fsync"
        ), mock.patch.object(
            self.dwipe.os, "fdopen", return_value=FakeFile()
        ), mock.patch.object(
            self.dwipe.os, "chmod"
        ), mock.patch.object(
            self.dwipe.tempfile, "mkstemp", return_value=(123, "/mnt/secure.tmp")
        ), mock.patch.object(
            self.dwipe.sys.stdout, "write"
        ), mock.patch.object(
            self.dwipe.sys.stdout, "flush"
        ), mock.patch(
            "builtins.print"
        ):
            self.dwipe.wipe_free_space(
                root="/mnt",
                passes=1,
                block_size=block_size,
                verify=False,
                pattern=pattern,
                no_confirm=True,
            )

        self.assertTrue(writes)
        return writes[0]

    def test_parse_windows_disk_number_accepts_multiple_forms(self):
        self.assertEqual(self.dwipe.parse_windows_disk_number(r"\\.\PhysicalDrive7"), "7")
        self.assertEqual(self.dwipe.parse_windows_disk_number("PhysicalDrive3"), "3")
        self.assertEqual(self.dwipe.parse_windows_disk_number("9"), "9")
        self.assertIsNone(self.dwipe.parse_windows_disk_number("not-a-disk"))

    def test_disk_path_exists_accepts_windows_raw_disks(self):
        self.assertTrue(self.dwipe.disk_path_exists("Windows", r"\\.\PhysicalDrive4"))
        self.assertTrue(self.dwipe.disk_path_exists("Windows", "4"))
        self.assertFalse(self.dwipe.disk_path_exists("Windows", "diskX"))

    def test_normalize_windows_disk_path_returns_canonical_form(self):
        self.assertEqual(
            self.dwipe.normalize_windows_disk_path("PhysicalDrive5"),
            r"\\.\PhysicalDrive5",
        )
        self.assertEqual(
            self.dwipe.normalize_windows_disk_path("8"),
            r"\\.\PhysicalDrive8",
        )
        self.assertIsNone(self.dwipe.normalize_windows_disk_path("diskX"))

    def test_get_parent_disk_path_normalizes_darwin_and_windows(self):
        self.assertEqual(
            self.dwipe.get_parent_disk_path("/dev/disk3s1", system="Darwin"),
            "/dev/disk3",
        )
        self.assertEqual(
            self.dwipe.get_parent_disk_path("7", system="Windows"),
            r"\\.\PhysicalDrive7",
        )

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

    def test_wipe_free_space_patterns_generate_expected_chunks(self):
        expected_chunks = {
            "zeroes": bytes([0]) * 10,
            "ones": bytes([0xFF]) * 10,
            "dicks": b"3===D3===D",
            "haha": b"haha-haha-",
            "random": b"R" * 10,
            "all": b"R" * 10,
        }

        for pattern, expected in expected_chunks.items():
            with self.subTest(pattern=pattern):
                self.assertEqual(self._capture_single_wipe_chunk(pattern), expected)

    def test_wipe_free_space_uses_secure_tempfile_creation(self):
        class FakeProgressBar:
            disable = False

            def update(self, amount):
                return None

            def close(self):
                return None

        class FakeFile:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def write(self, chunk):
                raise OSError(errno.ENOSPC, "disk full")

            def flush(self):
                return None

            def fileno(self):
                return 1

        time_values = iter([0, 1, 2])

        with mock.patch.object(self.dwipe, "find_writable_path", return_value=("/mnt", 16)), mock.patch.object(
            self.dwipe, "get_device_path_for_mount", return_value=None
        ), mock.patch.object(
            self.dwipe, "tqdm", return_value=FakeProgressBar()
        ), mock.patch.object(
            self.dwipe.time, "time", side_effect=lambda: next(time_values)
        ), mock.patch.object(
            self.dwipe.atexit, "register"
        ), mock.patch.object(
            self.dwipe.atexit, "unregister"
        ), mock.patch.object(
            self.dwipe.signal, "signal"
        ), mock.patch.object(
            self.dwipe.os.path, "exists", return_value=True
        ), mock.patch.object(
            self.dwipe.os, "remove"
        ), mock.patch.object(
            self.dwipe.os, "sync"
        ), mock.patch.object(
            self.dwipe.os, "fsync"
        ), mock.patch.object(
            self.dwipe.os, "chmod"
        ) as chmod_mock, mock.patch.object(
            self.dwipe.tempfile, "mkstemp", return_value=(123, "/mnt/secure.tmp")
        ) as mkstemp_mock, mock.patch.object(
            self.dwipe.os, "fdopen", return_value=FakeFile()
        ) as fdopen_mock, mock.patch.object(
            self.dwipe.sys.stdout, "write"
        ), mock.patch.object(
            self.dwipe.sys.stdout, "flush"
        ), mock.patch(
            "builtins.print"
        ):
            self.dwipe.wipe_free_space(
                root="/mnt",
                passes=1,
                block_size=16,
                verify=False,
                pattern="zeroes",
                no_confirm=True,
            )

        mkstemp_mock.assert_called_once_with(dir="/mnt", prefix=".dwipe_free_space_", suffix=".tmp")
        chmod_mock.assert_called_once_with("/mnt/secure.tmp", 0o600)
        fdopen_mock.assert_called_once_with(123, "wb")

    def test_verify_written_samples_accepts_matching_data(self):
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            handle.write(b"abcdefghij")
            path = handle.name

        try:
            verified, message = self.dwipe.verify_written_samples(
                path,
                [(0, b"abcd"), (6, b"ghij")],
            )
        finally:
            os.remove(path)

        self.assertTrue(verified)
        self.assertIn("Verified 2 sample region", message)

    def test_verify_written_samples_detects_mismatch(self):
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            handle.write(b"abcdefghij")
            path = handle.name

        try:
            verified, message = self.dwipe.verify_written_samples(
                path,
                [(0, b"zzzz")],
            )
        finally:
            os.remove(path)

        self.assertFalse(verified)
        self.assertIn("offset 0", message)

    def test_update_verification_samples_keeps_first_two_and_latest(self):
        samples = []

        self.dwipe.update_verification_samples(samples, 0, b"aaaa")
        self.dwipe.update_verification_samples(samples, 4, b"bbbb")
        self.dwipe.update_verification_samples(samples, 8, b"cccc")
        self.dwipe.update_verification_samples(samples, 12, b"dddd")

        self.assertEqual(samples, [(0, b"aaaa"), (4, b"bbbb"), (12, b"dddd")])

    def test_get_confirmation_accepts_yes_and_defaults_to_no(self):
        with mock.patch("builtins.input", return_value="yes"), mock.patch("builtins.print"):
            self.assertTrue(self.dwipe.get_confirmation("Proceed?", box_style=True))

        with mock.patch("builtins.input", return_value=""), mock.patch("builtins.print"):
            self.assertFalse(self.dwipe.get_confirmation("Proceed?", box_style=False))

    def test_format_time_human_readable_supports_full_and_abbreviated_output(self):
        self.assertEqual(
            self.dwipe.format_time_human_readable(3661, abbreviated=False),
            "1 hour 1 minute",
        )
        self.assertEqual(
            self.dwipe.format_time_human_readable(3661, abbreviated=True),
            "1h 1m",
        )

    def test_wipe_free_space_switches_to_format_with_selected_options(self):
        with mock.patch.object(self.dwipe, "find_writable_path", return_value=("/mnt", 1024)), mock.patch.object(
            self.dwipe, "get_device_path_for_mount", return_value="/dev/sdz"
        ), mock.patch.object(
            self.dwipe, "get_confirmation", return_value=True
        ), mock.patch.object(
            self.dwipe, "format_disk"
        ) as format_disk, mock.patch(
            "builtins.input", side_effect=["2", "ARCHIVE"]
        ), mock.patch(
            "builtins.print"
        ):
            self.dwipe.wipe_free_space(
                root="/mnt",
                passes=7,
                block_size=4096,
                verify=True,
                pattern="ones",
                no_confirm=False,
            )

        format_disk.assert_called_once_with(
            "/dev/sdz",
            "fat32",
            "ARCHIVE",
            False,
            passes=7,
            pattern="ones",
            verify=True,
        )

    def test_format_disk_windows_writes_numeric_diskpart_script(self):
        scripts = []

        def fake_run(command, *args, **kwargs):
            if command[:2] == ["diskpart", "/s"]:
                scripts.append(Path(command[2]).read_text())
                return self.Completed(0, "ok", "")
            return self.Completed(0, "", "")

        with mock.patch.object(self.dwipe.platform, "system", return_value="Windows"), mock.patch.object(
            self.dwipe, "clear_drive_cache", return_value=(False, [])
        ), mock.patch.object(
            self.dwipe, "handle_remapped_sectors", return_value=(False, [])
        ), mock.patch.object(
            self.dwipe, "check_hpa_dco", return_value=(False, [])
        ), mock.patch.object(
            self.dwipe, "secure_erase_enhanced", return_value=(False, [])
        ), mock.patch.object(
            self.dwipe, "clear_smart_data", return_value=(False, [])
        ), mock.patch.object(
            self.dwipe, "disk_path_exists", return_value=True
        ), mock.patch.object(
            self.dwipe, "run_windows_powershell", side_effect=[
                self.Completed(0, '{"FriendlyName":"USB","Size":64000}', ""),
                self.Completed(0, "", ""),
            ]
        ), mock.patch.object(
            self.dwipe.subprocess, "run", side_effect=fake_run
        ), mock.patch(
            "builtins.print"
        ):
            self.dwipe.format_disk(
                r"\\.\PhysicalDrive4",
                filesystem="ntfs",
                label="USB",
                no_confirm=True,
                passes=1,
                pattern="zeroes",
                verify=False,
            )

        self.assertGreaterEqual(len(scripts), 2)
        self.assertTrue(all("select disk 4" in script for script in scripts))
        self.assertTrue(all("PhysicalDrive4" not in script for script in scripts))

    def test_format_disk_windows_rejects_unsupported_filesystem(self):
        with mock.patch.object(self.dwipe.platform, "system", return_value="Windows"), mock.patch.object(
            self.dwipe, "clear_drive_cache", return_value=(False, [])
        ), mock.patch.object(
            self.dwipe, "handle_remapped_sectors", return_value=(False, [])
        ), mock.patch.object(
            self.dwipe, "check_hpa_dco", return_value=(False, [])
        ), mock.patch.object(
            self.dwipe, "secure_erase_enhanced", return_value=(False, [])
        ), mock.patch.object(
            self.dwipe, "clear_smart_data", return_value=(False, [])
        ), mock.patch.object(
            self.dwipe, "disk_path_exists", return_value=True
        ), mock.patch.object(
            self.dwipe,
            "run_windows_powershell",
            return_value=self.Completed(0, '{"FriendlyName":"USB","Size":64000}', ""),
        ), mock.patch(
            "builtins.print"
        ) as print_mock:
            with self.assertRaises(SystemExit) as exc:
                self.dwipe.format_disk(
                    r"\\.\PhysicalDrive4",
                    filesystem="ext4",
                    label=None,
                    no_confirm=True,
                    passes=1,
                    pattern="all",
                    verify=False,
                )

        self.assertEqual(exc.exception.code, 1)
        printed = " ".join(" ".join(str(arg) for arg in call.args) for call in print_mock.call_args_list)
        self.assertIn("Unsupported filesystem ext4 for Windows", printed)


if __name__ == "__main__":
    unittest.main()
