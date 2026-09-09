"""
Open an EXISTING named Windows file mapping and read from it.

Python's stdlib `mmap.mmap(-1, size, tagname=name)` is unreliable for this: passed a -1
fileno, it can silently CREATE a fresh zero-filled mapping under that name instead of
attaching to one that already exists, with no exception raised either way -- which looks
identical to "opened fine" while actually reading nothing real. Calling the real Win32
`OpenFileMappingW` directly fails loudly (OSError) if the mapping doesn't exist, instead of
masking the problem.
"""

import ctypes
from ctypes import wintypes

FILE_MAP_READ = 0x0004

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

_kernel32.OpenFileMappingW.restype = wintypes.HANDLE
_kernel32.OpenFileMappingW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]

_kernel32.MapViewOfFile.restype = ctypes.c_void_p
_kernel32.MapViewOfFile.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t,
]

_kernel32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


class ExistingFileMapping:
    """Attaches to a named mapping that must already exist; raises OSError otherwise."""

    def __init__(self, name: str, size: int):
        self.size = size
        self._handle = _kernel32.OpenFileMappingW(FILE_MAP_READ, False, name)
        if not self._handle:
            err = ctypes.get_last_error()
            raise OSError(
                err, f"OpenFileMappingW({name!r}) failed: {ctypes.FormatError(err).strip()}"
            )
        self._view = _kernel32.MapViewOfFile(self._handle, FILE_MAP_READ, 0, 0, size)
        if not self._view:
            err = ctypes.get_last_error()
            _kernel32.CloseHandle(self._handle)
            raise OSError(
                err, f"MapViewOfFile failed: {ctypes.FormatError(err).strip()}"
            )

    def read(self) -> bytes:
        return ctypes.string_at(self._view, self.size)

    def close(self) -> None:
        if self._view:
            _kernel32.UnmapViewOfFile(self._view)
            self._view = None
        if self._handle:
            _kernel32.CloseHandle(self._handle)
            self._handle = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
