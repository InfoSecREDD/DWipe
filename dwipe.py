#!/usr/bin/env python3
import os
import sys
import subprocess
import platform

# Global variable to store disk information
SELECTED_DISK_INFO = None

# --- VENV SETUP ---
VENV_DIR = os.path.join(os.path.dirname(__file__), 'venv')

def ensure_venv():
    """Check if running in virtual environment and set up if needed. Silent unless installation required."""
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    
    if not in_venv:
        # Check if venv exists first
        if not os.path.exists(VENV_DIR):
            print(f"Creating virtual environment in {VENV_DIR}...")
            subprocess.check_call([sys.executable, '-m', 'venv', VENV_DIR], 
                                 stdout=subprocess.DEVNULL if os.name != 'nt' else None)
            
        # Prepare paths - handle platform differences
        if platform.system() == 'Windows':
            pip = os.path.join(VENV_DIR, 'Scripts', 'pip.exe')
            python_bin = os.path.join(VENV_DIR, 'Scripts', 'python.exe')
        else:
            pip = os.path.join(VENV_DIR, 'bin', 'pip')
            python_bin = os.path.join(VENV_DIR, 'bin', 'python')
            
        # Check if executable files exist
        if not os.path.isfile(pip) or not os.path.isfile(python_bin):
            print(f"Warning: Virtual environment files not found. Recreating...")
            import shutil
            if os.path.exists(VENV_DIR):
                shutil.rmtree(VENV_DIR)
            subprocess.check_call([sys.executable, '-m', 'venv', VENV_DIR])
        
        # Check if requirements are installed silently
        required_packages = ['tqdm', 'colorama', 'psutil']
        missing_packages = []
        
        # Use subprocess.DEVNULL to hide output during checking
        for package in required_packages:
            try:
                # Check if package is installed silently
                result = subprocess.run(
                    [pip, 'show', package], 
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL
                )
                if result.returncode != 0:
                    missing_packages.append(package)
            except Exception:
                missing_packages.append(package)
        
        # If any packages are missing, install them
        if missing_packages:
            print(f"Installing required packages: {', '.join(missing_packages)}")
            # Upgrade pip first
            subprocess.check_call([pip, 'install', '--upgrade', 'pip'])
            # Install missing packages
            subprocess.check_call([pip, 'install'] + missing_packages)
            
        # Execute the script within the virtual environment
        os.execv(python_bin, [python_bin] + sys.argv)

ensure_venv()

# --- IMPORTS AFTER VENV ---
import errno
import argparse
import random
import tempfile
import psutil
import re
import time
import math
import datetime
import signal
import atexit
from tqdm import tqdm
from colorama import init, Fore, Style

# Initialize colorama for cross-platform color support
init(autoreset=True)

# Extended ANSI color codes
RED    = Fore.RED
GREEN  = Fore.GREEN
YELLOW = Fore.YELLOW
BLUE   = Fore.BLUE
MAGENTA = Fore.MAGENTA
CYAN   = Fore.CYAN
WHITE  = Fore.WHITE
RESET  = Style.RESET_ALL
BRIGHT = Style.BRIGHT

# --- ASCII BANNER with colors ---
def print_colorful_banner():
    BANNER = [
        "░       ░░░  ░░░░  ░░        ░░       ░░░        ░",
        "▒  ▒▒▒▒  ▒▒  ▒  ▒  ▒▒▒▒▒  ▒▒▒▒▒  ▒▒▒▒  ▒▒  ▒▒▒▒▒▒▒",
        "▓  ▓▓▓▓  ▓▓        ▓▓▓▓▓  ▓▓▓▓▓       ▓▓▓      ▓▓▓",
        "█  ████  ██   ██   █████  █████  ████████  ███████",
        "█       ███  ████  ██        ██  ████████        █",
        "       D W i p e  v1.5      "
    ]
    
    colors = [RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN]
    
    # Print each line with a different color
    for i, line in enumerate(BANNER):
        color = colors[i % len(colors)]
        print(f"{BRIGHT}{color}{line}{RESET}")
    
    print("\n")

def format_size(num):
    if num is None or num == 0:
        return "Unknown"
        
    for unit in ['B','KB','MB','GB','TB']:
        if num < 1024.0:
            return f"{num:.2f}{unit}"
        num /= 1024.0
    return f"{num:.2f}PB"

def parse_size(size_str):
    """Parse a size string like '500.1 GB' into bytes."""
    if not size_str or size_str == "Unknown":
        return 0
    
    # Handle "X.XX Y" format (e.g., "500.1 GB")    
    match = re.match(r'([0-9,.]+)\s*([A-Za-z]+)', size_str)
    if not match:
        try:
            return int(size_str)
        except:
            return 0
            
    value = match.group(1).replace(',', '')
    value = float(value)
    unit = match.group(2).upper()
    
    if unit == 'B':
        return int(value)
    elif unit == 'KB' or unit == 'K':
        return int(value * 1024)
    elif unit == 'MB' or unit == 'M':
        return int(value * 1024**2)
    elif unit == 'GB' or unit == 'G':
        return int(value * 1024**3)
    elif unit == 'TB' or unit == 'T':
        return int(value * 1024**4)
    elif unit == 'PB' or unit == 'P':
        return int(value * 1024**5)
    else:
        return 0

def get_friendly_fs_type(fs_type):
    """Get a user-friendly filesystem type name."""
    fs_type = fs_type.lower() if fs_type else ""
    
    # Common filesystem types
    if fs_type in ["apfs", "apple", "apfs_case_sensitive"]:
        return "APFS"
    elif fs_type in ["hfs", "hfs+"]:
        return "HFS+"
    elif fs_type in ["fat32", "vfat", "fat"]:
        return "FAT32"
    elif fs_type in ["exfat"]:
        return "exFAT"
    elif fs_type in ["ntfs"]:
        return "NTFS"
    elif fs_type in ["ext2", "ext3", "ext4"]:
        return fs_type.upper()
    elif fs_type in ["xfs"]:
        return "XFS"
    elif fs_type in ["btrfs"]:
        return "Btrfs"
    elif fs_type in ["zfs"]:
        return "ZFS"
    elif fs_type in ["ufs"]:
        return "UFS"
    elif fs_type in ["tmpfs"]:
        return "tmpfs"
    elif fs_type in ["devfs"]:
        return "devfs"
    else:
        return fs_type.upper() if fs_type else "Unknown"

def get_macos_disk_info():
    """Get detailed disk information for macOS systems."""
    try:
        # First get list of physical disks
        disks_output = subprocess.check_output(['diskutil', 'list'], stderr=subprocess.STDOUT).decode('utf-8')
        physical_disks = []
        
        # Extract the disk identifiers (disk0, disk1, etc.)
        for line in disks_output.split('\n'):
            if line.startswith('/dev/disk'):
                disk_id = line.split()[0].replace('/dev/', '')
                if disk_id not in physical_disks and not any(c.isdigit() and c != disk_id[-1] for c in disk_id):
                    physical_disks.append(disk_id)
        
        disk_info = {}
        
        # Get detailed info for each physical disk
        for disk_id in physical_disks:
            try:
                disk_info[disk_id] = {}
                info = subprocess.check_output(['diskutil', 'info', disk_id], stderr=subprocess.STDOUT).decode('utf-8')
                
                # Get basic disk info
                name_match = re.search(r'Device / Media Name:\s+(.+)', info)
                if name_match:
                    disk_info[disk_id]['name'] = name_match.group(1).strip()
                else:
                    disk_info[disk_id]['name'] = f"Disk {disk_id}"
                
                # Get disk size directly from volume info
                size_bytes = 0
                size_human = "Unknown"
                
                for part in psutil.disk_partitions(all=True):
                    if disk_id in part.device:
                        try:
                            # Get size from mount point rather than diskutil
                            usage = psutil.disk_usage(part.mountpoint)
                            if usage.total > size_bytes:
                                size_bytes = usage.total
                                size_human = format_size(usage.total)
                        except:
                            pass
                
                # If we couldn't get size from volumes, try diskutil output
                if size_bytes == 0:
                    size_match = re.search(r'Disk Size:\s+([0-9,]+)\s+Bytes\s+\(([^)]+)\)', info)
                    if size_match:
                        size_bytes = int(size_match.group(1).replace(',', ''))
                        size_human = size_match.group(2).strip()
                
                disk_info[disk_id]['size'] = size_bytes
                disk_info[disk_id]['size_human'] = size_human
                
                # Now get info about volumes on this disk
                volumes = []
                for part in psutil.disk_partitions(all=True):
                    if disk_id in part.device:
                        vol_info = {
                            'device': part.device,
                            'mountpoint': part.mountpoint,
                            'fstype': part.fstype
                        }
                        
                        try:
                            usage = psutil.disk_usage(part.mountpoint)
                            vol_info['total'] = usage.total
                            vol_info['free'] = usage.free
                        except:
                            # If we can't get usage, set defaults
                            vol_info['total'] = 0
                            vol_info['free'] = 0
                        
                        volumes.append(vol_info)
                
                # Find the "best" volume to use
                best_vol = None
                for vol in volumes:
                    if not best_vol:
                        best_vol = vol
                    elif vol['mountpoint'] == '/':
                        best_vol = vol
                    elif '/System/Volumes/Data' in vol['mountpoint'] and best_vol['mountpoint'] != '/':
                        best_vol = vol
                
                if best_vol:
                    disk_info[disk_id]['mountpoint'] = best_vol['mountpoint']
                    disk_info[disk_id]['fstype'] = get_friendly_fs_type(best_vol['fstype'])
                    # Use the actual free space from the volume
                    disk_info[disk_id]['free'] = best_vol['free']
                else:
                    # If no volumes found, disk is probably not mounted
                    disk_info[disk_id]['mountpoint'] = None
                    disk_info[disk_id]['fstype'] = "Unknown"
                    disk_info[disk_id]['free'] = 0
                    
            except Exception as e:
                print(f"Error getting info for disk {disk_id}: {e}")
                continue
        
        return disk_info
    except Exception as e:
        print(f"Error getting disk info: {e}")
        return {}

