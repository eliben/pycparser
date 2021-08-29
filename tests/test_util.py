import platform

def cpp_supported():
    return platform.system() == 'Linux' or platform.system() == 'Darwin'

def cpp_path():
    if platform.system() == 'Darwin':
        return 'gcc'
    return 'cpp'

def cpp_args(args=[]):
    if isinstance(args, str):
        args = [args]
    if platform.system() == 'Darwin':
        return ['-E'] + args
    return args
