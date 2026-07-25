# HepMC3 event format and Rust extraction contract

QuarkSim's PYTHIA 8 backend writes HepMC3 ASCII v3 with `HepMC3::WriterAscii` in
`physics-engine/src/pythia_dis_generator.cpp::run_generator`. The installed and
observed writer version is HepMC3 3.3.0 (`HepMC::Version 3.03.00`). The
authoritative Rust reader for this dialect is `src/physics/hepmc3.rs`.

## Observed record grammar

Each event begins with:

```text
E event_number declared_vertex_count declared_particle_count [@ x y z t]
U momentum_unit length_unit
W weight_1 [weight_2 ...]
```

The generated files use `U GEV MM`. All weight values are retained as `f64` in
`HepMcEvent::weights`; the reader does not silently select a nominal weight.

The particle record written by HepMC3 3.3.0 is exactly:

```text
P particle_id parent_object pdg_id px py pz E generated_mass status
```

`parent_object` is not the PDG ID. It has three forms:

- `0`: no production vertex (for example, an incoming beam);
- a negative number: the ID of an explicit `V` record; or
- a positive number: a parent particle ID that compactly represents an
  implicit one-incoming-particle vertex.

The previous GUI parser interpreted `parent_object` as the PDG ID and shifted
all later columns. It has been removed. `HepMcParticle::production_reference`
preserves the raw field, while `production_vertex_id`, `end_vertex_id`,
`parent_particle_ids`, and `child_particle_ids` expose the reconstructed graph.
Implicit negative vertex IDs are reconstructed with the same gap-order rule as
HepMC3 3.3.0's `ReaderAscii`.

Explicit vertices use:

```text
V vertex_id status [incoming_particle_id,...] [@ x y z t]
```

`HepMcVertex` records whether a vertex was explicit or reconstructed, its
incoming and outgoing particle IDs, optional position, and source line when an
explicit record exists. Declared particle and vertex counts are checked.

Attributes use:

```text
A owner_id name serialized_value
```

All event attributes are retained as `HepMcAttribute`, including particle and
vertex attributes such as PYTHIA color-flow tags. The following owner-0
attributes receive typed projections on `HepMcEvent`:

- `GenPdfInfo`;
- `event_scale`;
- `alphaQCD`;
- `alphaQED`; and
- `signal_process_id`.

Unknown attributes remain available through their raw owner, name, value, and
source line.

## `GenPdfInfo`

HepMC3 3.3.0 serializes nine fields:

```text
GenPdfInfo parton_id_1 parton_id_2 x1 x2 scale xf1 xf2 pdf_id_1 pdf_id_2
```

They map directly to `HepMcPdfInfo`. The observed electron-proton records put
the electron-side incoming ID and momentum fraction first and the proton-side
parton second. Any future trailing fields are preserved in
`additional_fields`. `event_scale` is independently retained as an optional
event attribute; QuarkSim does not claim that it is separately both the
factorization and renormalization scale.

Hard incoming flavor and nominal `xf` values are generator truth needed for
provenance and a future reweighting study. They are not detector-observable
quantities and must not be exposed as default neural-inference input features.

## Event fields versus run provenance

`HepMcEvent` contains serialized event facts: event number, units, all weights,
typed and raw attributes, particles, vertices, graph connectivity, and source
line context. It does not copy run configuration into every event.

`HepMcRunProvenance::load(run_directory)` separately merges the associated
`config.json` and `metadata.json`. It retains PDF set/member, configured and
actual seed separately, beam energies, process, shower/hadronization switches,
cuts, event counts, available generator/library versions, Git information, and
the source paths. Missing values remain `None`. In current real runs beam PDG
IDs and Git dirty state are absent from JSON; beam IDs can be populated from an
observed event with `enrich_beam_ids_from_event`, while absent Git/APFEL data
remain absent.

## Streaming API

```rust
use quark_sim::physics::HepMcReader;

let mut reader = HepMcReader::open("outputs/dis_run/example/events.hepmc3")?;
while let Some(event) = reader.next_event()? {
    // Process or compact one event, then release it.
}
```

`HepMcReader<R>` accepts any `BufRead`, also implements `Iterator<Item =
Result<HepMcEvent, HepMcError>>`, and buffers only the current event plus one
pending event-header line. Parse and I/O errors carry line number and, when
known, event number. Malformed mandatory records return an error rather than
using zero defaults or panicking.

The GUI uses `HepMcReader::open` and converts each authoritative event to its
display projection. The current viewer still retains all projected events for
interactive navigation; scientific extraction code need not do so.

## Supported scope and limitations

The reader deliberately supports the ASCII v3 dialect emitted by this
repository's HepMC3 3.3.0/PYTHIA 8 converter. It does not currently support:

- HepMC2 ASCII, ROOT trees, protobuf, compressed input, or other historical
  dialects;
- general run-info weight names, tools, or arbitrary run attributes embedded
  before the event list (QuarkSim run provenance comes from JSON);
- semantic decoding of attributes other than the typed owner-0 fields above;
- unescaping every general HepMC string escape sequence; or
- unknown non-attribute record types inside an event.

Unsupported structural records are rejected clearly. Valid optional `A`
attributes are tolerated and preserved. The real-format regression fixture at
`tests/fixtures/hepmc3_real_minimal.hepmc3` contains two complete events copied
from QuarkSim run `dis_run_20260717_141023` (event numbers 225 and 2743), with
only the surrounding file reduced.

## Status conventions used by the viewer

- status `4`: beam particles;
- status `1`: stable final-state particles;
- statuses `2`: decayed/intermediate particles; and
- statuses `21`-`29` and other PYTHIA codes: hard-process/documentation or
  shower-history particles.

The scattered electron selector follows descendants of the status-4 PDG 11
beam through reconstructed graph links and falls back to a stable PDG 11 only
when ancestry is unavailable.