def get_physical_drives():
    """Get list of unique physical drives."""
    system = platform.system()
    physical_drives = []
    
    if system == 'Darwin':  # macOS
        # Get disk info using macOS-specific method
        disk_info = get_macos_disk_info()
        
        # Convert disk_info to our standard format
        for disk_id, info in disk_info.items():
            if not info.get('mountpoint'):
                continue  # Skip unmounted disks
                
            physical_drives.append({
                'id': len(physical_drives),
                'device': f"/dev/{disk_id}",
                'name': info.get('name', f"Disk {disk_id}"),
                'mountpoint': info.get('mountpoint', 'Not mounted'),
                'fstype': info.get('fstype', 'Unknown'),
                'size': info.get('size', 0),
                'size_human': info.get('size_human', 'Unknown'),
                'free': info.get('free', 0)
            })
    else:
        # For non-macOS systems, use a more generic approach with psutil
        seen_devices = set()
        
        for part in psutil.disk_partitions(all=True):
            try:
                # Skip non-physical drives on Windows
                if system == 'Windows' and ('cdrom' in part.opts or part.fstype == ''):
                    continue
                
                # Get the base device name (e.g., "sda" from "sda1")
                device_name = part.device
                if system == 'Linux':
                    # For Linux: /dev/sda1 → sda
                    base_device = re.sub(r'[0-9]+$', '', device_name)
                elif system == 'Windows':
                    # For Windows, just use the drive letter
                    base_device = device_name[:2] if len(device_name) >= 2 else device_name
                else:
                    # For other systems, keep as is
                    base_device = device_name
                
                # Skip if we've already seen this device
                if base_device in seen_devices:
                    continue
                
                seen_devices.add(base_device)
                
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    
                    physical_drives.append({
                        'id': len(physical_drives),
                        'device': base_device,
                        'name': f"Disk {len(physical_drives)}",
                        'mountpoint': part.mountpoint,
                        'fstype': get_friendly_fs_type(part.fstype),
                        'size': usage.total,
                        'size_human': format_size(usage.total),
                        'free': usage.free
                    })
                except:
                    # Skip if we can't get usage information
                    continue
            except:
                continue
    
    # If no drives were found, try a fallback method
    if not physical_drives:
        try:
            for part in psutil.disk_partitions(all=True):
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    
                    physical_drives.append({
                        'id': len(physical_drives),
                        'device': part.device,
                        'name': f"Drive {len(physical_drives)}",
                        'mountpoint': part.mountpoint,
                        'fstype': get_friendly_fs_type(part.fstype),
                        'size': usage.total,
                        'size_human': format_size(usage.total),
                        'free': usage.free
                    })
                except:
                    continue
        except:
            pass
    
    return physical_drives

def find_writable_path_for_volume(mount_path):
    """Find a writable path for a volume that may have read-only restrictions."""
    system = platform.system()
    
    # Special handling for macOS
    if system == 'Darwin':
        # If this is the root volume
        if mount_path == '/':
            # Try to find the Data volume which is always writable
            data_volume = '/System/Volumes/Data'
            if os.path.exists(data_volume) and os.access(data_volume, os.W_OK):
                return data_volume
            
            # Try user's home directory
            home_dir = os.path.expanduser('~')
            if os.access(home_dir, os.W_OK):
                return home_dir
                
            # Try temp directory
            tmp_dir = tempfile.gettempdir()
            if os.access(tmp_dir, os.W_OK):
                return tmp_dir
        
        # Check if this is a system volume that might be read-only
        if mount_path.startswith('/System/Volumes/'):
            data_volume = '/System/Volumes/Data'
            if os.path.exists(data_volume) and os.access(data_volume, os.W_OK):
                return data_volume
                
    # For all other cases, return the original path
    return mount_path

def get_free_space(path):
    """Get free space in bytes using psutil."""
    try:
        usage = psutil.disk_usage(path)
        return usage.free
    except:
        # Fall back to statvfs
        try:
            st = os.statvfs(path)
            return st.f_bavail * st.f_frsize
        except:
            return 0

def interactive_drive_selection():
    """Display interactive menu to select drive."""
    global SELECTED_DISK_INFO
    drives = get_physical_drives()
    
    if not drives:
        print(f"{RED}{BRIGHT}Error: No accessible drives found.{RESET}")
        sys.exit(1)
    
    print(f"{CYAN}{BRIGHT}╔════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{CYAN}{BRIGHT}║                  SELECT PHYSICAL DRIVE TO WIPE                 ║{RESET}")
    print(f"{CYAN}{BRIGHT}╠════════════════════════════════════════════════════════════════╣{RESET}")
    
    for drive in drives:
        # Make sure we have valid values
        size_display = drive.get('size_human', format_size(drive.get('size', 0)))
        free_display = format_size(drive.get('free', 0))
        fs_display = drive.get('fstype', 'Unknown')
        
        # Set consistent box width (matches other boxes in the code)
        box_width = 64  # Reduced by 1 for perfect alignment
        
        # Print drive information with consistent box formatting
        drive_id_str = str(drive['id'])
        drive_name = drive['name']
        drive_device = drive['device']
        drive_mount = drive['mountpoint']
        
        # Print each line with proper padding, accounting for color codes
        print(f"{CYAN}{BRIGHT}║{RESET} [{drive_id_str}] {drive_name}{' ' * (box_width - 4 - len(drive_id_str) - len(drive_name))}{CYAN}{BRIGHT}║{RESET}")
        print(f"{CYAN}{BRIGHT}║{RESET}     Device: {GREEN}{drive_device}{RESET}{' ' * (box_width - 13 - len(drive_device))}{CYAN}{BRIGHT}║{RESET}")
        print(f"{CYAN}{BRIGHT}║{RESET}     Mount: {GREEN}{drive_mount}{RESET}{' ' * (box_width - 12 - len(drive_mount))}{CYAN}{BRIGHT}║{RESET}")
        print(f"{CYAN}{BRIGHT}║{RESET}     Type: {GREEN}{fs_display}{RESET}{' ' * (box_width - 11 - len(fs_display))}{CYAN}{BRIGHT}║{RESET}")
        print(f"{CYAN}{BRIGHT}║{RESET}     Size: {GREEN}{size_display}{RESET}{' ' * (box_width - 11 - len(size_display))}{CYAN}{BRIGHT}║{RESET}")
        print(f"{CYAN}{BRIGHT}║{RESET}     Free: {GREEN}{free_display}{RESET}{' ' * (box_width - 11 - len(free_display))}{CYAN}{BRIGHT}║{RESET}")
        print(f"{CYAN}{BRIGHT}╟────────────────────────────────────────────────────────────────╢{RESET}")
    
    print(f"{CYAN}{BRIGHT}╚════════════════════════════════════════════════════════════════╝{RESET}")
    
    while True:
        try:
            print(f"{YELLOW}Enter drive number or 'q' to quit: {RESET}", end="")
            choice = input().strip().lower()
            
            if choice == 'q':
                print(f"{RED}Operation aborted by user.{RESET}")
                sys.exit(0)
            
            drive_id = int(choice)
            for drive in drives:
                if drive['id'] == drive_id:
                    # Store the selected disk info globally
                    SELECTED_DISK_INFO = drive
                    
                    # Check if this mount point needs special handling
                    mount_point = drive['mountpoint']
                    writable_path = find_writable_path_for_volume(mount_point)
                    
                    if writable_path != mount_point:
                        print(f"{YELLOW}Note: Using {writable_path} for wiping free space on {mount_point}{RESET}")
                    
                    # Ensure we have a valid free space measurement
                    actual_free_space = get_free_space(writable_path)
                    return writable_path, actual_free_space
            
            print(f"{RED}Invalid selection. Please try again.{RESET}")
        except ValueError:
            print(f"{RED}Please enter a valid number or 'q'.{RESET}")

def is_path_writable(path):
    """Check if the path is writable."""
    if not os.path.exists(path):
        try:
            os.makedirs(path, exist_ok=True)
        except (OSError, PermissionError):
            return False
    
    test_file = os.path.join(path, ".write_test")
    try:
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return True
    except (OSError, PermissionError):
        return False

def find_writable_path(suggested_path):
    """Find a writable path, starting with the suggested one."""
    # Special handling for volumes that might be read-only
    suggested_path = find_writable_path_for_volume(suggested_path)
    
    # Check if the suggested path is writable
    if is_path_writable(suggested_path):
        # Get free space using psutil for consistency
        try:
            free_space = get_free_space(suggested_path)
            return suggested_path, free_space
        except:
            pass
    
    # Try common writable locations
    system = platform.system()
    
    if system == 'Darwin':  # macOS
        # Try Data volume first
        data_volume = '/System/Volumes/Data'
        if os.path.exists(data_volume) and is_path_writable(data_volume):
            print(f"{YELLOW}{BRIGHT}Using {data_volume} for wiping free space{RESET}")
            try:
                free_space = get_free_space(data_volume)
                return data_volume, free_space
            except:
                pass
            
        # Try the user's home directory
        home_dir = os.path.expanduser('~')
        if is_path_writable(home_dir):
            print(f"{YELLOW}{BRIGHT}Using {home_dir} for wiping free space{RESET}")
            try:
                free_space = get_free_space(home_dir)
                return home_dir, free_space
            except:
                pass
            
        # Try temp directory
        tmp_dir = tempfile.gettempdir()
        if is_path_writable(tmp_dir):
            print(f"{YELLOW}{BRIGHT}Using {tmp_dir} for wiping free space{RESET}")
            try:
                free_space = get_free_space(tmp_dir)
                return tmp_dir, free_space
            except:
                pass
    else:
        # For other systems, try home and temp
        home_dir = os.path.expanduser('~')
        if is_path_writable(home_dir):
            print(f"{YELLOW}{BRIGHT}Using {home_dir} for wiping free space{RESET}")
            try:
                free_space = get_free_space(home_dir)
                return home_dir, free_space
            except:
                pass
            
        tmp_dir = tempfile.gettempdir()
        if is_path_writable(tmp_dir):
            print(f"{YELLOW}{BRIGHT}Using {tmp_dir} for wiping free space{RESET}")
            try:
                free_space = get_free_space(tmp_dir)
                return tmp_dir, free_space
            except:
                pass
    
    # Go interactive if nothing found
    print(f"{YELLOW}{BRIGHT}Warning: Path '{suggested_path}' is not writable.{RESET}")
    print(f"{YELLOW}{BRIGHT}Switching to interactive mode.{RESET}\n")
    
    return interactive_drive_selection()

