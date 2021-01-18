#!/usr/bin/env python3

import argparse
import collections
import enum
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys

class ExitCode(enum.IntEnum):
    SUCCESS = 0 # 0 is automatically returned on success
    FAILURE = 1 # 1 is automatically returned on exception
    BAD_CONFIG = 2
    CHECKIN_ERROR = 3
    CHECKOUT_ERROR = 4

def printerr(s):
    print(s, file=sys.stderr)

if "linux" in platform.system().lower():
    PLATFORM = "linux"
elif "windows" in platform.system().lower():
    PLATFORM = "windows"
else:
    printerr(f"Error: Unsupported OS: {platform.system()}")

# The items in the config
CONFIG_ITEMS = {
    "project_name":   { "required": True },
    "repo_path":      { "required": False, "default": "." },
    "vivado_path":    { "required": True },
    "vivado_version": { "required": True },
    "workspace_path": { "required": False, "default": "{repo_path}/sdk" },
    "xpr_path":       { "required": False, "default": "proj/{project_name}.xpr" },
}

# The encoding for subprocess communication.
DEFAULT_ENCODING = "utf-8"

# The configuration base filename.
CONFIG_FILENAME = "vivado-scripts.json"

def read_config():
    config = {}
    def load_file(*paths):
        path = os.path.join(*paths)
        if os.path.isfile(path):
            try:
                with open(path) as f:
                    config.update(json.load(f))
            except Exception as e:
                printerr("Error: could not load config: {e}")
                sys.exit(ExitCode.BAD_CONFIG)
    if PLATFORM == "linux":
        if "XDG_CONFIG_HOME" in os.environ:
            xdg_config_home = os.environ["XDG_CONFIG_HOME"]
        else:
            xdg_config_home = os.path.join(os.environ["HOME"], ".config")
        load_file(xdg_config_home, "vivado-scripts", CONFIG_FILENAME)
        load_file(xdg_config_home, CONFIG_FILENAME)
        load_file(os.environ["HOME"], ".vivado-scripts", CONFIG_FILENAME)
        load_file(os.environ["HOME"], "." + CONFIG_FILENAME)
        load_file(CONFIG_FILENAME)
    elif PLATFORM == "windows":
        load_file(os.environ["APPDATA"], "vivado-scripts", "vivado-scripts", "config", FILENAME)
        load_file(CONFIG_FILENAME)
    # Check that the config defined everything, and if not, fill in default
    # values
    for k, v in CONFIG_ITEMS.items():
        if k not in config:
            if v["required"]:
                printerr(f"Error: Missing configuration key: {k}")
                sys.exit(ExitCode.BAD_CONFIG)
            else:
                config[k] = v["default"]
    c = {}
    for k, v in config.items():
        c[k] = v.format(**config) if isinstance(v, str) else v
    return c

def copy_dir_contents(src, dest, exit_code=ExitCode.FAILURE):
    """
    Copy the contents of the source directory to the destination directory.
    """
    # Make sure the source directory exists
    if not os.path.isdir(src):
        printerr(f"Error: {src} must be a directory")
        sys.exit(exit_code)
    # Create the destination directory if it does not exist
    pathlib.Path(dest).mkdir(parents=True, exist_ok=True)
    # Copy the files
    for f in sorted(os.listdir(src)):
        s = os.path.join(src, f)
        d = os.path.join(dest, f)
        if os.path.isdir(s):
            # Delete the target directory before the copy if it already exists
            if os.path.isdir(d):
                shutil.rmtree(d)
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)

def run_cmd(cmd, encoding=DEFAULT_ENCODING):
    """
    Run a command as a subprocess.

    # Arguments

    * `cmd` (list<str>): The command to run.
    * `encoding` (str): The encoding to use for communicating with the
        subprocess.

    # Returns

    A named tuple with the following fields:
        - returncode: The returned value from the subproccess.
        - stderr: The stderr output from the subprocess.
        - stdout: The stdout output from the subprocess.
    """
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return collections.namedtuple("CmdResult",
        ["returncode", "stderr", "stdout"])(
            p.returncode,
            p.stderr.decode(encoding).strip(),
            p.stdout.decode(encoding).strip())

def default_handler(args):
    """
    The default argument handler. This prints some information about the
    program.
    """
    c = read_config()
    for k in sorted(c):
        print(f"{k}: {c[k]}")

def vivado_tcl(script_name, exit_code):
    """
    A generic function for performing Vivado Tcl operations.

    # Arguments

    * script_name (str): The name of the Tcl script within the script directory
        to run.
    * exit_code (ExitCode): The exit code to use if something fails.
    """
    script_path = os.path.join(args.script_dir, script_name).replace('\\', '/')
    r = None
    e = None
    try:
        cmd = [
            args.vivado_path,
            "-mode", "batch",
            "-source", script_path,
            "-tclargs",
            "-x", args.xpr_path,
            "-r", args.repo_path,
            "-v", args.vivado_version,
            "-w", args.workspace_path,
        ]
        r = run_cmd(cmd)
    except Exception as ex:
        e = ex
    if (r is not None and r.returncode) or e is not None:
        if e is not None:
            printerr(f"Exception: {e}")
        if r is not None:
            printerr(f"Error (stderr): {r.stderr}")
            printerr(f"Error (stdout): {r.stdout}")
        sys.exit(exit_code)

