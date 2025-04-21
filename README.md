# DWipe - Secure Data Wiping Tool

DWipe is a powerful cross-platform tool for securely wiping free space and formatting drives to prevent data recovery. It implements DoD-compliant multi-pass wiping methods to ensure that deleted data cannot be recovered using standard or advanced recovery tools.


## Features

- **Cross-platform support**: Works on macOS, Linux, and Windows
- **Two operation modes**:
  - Free space wiping (securely wipes only unused space)
  - Full disk formatting (erases entire drives securely)
- **Configurable wiping patterns**:
  - Zero-fill (all zeros)
  - One-fill (all ones)
  - Random data (cryptographically secure random values)
  - Alternating patterns
  - "All" pattern (combines random, zeros, and ones in sequence)
  - Special patterns (humor-based patterns)
- **Multi-pass wiping**: Perform up to any number of passes for enhanced security
- **Progress tracking**: Real-time progress bars and ETA calculations
- **User-friendly interface**: Colorful, intuitive console interface with clear status information
- **Automatic filesystem detection**: Identifies and works with all major filesystem types

## Wiping Patterns

DWipe offers multiple data patterns for secure wiping through the `-t` parameter:

### all (Default)
The default wiping method uses a sequence of different patterns across multiple passes:
- First pass: **Random data** (cryptographically secure random bytes)
- Second pass: **All zeros** (0x00 bytes)
- Third pass: **All ones** (0xFF bytes)
- Subsequent passes: Cycles through random, zeros, and ones

This multi-pattern approach provides high security for data sanitization.

### DWipe and SSDs

While DWipe's multi-pass wiping is still valuable for SSDs by filling all user-accessible areas, it cannot guarantee access to wear-leveled blocks. For maximum security with SSDs:

1. Use DWipe's format mode which combines formatting with free space wiping
2. Follow up with a manufacturer's secure erase tool if available
3. For sensitive data, consider using encryption from the beginning

**Note**: Some newer SSDs implement the TRIM command on secure erase, which may be effective in wiping data but might not meet the most stringent security requirements.

## Installation

### Prerequisites

- Python 3.6 or higher
- pip (Python package manager)
- Administrative privileges (for disk operations)

### Basic Installation

1. Clone or download the repository:
   ```
   git clone https://github.com/InfoSecREDD/DWipe.git
   cd DWipe
   ```

2. Run the script directly:
   ```
   python dwipe.py
   ```

The script will automatically set up a virtual environment and install required dependencies on first run.

### Required Dependencies

DWipe will automatically install these in its virtual environment:
- tqdm (progress bars)
- colorama (cross-platform color support)
- psutil (disk information)

## Usage

### Basic Usage

```bash
# Wipe free space (interactive mode)
python dwipe.py

# Wipe free space on a specific volume
python dwipe.py freespace -r /path/to/volume

# Format and securely wipe an entire disk
python dwipe.py format -d /dev/diskX
```

### Free Space Wiping Mode

This mode securely wipes only the free space on a volume, leaving existing files intact:

```bash
# Basic free space wiping with interactive drive selection
python dwipe.py freespace

# Specify volume path
python dwipe.py freespace -r /path/to/volume

# Customize number of passes
python dwipe.py freespace -r /path/to/volume -p 7

# Specify pattern
python dwipe.py freespace -r /path/to/volume -t random

# Skip confirmation prompt
python dwipe.py freespace -r /path/to/volume -y
```

### Disk Formatting Mode

⚠️ **WARNING**: This mode erases **ALL DATA** on the target disk!

```bash
# Format a disk with default settings (exFAT filesystem)
python dwipe.py format -d /dev/diskX

# Specify filesystem type
python dwipe.py format -d /dev/diskX -f ntfs

# Specify volume label
python dwipe.py format -d /dev/diskX -l "MyDrive"
```

## Command Line Arguments

### Global Arguments

- `-h`, `--help`: Show help message and exit

### Free Space Wiping Mode Arguments

- `-r`, `--root`: Root path to wipe (default: interactive selection)
- `-p`, `--passes`: Number of overwrite passes (default: 3)
- `-b`, `--block`: Block size in bytes (default: 1048576)
- `-v`, `--verify`: Verify wiped space after each pass
- `-t`, `--pattern`: Data pattern to use (choices: all, zeroes, ones, random, dicks, haha; default: all)
- `-y`, `--yes`: Skip confirmation prompt
- `-i`, `--interactive`: Force interactive drive selection

### Format Mode Arguments

- `-d`, `--disk`: Disk device to format (e.g., /dev/disk2, /dev/sda)
- `-f`, `--filesystem`: Filesystem to use (choices: exfat, fat32, ntfs, apfs, hfs+, ext4, ext3, ext2, vfat; availability depends on OS)
- `-l`, `--label`: Volume label for the formatted disk
- `-y`, `--yes`: Skip confirmation prompt (DANGEROUS)

## Platform-Specific Information

### macOS

- Works with APFS, HFS+, ExFAT, FAT32, and NTFS volumes
- Handles special cases with read-only system volumes
- Uses `diskutil` commands for improved disk operations

### Linux

- Supports ext2/3/4, FAT32, ExFAT, and NTFS filesystems
- Uses native Linux disk utilities for formatting

### Windows

- Works with NTFS, FAT32, and ExFAT volumes
- Uses PowerShell and `diskpart` commands for disk operations

