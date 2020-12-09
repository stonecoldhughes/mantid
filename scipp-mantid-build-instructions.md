## Instructions for producing Mantid Workbench bundling scipp (OSX)

###
**Warning** At the time of writing these instructions cover the generation of an unofficial, unstable and unsupported package combining Mantid and Scipp

### Background

The combined Mantid-Scipp package serves two purposes.

1. For neutron scattering [scipp](https://scipp.github.io/) requires Mantid for some of it's base operations. While scipp provides conda packages for a range of platforms, the `mantid-framework` conda pacakge is linux only. The OSX and Windows curren work around (untested on Windows but will work in principle) is to piggy-back the distribution of the combined package on the Mantid Workbench installation. Currently at time of writing, this is the only commonly supported cross-platform distribution mechanism for Mantid. Scipp is relatively light-weight in terms of c++ dependencies all of which it can fetch via cmake external project at cmake/build time. 

2. Scipp is also exclusively meant to be used as a python package, and therfore can be considered within the Mantid project much like any other third-party such as numpy. Scipp also provides `to-from` converters between scipp objects (Dataset/DataArray etc and Mantid Workspaces) given compatibility between the two frameworks. At the time of writing this gives the possibility for full scipp use within the Mantid environment.


### Overall how this works

scipp is introduced as a cmake external project, and is downloaded, configured and built at cmake time (though this could be made mixed cmake-time/build-time). The configuration files can be used to select the SHA1 of scipp to use. Key Mantid cmake variables, such as the python executable are passed through to cmake. scipp is then "installed" into the Mantid build directory (bin). At packaging time, scipp is copied into the mantid site-packages. It's pretty much as simple as that.

### Commands Required

Essential steps are much like the following
```bash
conda deactivate # Ensure you are NOT using any conda environment
git checkout scipp_with_mantid
git pull origin master # (possibly have to resolve conficts here)
mkdir build
cd build
# download, configure, build, install scipp
cmake -G"Ninja" -DCMAKE_BUILD_TYPE=Release -DENABLE_CPACK=ON -DENABLE_WORKBENCH=OFF, -DENABLE_MANTIDPLOT=OFF -DPYTHON_EXECUTABLE=/usr/local/bin/python3.8 -DENABLE_SCIPP=ON ~/sources/mantid/
ninja Framework workbench
cpack .
```

## Installing and running

The resulting Drag and drop package can be distributed and installed into Applications in the usual manner.

Jupyter and other critical python dependencies need to be pip installed into the MantidWorkbench site-packages. Jupyter extensions need to be enabled at runtime and the correct jupyter instance with python kernel (all from MantidWorkbench.app) need to be run.

```bash
install_jupyter.sh # on owncloud
run.sh # on owncloud
```