def checkin_handler(args):
    """
    Perform a check in using the parsed command line arguments.
    """
    vivado_tcl("vivado-checkin.tcl", ExitCode.CHECKIN_ERROR)
    # Handle the SDK project
    if args.sdk:
        copy_dir_contents(
                os.path.join(os.path.dirname(args.xpr_path),
                    f"{args.project_name}.sdk"),
                os.path.join(args.repo_path, "sdk"),
                exit_code=ExitCode.CHECKIN_ERROR)

def checkout_handler(args):
    """
    Perform a checkout using the parsed command line arguments.
    """
    vivado_tcl("vivado-checkout.tcl", ExitCode.CHECKOUT_ERROR)
    # Handle the SDK project
    if args.sdk:
        copy_dir_contents(
                os.path.join(args.repo_path, "sdk"),
                os.path.join(os.path.dirname(args.xpr_path),
                    f"{args.project_name}.sdk"),
                exit_code=ExitCode.CHECKOUT_ERROR)

def parse_args():
    """
    Parses the command line arguments.

    # Returns

    A named tuple with the following fields:
        - func (Fn<Args>): The function to run with the args for a supplied
          subcommand.
        - repo_path (str): The path to the repo to generate the project.
        - script_dir (str): The path to the directory which contains the Tcl
          scripts.
        - vivado_path (str): Path to the Vivado binary
        - vivado_version (str): The Vivado binary version
        - xpr_path (str): The path to the XPR file to use.
    """
    # Read defaults
    c = read_config()
    PROJECT_NAME = c["project_name"]
    DEFAULT_REPO_PATH = c["repo_path"]
    DEFAULT_VIVADO_PATH = c["vivado_path"]
    DEFAULT_VIVADO_VERSION = c["vivado_version"]
    DEFAULT_WORKSPACE_PATH = c["workspace_path"]
    DEFAULT_XPR_PATH = c["xpr_path"]
    # Create a parser
    p = argparse.ArgumentParser(description="Handles Vivado project git repository operations")
    # Set defaults
    p.set_defaults(vivado_path=DEFAULT_VIVADO_PATH)
    p.set_defaults(repo_path=DEFAULT_REPO_PATH)
    p.set_defaults(workspace_path=DEFAULT_WORKSPACE_PATH)
    p.set_defaults(xpr_path=DEFAULT_XPR_PATH)
    p.set_defaults(vivado_version=DEFAULT_VIVADO_VERSION)
    p.set_defaults(func=default_handler)
    sp = p.add_subparsers()
    # Checkin arguments
    pin = sp.add_parser("checkin", aliases=["ci"], help="Checks XPR into repo")
    pin.add_argument("-b", "--vivado-path",    type=str, default=DEFAULT_VIVADO_PATH,    help="The path to the Vivado binary")
    pin.add_argument("-r", "--repo-path",      type=str, default=DEFAULT_REPO_PATH,      help="The path to the repo to use")
    pin.add_argument("-w", "--workspace-path", type=str, default=DEFAULT_WORKSPACE_PATH, help="The path to the SDK workspace to use")
    pin.add_argument("-x", "--xpr-path",       type=str, default=DEFAULT_XPR_PATH,       help="The path to the XPR file to use")
    pin.add_argument("-v", "--vivado-version", type=str, default=DEFAULT_VIVADO_VERSION, help="The Vivado version to use")
    pin.add_argument(      "--sdk",                      action='store_true',            help="Copy the SDK files into the repository")
    pin.set_defaults(func=checkin_handler)
    # Checkout arguments
    pout = sp.add_parser("checkout", aliases=["co"], help="Checks XPR out from repo")
    pout.add_argument("-b", "--vivado-path",    type=str, default=DEFAULT_VIVADO_PATH,    help="The path to the Vivado binary")
    pout.add_argument("-r", "--repo-path",      type=str, default=DEFAULT_REPO_PATH,      help="The path to the repo to use")
    pout.add_argument("-w", "--workspace-path", type=str, default=DEFAULT_WORKSPACE_PATH, help="The path to the SDK workspace to use")
    pout.add_argument("-x", "--xpr-path",       type=str, default=DEFAULT_XPR_PATH,       help="The path to the XPR file to use")
    pout.add_argument("-v", "--vivado-version", type=str, default=DEFAULT_VIVADO_VERSION, help="The Vivado version to use")
    pout.add_argument(      "--sdk",                      action='store_true',            help="Copy the SDK files into the project")
    pout.set_defaults(func=checkout_handler)
    # Parse the arguments
    args = p.parse_args()
    return collections.namedtuple("Args",
        ["func", "project_name", "repo_path", "script_dir", "vivado_path",
                "vivado_version", "workspace_path", "xpr_path", "sdk"])(
            args.func,
            PROJECT_NAME,
            os.path.abspath(args.repo_path.replace("\\", "/")),
            os.path.dirname(os.path.abspath(__file__)),
            args.vivado_path.replace("\\", "/"),
            args.vivado_version,
            args.workspace_path,
            os.path.abspath(args.xpr_path.replace("\\", "/")),
            args.sdk,
        )

if __name__ == "__main__":
    args = parse_args()
    args.func(args)