## How It Works

### Free Space Wiping Process

1. Creates a temporary file on the target volume
2. Continuously writes data to the file until the disk is full
3. Different patterns are used based on the selected wiping mode
4. The file is securely deleted after each pass
5. Process repeats for each pass

### Disk Formatting Process

1. Initial format to create a clean filesystem
2. Free space wiping with multiple passes
3. Final format to complete the sanitization process


### zeroes
Fills the free space with all zeros (0x00 bytes). This basic pattern overwrites data with null bytes, which is fast but less secure than other patterns when used alone.

```
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
```

### ones
Fills the free space with all ones (0xFF bytes). This creates a pattern of all bits set to 1, which is useful as part of a multi-pass approach.

```
FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF
FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF
```

### random
Fills the free space with cryptographically secure random data using Python's `os.urandom()`. This is considered highly secure as it introduces true randomness that makes data recovery more difficult.

The random pattern produces different values on each execution:
```
A3 F5 9C 23 7D E8 B2 5F 01 C6 ... (random bytes)
```

### dicks
A novelty pattern that repeats the ASCII characters "3===D" throughout the free space. This is primarily for humor and not recommended for serious security applications.

```
33 3D 3D 3D 44 33 3D 3D 3D 44 33 3D 3D 3D 44 ...
```

### haha
Another novelty pattern that repeats the ASCII characters "haha-" throughout the free space. Like the "dicks" pattern, this is included for fun rather than security.

```
68 61 68 61 2D 68 61 68 61 2D 68 61 68 61 2D ...
```

For maximum security, use the default `all` pattern with at least 3 passes. The US Department of Defense previously recommended multiple passes with different patterns to ensure data cannot be recovered using specialized equipment.

## Security Standards and Modern Recommendations

While DWipe implements the classic multi-pass wiping approach, it's worth noting that current data sanitization standards have evolved:

1. **Historical DoD Standard**: The Department of Defense 5220.22-M standard was often cited as requiring multiple overwrite passes (3 or 7 passes). This standard became widely referenced in data security.

2. **Current NIST Guidance**: The National Institute of Standards and Technology (NIST) Special Publication 800-88 ("Guidelines for Media Sanitization") has superseded the old DoD standards. For modern storage devices, NIST generally recognizes that a single overwrite pass is sufficient for conventional hard drives.

3. **Modern Storage Considerations**: 
   - For HDDs: Single-pass overwriting is generally effective due to high recording densities of modern drives
   - For SSDs: Overwriting is less effective due to wear-leveling algorithms and block management. Secure erase commands or encryption-based sanitization are preferred

DWipe's multi-pass approach provides a thorough and conservative method that exceeds current minimum recommendations, giving users higher confidence that data cannot be recovered, especially on older storage media.

## Secure Erasure for SSDs and Wear-Leveling

### The Wear-Leveling Challenge

Standard overwriting techniques (including DWipe's multi-pass approach) have limitations when applied to Solid State Drives (SSDs) due to:

1. **Wear-leveling technology**: SSDs distribute writes across memory cells to extend drive life. When you "overwrite" data, the SSD controller may write to new cells and mark old cells for later reuse, leaving original data intact.

2. **Over-provisioning**: SSDs contain extra storage capacity not accessible to the operating system, which may contain remnants of sensitive data.

3. **Block remapping**: Bad blocks are remapped to spare areas, potentially leaving data in inaccessible areas.

### Most Effective SSD Sanitization Methods

For complete SSD sanitization, in order of effectiveness:

1. **ATA/NVMe Secure Erase Commands**: Uses manufacturer-implemented firmware commands to erase all flash memory cells.
   - For SATA SSDs: `hdparm --security-erase` (Linux)
   - For NVMe SSDs: `nvme format` or `nvme sanitize` (most secure)

2. **Manufacturer Tools**: Most SSD manufacturers provide secure erasure utilities designed for their specific hardware.
   - Samsung Magician
   - Western Digital Dashboard
   - Crucial Storage Executive
   - Intel Memory & Storage Tool

3. **Encryption-Based Method**:
   - Enable full disk encryption before using the drive
   - Fill the drive with data
   - Securely erase the encryption keys (most operating systems provide this option)

4. **Physical Destruction**: For highest security, physical destruction remains the only absolutely certain method.
   - Shredding
   - Disintegration 
   - Pulverization
   - High-temperature incineration


## Troubleshooting

### Common Issues

- **"Permission denied" errors**: Run the script with administrator/sudo privileges
- **Path not writable**: Use the `-i` flag to force interactive drive selection
- **"Cannot determine mount point"**: Try specifying a different path with `-r`
- **Disk not found**: Ensure the disk identifier is correct

### Getting Help

If you encounter issues not covered in this documentation, please file an issue in the GitHub repository with the following information:

- Operating system and version
- Full command you were trying to run
- Complete error message
- Any relevant system information

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Inspired by secure data wiping standards and best practices
- Thanks to all contributors and testers who have helped improve this tool

## Disclaimer

While DWipe implements secure wiping techniques, no software can guarantee 100% data destruction on all storage types. Modern SSDs, for example, use wear-leveling that may preserve some data blocks despite overwriting. For maximum security on highly sensitive data, physical destruction of media may be necessary.

The authors are not responsible for any data loss resulting from the use of this tool. 
