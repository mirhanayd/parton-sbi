# LHAPDF integration

The DIS cross-section command uses the official LHAPDF C++ library and an
installed proton PDF set. It does not interpolate PDF grids itself.

## Supported WSL setup

The supported development environment is WSL Ubuntu. Ubuntu 24.04 does not
currently provide an `lhapdf` or `liblhapdf-dev` candidate in its standard
repositories, so the project installs the official LHAPDF 6.5.6 release into a
user-owned prefix and does not require `sudo`.

From the `quark_sim` directory:

```bash
bash scripts/setup_lhapdf_wsl.sh
source scripts/lhapdf_env.sh
lhapdf-config --version
pkg-config --modversion lhapdf
```

The setup script is idempotent where practical. It checks the required compiler
and download tools, builds LHAPDF only when the requested version is absent,
installs the verified `CT18LO` directory from the official CERN set archive, and
prints the active prefix, data directory, version, selected member, and set
metadata. The
prefix can be overridden before running it:

```bash
LHAPDF_PREFIX=/some/user/writable/path bash scripts/setup_lhapdf_wsl.sh
LHAPDF_PREFIX=/some/user/writable/path source scripts/lhapdf_env.sh
```

`scripts/lhapdf_env.sh` must be sourced in each new shell before Cargo builds or
runs the executable. It configures `PATH`, `PKG_CONFIG_PATH`,
`LD_LIBRARY_PATH`, and `LHAPDF_DATA_PATH` without replacing existing entries.

The selected set is `CT18LO`, member 0. It is a leading-order proton set with one
member, so it matches the accuracy claimed by this phase. The CLI still requires
`--pdf-set` explicitly; it does not silently select a set.

## Binding choice

The Rust layer uses `managed-lhapdf` 0.4.2, pinned in `Cargo.toml`, rather than a
new project-specific C or C++ bridge. This maintained binding already wraps the
LHAPDF C++ API through `cxx` and verifies the native library through
`pkg-config`. Its default `managed` feature is disabled: dependency and PDF-set
installation remain the explicit responsibility of the WSL setup script, and
the application does not download data or mutate `LHAPDF_DATA_PATH` at runtime.

This was preferred over:

- a local `cxx` bridge, which would duplicate the maintained binding;
- a C ABI shim, which would add manual ownership, exception, and `unsafe` FFI
  code without improving the physics interface.

LHAPDF 6.5.x is required because the official project documents that series as
fully thread-safe. The application itself keeps each provider owned by its
caller and does not introduce global mutable PDF state.

`managed-lhapdf` and LHAPDF use GPL-family licensing. This must be considered
before distributing binaries; adding the dependency does not by itself choose a
license for the rest of this repository.

## Rust-facing convention

`PdfProvider` decouples physics calculations from the native backend:

```rust,ignore
pub trait PdfProvider {
    fn parton_densities(
        &self,
        x: f64,
        q2: f64,
    ) -> Result<PartonDensities, PdfError>;
}
```

`LhapdfProvider` is the production implementation. Deterministic unit tests use
mock implementations of the same trait.

Every flavor field in `PartonDensities` means

```text
x f_i(x, Q²),
```

not `f_i(x,Q²)`. This is the native `xfxQ2` convention. In particular, the
structure-function code must not multiply these values by `x` again. PDG flavor
IDs are used internally: `g=21`, `d=1`, `u=2`, `s=3`, `c=4`, `b=5`, with
negative IDs for antiquarks. A flavor not supplied by the selected set is
reported as zero. Finite negative grid values are retained because some valid
PDF schemes can produce them in limited regions.

The wrapper validates finite inputs, `0 < x < 1`, `Q² > 0`, set/member
availability, and known grid bounds before calling LHAPDF. It returns typed
errors for unavailable sets or members, malformed metadata, out-of-grid points,
and non-finite backend results.

## External integration tests

Pure unit tests never query the LHAPDF backend or require a PDF data grid.
However, `managed-lhapdf` is an unconditional native dependency, so every Cargo
build still needs the LHAPDF headers and shared library activated in the shell.
Tests that actually load a set are clearly ignored during an ordinary
`cargo test` and are run deliberately after sourcing the environment:

```bash
source scripts/lhapdf_env.sh
cargo test --test lhapdf_integration -- --ignored --nocapture
```

These tests require LHAPDF 6.5.6 plus the pinned `CT18LO` member 0. Missing native
software or data is a visible test failure, not a silent skip.

## References

- [Official LHAPDF installation guide](https://www.lhapdf.org/install.html)
- [Official LHAPDF PDF API (`xfxQ2`)](https://www.lhapdf.org/classLHAPDF_1_1PDF.html)
- [Official LHAPDF set catalogue](https://www.lhapdf.org/pdfsets.html)
