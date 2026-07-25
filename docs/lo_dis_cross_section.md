# Leading-order inclusive electron-proton DIS

This phase evaluates the inclusive neutral-current process

```text
e⁻ + p -> e⁻ + X
```

in the leading-order, single-photon electromagnetic approximation, using real
LHAPDF parton densities. It builds on the tested massive-beam kinematics core.

## Inputs and beam relation

Inputs use GeV-based natural units and must satisfy

```text
0 < x < 1
Q² > 0.
```

For on-shell electron and proton beams, the existing collider helpers calculate
`s=(P+k)²`. The inelasticity used by the cross-section API is then

```text
y = Q² / [x (s - m_p² - m_e²)].
```

This retains both beam masses. A point is rejected unless `0 < y < 1`.

## PDF and structure-function convention

LHAPDF returns `x f_i(x,Q²)`. The fields displayed by the CLI and stored in
`PartonDensities` therefore already contain one factor of `x`.

At leading electromagnetic order,

```text
F₂ = (4/9) [xu + xū + xc + xc̄]
   + (1/9) [xd + xd̄ + xs + xs̄ + xb + xb̄].
```

The gluon density is displayed but does not enter this LO formula. Flavor
availability and heavy-quark threshold behavior come from the chosen PDF set;
the application does not implement its own interpolation or threshold model.

This phase explicitly assumes

```text
F_L = 0
xF₃ = 0.
```

## Differential cross section

Define

```text
Y₊ = 1 + (1-y)².
```

The implemented approximation is

```text
d²σ/(dx dQ²) = [2 π α² / (x (Q²)²)] Y₊ F₂.
```

Here `(Q²)²` is `Q⁴`; it is not the fourth power of the numeric `Q²` input.
The default fixed electromagnetic coupling is

```text
α(0) = 1 / 137.035999084.
```

It is supplied through an interface so a future running-coupling implementation
can replace it without changing the cross-section formula.

### Units

Because the result is differential in `Q²`, its natural-unit dimension is
`GeV⁻⁴`. The prompt's shorthand `GeV⁻²` for this differential quantity would be
dimensionally incorrect. The conversion constant is stored once in the
cross-section module:

```text
1 GeV⁻² = 389379372.1 pb.
```

Therefore the same numeric conversion maps

```text
GeV⁻⁴ -> pb/GeV²
```

for `d²σ/(dx dQ²)`. Both values are printed with their full units.

## CLI

After installing and activating LHAPDF:

```bash
source scripts/lhapdf_env.sh
cargo run --release -- dis-cross-section \
  --x 0.01 \
  --q2 100.0 \
  --electron-energy 27.5 \
  --proton-energy 920.0 \
  --pdf-set CT18LO \
  --pdf-member 0
```

Help is side-effect free:

```bash
cargo run --release -- dis-cross-section --help
```

The result identifies the set/member and prints `x`, `Q²`, `s`, `y`, each       
LHAPDF `x f_i`, `F₂`, the assumed `F_L` and `xF₃`, and the differential cross   
section in `GeV⁻⁴` and `pb/GeV²`.

With LHAPDF 6.5.6 and the pinned `CT18LO/0` member installed by the setup
script, the numerical part of the example output is:

```text
Leading-order electromagnetic neutral-current e⁻p DIS
PDF set/member: CT18LO/0
x      = 1.000000000000e-2
Q²     = 1.000000000000e2 GeV²
s      = 1.012008540311e5 GeV²
y      = 9.881425495213e-2
Y₊     = 1.812135747077e0
LHAPDF x f(x,Q²):
  g    = 7.048573373781e0
  u    = 6.972430770624e-1
  ū    = 4.983104262758e-1
  d    = 6.374047349488e-1
  d̄    = 5.394405563481e-1
  s    = 8.543723253063e-2
  s̄    = 8.543723253063e-2
  c    = 1.932392174033e-1
  c̄    = 1.932392174033e-1
  b    = 6.998711215288e-2
  b̄    = 6.998711215288e-2
F₂     = 8.684246370271e-1
F_L    = 0.000000000000e0 (LO assumption)
xF₃    = 0.000000000000e0 (photon-exchange assumption)
α      = 7.297352569284e-3 (fixed α(0))
d²σ/(dx dQ²) = 5.265424511647e-6 GeV⁻⁴
d²σ/(dx dQ²) = 2.050247690185e3 pb/GeV²
```

LHAPDF also prints its own load and citation messages around this block. The
external regression test pins the set metadata and representative densities so
an unintended data-grid change is reported rather than silently accepted.

## Current scientific limitations

- This is a fixed-α, leading-order photon-exchange approximation, not an NLO or
  NNLO prediction.
- It omits `Z` exchange, photon-Z interference, parity-violating `xF₃`, a
  nonzero longitudinal structure function, electroweak running, and lepton-mass
  terms in the hard-scattering formula.
- It provides no PDF uncertainties, scale variations, QED/electroweak radiative
  corrections, target-mass or higher-twist corrections, heavy-flavor scheme
  choice, nuclear effects, or resonance modeling.
- It computes an inclusive differential density at one `(x,Q²)` point. There is
  no phase-space integration, random event generation, parton shower,
  hadronization, detector simulation, or event record.
- Grid validity and flavor content are defined by the selected LHAPDF set. The
  calculation does not extrapolate points rejected by the wrapper.
- The legacy Cornell neural-network visualization remains independent and is not
  a PDF provider.

## References

- [PDG review of structure functions](https://pdg.lbl.gov/2024/reviews/rpp2024-rev-structure-functions.pdf)
- [PDG physical constants](https://pdg.lbl.gov/2024/reviews/constants_atomic_and_related.html)
- [Official LHAPDF API](https://www.lhapdf.org/classLHAPDF_1_1PDF.html)
