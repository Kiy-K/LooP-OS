import pytest
from loop.kernel.filesystem import FileSystem, FileNode, DirectoryNode

@pytest.fixture
def fs():
    return FileSystem()

def test_initial_structure(fs):
    assert fs.get_node_type("/usr") == "dir"
    assert fs.get_node_type("/etc") == "dir"
    assert fs.get_node_type("/home/root") == "dir"
    assert fs.get_node_type("/nonexistent") is None

def test_mkdir(fs):
    fs.mkdir("/home/user1", uid="root")
    assert fs.get_node_type("/home/user1") == "dir"

    # Test duplicate creation
    with pytest.raises(FileExistsError):
        fs.mkdir("/home/user1", uid="root")

    # Test permission denied (guest creating in /)
    with pytest.raises(PermissionError):
        fs.mkdir("/root_guest", uid="guest")

def test_file_operations(fs):
    # Write new file
    fs.write_file("/home/guest/notes.txt", "hello world", uid="guest")
    assert fs.get_node_type("/home/guest/notes.txt") == "file"
    assert fs.read_file("/home/guest/notes.txt", uid="guest") == "hello world"

    # Overwrite
    fs.write_file("/home/guest/notes.txt", "updated", uid="guest")
    assert fs.read_file("/home/guest/notes.txt", uid="guest") == "updated"

    # Append
    fs.append_file("/home/guest/notes.txt", " line 2", uid="guest")
    content = fs.read_file("/home/guest/notes.txt", uid="guest")
    # append_file adds a newline to the text being appended.
    # Original text: "updated" (no newline, write_file just sets data)
    # Appended: " line 2" + "\n"
    # Result: "updated" + " line 2" + "\n"
    assert content == "updated line 2\n"

def test_permissions(fs):
    # Setup: Create a file owned by root
    fs.write_file("/etc/config", "secret", uid="root")

    # Guest tries to read root file
    # Default is now strict (world_mode=""), so this should fail
    with pytest.raises(PermissionError):
        fs.read_file("/etc/config", uid="guest")

    with pytest.raises(PermissionError):
        fs.write_file("/etc/config", "hacked", uid="guest")

def test_world_readable(fs):
    """Test that we can explicitly make a file world readable."""
    # 1. Create file as root (secure by default)
    fs.write_file("/public_info", "public data", uid="root")

    # 2. Verify guest cannot read it
    with pytest.raises(PermissionError):
        fs.read_file("/public_info", uid="guest")

    # 3. Make it world readable
    fs.chmod("/public_info", world_mode="r", uid="root")

    # 4. Verify guest CAN read it
    content = fs.read_file("/public_info", uid="guest")
    assert content == "public data"

    # 5. Verify guest CANNOT write to it (only 'r' given)
    with pytest.raises(PermissionError):
        fs.write_file("/public_info", "overwrite", uid="guest")

def test_chmod_permissions(fs):
    """Test that only owner/root can chmod."""
    fs.write_file("/home/guest/private", "data", uid="guest")

    # Guest (owner) can chmod
    fs.chmod("/home/guest/private", world_mode="r", uid="guest")

    # Root can chmod
    fs.chmod("/home/guest/private", world_mode="", uid="root")

    # Another user cannot chmod
    with pytest.raises(PermissionError):
        fs.chmod("/home/guest/private", world_mode="r", uid="other")

def test_list_dir(fs):
    fs.write_file("/home/guest/f1", "", uid="guest")
    fs.write_file("/home/guest/f2", "", uid="guest")

    items = fs.list_dir("/home/guest", uid="guest")
    assert "f1" in items
    assert "f2" in items
    assert len(items) == 2

    # Test listing file as dir
    with pytest.raises(ValueError):
        fs.list_dir("/home/guest/f1", uid="guest")

def test_delete_file(fs):
    fs.write_file("/home/guest/temp", "data", uid="guest")
    fs.delete_file("/home/guest/temp", uid="guest")
    assert fs.get_node_type("/home/guest/temp") is None

    # Test delete non-existent
    with pytest.raises(FileNotFoundError):
        fs.delete_file("/home/guest/temp", uid="guest")

def test_delete_directory(fs):
    fs.mkdir("/home/guest/folder", uid="guest")
    fs.delete_file("/home/guest/folder", uid="guest") # delete_file handles dirs too?
    # The method is named delete_file but docstring says "Deletes a file or directory."
    assert fs.get_node_type("/home/guest/folder") is None

    # Test delete non-empty directory
    fs.mkdir("/home/guest/full", uid="guest")
    fs.write_file("/home/guest/full/file", "x", uid="guest")
    with pytest.raises(OSError, match="Directory not empty"):
        fs.delete_file("/home/guest/full", uid="guest")

def test_invalid_paths(fs):
    with pytest.raises(ValueError, match="Not a file"):
        fs.read_file("/home", uid="root")

    with pytest.raises(ValueError, match="Path is a directory"):
        fs.write_file("/home", "data", uid="root")
