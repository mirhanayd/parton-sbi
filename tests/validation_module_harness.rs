extern crate quark_sim as quark_sim_real;

mod physics {
    pub mod structure_function_provider {
        pub use quark_sim_real::physics::structure_function_provider::*;
    }

    pub use quark_sim_real::physics::{
        PerturbativeOrder, StructureFunctionBackend, StructureFunctionMetadata,
        StructureFunctionProvider, StructureFunctionProviderError, StructureFunctionRequest,
        StructureFunctionResult,
    };

    #[path = "/mnt/c/Users/mirha/OneDrive/Belgeler/GitHub/neuronswq/quark_sim/src/physics/structure_function_validation.rs"]
    pub mod structure_function_validation;
}

#[path = "/mnt/c/Users/mirha/OneDrive/Belgeler/GitHub/neuronswq/quark_sim/src/structure_function_cli.rs"]
mod structure_function_cli;

#[path = "/mnt/c/Users/mirha/OneDrive/Belgeler/GitHub/neuronswq/quark_sim/src/validation_artifacts.rs"]
mod validation_artifacts;

#[test]
fn harness_compiles_all_new_modules() {
    assert_eq!(
        physics::structure_function_validation::VALIDATION_POINT_COUNT,
        20
    );
}
