import ctypes
from ctypes import wintypes

#WIN32API GetCurrentProcess
GetCurrentProcess = ctypes.windll.kernel32.GetCurrentProcess
GetCurrentProcess.argtypes = []
GetCurrentProcess.restype = wintypes.HANDLE

class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [
        ('cb', wintypes.DWORD),
        ('PageFaultCount', wintypes.DWORD),
        ('PeakWorkingSetSize', ctypes.c_size_t),
        ('WorkingSetSize', ctypes.c_size_t),
        ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
        ('QuotaPagedPoolUsage', ctypes.c_size_t),
        ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
        ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
        ('PagefileUsage', ctypes.c_size_t),
        ('PeakPagefileUsage', ctypes.c_size_t),
        ('PrivateUsage', ctypes.c_size_t),
    ]

#PSAPI GetProcessMemoryInfo
GetProcessMemoryInfo = ctypes.windll.psapi.GetProcessMemoryInfo
GetProcessMemoryInfo.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX),
    wintypes.DWORD,
]
GetProcessMemoryInfo.restype = wintypes.BOOL

def get_peak_workingset():
    proc_mem_cnt = PROCESS_MEMORY_COUNTERS_EX()
    result = GetProcessMemoryInfo(GetCurrentProcess(), ctypes.byref(proc_mem_cnt),
                               ctypes.sizeof(proc_mem_cnt))
    if not result:
        raise ctypes.WinError() 
 
    for field in proc_mem_cnt._fields_:
      if field[0] == 'PeakWorkingSetSize':
        return getattr(proc_mem_cnt, field[0])
    raise ctypes.Winerror()
