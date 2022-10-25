from msilib.schema import Error
import subprocess
import sys
from subprocess import CalledProcessError
import cmd 

IS_WIN32 = 'win32' in str(sys.platform).lower()


def subprocess_call(*args, **kwargs):
    #also works for Popen. It creates a new *hidden* window, so it will work in frozen apps (.exe).
    if IS_WIN32:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags = subprocess.CREATE_NEW_CONSOLE | subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        kwargs['startupinfo'] = startupinfo
        #print("start")
        #print(*args)
    try: 
        # if manually: cmd.exe -> conda activate [env folder] -> pip install specklepy 
        result = subprocess.run(*args, capture_output=True, text=True, shell=True, timeout=1000)
        #print(result)
        #result = subprocess.Popen( arg, shell=True, stdout=subprocess.PIPE) #, stderr=subprocess.STDOUT)
        #retcode = subprocess.check_call(*args, **kwargs) # Creates infinite loop, known issue: https://github.com/python/cpython/issues/87512
    except CalledProcessError as e: 
        #print("ERROR: " + e.output)
        return False
    except subprocess.TimeoutExpired as e: 
        #print("Timeout Error: " + str(e.args[0])) # e.g. Defaulting to user installation because normal site-packages is not writeable
        return False
    except Exception as e: 
        #print(str(e))
        return False
    except: print("unknown error") 
    print("end")
    return True

    