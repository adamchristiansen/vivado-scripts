# Vivado Scripts

## Introduction

> This repository is a fork of
[Digilent/digilent-vivado-scripts](https://github.com/Digilent/digilent-vivado-scripts),
however, it does not try to maintain compatibility. If you already use the
Digilent scripts, then switching to this repository will require a small number
of changes.

This is a collection of scripts for maintaining a Xilinx Vivado and SDK
projects as a minimal git repository. These scripts have been tested with
Vivado 2018.2 and 2019.1 and they may or may not work with newer or older
versions of Vivado.

**Requirements**

- A Xilinx Vivado install
- Python 3.6.3 or newer

## Python Script

The provided Python script, `git-vivado.py`, is provided as a clean front-end
to the Tcl scripts which do the heavy lifting. Here is how it can be run:

- With no arguments the configuration that will be used is printed.
- `checkin` creates the repository to track with git from the XPR path. It
  can accept the following options:
    - `-b` is the path to the Vivado binary to use
    - `-r` is the path to the repository root
    - `-w` is the path to the SDK workspace
    - `-x` is the path to the XPR file to use
    - `-v` is the version number of the Vivado binary
    - `-n` disables hardware handoff
    - `-h` shows help information for this subcommand
  Note that sources do not need to be added local to a Vivado project in order
  to be detected by this script.
- `checkout` creates the project using the XPR path from the repository. It
  can accept the following options:
    - `-b` is the path to the Vivado binary to use
    - `-r` is the path to the repository root
    - `-w` is the path to the SDK workspace
    - `-x` is the path to the XPR file to use
    - `-v` is the version number of the Vivado binary
    - `-h` shows help information for this subcommand
- `release` creates a release archive from the the project using the XPR path.
  It can accept the following options:
    - `-b` is the path to the Vivado binary to use
    - `-r` is the path to the repository root
    - `-w` is the path to the SDK workspace
    - `-x` is the path to the XPR file to use
    - `-v` is the version number of the Vivado binary
    - `-z` is the path to the zip file to create
    - `-h` shows help information for this subcommand

## Configuration File

Multiple configuration files can be specified, and they are read in a specific
order, each one overwriting the last.

On Linux, the order is:

- `$XDG_CONFIG_HOME/vivado-scripts/vivado-scripts.json`
- `$XDG_CONFIG_HOME/vivado-scripts.json`
- `$HOME/.vivado-scripts/vivado-scripts.json`
- `$HOME/.vivado-scripts.json`
- `./vivado-scripts.json`

If `$XDG_CONFIG_HOME` is not defined, then `$HOME/.config` will be used.

On Windows, the order is:

- `%APPDATA/vivado-scripts/vivado-scripts/config/vivado-scripts.json`
- `./vivado-scripts.json`

The configuration file may contain the following:

```json
{
  "no_hdf": false,
  "project_name": "Project",
  "repo_path": ".",
  "vivado_path": "/opt/Xilinx/Vivado/{vivado_version}/bin/vivado",
  "vivado_version": "2019.1",
  "workspace_path": "{repo_path}/sdk",
  "xpr_path": "proj/{project_name}.xpr",
  "zip_path": "{repo_path}/release/{project_name}.zip"
}
```

The above is for Linux. On Windows it will look more like:

```json
{
  "no_hdf": false,
  "project_name": "Project",
  "project_name": "Project",
  "repo_path": ".",
  "vivado_path": "C:/Xilinx/Vivado/{vivado_version}/bin/vivado",
  "vivado_version": "2019.1",
  "workspace_path": "{repo_path}/sdk",
  "xpr_path": "proj/{project_name}.xpr",
  "zip_path": "{repo_path}/release/{project_name}.zip"
}
```

The configs support interpolation of other parameters using the `{...}` syntax.
Note that nested interpolation is undefined behaviour. Suppose `xpr_path`
interpolates `project_name` (like the above example), and `project_name`
interpolates `vivado_version`, this may or may not work depending on the order
that the parameters are interpolated. Therefore, nested interpolation should
not be relied on.

It is recommended to have at least the `vivado_path` and `vivado_version`
stored external to the project. For most projects, it is likely that the
project local `vivado-scripts.json` only needs to define `project_name`,
which should be the same as the project name selected in Vivado.

## Repository Structure

In order to ensure that any changes to this repository do not break the
projects that use them, it is expected that this repository will be used as a
submodule of each project repository that is intended to use them.

The project structure is outlined below, relative to the repository root.

- `/vivado-scripts` contains the scripts described by this document.
- `/proj` contains a checked-out Vivado project.
- `/release` contains temporary files necessary to generate a release zip
  archive.
- `/repo` contains local IP, IP submodules, and cached generated sources.
- `/sdk` contains exported SDK sources.
- `/src` contains source files for the Vivado Project.
  - `/src/bd` contains a TCL script used to re-create a block design.
  - `/src/constraints` contains XDC constraint files.
  - `/src/hdl` contains Verilog and VHDL source files.
  - `/src/ip` contains XCI files describing IP to be instantiated in non-IPI
    projects.
  - `/src/others` contains all other required sources, such as memory
    initialization files.
- `/.gitignore` is a file describing which sources should be version
  controlled. An example is generated by the checkin process.
- `/.gitmodules` is a file describing submodules of the repository.
  Automatically maintained by the "git submodule" command.
- `/project_info.tcl` is a script generated by first-time checkin used to save
  and re-apply project settings like board/part values. This can be modified
  after initial creation to manually configure settings that are not initially
  supported. Note that this should be deleted and recreated when porting a
  project from one board to another.
- `/README.md` is a Markdown file describing the project and the process needed
  to use it, from downloading the release archive, to programming the FPGA.

## Workflows

### Creating a New Project

1.  Create a new Vivado project at an arbitrary location on your computer. When
    exporting to and launching SDK, make sure to use exported locations and
    workspaces that are not `Local to Project`.
2.  Create a repository on Github for your project. Use the naming convention
    `<board>-<variant_number>-<project name>` (for example: `Zybo-Z7-20-DMA`).
    Do not have Github create a gitignore file for you. Clone the repository.
3.  Add these scripts to the repository as a git submodule using
    ```sh
    git submodule add git@github.com:AdamChristiansen/vivado-scripts.git
    # or if you prefer HTTP over SSH
    git submodule add https://github.com/AdamChristiansen/vivado-scripts.git
    ```
4.  Add [configuration files](#configuration-files).
5.  Call
    ```sh
    python ./vivado-scripts/git-vivado.py checkin
    ```
    This command can be called from anywhere in your filesystem, with relative
    paths changed as required. This will also create a `.gitignore` file for
    the repository.
6.  If required, in Xilinx SDK, right click on your application project's `src`
    folder and select "Export". Use this to copy all of the sources from
    `<app>/src` to `<project_repo>/sdk/appsrc`.
7.  Create a `README.md` for the repo that specifies what the project is
    supposed to do and how to use a release archive for it.
8.  Add, commit, and push your changes.
9.  Create and upload a release ZIP to Github - see
    [Creating a Release Archive](#creating-a-release-archive) below.

### Retargeting an Existing Project to use these Scripts

1.  Clone (or pull) the Vivado project to be retargeted. Use its existing
    version control system to generate an XPR. Make sure to run
    ```sh
    git submodule init && git submodule update
    ```
    if it uses any submodules.
2.  Open the project in Vivado and make any changes necessary (perhaps
    upgrading IP). When exporting to and launching SDK, make sure to use
    exported locations and workspaces that are not `Local to Project`.
3.  Clone the project repository again in a different location. Remove all
    files from this directory.
4.  Add these scripts to the repository as a git submodule using
    ```sh
    git submodule add git@github.com:AdamChristiansen/vivado-scripts.git
    # or if you prefer HTTP over SSH
    git submodule add https://github.com/AdamChristiansen/vivado-scripts.git
    ```
5.  Add [configuration files](#configuration-files).
6.  Call
    ```sh
    python ./vivado-scripts/git-vivado.py checkin -x <path_to_XPR>
    ```
    This command can be called from anywhere in your filesystem, with relative
    paths changed as required. This will also create a `.gitignore` file for
    the repository.
7.  If required, in Xilinx SDK, right click on your application project's `src`
    folder and select "Export". Use this to copy all of the sources from
    `<app>/src` to `<project_repo>/sdk/appsrc`.
8.  Create a `README.md` for the repo that specifies what the project is
    supposed to do and how to use a release archive for it.
9.  Add, commit, and push your changes.
10. Create and upload a release ZIP to Github - see
    [Creating a Release Archive](#creating-a-release-archive) below.

### Making Changes to a Project that uses this Submodule

1.  Clone (or pull) the Vivado project to be changed. Get these scripts by
    running
    ```sh
    git submodule init && git submodule update
    ```
2.  Call
    ```sh
    python ./vivado-scripts/git-vivado.py checkout
    ```
    This command can be called from anywhere in your filesystem, with relative
    paths changed as required. This will also create a `.gitignore` file for
    the repository.
4.  Add a [`vivado.json` configuration file](#configuration-files) for the
    installed Vivado version.
3.  Run
    ```sh
    python ./vivado-scripts/git-vivado.py checkout
    ```
4.  Open the project in Vivado and make any changes necessary (perhaps
    upgrading IP or fixing a bug). When exporting to and launching SDK, make
    sure to use exported locations and workspaces that are not `Local to
    Project`.
5.  Call
    ```sh
    python ./vivado-scripts/git-vivado.py checkin -x <path_to_XPR>
    ```
    This command can be called from anywhere in your filesystem, with relative
    paths changed as required. This will also create a `.gitignore` file for
    the repository.
6.  If required, in Xilinx SDK, right click on your application project's `src`
    folder and select "Export". Use this to copy all of the sources from
    `<app>/src` to `<project_repo>/sdk/appsrc`.
7.  Make sure to update the repo's README as required.
8.  Add, commit, and push your changes.

## Known Issues

* For both releases and checked out repositories, SDK Application and BSP
  projects must be manually configured in order to add any additional libraries
  and compiler flags. This process is fairly error-prone.
* The process of creating a release archive currently must be done manually.
  This process can be automated further, but will require creation of an XSCT
  script to collect SDK application sources.
* There is some danger that modifications to Digilent's board files may break
  existing projects, it may be worth considering adding the
  [Digilent/vivado-boards](https://github.com/Digilent/vivado-boards)
  repository as a submodule to project repositories.
