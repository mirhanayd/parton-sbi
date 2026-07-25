# Historical configuration note

This filename is retained for compatibility with existing repository links, but the project does not provide a validated “production” physics configuration.

The active demonstration currently uses:

- 15,000 randomly generated training samples over `r = 0.05..3.0`;
- 5,000 full-batch epochs;
- AdamW with learning rate `0.01` and weight decay `0.01`;
- a `3 -> 256 -> 128 -> 64 -> 1` ReLU network;
- 30 static visualization electrons over impact parameters `-2.5..+2.5`.

These defaults are defined in `src/main.rs`, `src/model.rs`, `src/training.rs`, and `src/scattering.rs`. See `README.md` for commands, session behavior, outputs, and the full scientific-limitations statement.

The model approximates an analytic Cornell-potential function and feeds an ad hoc 2D trajectory visualization. It is not a real DIS event generator, is not research/publication quality, and has no accuracy or runtime guarantee.