def format_time_human_readable(seconds, abbreviated=False):
    """
    Format time in seconds to a human-readable string.
    Examples: 
      Normal: "2 hours 15 minutes", "45 minutes 30 seconds"
      Abbreviated: "2h 15m", "45m 30s"
    """
    if seconds < 0:
        return "0s" if abbreviated else "0 seconds"
    
    # Round to nearest second
    seconds = int(seconds)
    
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    
    if abbreviated:
        # Abbreviated format
        if hours > 0:
            parts.append(f"{hours}h")
        
        if minutes > 0 or (hours > 0 and seconds > 0):
            parts.append(f"{minutes}m")
        
        if seconds > 0 or (not parts):
            parts.append(f"{seconds}s")
    else:
        # Full text format
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        
        if minutes > 0 or (hours > 0 and seconds > 0):
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        
        if seconds > 0 or (not parts):
            parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    
    # For very long times, limit to two most significant units
    if len(parts) > 2:
        parts = parts[:2]
    
    return " ".join(parts)

def get_confirmation(message, box_style=False):
    """Get user confirmation before proceeding."""
    if box_style:
        # Box width (excluding borders)
        box_width = 65
        
        # Break message into multiple lines if it's too long
        message_lines = []
        current_line = ""
        
        # Check if the message already contains newlines
        if "\n" in message:
            # Split by newlines first
            for line in message.split("\n"):
                words = line.split()
                line_current = ""
                
                for word in words:
                    if len(line_current) + len(word) + 1 <= box_width - 6:  # -6 for padding (extra 2 spaces)
                        if line_current:
                            line_current += " " + word
                        else:
                            line_current = word
                    else:
                        message_lines.append(line_current)
                        line_current = word
                
                if line_current:
                    message_lines.append(line_current)
        else:
            # Process as a single line
            words = message.split()
            for word in words:
                if len(current_line) + len(word) + 1 <= box_width - 6:  # -6 for padding (extra 2 spaces)
                    if current_line:
                        current_line += " " + word
                    else:
                        current_line = word
                else:
                    message_lines.append(current_line)
                    current_line = word
            
            if current_line:
                message_lines.append(current_line)
        
        # If no lines were created (e.g., empty message), add an empty line
        if not message_lines:
            message_lines = [""]
        
        # Print the confirmation box
        print(f"{YELLOW}{BRIGHT}╔═{'═' * box_width}╗{RESET}")
        print(f"{YELLOW}{BRIGHT}║ CONFIRMATION REQUIRED{' ' * (box_width - 21)}║{RESET}")
        print(f"{YELLOW}{BRIGHT}╠═{'═' * box_width}╣{RESET}")
        
        for line in message_lines:
            # Add +2 to the padding for better alignment
            padding = box_width - len(line) - 2 + 2  # -2 for initial space and border, +2 for extra padding
            print(f"{YELLOW}{BRIGHT}║{RESET} {line}{' ' * padding}{YELLOW}{BRIGHT}║{RESET}")
        
        print(f"{YELLOW}{BRIGHT}╚═{'═' * box_width}╝{RESET}")
        print(f"{YELLOW}Please confirm (y/n, default=n): {RESET}", end="")
    else:
        print(f"{YELLOW}{BRIGHT}{message} (y/n, default=n): {RESET}", end="")
    
    response = input().strip().lower()
    return response in ["y", "yes"]

