extern crate parton_sbi as parton_sbi_real;

mod structure_function_provider {
    pub use parton_sbi_real::physics::structure_function_provider::*;
}

#[path = "../src/physics/structure_function_validation.rs"]
pub mod structure_function_validation;

mod physics {
    pub use parton_sbi_real::physics::{
        PerturbativeOrder, StructureFunctionBackend, StructureFunctionMetadata,
        StructureFunctionProvider, StructureFunctionProviderError, StructureFunctionRequest,
        StructureFunctionResult,
    };

    pub use crate::structure_function_validation;
}

#[path = "../src/structure_function_cli.rs"]
#[allow(dead_code)]
mod structure_function_cli;

#[path = "../src/validation_artifacts.rs"]
mod validation_artifacts;

#[test]
fn harness_compiles_all_new_modules() {
    assert_eq!(
        physics::structure_function_validation::VALIDATION_POINT_COUNT,
        20
    );
}
