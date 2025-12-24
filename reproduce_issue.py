from loop.kernel.filesystem import FileSystem

fs = FileSystem()
# Setup: Create a file owned by root
fs.write_file("/etc/config", "secret", uid="root")

# Guest tries to read root file
try:
    content = fs.read_file("/etc/config", uid="guest")
    print(f"Read success: {content}")
except PermissionError:
    print("Read failed: PermissionError")
