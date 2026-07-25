# PYTHIA 8 DIS Event Generation

This document describes the physics settings, configuration options, and implementation details of the PYTHIA 8 event-generation backend for electron-proton Deep Inelastic Scattering (DIS).

## Configuration Schema

The backend uses a schema-v1 JSON file to parse setup configurations. Below is an example:

```json
{
  "schema_version": 1,
  "process": "neutral_current_dis",
  "electron_energy_gev": 27.5,
  "proton_energy_gev": 920.0,
  "q2_min_gev2": 10.0,
  "q2_max_gev2": 10000.0,
  "x_min": 0.0001,
  "x_max": 0.8,
  "y_min": 0.01,
  "y_max": 0.95,
  "number_of_events": 10000,
  "random_seed": 123456,
  "pdf_set": "CT18LO",
  "pdf_member": 0,
  "parton_shower": true,
  "hadronization": true
}
```

### Parameters

- `schema_version`: Must be exactly `1`.
- `process`: Must be `"neutral_current_dis"`.
- `electron_energy_gev`: Incoming electron beam energy in GeV.
- `proton_energy_gev`: Incoming proton beam energy in GeV.
- `q2_min_gev2`: Minimum virtuality $Q^2$ in $\text{GeV}^2$.
- `q2_max_gev2`: Maximum virtuality $Q^2$ in $\text{GeV}^2$ (default: `10000.0`).
- `x_min`: Minimum Bjorken $x$ fraction (default: `0.0001`).
- `x_max`: Maximum Bjorken $x$ fraction (default: `0.8`).
- `y_min`: Minimum inelasticity $y$ fraction (default: `0.01`).
- `y_max`: Maximum inelasticity $y$ fraction (default: `0.95`).
- `number_of_events`: The number of accepted events to generate.
- `random_seed`: The seed for the random number generator. If negative or omitted, a random seed is dynamically generated.
- `pdf_set`: Name of the LHAPDF 6 set.
- `pdf_member`: PDF member index (default: `0`).
- `parton_shower`: Switch to toggle Parton Shower (ISR/FSR) on/off (default: `true`).
- `hadronization`: Switch to toggle Hadronization on/off (default: `true`).

---

## Physics Process and Beams

- **Process Selection**: The Neutral Current (NC) DIS process is configured via the electroweak t-channel boson exchange:
  `WeakBosonExchange:ff2ff(t:gmZ) = on`
  This enables $\gamma^* / Z^0$ t-channel exchange between the lepton and a quark.
- **Beam Configuration**:
  - Beam A: Electron (PDG ID `11`), traveling along the $+z$ direction.
  - Beam B: Proton (PDG ID `2212`), traveling along the $-z$ direction.
  - Frame Type: `Beams:frameType = 2` is used for unequal beam energies.
- **Parton Shower and Hadronization Options**:
  - Turning `parton_shower` off disables Initial-State Radiation (`PartonLevel:ISR = off`), Final-State Radiation (`PartonLevel:FSR = off`), and Multi-Parton Interactions (`PartonLevel:MPI = off`).
  - Turning `hadronization` off disables hadronization and particle decays (`HadronLevel:all = off`).

---

## Kinematics Reconstruction and Observables

For each accepted event, the generator computes physical observables using two methods:
1. **True/Hard Process Kinematics**:
   Variables $Q^2$ and $x$ are extracted directly from PYTHIA's internal hard process block (`pythia.info.Q2()`, etc.).
2. **Reconstructed Kinematics (Electron Method)**:
   Variables are computed from the incoming and final-state scattered electron's four-vectors:
   - $q = k_{\text{beam}} - k'_{\text{final}}$
   - $Q^2_{\text{reco}} = -q^2$
   - $x_{\text{reco}} = \frac{Q^2_{\text{reco}}}{2 P_{\text{beam}} \cdot q}$
   - $y_{\text{reco}} = \frac{P_{\text{beam}} \cdot q}{P_{\text{beam}} \cdot k_{\text{beam}}}$
   - $W^2_{\text{reco}} = (P_{\text{beam}} + q)^2$

Both true and reconstructed variables, alongside their absolute mismatches (due to QED radiation or numerical precision), are saved in the output CSV file.

---

## Limitations

- **QED Radiative Corrections**: Only QED ISR/FSR radiation from partons/leptons implemented via the parton shower is included. Full electroweak NLO corrections or full QED radiative corrections require specialized generators (e.g. HERACLES/DJANGOH).
- **No Detector Effects**: The generated particles are at the generator level (stable final-state particles). They do not undergo detector tracking, energy smearing, or acceptance cuts.
- **Born-Level Hard Scattering**: The hard process is evaluated at the leading order (Born) level.
