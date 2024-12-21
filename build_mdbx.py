from pathlib import Path
import tempfile
import subprocess
import os
import sys
import multiprocessing
import shutil
import platform

SO_FILE = {
    "linux": "libmdbx.so",
    "linux2": "libmdbx.so",
    "darwin": "libmdbx.dylib",
    "win32": "libmdbx.dll",
}.get(sys.platform, "libmdbx.so")

def ensure_dependency():
    subprocess.check_call(["cmake", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if sys.platform == "win32" or sys.platform == "darwin":
        subprocess.check_call(["ninja", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def build(setup_kws: dict):
    ensure_dependency()
    debug = "DEBUG" in os.environ
    pwd = Path(__file__).parent.resolve()
    out_lib = pwd / "mdbx" / "lib"
    libmdbx_source = pwd / "libmdbx"
    
    tmpdir = None
    if debug:
        tmpdir = pwd / "build_libmdbx"
        if tmpdir.exists():
            shutil.rmtree(tmpdir)
        os.makedirs(tmpdir, exist_ok=True)
        tmpdir_path = tmpdir
    else:
        tmpdir = tempfile.TemporaryDirectory()
        tmpdir_path = Path(tmpdir.name)
    
    if debug:
        build_type = ["-DCMAKE_BUILD_TYPE=Debug"]
    else:
        build_type = ["-DCMAKE_BUILD_TYPE=Release"]
    
    cmake_gen = ["cmake"]
    
    if sys.platform == "darwin":
        cmake_gen += ["-G", "Ninja"]
        
    if sys.platform == "win32":
        plat = 'Win32' if platform.architecture()[0] == '32bit' else 'x64'
        cmake_gen += [
            "-G", "Visual Studio 16 2019",
            "-A", plat
        ]
        
    cmake_gen += [
        "-S", str(libmdbx_source.absolute()), "-B", str(tmpdir_path.absolute())
    ]
    cmake_gen += build_type
    subprocess.check_call(
        cmake_gen,
        cwd=tmpdir_path
    )
    threads = multiprocessing.cpu_count()
    if "THREADS" in os.environ:
        threads = int(os.environ["THREADS"])
    
    if out_lib.exists():
        shutil.rmtree(out_lib)
    os.makedirs(out_lib, exist_ok=True)
    shutil.copy(libmdbx_source / "LICENSE", out_lib)

    if sys.platform != "win32":
        subprocess.check_call(
            ["cmake", "--build", str(tmpdir_path.absolute()), "-j", str(threads)],
            cwd=tmpdir_path
        )
        shutil.copy(tmpdir_path / SO_FILE, out_lib)
    else:
        plat = 'Win32' if platform.architecture()[0] == '32bit' else 'x64'
        conf = 'Debug' if debug else 'Release'
        subprocess.check_call(
            ["msbuild", "libmdbx.sln", f"-maxcpucount:{threads}", f"-p:Platform={plat}", f'-p:Configuration={conf}'],
            cwd=tmpdir_path
        )
        shutil.copy(tmpdir_path / conf / SO_FILE, out_lib)
    
if __name__ == "__main__":
    build({})