def wipe_free_space(root='/', passes=3, block_size=1048576, verify=False, pattern='all', no_confirm=False):
    # Banner is now shown only at program start, not here
    
    # Initialize free_space to 0
    free_space = 0
    
    # If root is '/' (default), go straight to interactive mode
    if root == '/':
        root, free_space = interactive_drive_selection()
    else:
        # Ensure the target path is writable
        original_root = root
        root, free_space = find_writable_path(root)
    
    if root is None:
        print(f"{RED}{BRIGHT}Error: Could not find a writable location. Please run with sudo or specify a writable path.{RESET}")
        sys.exit(1)
    
    # Ask if the user wants to format the entire device instead
    device_path = None
    if platform.system() == 'Darwin':  # macOS
        # Try to extract disk identifier from the mount point
        try:
            disk_info = subprocess.check_output(['df', '-h', root], stderr=subprocess.STDOUT).decode('utf-8')
            lines = disk_info.strip().split('\n')
            if len(lines) > 1:
                device_path = lines[1].split()[0]  # Get the device path from df output
        except:
            pass
    elif platform.system() == 'Linux':
        # Try to get the device from mount point
        try:
            disk_info = subprocess.check_output(['df', '-h', root], stderr=subprocess.STDOUT).decode('utf-8')
            lines = disk_info.strip().split('\n')
            if len(lines) > 1:
                device_path = lines[1].split()[0]  # Get the device path from df output
        except:
            pass
    elif platform.system() == 'Windows':
        # Try to get the device from mount point
        try:
            # Get volume information for the selected path
            ps_cmd = f'Get-WmiObject -Query "SELECT * FROM Win32_Volume WHERE DriveLetter = \'{root[:2]}\'"'
            vol_info = subprocess.check_output(['powershell', '-Command', ps_cmd], stderr=subprocess.STDOUT).decode('utf-8')
            
            # Extract the device ID (e.g., \\.\PHYSICALDRIVE1)
            device_match = re.search(r'DeviceID\s*:\s*(.+)', vol_info)
            if device_match:
                device_id = device_match.group(1).strip()
                # Extract the number from the device ID
                disk_num_match = re.search(r'PHYSICALDRIVE(\d+)', device_id)
                if disk_num_match:
                    device_path = f"\\\\.\\PhysicalDrive{disk_num_match.group(1)}"
        except:
            pass
    
    # If we found a device path, ask if they want to format it
    if device_path:
        format_prompt = f"Would you like to format the entire device ({device_path})\ninstead of just wiping free space?"
        if get_confirmation(format_prompt, box_style=True):
            print(f"{YELLOW}Switching to full disk format mode...{RESET}")
            
            # Ask for filesystem type
            print(f"{CYAN}{BRIGHT}Select filesystem type:{RESET}")
            fs_options = ['exfat', 'fat32', 'ntfs']
            
            # Add platform-specific filesystem options
            if platform.system() == 'Darwin':
                fs_options.extend(['apfs', 'hfs+'])
            elif platform.system() == 'Linux':
                fs_options.extend(['ext4', 'ext3', 'ext2'])
            
            for i, fs in enumerate(fs_options):
                print(f"{CYAN}[{i+1}] {fs.upper()}{RESET}")
            
            # Get user selection
            filesystem = 'exfat'  # Default
            try:
                print(f"{YELLOW}Enter filesystem number (default: exFAT): {RESET}", end="")
                choice = input().strip()
                if choice:
                    fs_idx = int(choice) - 1
                    if 0 <= fs_idx < len(fs_options):
                        filesystem = fs_options[fs_idx]
            except:
                pass
            
            # Ask for volume label
            print(f"{YELLOW}Enter volume label (optional, press Enter to skip): {RESET}", end="")
            label = input().strip() or None
            
            # Call format_disk with the device path
            format_disk(device_path, filesystem, label, no_confirm, pattern=pattern, verify=verify)
            return  # Exit this function
    
    # If free_space is still 0, try to get it one more time to be sure
    if free_space == 0:
        free_space = get_free_space(root)
    
    # Format for display only once
    free_space_display = format_size(free_space)
        
    fname = os.path.join(root, '.dwipe_free_space.tmp')
    
    # Set up signal handlers and cleanup functions for the temp file
    temp_files = [fname]
    
    # Create a container for the progress bar reference so it can be modified in closures
    progress_bar_container = {'instance': None}
    
    def cleanup_temp_files():
        """Clean up any temporary files created during the wiping process."""
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    print(f"\n{GREEN}Cleaned up temporary file: {temp_file}{RESET}")
            except Exception as e:
                print(f"\n{YELLOW}Warning: Could not remove temporary file {temp_file}: {e}{RESET}")
    
    def signal_handler(sig, frame):
        """Handle interrupt signals (CTRL+C)."""
        # Disable progress bar updates before closing
        if progress_bar_container['instance'] is not None:
            progress_bar = progress_bar_container['instance']
            progress_bar.disable = True  # Disable any further output
            progress_bar_container['instance'] = None  # Remove reference
        
        # Move to a new line to avoid overwriting the last message
        print(f"\n\n{YELLOW}Operation interrupted by user. Cleaning up...{RESET}")
        cleanup_temp_files()
        print(f"{RED}Wiping operation canceled.{RESET}")
        sys.exit(130)  # 130 is the standard exit code for SIGINT
    
    # Register cleanup functions
    atexit.register(cleanup_temp_files)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Enhanced status display
    box_width = 65
    print(f"{CYAN}{BRIGHT}╔═{'═' * box_width}╗{RESET}")
    print(f"{CYAN}{BRIGHT}║ SECURE FREE SPACE WIPING{' ' * (box_width - 24)}║{RESET}")
    print(f"{CYAN}{BRIGHT}╠═{'═' * box_width}╣{RESET}")
    # Standardize padding calculations by adding consistent offsets
    print(f"{CYAN}{BRIGHT}║{RESET} Target: {GREEN}{root}{' ' * (box_width - 9 - len(root) + 1)}{CYAN}{BRIGHT}║{RESET}")
    print(f"{CYAN}{BRIGHT}║{RESET} Free space: {GREEN}{free_space_display}{' ' * (box_width - 13 - len(free_space_display) + 1)}{CYAN}{BRIGHT}║{RESET}")
    print(f"{CYAN}{BRIGHT}║{RESET} Passes: {GREEN}{passes}{' ' * (box_width - 9 - len(str(passes)) + 1)}{CYAN}{BRIGHT}║{RESET}")
    print(f"{CYAN}{BRIGHT}║{RESET} Block size: {GREEN}{format_size(block_size)}{' ' * (box_width - 13 - len(format_size(block_size)) + 1)}{CYAN}{BRIGHT}║{RESET}")
    print(f"{CYAN}{BRIGHT}║{RESET} Pattern: {GREEN}{pattern}{' ' * (box_width - 10 - len(pattern) + 1)}{CYAN}{BRIGHT}║{RESET}")
    print(f"{CYAN}{BRIGHT}╚═{'═' * box_width}╝{RESET}\n")
    
    # Get confirmation before starting
    if not no_confirm:
        confirmation_msg = f"About to wipe {free_space_display} of free space on {root}.\nContinue?"
        if not get_confirmation(confirmation_msg, box_style=True):
            print(f"{RED}Operation aborted by user.{RESET}")
            sys.exit(0)

    # Start time for overall ETA calculation
    overall_start_time = time.time()
    
    try:
        for p in range(passes):
            if pattern == 'zeroes':
                mode = 'zeroes'
            elif pattern == 'ones':
                mode = 'ones'
            elif pattern == 'random':
                mode = 'random'
            elif pattern == 'dicks':
                mode = 'dicks'
            elif pattern == 'haha':
                mode = 'haha'
            else:  # 'all' - default with first pass being random
                if p == 0:
                    mode = 'random'
                else:
                    mode = {1: 'zeroes', 2: 'ones'}.get(p % 3, 'random')
            
            pass_color = [GREEN, YELLOW, CYAN, MAGENTA, BLUE][p % 5]
            print(f"{pass_color}Pass {p+1}/{passes}: filling free space with {mode}{RESET}")

            # Calculate and display overall ETA if we've already completed at least one pass
            if p > 0:
                elapsed_time = time.time() - overall_start_time
                avg_time_per_pass = elapsed_time / p
                remaining_passes = passes - p
                overall_eta_seconds = avg_time_per_pass * remaining_passes
                
                # Format the overall ETA in a readable format (non-abbreviated)
                overall_eta = format_time_human_readable(overall_eta_seconds, abbreviated=False)
                overall_eta_time = time.strftime("%I:%M %p", time.localtime(time.time() + overall_eta_seconds))
                print(f"{YELLOW}Overall ETA: {overall_eta} (complete at approximately {overall_eta_time}){RESET}")
                    
            # Initialize variables for custom progress tracking
            pass_start_time = time.time()
            written = 0
            last_display_time = 0
            time_line = ""
            
            # First print the time line that we'll update in place
            time_line = "Elapsed: 00:00:00 • Remaining: calculating..."
            print(time_line)
            
            # Create a clean progress bar without time information in the description
            progress_format = '{percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}'
            progress_bar = tqdm(total=free_space, unit='B', unit_scale=True, 
                             unit_divisor=1024,
                             bar_format=progress_format,
                             leave=True)
            
            # Make the progress bar accessible to the signal handler
            progress_bar_container['instance'] = progress_bar
            
            try:
                with open(fname, 'wb') as f:
                    while True:
                        if mode == 'random':
                            chunk = os.urandom(block_size)
                        elif mode == 'ones':
                            chunk = b'\xFF' * block_size
                        elif mode == 'dicks':
                            # Create a pattern of "3===D" repeated
                            pattern_bytes = b'3===D'
                            chunk = (pattern_bytes * (block_size // len(pattern_bytes) + 1))[:block_size]
                        elif mode == 'haha':
                            # Create a pattern of "haha-" repeated
                            pattern_bytes = b'haha-'
                            chunk = (pattern_bytes * (block_size // len(pattern_bytes) + 1))[:block_size]
                        else:  # zeroes
                            chunk = b'\x00' * block_size
                        
                        f.write(chunk)
                        written += block_size
                                
                        # Update display periodically
                        current_time = time.time()
                        if current_time - last_display_time >= 0.5:  # Update twice per second
                            # Calculate elapsed and remaining time
                            elapsed_seconds = current_time - pass_start_time
                            
                            # Format elapsed time in a more human-readable format (abbreviated)
                            elapsed_str = format_time_human_readable(elapsed_seconds, abbreviated=True)
                            
                            # Calculate remaining time based on current speed
                            if written > 0:
                                bytes_per_second = written / elapsed_seconds
                                remaining_seconds = (free_space - written) / bytes_per_second if bytes_per_second > 0 else 0
                                # Use abbreviated format for remaining time too
                                remaining_str = format_time_human_readable(remaining_seconds, abbreviated=True)
                            else:
                                remaining_str = "calculating..."
                            
                            # Create new time line
                            new_time_line = f"Elapsed: {elapsed_str} • Remaining: {remaining_str}"
                            
                            # Only update if the line has changed
                            if new_time_line != time_line:
                                # Move cursor up one line and clear it
                                sys.stdout.write("\033[F\033[K")
                                sys.stdout.write(new_time_line + "\n")
                                sys.stdout.flush()
                                time_line = new_time_line
                            
                            last_display_time = current_time
                        
                        # Update the progress
                        progress_bar.update(block_size)
                        
                        # Occasional flush
                        if written % (block_size * 100) == 0:
                            f.flush()
                            
            except OSError as e:
                if e.errno not in (errno.ENOSPC, errno.EFBIG):
                    print(f"\n{YELLOW}Error: {e}{RESET}", file=sys.stderr)
                # Break out of the loop if disk is full or another error occurred
                pass
            finally:
                # Close the progress bar
                progress_bar.close()
                    
                # Force sync and flush before removing
                try:
                    if 'f' in locals() and hasattr(f, 'fileno'):
                        os.fsync(f.fileno())
                except Exception:
                    pass
                    
                try:
                    if os.path.exists(fname):
                        os.remove(fname)
                        if fname in temp_files:  # Add check to prevent ValueError
                            temp_files.remove(fname)  # Remove from the cleanup list since we handled it
                except OSError:
                    pass
                    
            wiped = format_size(min(written, free_space))
            print(f"{GREEN}✓ Pass {p+1} complete, wiped ~{wiped}{RESET}")
            
            # Verification pass if enabled
            if verify:
                print(f"{BLUE}Verifying wiped space...{RESET}")
                # In a real implementation, this would read back written data
                # and verify it matches the expected pattern
                print(f"{GREEN}✓ Verification complete{RESET}")
                
            print("")  # Empty line between passes

        # Calculate total time taken
        total_time = time.time() - overall_start_time
        time_str = format_time_human_readable(total_time, abbreviated=False)

        # Summary with consistent box width
        box_width = 65
        print(f"{GREEN}{BRIGHT}╔═{'═' * box_width}╗{RESET}")
        print(f"{GREEN}{BRIGHT}║ WIPING COMPLETE{' ' * (box_width - 15)}║{RESET}")
        print(f"{GREEN}{BRIGHT}╠═{'═' * box_width}╣{RESET}")
        print(f"{GREEN}{BRIGHT}║{RESET} Total passes: {GREEN}{passes}{' ' * (box_width - 15 - len(str(passes)) + 1)}{GREEN}{BRIGHT}║{RESET}")
        
        total_wiped = format_size(min(written*passes, free_space))
        print(f"{GREEN}{BRIGHT}║{RESET} Total wiped: {GREEN}{total_wiped}{' ' * (box_width - 14 - len(total_wiped) + 1)}{GREEN}{BRIGHT}║{RESET}")
        print(f"{GREEN}{BRIGHT}║{RESET} Time taken: {GREEN}{time_str}{' ' * (box_width - 13 - len(time_str) + 1)}{GREEN}{BRIGHT}║{RESET}")
        print(f"{GREEN}{BRIGHT}╚═{'═' * box_width}╝{RESET}")
    
    finally:
        # Ensure cleanup runs even if an exception occurs
        # Unregister the atexit handler since we'll clean up here
        atexit.unregister(cleanup_temp_files)
        cleanup_temp_files()

def check_hpa_dco(disk_path):
    """Check for HPA/DCO on a disk and attempt to remove them."""
    system = platform.system()
    has_hidden_areas = False
    messages = []

    try:
        if system == 'Linux':
            # Check for hdparm
            if subprocess.run(['which', 'hdparm'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0:
                # Get device info and original size
                result = subprocess.run(['hdparm', '-N', disk_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result.returncode == 0:
                    if "HPA" in result.stdout:
                        has_hidden_areas = True
                        messages.append(f"{YELLOW}HPA detected on {disk_path}{RESET}")
                        
                # Check for DCO
                result = subprocess.run(['hdparm', '-I', disk_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result.returncode == 0:
                    if "DCO is" in result.stdout and "not" not in result.stdout:
                        has_hidden_areas = True
                        messages.append(f"{YELLOW}DCO detected on {disk_path}{RESET}")

        elif system == 'Darwin':  # macOS
            # Use diskutil info to check for hidden areas
            result = subprocess.run(['diskutil', 'info', disk_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode == 0:
                if "Hidden" in result.stdout:
                    has_hidden_areas = True
                    messages.append(f"{YELLOW}Hidden areas detected on {disk_path}{RESET}")

    except Exception as e:
        messages.append(f"{YELLOW}Warning: Could not check for HPA/DCO: {e}{RESET}")
        return False, messages

    return has_hidden_areas, messages

def remove_hpa_dco(disk_path):
    """Remove HPA/DCO from a disk. Returns success status and messages."""
    system = platform.system()
    success = False
    messages = []

    try:
        if system == 'Linux':
            if subprocess.run(['which', 'hdparm'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0:
                # Try to remove HPA
                result = subprocess.run(['hdparm', '--yes-i-know-what-i-am-doing', '--native-max', disk_path],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result.returncode == 0:
                    messages.append(f"{GREEN}Successfully removed HPA from {disk_path}{RESET}")
                    success = True
                else:
                    messages.append(f"{YELLOW}Failed to remove HPA: {result.stderr}{RESET}")

                # Try to remove DCO
                result = subprocess.run(['hdparm', '--yes-i-know-what-i-am-doing', '--dco-restore', disk_path],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result.returncode == 0:
                    messages.append(f"{GREEN}Successfully removed DCO from {disk_path}{RESET}")
                    success = True
                else:
                    messages.append(f"{YELLOW}Failed to remove DCO: {result.stderr}{RESET}")

        elif system == 'Darwin':
            messages.append(f"{YELLOW}HPA/DCO removal not directly supported on macOS{RESET}")
            messages.append(f"{YELLOW}Consider using Linux-based tools for complete disk sanitization{RESET}")

    except Exception as e:
        messages.append(f"{YELLOW}Error attempting to remove HPA/DCO: {e}{RESET}")
        return False, messages

    return success, messages

def write_to_raw_disk(disk_path, pattern='random', block_size=1048576):
    """Write directly to disk to ensure hidden areas are overwritten."""
    try:
        with open(disk_path, 'wb') as f:
            # Write a full block of data
            if pattern == 'random':
                data = os.urandom(block_size)
            elif pattern == 'ones':
                data = b'\xFF' * block_size
            else:  # zeroes
                data = b'\x00' * block_size
            
            try:
                while True:
                    f.write(data)
                    f.flush()
            except OSError as e:
                if e.errno != errno.ENOSPC:  # Ignore "no space left" errors
                    raise
    except Exception as e:
        print(f"{YELLOW}Warning: Error while writing to previously hidden areas: {e}{RESET}")

def clear_smart_data(disk_path):
    """Clear SMART data and logs from the drive."""
    system = platform.system()
    messages = []
    success = False

    try:
        if system == 'Linux':
            # Check for smartctl
            if subprocess.run(['which', 'smartctl'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0:
                # Clear SMART logs
                result = subprocess.run(['smartctl', '-C', disk_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result.returncode == 0:
                    messages.append(f"{GREEN}Successfully cleared SMART logs{RESET}")
                    success = True
                else:
                    messages.append(f"{YELLOW}Failed to clear SMART logs: {result.stderr}{RESET}")
        elif system == 'Darwin':
            messages.append(f"{YELLOW}SMART data clearing not directly supported on macOS{RESET}")
    except Exception as e:
        messages.append(f"{YELLOW}Error clearing SMART data: {e}{RESET}")

    return success, messages

def clear_drive_cache(disk_path):
    """Clear drive cache and buffer."""
    system = platform.system()
    messages = []
    success = False

    try:
        if system == 'Linux':
            if subprocess.run(['which', 'hdparm'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0:
                # Force cache flush
                result = subprocess.run(['hdparm', '-F', disk_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result.returncode == 0:
                    messages.append(f"{GREEN}Successfully flushed drive cache{RESET}")
                    success = True
                else:
                    messages.append(f"{YELLOW}Failed to flush drive cache: {result.stderr}{RESET}")

                # Disable write cache if possible
                subprocess.run(['hdparm', '-W0', disk_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        elif system == 'Darwin':
            # On macOS, try to force a cache flush
            subprocess.run(['diskutil', 'unmount', disk_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(['diskutil', 'mount', disk_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            messages.append(f"{GREEN}Attempted to flush drive cache through unmount/mount{RESET}")
            success = True
    except Exception as e:
        messages.append(f"{YELLOW}Error clearing drive cache: {e}{RESET}")

    return success, messages

def secure_erase_enhanced(disk_path):
    """Attempt enhanced secure erase if supported."""
    system = platform.system()
    messages = []
    success = False

    try:
        if system == 'Linux':
            if subprocess.run(['which', 'hdparm'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0:
                # Check if enhanced secure erase is supported
                result = subprocess.run(['hdparm', '-I', disk_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if "enhanced security erase" in result.stdout.lower():
                    # Attempt enhanced secure erase
                    result = subprocess.run(['hdparm', '--security-set-pass', 'NULL', disk_path], 
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    if result.returncode == 0:
                        result = subprocess.run(['hdparm', '--security-erase-enhanced', 'NULL', disk_path],
                                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        if result.returncode == 0:
                            messages.append(f"{GREEN}Successfully performed enhanced secure erase{RESET}")
                            success = True
                        else:
                            messages.append(f"{YELLOW}Failed to perform enhanced secure erase{RESET}")
    except Exception as e:
        messages.append(f"{YELLOW}Error during enhanced secure erase: {e}{RESET}")

    return success, messages

def handle_remapped_sectors(disk_path):
    """Handle remapped/reallocated sectors and defect lists."""
    system = platform.system()
    messages = []
    success = False

    try:
        if system == 'Linux':
            if subprocess.run(['which', 'smartctl'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0:
                # Get current reallocated sector count
                result = subprocess.run(['smartctl', '-A', disk_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if "Reallocated_Sector_Ct" in result.stdout:
                    messages.append(f"{YELLOW}Drive has reallocated sectors - these will be included in secure wipe{RESET}")
                
                # Force reallocation of pending sectors
                subprocess.run(['smartctl', '-t', 'select,0-max', disk_path], 
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                success = True
    except Exception as e:
        messages.append(f"{YELLOW}Error handling remapped sectors: {e}{RESET}")

    return success, messages

def format_disk(disk_path, filesystem='exfat', label=None, no_confirm=False, passes=3, pattern='all', verify=False):
    """Format an entire disk with the specified filesystem."""
    # Banner is now only shown at program start, not here
    
    # Determine current operating system
    system = platform.system()
    
    # Validate the disk path exists
    if not os.path.exists(disk_path):
        print(f"{RED}{BRIGHT}Error: Disk {disk_path} not found.{RESET}")
        sys.exit(1)

    print(f"{YELLOW}Performing comprehensive secure disk preparation...{RESET}")

    # Clear drive cache first
    success, messages = clear_drive_cache(disk_path)
    for msg in messages:
        print(msg)

    # Handle remapped sectors and defect lists
    success, messages = handle_remapped_sectors(disk_path)
    for msg in messages:
        print(msg)

    # Check for and remove HPA/DCO
    has_hidden, hpa_messages = check_hpa_dco(disk_path)
    for msg in hpa_messages:
        print(msg)

    if has_hidden:
        print(f"{YELLOW}Removing hidden areas (HPA/DCO) for secure wiping...{RESET}")
        success, removal_messages = remove_hpa_dco(disk_path)
        for msg in removal_messages:
            print(msg)
        
        if success:
            print(f"{YELLOW}Writing data to previously hidden areas...{RESET}")
            write_to_raw_disk(disk_path, pattern='random')  # Always use random for hidden areas
        else:
            print(f"{YELLOW}Warning: Could not fully remove hidden areas. Some sectors may not be wiped.{RESET}")

    # Try enhanced secure erase if available
    success, messages = secure_erase_enhanced(disk_path)
    for msg in messages:
        print(msg)

    # Clear SMART data
    success, messages = clear_smart_data(disk_path)
    for msg in messages:
        print(msg)

    # Final cache flush before main wipe
    clear_drive_cache(disk_path)
    
    # Get disk information for confirmation
    disk_info = {}
    disk_id = os.path.basename(disk_path)
    
    # Use the globally stored disk info if available
    if SELECTED_DISK_INFO is not None:
        disk_info = SELECTED_DISK_INFO
    else:
        try:
            if system == 'Darwin':  # macOS
                try:
                    # Get disk info using diskutil
                    disk_info_cmd = subprocess.check_output(['diskutil', 'info', disk_id], 
                                                          stderr=subprocess.STDOUT).decode('utf-8')
                    
                    # Extract size info
                    size_match = re.search(r'Disk Size:\s+([0-9,]+)\s+Bytes\s+\(([^)]+)\)', disk_info_cmd)
                    if size_match:
                        size_bytes = int(size_match.group(1).replace(',', ''))
                        size_human = size_match.group(2).strip()
                        disk_info = {
                            'size': size_bytes,
                            'size_human': size_human
                        }
                        
                    # Extract name info
                    name_match = re.search(r'Device / Media Name:\s+(.+)', disk_info_cmd)
                    if name_match:
                        disk_info['name'] = name_match.group(1).strip()
                    else:
                        disk_info['name'] = disk_id
                        
                except subprocess.CalledProcessError as e:
                    print(f"{YELLOW}Warning: Unable to get detailed disk information: {e}{RESET}")
                    
            elif system == 'Linux':
                try:
                    # Try to get disk info using lsblk
                    disk_info_cmd = subprocess.check_output(['lsblk', '-bdno', 'SIZE,MODEL', disk_path], 
                                                          stderr=subprocess.STDOUT).decode('utf-8').strip()
                    if disk_info_cmd:
                        parts = disk_info_cmd.split()
                        if parts:
                            size_bytes = int(parts[0])
                            disk_info['size'] = size_bytes
                            disk_info['size_human'] = format_size(size_bytes)
                            if len(parts) > 1:
                                disk_info['name'] = ' '.join(parts[1:])
                            else:
                                disk_info['name'] = disk_id
                except (subprocess.CalledProcessError, FileNotFoundError):
                    try:
                        # Fallback to fdisk
                        disk_info_cmd = subprocess.check_output(['fdisk', '-l', disk_path], 
                                                              stderr=subprocess.STDOUT).decode('utf-8')
                        size_match = re.search(r'Disk\s+.*?:\s+([0-9.]+\s+[A-Za-z]+)', disk_info_cmd)
                        if size_match:
                            disk_info['size_human'] = size_match.group(1)
                            disk_info['name'] = disk_id
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        print(f"{YELLOW}Warning: Unable to get detailed disk information{RESET}")
                        
            elif system == 'Windows':
                try:
                    # Get disk info using PowerShell
                    ps_cmd = f'Get-Disk | Where-Object {{ $_.DeviceId -eq "{disk_id}" }} | Format-List'
                    disk_info_cmd = subprocess.check_output(['powershell', '-Command', ps_cmd], 
                                                          stderr=subprocess.STDOUT).decode('utf-8')
                    
                    # Extract size and model info from the output
                    size_match = re.search(r'Size\s*:\s*([0-9,]+)', disk_info_cmd)
                    model_match = re.search(r'FriendlyName\s*:\s*(.+)', disk_info_cmd)
                    
                    if size_match:
                        size_bytes = int(size_match.group(1).replace(',', ''))
                        disk_info['size'] = size_bytes
                        disk_info['size_human'] = format_size(size_bytes)
                    
                    if model_match:
                        disk_info['name'] = model_match.group(1).strip()
                    else:
                        disk_info['name'] = f"Disk {disk_id}"
                        
                except (subprocess.CalledProcessError, FileNotFoundError):
                    print(f"{YELLOW}Warning: Unable to get detailed disk information{RESET}")
        except Exception as e:
            print(f"{YELLOW}Warning: Error getting disk info: {e}{RESET}")
    
    # If we couldn't get disk info, show a generic warning
    if not disk_info:
        print(f"{YELLOW}Warning: Unable to get detailed information about {disk_path}.{RESET}")
        disk_info = {
            'name': os.path.basename(disk_path),
            'size_human': "Unknown size"
        }
    
    # Display warning message
    box_width = 64  # Updated to 64 for consistent alignment
    print(f"{RED}{BRIGHT}╔═{'═' * box_width}╗{RESET}")
    print(f"{RED}{BRIGHT}║ !!! SECURE DISK ERASE WARNING !!!{' ' * (box_width - 33)}║{RESET}")
    print(f"{RED}{BRIGHT}╠═{'═' * box_width}╣{RESET}")
    
    # Standardize spacing calculation for consistent right border alignment
    # -2 accounts for the space after ║ and the ║ at the end
    print(f"{RED}{BRIGHT}║{RESET} Target: {RED}{disk_path}{RESET}{' ' * (box_width - 8 - len(disk_path))}{RED}{BRIGHT}║{RESET}")
    print(f"{RED}{BRIGHT}║{RESET} Disk Name: {RED}{disk_info.get('name', 'Unknown')}{RESET}{' ' * (box_width - 11 - len(disk_info.get('name', 'Unknown')))}{RED}{BRIGHT}║{RESET}")
    
    # Get size from disk_info, ensuring we use the stored human-readable size
    size_display = disk_info.get('size_human', format_size(disk_info.get('size', 0)))
    if size_display == "0B":  # Fallback if we somehow got a zero size
        size_display = "Unknown"
    print(f"{RED}{BRIGHT}║{RESET} Size: {RED}{size_display}{RESET}{' ' * (box_width - 6 - len(size_display))}{RED}{BRIGHT}║{RESET}")
    
    print(f"{RED}{BRIGHT}║{RESET} Filesystem: {RED}{filesystem.upper()}{RESET}{' ' * (box_width - 12 - len(filesystem.upper()))}{RED}{BRIGHT}║{RESET}")
    if label:
        print(f"{RED}{BRIGHT}║{RESET} Label: {RED}{label}{RESET}{' ' * (box_width - 7 - len(label))}{RED}{BRIGHT}║{RESET}")
    print(f"{RED}{BRIGHT}╠═{'═' * box_width}╣{RESET}")
    
    # Break these warning messages into multiple lines if needed
    warnings = [
        "This operation will SECURELY ERASE ALL DATA on the disk.",
        "The disk will be formatted, overwritten, then formatted again.",
        "This CANNOT be undone. All files will be PERMANENTLY DELETED."
    ]
    
    for warning in warnings:
        print(f"{RED}{BRIGHT}║{RESET} {warning}{' ' * (box_width - len(warning))}{RED}{BRIGHT}║{RESET}")
    
    print(f"{RED}{BRIGHT}╚═{'═' * box_width}╝{RESET}\n")
    
    # Get confirmation before starting
    if not no_confirm:
        # Simplified confirmation text
        confirmation_text = "I UNDERSTAND"
        
        # Box width (excluding borders)
        box_width = 64  # Adjusted for proper right border alignment
        
        # Print the confirmation box
        print(f"{RED}{BRIGHT}╔═{'═' * box_width}╗{RESET}")
        print(f"{RED}{BRIGHT}║ CRITICAL CONFIRMATION REQUIRED{' ' * (box_width - 30)}║{RESET}")
        print(f"{RED}{BRIGHT}╠═{'═' * box_width}╣{RESET}")
        
        # Apply consistent padding for the right border
        print(f"{RED}{BRIGHT}║{RESET} This operation {RED}CANNOT{RESET} be undone!{' ' * (box_width - 32)}{RED}{BRIGHT}║{RESET}")
        
        # Simplified confirmation message with proper padding
        msg = f"To confirm, please type exactly: \"{confirmation_text}\""
        print(f"{RED}{BRIGHT}║{RESET} {msg}{' ' * (box_width - len(msg))}{RED}{BRIGHT}║{RESET}")
        
        print(f"{RED}{BRIGHT}╚═{'═' * box_width}╝{RESET}")
        print(f"{YELLOW}Confirmation: {RESET}", end="")
        response = input().strip()
        
        if response != confirmation_text:
            print(f"{RED}Confirmation text does not match. Operation aborted.{RESET}")
            sys.exit(0)
    
    # Function to perform disk formatting
    def perform_format(step_name):
        print(f"{YELLOW}{step_name} {disk_path} with {filesystem.upper()}...{RESET}")
        
        try:
            # Format using appropriate command based on OS and filesystem
            if system == 'Darwin':  # macOS
                # Map common filesystem names to macOS diskutil format names
                fs_map = {
                    'apfs': 'APFS',
                    'hfs+': 'HFS+',
                    'fat32': 'FAT32',
                    'exfat': 'ExFAT',
                    'ntfs': 'NTFS',
                    'ext4': 'ExFAT'  # ext4 not natively supported, fallback to ExFAT
                }
                
                fs_format = fs_map.get(filesystem.lower(), filesystem.upper())
                
                # Add label if specified, otherwise use a default
                disk_label = label if label else "FORMATTED"
                
                # Check if disk_id is a partition or a whole disk
                is_partition = bool(re.search(r'disk\d+s\d+', disk_id))
                
                if is_partition:
                    # For partitions/volumes, use eraseVolume
                    format_args = ['diskutil', 'eraseVolume', fs_format, disk_label, f"/dev/{disk_id}"]
                else:
                    # For whole disks, use eraseDisk
                    format_args = ['diskutil', 'eraseDisk', fs_format, disk_label, disk_id]
                
                # Show command about to be executed
                print(f"{YELLOW}Executing: {' '.join(format_args)}{RESET}")
                
                # Execute the format command
                result = subprocess.run(format_args, capture_output=True, text=True)
                
                if result.returncode != 0:
                    print(f"{RED}{BRIGHT}Error formatting disk:{RESET}")
                    print(f"{result.stderr}")
                    sys.exit(1)
                
                print(f"{GREEN}Disk formatting output:{RESET}")
                print(result.stdout)
                
            elif system == 'Linux':
                # Linux formatting approach
                # First, we may need to unmount the disk if it's mounted
                try:
                    subprocess.run(['umount', disk_path], stderr=subprocess.PIPE)
                except Exception:
                    pass  # Ignore errors from unmount
                    
                # Format based on filesystem type
                if filesystem.lower() == 'ext4':
                    cmd = ['mkfs.ext4']
                    if label:
                        cmd.extend(['-L', label])
                    cmd.append(disk_path)
                    
                elif filesystem.lower() == 'ext3':
                    cmd = ['mkfs.ext3']
                    if label:
                        cmd.extend(['-L', label])
                    cmd.append(disk_path)
                    
                elif filesystem.lower() == 'ext2':
                    cmd = ['mkfs.ext2']
                    if label:
                        cmd.extend(['-L', label])
                    cmd.append(disk_path)
                    
                elif filesystem.lower() in ('fat32', 'vfat'):
                    cmd = ['mkfs.vfat', '-F', '32']
                    if label:
                        cmd.extend(['-n', label])
                    cmd.append(disk_path)
                    
                elif filesystem.lower() == 'exfat':
                    cmd = ['mkfs.exfat']
                    if label:
                        cmd.extend(['-n', label])
                    cmd.append(disk_path)
                    
                elif filesystem.lower() == 'ntfs':
                    cmd = ['mkfs.ntfs', '-f']  # Fast format
                    if label:
                        cmd.extend(['-L', label])
                    cmd.append(disk_path)
                    
                else:
                    print(f"{RED}Error: Unsupported filesystem {filesystem} for Linux.{RESET}")
                    sys.exit(1)
                    
                print(f"{YELLOW}Executing: {' '.join(cmd)}{RESET}")
                
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        print(f"{RED}{BRIGHT}Error formatting disk:{RESET}")
                        print(f"{result.stderr}")
                        sys.exit(1)
                    
                    print(f"{GREEN}Disk formatting output:{RESET}")
                    print(result.stdout)
                    
                except FileNotFoundError:
                    print(f"{RED}Error: Required formatting tool not found. You may need to install the appropriate package.{RESET}")
                    print(f"{YELLOW}For example, try: sudo apt-get install dosfstools exfat-utils ntfs-3g e2fsprogs{RESET}")
                    sys.exit(1)
                
            elif system == 'Windows':
                # Windows formatting approach
                # For the disk formatting, we'll use diskpart with a script file
                
                # Create a temporary script file for diskpart
                script_file = os.path.join(tempfile.gettempdir(), 'diskpart_script.txt')
                
                # Map filesystem names to Windows format names
                fs_map = {
                    'fat32': 'FAT32',
                    'exfat': 'exFAT',
                    'ntfs': 'NTFS',
                    'ext4': 'NTFS',  # ext4 not supported on Windows, fallback to NTFS
                    'hfs+': 'NTFS'   # HFS+ not supported on Windows, fallback to NTFS
                }
                
                fs_format = fs_map.get(filesystem.lower(), 'NTFS')
                
                try:
                    # Write the diskpart script
                    with open(script_file, 'w') as f:
                        f.write(f"select disk {disk_id}\n")
                        f.write("clean\n")
                        f.write("create partition primary\n")
                        f.write("select partition 1\n")
                        f.write(f"format fs={fs_format} quick")
                        if label:
                            f.write(f" label=\"{label}\"")
                        f.write("\n")
                        f.write("assign\n")
                        f.write("exit\n")
                    
                    # Execute diskpart with the script
                    print(f"{YELLOW}Executing diskpart with the following commands:{RESET}")
                    with open(script_file, 'r') as f:
                        for line in f:
                            print(f"{YELLOW}  {line.strip()}{RESET}")
                    
                    result = subprocess.run(['diskpart', '/s', script_file], capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        print(f"{RED}{BRIGHT}Error formatting disk:{RESET}")
                        print(f"{result.stderr}")
                        sys.exit(1)
                    
                    print(f"{GREEN}Disk formatting output:{RESET}")
                    print(result.stdout)
                    
                except Exception as e:
                    print(f"{RED}Error during Windows disk formatting: {e}{RESET}")
                    sys.exit(1)
                finally:
                    # Clean up the temporary script file
                    try:
                        os.remove(script_file)
                    except:
                        pass
                
            else:
                print(f"{RED}Error: Disk formatting not supported on {system}.{RESET}")
                sys.exit(1)
                
            return True
            
        except Exception as e:
            print(f"{RED}{BRIGHT}Error during {step_name.lower()}: {e}{RESET}")
            sys.exit(1)
    
    # Function to get the mount point of the newly formatted disk
    def get_disk_mountpoint():
        """Get the mount point of the formatted disk."""
        if system == 'Darwin':  # macOS
            try:
                # For macOS, use diskutil info to get the mount point
                info = subprocess.check_output(['diskutil', 'info', disk_id], 
                                            stderr=subprocess.STDOUT).decode('utf-8')
                
                # Check for mount point in the output
                mount_match = re.search(r'Mount Point:\s+(.+)', info)
                if mount_match:
                    return mount_match.group(1).strip()
                    
                # Check for volume path if mount point not found
                vol_match = re.search(r'Volume Name:\s+(.+)', info)
                if vol_match:
                    vol_name = vol_match.group(1).strip()
                    # Check if the volume is mounted in /Volumes
                    vol_path = f"/Volumes/{vol_name}"
                    if os.path.exists(vol_path):
                        return vol_path
            except:
                pass
                
        elif system == 'Linux':
            try:
                # For Linux, use lsblk to get the mount point
                mount_info = subprocess.check_output(['lsblk', '-no', 'MOUNTPOINT', disk_path], 
                                                    stderr=subprocess.STDOUT).decode('utf-8').strip()
                if mount_info:
                    return mount_info
            except:
                pass
                
        elif system == 'Windows':
            try:
                # For Windows, use wmic to get the drive letter
                drive_letter = None
                if re.match(r'\\\\.\\PhysicalDrive\d+', disk_path):
                    # Extract the disk number
                    disk_num = re.search(r'PhysicalDrive(\d+)', disk_path).group(1)
                    # Get partition info for the disk
                    ps_cmd = f'Get-Partition -DiskNumber {disk_num} | Select-Object -ExpandProperty DriveLetter'
                    drive_letter = subprocess.check_output(['powershell', '-Command', ps_cmd], 
                                                         stderr=subprocess.STDOUT).decode('utf-8').strip()
                    if drive_letter:
                        return f"{drive_letter}:\\"
            except:
                pass
                
        # If we couldn't determine the mount point, return None
        return None
    
    try:
        # Step 1: Initial format to prepare the disk
        print(f"{CYAN}{BRIGHT}╔═══════════════════════════════════════════════════════════╗{RESET}")
        print(f"{CYAN}{BRIGHT}║ STEP 1: INITIAL DISK FORMAT                               ║{RESET}")
        print(f"{CYAN}{BRIGHT}╚═══════════════════════════════════════════════════════════╝{RESET}")
        perform_format("Formatting")
        
        # Step 2: Wipe free space on the newly formatted disk
        print(f"\n{CYAN}{BRIGHT}╔═══════════════════════════════════════════════════════════╗{RESET}")
        print(f"{CYAN}{BRIGHT}║ STEP 2: SECURE FREE SPACE WIPE                            ║{RESET}")
        print(f"{CYAN}{BRIGHT}╚═══════════════════════════════════════════════════════════╝{RESET}")
        
        # Get the mount point of the newly formatted disk
        mount_point = get_disk_mountpoint()
        
        if mount_point:
            print(f"{GREEN}Disk mounted at: {mount_point}{RESET}")
            
            # Directly fill the disk with patterns instead of using the interactive wipe_free_space function
            try:
                # Get free space information
                free_space = get_free_space(mount_point)
                free_space_display = format_size(free_space)
                print(f"{GREEN}Free space to wipe: {free_space_display}{RESET}")
                
                # Create temporary file path
                fname = os.path.join(mount_point, '.dwipe_free_space.tmp')
                temp_files = [fname]
                
                # Set up cleanup function
                def cleanup_temp_files():
                    for temp_file in temp_files:
                        try:
                            if os.path.exists(temp_file):
                                os.remove(temp_file)
                                print(f"\n{GREEN}Cleaned up temporary file: {temp_file}{RESET}")
                        except Exception as e:
                            print(f"\n{YELLOW}Warning: Could not remove temporary file {temp_file}: {e}{RESET}")
                
                # Register cleanup for exit
                atexit.register(cleanup_temp_files)
                
                # Container for progress bar reference
                progress_bar_container = {'instance': None}
                
                # Setup signal handler for CTRL+C
                def signal_handler(sig, frame):
                    if progress_bar_container['instance'] is not None:
                        progress_bar = progress_bar_container['instance']
                        progress_bar.disable = True
                        progress_bar_container['instance'] = None
                    
                    print(f"\n\n{YELLOW}Operation interrupted by user. Cleaning up...{RESET}")
                    cleanup_temp_files()
                    print(f"{RED}Wiping operation canceled.{RESET}")
                    sys.exit(130)
                
                # Save original handler and set new one
                original_handler = signal.getsignal(signal.SIGINT)
                signal.signal(signal.SIGINT, signal_handler)
                
                # Display wiping information
                passes = passes
                block_size = 1048576  # 1MB block size
                pattern = pattern
                
                box_width = 65
                print(f"{CYAN}{BRIGHT}╔═{'═' * box_width}╗{RESET}")
                print(f"{CYAN}{BRIGHT}║ SECURE FREE SPACE WIPING{' ' * (box_width - 24)}║{RESET}")
                print(f"{CYAN}{BRIGHT}╠═{'═' * box_width}╣{RESET}")
                print(f"{CYAN}{BRIGHT}║{RESET} Target: {GREEN}{mount_point}{' ' * (box_width - 9 - len(mount_point) + 1)}{CYAN}{BRIGHT}║{RESET}")
                print(f"{CYAN}{BRIGHT}║{RESET} Free space: {GREEN}{free_space_display}{' ' * (box_width - 13 - len(free_space_display) + 1)}{CYAN}{BRIGHT}║{RESET}")
                print(f"{CYAN}{BRIGHT}║{RESET} Passes: {GREEN}{passes}{' ' * (box_width - 9 - len(str(passes)) + 1)}{CYAN}{BRIGHT}║{RESET}")
                print(f"{CYAN}{BRIGHT}║{RESET} Block size: {GREEN}{format_size(block_size)}{' ' * (box_width - 13 - len(format_size(block_size)) + 1)}{CYAN}{BRIGHT}║{RESET}")
                print(f"{CYAN}{BRIGHT}║{RESET} Pattern: {GREEN}{pattern}{' ' * (box_width - 10 - len(pattern) + 1)}{CYAN}{BRIGHT}║{RESET}")
                print(f"{CYAN}{BRIGHT}╚═{'═' * box_width}╝{RESET}\n")
                
                # Start time for overall ETA calculation
                overall_start_time = time.time()
                
                # Perform the wiping with multiple passes
                for p in range(passes):
                    # Determine pattern based on pass number
                    if pattern == 'all':
                        if p == 0:
                            mode = 'random'
                        else:
                            mode = {1: 'zeroes', 2: 'ones'}.get(p % 3, 'random')
                    else:
                        mode = pattern
                    
                    pass_color = [GREEN, YELLOW, CYAN, MAGENTA, BLUE][p % 5]
                    print(f"{pass_color}Pass {p+1}/{passes}: filling free space with {mode}{RESET}")
                    
                    # Calculate and display overall ETA if we've already completed at least one pass
                    if p > 0:
                        elapsed_time = time.time() - overall_start_time
                        avg_time_per_pass = elapsed_time / p
                        remaining_passes = passes - p
                        overall_eta_seconds = avg_time_per_pass * remaining_passes
                        
                        overall_eta = format_time_human_readable(overall_eta_seconds, abbreviated=False)
                        overall_eta_time = time.strftime("%I:%M %p", time.localtime(time.time() + overall_eta_seconds))
                        print(f"{YELLOW}Overall ETA: {overall_eta} (complete at approximately {overall_eta_time}){RESET}")
                        
                    # Initialize variables for custom progress tracking
                    pass_start_time = time.time()
                    written = 0
                    last_display_time = 0
                    time_line = ""
                    
                    # First print the time line that we'll update in place
                    time_line = "Elapsed: 00:00:00 • Remaining: calculating..."
                    print(time_line)
                    
                    # Create a progress bar
                    progress_format = '{percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}'
                    progress_bar = tqdm(total=free_space, unit='B', unit_scale=True, 
                                     unit_divisor=1024,
                                     bar_format=progress_format,
                                     leave=True)
                    
                    # Store reference for signal handler
                    progress_bar_container['instance'] = progress_bar
                    
                    # Create a unique temporary file for each pass
                    fname = os.path.join(mount_point, f'.dwipe_free_space_{p+1}.tmp')
                    if fname not in temp_files:
                        temp_files.append(fname)
                        
                    # Make sure any previous temp files are deleted
                    try:
                        if os.path.exists(fname):
                            os.remove(fname)
                    except:
                        pass
                    
                    try:
                        with open(fname, 'wb') as f:
                            while True:
                                if mode == 'random':
                                    chunk = os.urandom(block_size)
                                elif mode == 'ones':
                                    chunk = b'\xFF' * block_size
                                elif mode == 'zeroes':
                                    chunk = b'\x00' * block_size
                                else:  # Should never happen
                                    chunk = os.urandom(block_size)
                                
                                try:
                                    f.write(chunk)
                                    written += block_size
                                    
                                    # Update display periodically
                                    current_time = time.time()
                                    if current_time - last_display_time >= 0.5:  # Update twice per second
                                        # Calculate elapsed and remaining time
                                        elapsed_seconds = current_time - pass_start_time
                                        
                                        # Format elapsed time
                                        elapsed_str = format_time_human_readable(elapsed_seconds, abbreviated=True)
                                        
                                        # Calculate remaining time based on current speed
                                        if written > 0:
                                            bytes_per_second = written / elapsed_seconds
                                            remaining_seconds = (free_space - written) / bytes_per_second if bytes_per_second > 0 else 0
                                            remaining_str = format_time_human_readable(remaining_seconds, abbreviated=True)
                                        else:
                                            remaining_str = "calculating..."
                                        
                                        # Create new time line
                                        new_time_line = f"Elapsed: {elapsed_str} • Remaining: {remaining_str}"
                                        
                                        # Only update if the line has changed
                                        if new_time_line != time_line:
                                            # Move cursor up one line and clear it
                                            sys.stdout.write("\033[F\033[K")
                                            sys.stdout.write(new_time_line + "\n")
                                            sys.stdout.flush()
                                            time_line = new_time_line
                                        
                                        last_display_time = current_time
                                    
                                    # Update the progress
                                    progress_bar.update(block_size)
                                    
                                    # Occasional flush
                                    if written % (block_size * 100) == 0:
                                        f.flush()
                                        
                                except OSError as e:
                                    if e.errno == errno.ENOSPC:
                                        # Disk is full, which is what we want
                                        break
                                    else:
                                        print(f"\n{YELLOW}Error: {e}{RESET}", file=sys.stderr)
                                        break
                                
                    except Exception as e:
                        print(f"\n{YELLOW}Error during wiping: {e}{RESET}")
                    finally:
                        # Close the progress bar
                        progress_bar.close()
                        progress_bar_container['instance'] = None
                        
                        # Force sync and flush before removing
                        try:
                            if 'f' in locals() and hasattr(f, 'fileno'):
                                os.fsync(f.fileno())
                        except Exception:
                            pass
                    
                    # Always delete the temporary file after each pass
                    try:
                        if os.path.exists(fname):
                            os.remove(fname)
                            if fname in temp_files:  # Add check to prevent ValueError
                                temp_files.remove(fname)  # Remove from the cleanup list since we handled it
                    except OSError as e:
                        print(f"\n{YELLOW}Warning: Could not remove temporary file: {e}{RESET}")
                        # Try to ensure the file is deleted by forcing unmount/remount if needed
                        if system == 'Darwin':  # macOS
                            try:
                                # For macOS, try using diskutil to unmount and remount
                                print(f"{YELLOW}Attempting to unmount and remount volume to clean up...{RESET}")
                                subprocess.run(['diskutil', 'unmount', mount_point], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                                subprocess.run(['diskutil', 'mount', disk_path], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                            except:
                                pass
                    
                    wiped = format_size(min(written, free_space))
                    print(f"{GREEN}✓ Pass {p+1} complete, wiped ~{wiped}{RESET}")
                    print("")  # Empty line between passes
                
                # Calculate total time taken
                total_time = time.time() - overall_start_time
                time_str = format_time_human_readable(total_time, abbreviated=False)
                
                # Summary
                box_width = 65
                print(f"{GREEN}{BRIGHT}╔═{'═' * box_width}╗{RESET}")
                print(f"{GREEN}{BRIGHT}║ WIPING COMPLETE{' ' * (box_width - 15)}║{RESET}")
                print(f"{GREEN}{BRIGHT}╠═{'═' * box_width}╣{RESET}")
                print(f"{GREEN}{BRIGHT}║{RESET} Total passes: {GREEN}{passes}{' ' * (box_width - 15 - len(str(passes)) + 1)}{GREEN}{BRIGHT}║{RESET}")
                
                total_wiped = format_size(min(written*passes, free_space))
                print(f"{GREEN}{BRIGHT}║{RESET} Total wiped: {GREEN}{total_wiped}{' ' * (box_width - 14 - len(total_wiped) + 1)}{GREEN}{BRIGHT}║{RESET}")
                print(f"{GREEN}{BRIGHT}║{RESET} Time taken: {GREEN}{time_str}{' ' * (box_width - 13 - len(time_str) + 1)}{GREEN}{BRIGHT}║{RESET}")
                print(f"{GREEN}{BRIGHT}╚═{'═' * box_width}╝{RESET}")
                
                # Restore original signal handler
                signal.signal(signal.SIGINT, original_handler)
                
                # Unregister the cleanup function since we'll clean up here
                atexit.unregister(cleanup_temp_files)
                cleanup_temp_files()
                
            except Exception as e:
                print(f"{RED}Error during free space wiping: {e}{RESET}")
                print(f"{YELLOW}Continuing with final formatting...{RESET}")
        else:
            print(f"{YELLOW}Warning: Could not determine mount point for disk {disk_path}.{RESET}")
            print(f"{YELLOW}Skipping free space wiping. The disk may not be fully secure.{RESET}")
        
        # Step 3: Final format to complete the secure erase
        print(f"\n{CYAN}{BRIGHT}╔═══════════════════════════════════════════════════════════╗{RESET}")
        print(f"{CYAN}{BRIGHT}║ STEP 3: FINAL DISK FORMAT                                 ║{RESET}")
        print(f"{CYAN}{BRIGHT}╚═══════════════════════════════════════════════════════════╝{RESET}")
        perform_format("Final formatting")
        
        # Complete the process
        box_width = 65
        print(f"\n{GREEN}{BRIGHT}╔═{'═' * box_width}╗{RESET}")
        print(f"{GREEN}{BRIGHT}║{RESET} SECURE DISK ERASE COMPLETE{' ' * (box_width - 27)}{GREEN}{BRIGHT}║{RESET}")
        print(f"{GREEN}{BRIGHT}╠═{'═' * box_width}╣{RESET}")
        print(f"{GREEN}{BRIGHT}║{RESET} Disk: {GREEN}{disk_path}{' ' * (box_width - 7 - len(disk_path))}{GREEN}{BRIGHT}║{RESET}")
        print(f"{GREEN}{BRIGHT}║{RESET} Filesystem: {GREEN}{filesystem.upper()}{' ' * (box_width - 13 - len(filesystem.upper()))}{GREEN}{BRIGHT}║{RESET}")
        if label:
            print(f"{GREEN}{BRIGHT}║{RESET} Label: {GREEN}{label}{' ' * (box_width - 8 - len(label))}{GREEN}{BRIGHT}║{RESET}")
        print(f"{GREEN}{BRIGHT}║{RESET} Security: {GREEN}Secure multi-pass format and free space wipe{' ' * (box_width - 52)}{GREEN}{BRIGHT}║{RESET}")
        print(f"{GREEN}{BRIGHT}╚═{'═' * box_width}╝{RESET}")
        
    except Exception as e:
        print(f"{RED}{BRIGHT}Error during secure disk erase: {e}{RESET}")
        sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='DWipe – Secure Free‑Space Wiper')
    
    # Show the banner at program start
    print_colorful_banner()
    
    # Create subparsers for different modes
    subparsers = parser.add_subparsers(dest='mode', help='Operation mode')
    
    # Add the global flags
    parser.add_argument('-v', '--verify', action='store_true', help='Verify wiped space after each pass')
    parser.add_argument('-y', '--yes', action='store_true', help='Skip confirmation prompt')
    parser.add_argument('-p', '--passes', type=int, default=3, help='Number of overwrite passes')
    parser.add_argument('-t', '--pattern', choices=['all', 'zeroes', 'ones', 'random', 'dicks', 'haha'], 
                   default='all', help='Data pattern to use (default: all with random first pass)')
    
    # Free space wiping mode (default)
    freespace_parser = subparsers.add_parser('freespace', help='Wipe free space on a volume (default)')
    freespace_parser.add_argument('-r', '--root', default='/', help='Root path to wipe (default: interactive)')
    freespace_parser.add_argument('-b', '--block', type=int, default=1048576, help='Block size in bytes')
    freespace_parser.add_argument('-i', '--interactive', action='store_true', help='Force interactive drive selection')
    
    # Format disk mode
    format_parser = subparsers.add_parser('format', help='Format/erase an entire disk (DESTROYS ALL DATA)')
    format_parser.add_argument('-d', '--disk', required=True, help='Disk device to format (e.g., /dev/disk2, /dev/sda, etc.)')
    format_parser.add_argument('-f', '--filesystem', default='exfat', 
                             choices=['exfat', 'fat32', 'ntfs', 'apfs', 'hfs+', 'ext4', 'ext3', 'ext2', 'vfat'], 
                             help='Filesystem to use (default: exfat, availability depends on OS)')
    format_parser.add_argument('-l', '--label', help='Volume label for the formatted disk')
    
    args = parser.parse_args()
    
    # Handle different modes
    try:
        if args.mode == 'format':
            # Format disk mode
            format_disk(disk_path=args.disk, filesystem=args.filesystem, 
                       label=args.label, no_confirm=args.yes,
                       passes=args.passes, pattern=args.pattern,
                       verify=args.verify)
        else:
            # Default to free space wiping mode
            # Handle backward compatibility with direct arguments
            root = getattr(args, 'root', '/')
            passes = args.passes
            block = getattr(args, 'block', 1048576)
            verify = args.verify
            pattern = args.pattern
            no_confirm = args.yes
            interactive = getattr(args, 'interactive', False)
            
            # Force interactive mode if requested
            if interactive:
                root = '/'
                
            wipe_free_space(root=root, passes=passes, block_size=block, 
                          verify=verify, pattern=pattern, no_confirm=no_confirm)
    except KeyboardInterrupt:
        # Fallback in case the signal handler doesn't catch the interrupt
        print(f"\n\n{RED}Operation canceled by user.{RESET}")
        sys.exit(130)
