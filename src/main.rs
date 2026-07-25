mod gui;
mod model;
mod plotting;
mod scattering;
mod training;

use candle_core::{Device, Error, Result};
use chrono::Utc;
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use std::sync::Arc;

use gui::launch_gui;
use gui::legacy_cornell::{AppData, InteractiveContext};
use plotting::plot_results;
use quark_sim::physics::{
    collider_beams, compute_dis_kinematics, evaluate_lo_structure_functions, exact_inelasticity,
    lo_differential_cross_section, scattered_electron, FixedAlpha, LhapdfProvider,
};
use scattering::{get_proton_quarks, plot_scattering, simulate_scattering, ScatteringParams};
use training::{
    create_model_and_optimizer, generate_training_data, load_model_with_config,
    save_model_with_config, test_model, train_model,
};

const TRAINING_SAMPLES: usize = 15_000;
const TRAINING_EPOCHS: usize = 5_000;
const LEARNING_RATE: f64 = 0.01;

const HELP: &str = "Cornell-potential neural-network visualization

Usage:
  quark_sim
      Train a new model, create plots and launch the interactive GUI.

  quark_sim --load <session.json>
      Load saved arrays and trajectories for static viewing. This does not
      restore a model or resume/replay the simulation.

  quark_sim --load-model <model.safetensors>
      Load a trained model. A sibling <model>_config.json file is required.

  quark_sim dis-kinematics [OPTIONS]
      Compute validated inclusive electron-proton DIS invariants.
      Run `quark_sim dis-kinematics --help` for the required options.

  quark_sim dis-cross-section [OPTIONS]
      Evaluate LO electromagnetic inclusive DIS with an installed LHAPDF set.
      Run `quark_sim dis-cross-section --help` for the required options.

  quark_sim generate-dis-events [OPTIONS]
      Generate Monte Carlo DIS events using the PYTHIA 8 backend.
      Run `quark_sim generate-dis-events --help` for the required options.

  quark_sim validate-hera [OPTIONS]
      Validate predictions against HERA inclusive DIS measurements.
      Run `quark_sim validate-hera --help` for the options.

  quark_sim theory-uncertainties [OPTIONS]
      Validate predictions and calculate theory uncertainties against HERA DIS measurements.
      Run `quark_sim theory-uncertainties --help` for the options.

  quark_sim -h | --help
      Show this help message without training or launching the GUI.

Build modes:
  CPU (default): cargo run --release
  Optional CUDA: cargo run --release --features cuda
";

const DIS_HELP: &str = "Neutral-current inclusive electron-proton DIS kinematics

Usage:
  quark_sim dis-kinematics \\
      --electron-energy <GEV> \\
      --proton-energy <GEV> \\
      --scattered-electron-energy <GEV> \\
      --theta-deg <DEGREES>

Required options:
  --electron-energy <GEV>
      Incoming electron energy. The electron travels along +z.

  --proton-energy <GEV>
      Incoming proton energy. The proton travels along -z.

  --scattered-electron-energy <GEV>
      Outgoing electron energy.

  --theta-deg <DEGREES>
      Outgoing-electron polar angle measured from the incoming +z direction.
      The azimuth is fixed to zero; inclusive invariants are azimuth-independent.

The calculation keeps the electron and proton masses and prints s, Q², x, y,
and W² in GeV-based natural units. Unphysical inputs are rejected, not clamped.
";

const CROSS_SECTION_HELP: &str = "Leading-order electromagnetic inclusive electron-proton DIS

Usage:
  quark_sim dis-cross-section \\
      --x <BJORKEN_X> \\
      --q2 <GEV2> \\
      --electron-energy <GEV> \\
      --proton-energy <GEV> \\
      --pdf-set <INSTALLED_SET> \\
      --pdf-member <INDEX>

Required options:
  --x <BJORKEN_X>
      Bjorken x in the open interval (0, 1).

  --q2 <GEV2>
      Positive momentum-transfer scale Q² in GeV².

  --electron-energy <GEV>
      Incoming electron beam energy; the electron travels along +z.

  --proton-energy <GEV>
      Incoming proton beam energy; the proton travels along -z.

  --pdf-set <INSTALLED_SET>
      Name of an installed LHAPDF proton set, for example CT18LO.

  --pdf-member <INDEX>
      Non-negative LHAPDF member index.

The calculation uses LHAPDF x f(x,Q²) values, a fixed α(0), F_L = 0, and
xF₃ = 0. It prints d²σ/(dx dQ²) in GeV⁻⁴ and pb/GeV². Points with
unphysical y or outside the selected PDF grid are rejected.
";

const GENERATE_DIS_EVENTS_HELP: &str = "Generate Monte Carlo DIS events using the PYTHIA 8 backend

Usage:
  quark_sim generate-dis-events \
      --electron-energy <GEV> \
      --proton-energy <GEV> \
      --q2-min <GEV2> \
      --events <COUNT> \
      --pdf-set <SET> \
      --output <DIRECTORY> \
      [--q2-max <GEV2>] \
      [--x-min <X>] \
      [--x-max <X>] \
      [--y-min <Y>] \
      [--y-max <Y>] \
      [--seed <SEED>] \
      [--pdf-member <INDEX>] \
      [--parton-shower <true|false>] \
      [--hadronization <true|false>]

Required options:
  --electron-energy <GEV>   Incoming electron energy. Travels along +z.
  --proton-energy <GEV>     Incoming proton energy. Travels along -z.
  --q2-min <GEV2>           Minimum virtuality Q² in GeV².
  --events <COUNT>          Number of events to generate.
  --pdf-set <SET>           LHAPDF proton set name.
  --output <DIRECTORY>      Base directory for output run files.

Defaults:
  --q2-max 10000.0, --x-min 0.0001, --x-max 0.8, --y-min 0.01, --y-max 0.95,
  --pdf-member 0, --parton-shower true, --hadronization true.
  If --seed is omitted, a random seed is dynamically generated.
";

#[derive(Debug, PartialEq)]
enum Command {
    LaunchGui,
    Train,
    LoadSession(PathBuf),
    LoadModel(PathBuf),
    DisKinematics(DisCommand),
    DisCrossSection(CrossSectionCommand),
    GenerateDisEvents(GenerateDisEventsCommand),
    StructureFunctions(StructureFunctionsCliArgs),
    ValidateHera(ValidateHeraCliArgs),
    TheoryUncertainties(TheoryUncertaintiesCliArgs),
    TrainSurrogate(TrainSurrogateCliArgs),
    Help,
}

#[derive(Debug, PartialEq)]
enum DisCommand {
    Calculate(DisCliArgs),
    Help,
}

#[derive(Debug, PartialEq)]
enum GenerateDisEventsCommand {
    Calculate(GenerateDisEventsCliArgs),
    Help,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
struct GenerateDisEventsCliArgs {
    schema_version: i32,
    process: String,
    electron_energy_gev: f64,
    proton_energy_gev: f64,
    q2_min_gev2: f64,
    q2_max_gev2: f64,
    x_min: f64,
    x_max: f64,
    y_min: f64,
    y_max: f64,
    number_of_events: usize,
    #[serde(skip_serializing_if = "Option::is_none")]
    random_seed: Option<i32>,
    pdf_set: String,
    pdf_member: i32,
    parton_shower: bool,
    hadronization: bool,
    #[serde(skip)]
    output: PathBuf,
}

#[derive(Debug, Clone, PartialEq)]
struct StructureFunctionsCliArgs {
    backend: String,
    x: f64,
    q2: f64,
    order: String,
    pdf_set: String,
    pdf_member: i32,
    mu_f_over_q: f64,
    mu_r_over_q: f64,
}

#[derive(Debug, Clone, Copy, PartialEq)]
struct DisCliArgs {
    electron_energy: f64,
    proton_energy: f64,
    scattered_electron_energy: f64,
    theta_deg: f64,
}

#[derive(Debug, PartialEq)]
enum CrossSectionCommand {
    Calculate(CrossSectionCliArgs),
    Help,
}

#[derive(Debug, Clone, PartialEq)]
struct CrossSectionCliArgs {
    x: f64,
    q2: f64,
    electron_energy: f64,
    proton_energy: f64,
    pdf_set: String,
    pdf_member: i32,
}

#[derive(Debug, Clone, PartialEq)]
struct ValidateHeraCliArgs {
    dataset: String,
    backend: String,
    order: String,
    pdf_set: String,
    pdf_member: i32,
    output: PathBuf,
}

#[derive(Debug, Clone, PartialEq)]
struct TheoryUncertaintiesCliArgs {
    dataset: String,
    backend: String,
    order: String,
    pdf_set: String,
    pdf_member: i32,
    pdf_uncertainty: bool,
    scale_variations: bool,
    output: PathBuf,
}

#[derive(Debug, Clone, PartialEq)]
struct TrainSurrogateCliArgs {
    pdf_set: String,
    pdf_member: i32,
    order: String,
    output: PathBuf,
}

fn main() -> Result<()> {
    let command = parse_command(std::env::args().skip(1)).map_err(|message| {
        eprintln!("Error: {message}\n\n{HELP}");
        Error::Msg(message)
    })?;

    match command {
        Command::LaunchGui => gui::launch_dis_gui("QuarkSim"),
        Command::Train => run_training(),
        Command::LoadSession(session_file) => {
            let app_data = AppData::load_session(&session_file).map_err(Error::wrap)?;
            launch_gui(app_data, "Kayıtlı Oturum (Statik Görünüm)", None)
        }
        Command::LoadModel(model_path) => {
            let config_path = model_config_path(&model_path)?;
            if !config_path.is_file() {
                return Err(Error::Msg(format!(
                    "model configuration not found: {} (normalization values are required)",
                    config_path.display()
                )));
            }
            run_with_pretrained_model(&model_path, &config_path)
        }
        Command::DisKinematics(DisCommand::Calculate(arguments)) => run_dis_kinematics(arguments),
        Command::DisKinematics(DisCommand::Help) => {
            print!("{DIS_HELP}");
            Ok(())
        }
        Command::DisCrossSection(CrossSectionCommand::Calculate(arguments)) => {
            run_dis_cross_section(arguments)
        }
        Command::DisCrossSection(CrossSectionCommand::Help) => {
            print!("{CROSS_SECTION_HELP}");
            Ok(())
        }
        Command::GenerateDisEvents(GenerateDisEventsCommand::Calculate(arguments)) => {
            run_generate_dis_events(arguments)
        }
        Command::GenerateDisEvents(GenerateDisEventsCommand::Help) => {
            print!("{GENERATE_DIS_EVENTS_HELP}");
            Ok(())
        }
        Command::StructureFunctions(arguments) => {
            run_structure_functions(arguments)
        }
        Command::ValidateHera(arguments) => {
            run_validate_hera(arguments)
        }
        Command::TheoryUncertainties(arguments) => {
            run_theory_uncertainties(arguments)
        }
        Command::TrainSurrogate(arguments) => {
            run_train_surrogate(arguments)
        }
        Command::Help => {
            print!("{HELP}");
            Ok(())
        }
    }
}

fn parse_command(args: impl IntoIterator<Item = String>) -> std::result::Result<Command, String> {
    let args: Vec<String> = args.into_iter().collect();
    match args.as_slice() {
        [] => Ok(Command::LaunchGui),
        [flag] if flag == "-h" || flag == "--help" => Ok(Command::Help),
        [subcommand, remaining @ ..] if subcommand == "dis-kinematics" => {
            parse_dis_command(remaining).map(Command::DisKinematics)
        }
        [subcommand, remaining @ ..] if subcommand == "dis-cross-section" => {
            parse_cross_section_command(remaining).map(Command::DisCrossSection)
        }
        [subcommand, remaining @ ..] if subcommand == "generate-dis-events" => {
            parse_generate_dis_events_command(remaining).map(Command::GenerateDisEvents)
        }
        [subcommand, remaining @ ..] if subcommand == "validate-hera" => {
            parse_validate_hera_command(remaining).map(Command::ValidateHera)
        }
        [subcommand, remaining @ ..] if subcommand == "theory-uncertainties" => {
            parse_theory_uncertainties_command(remaining).map(Command::TheoryUncertainties)
        }
        [subcommand, remaining @ ..] if subcommand == "structure-functions" => {
            parse_structure_functions_command(remaining).map(Command::StructureFunctions)
        }
        [subcommand, remaining @ ..] if subcommand == "train-surrogate" => {
            parse_train_surrogate_command(remaining).map(Command::TrainSurrogate)
        }
        [flag, path] if flag == "--load" => Ok(Command::LoadSession(PathBuf::from(path))),
        [flag, path] if flag == "--load-model" => Ok(Command::LoadModel(PathBuf::from(path))),
        [flag] if flag == "--load" || flag == "--load-model" => {
            Err(format!("{flag} requires a file path"))
        }
        _ => Err(format!("unrecognized arguments: {}", args.join(" "))),
    }
}

fn parse_dis_command(args: &[String]) -> std::result::Result<DisCommand, String> {
    if matches!(args, [flag] if flag == "-h" || flag == "--help") {
        return Ok(DisCommand::Help);
    }
    if args.is_empty() {
        return Err(format!(
            "dis-kinematics requires four options\n\n{DIS_HELP}"
        ));
    }

    let mut electron_energy = None;
    let mut proton_energy = None;
    let mut scattered_electron_energy = None;
    let mut theta_deg = None;
    let mut index = 0;

    while index < args.len() {
        let flag = args[index].as_str();
        let slot = match flag {
            "--electron-energy" => &mut electron_energy,
            "--proton-energy" => &mut proton_energy,
            "--scattered-electron-energy" => &mut scattered_electron_energy,
            "--theta-deg" => &mut theta_deg,
            "-h" | "--help" => {
                return Err("--help must be used by itself after dis-kinematics".to_string())
            }
            _ => return Err(format!("unknown dis-kinematics option: {flag}")),
        };
        let value_text = args
            .get(index + 1)
            .ok_or_else(|| format!("{flag} requires a numeric value"))?;
        if value_text.starts_with("--") {
            return Err(format!("{flag} requires a numeric value"));
        }
        let value = value_text
            .parse::<f64>()
            .map_err(|_| format!("invalid numeric value for {flag}: {value_text}"))?;

        if slot.replace(value).is_some() {
            return Err(format!("duplicate dis-kinematics option: {flag}"));
        }
        index += 2;
    }

    Ok(DisCommand::Calculate(DisCliArgs {
        electron_energy: required_dis_option(electron_energy, "--electron-energy")?,
        proton_energy: required_dis_option(proton_energy, "--proton-energy")?,
        scattered_electron_energy: required_dis_option(
            scattered_electron_energy,
            "--scattered-electron-energy",
        )?,
        theta_deg: required_dis_option(theta_deg, "--theta-deg")?,
    }))
}

fn required_dis_option(
    value: Option<f64>,
    option: &'static str,
) -> std::result::Result<f64, String> {
    value.ok_or_else(|| format!("missing required dis-kinematics option: {option}"))
}

fn parse_cross_section_command(
    args: &[String],
) -> std::result::Result<CrossSectionCommand, String> {
    if matches!(args, [flag] if flag == "-h" || flag == "--help") {
        return Ok(CrossSectionCommand::Help);
    }
    if args.is_empty() {
        return Err(format!(
            "dis-cross-section requires six options\n\n{CROSS_SECTION_HELP}"
        ));
    }

    let mut x = None;
    let mut q2 = None;
    let mut electron_energy = None;
    let mut proton_energy = None;
    let mut pdf_set = None;
    let mut pdf_member = None;
    let mut index = 0;

    while index < args.len() {
        let flag = args[index].as_str();
        if flag == "-h" || flag == "--help" {
            return Err("--help must be used by itself after dis-cross-section".to_string());
        }
        if !matches!(
            flag,
            "--x" | "--q2" | "--electron-energy" | "--proton-energy" | "--pdf-set" | "--pdf-member"
        ) {
            return Err(format!("unknown dis-cross-section option: {flag}"));
        }

        let value_text = args
            .get(index + 1)
            .filter(|value| !value.starts_with("--"))
            .ok_or_else(|| format!("{flag} requires a value"))?;

        match flag {
            "--x" => set_cross_option(&mut x, parse_finite_cross_number(flag, value_text)?, flag)?,
            "--q2" => {
                set_cross_option(&mut q2, parse_finite_cross_number(flag, value_text)?, flag)?
            }
            "--electron-energy" => set_cross_option(
                &mut electron_energy,
                parse_finite_cross_number(flag, value_text)?,
                flag,
            )?,
            "--proton-energy" => set_cross_option(
                &mut proton_energy,
                parse_finite_cross_number(flag, value_text)?,
                flag,
            )?,
            "--pdf-set" => {
                let value = value_text.trim();
                if value.is_empty() {
                    return Err("--pdf-set must not be empty".to_string());
                }
                set_cross_option(&mut pdf_set, value.to_owned(), flag)?;
            }
            "--pdf-member" => {
                let value = value_text.parse::<i32>().map_err(|_| {
                    format!("invalid non-negative integer for {flag}: {value_text}")
                })?;
                if value < 0 {
                    return Err(format!("{flag} must be non-negative, got {value}"));
                }
                set_cross_option(&mut pdf_member, value, flag)?;
            }
            _ => unreachable!("supported options were checked above"),
        }
        index += 2;
    }

    Ok(CrossSectionCommand::Calculate(CrossSectionCliArgs {
        x: required_cross_option(x, "--x")?,
        q2: required_cross_option(q2, "--q2")?,
        electron_energy: required_cross_option(electron_energy, "--electron-energy")?,
        proton_energy: required_cross_option(proton_energy, "--proton-energy")?,
        pdf_set: required_cross_option(pdf_set, "--pdf-set")?,
        pdf_member: required_cross_option(pdf_member, "--pdf-member")?,
    }))
}

fn parse_finite_cross_number(flag: &str, value_text: &str) -> std::result::Result<f64, String> {
    let value = value_text
        .parse::<f64>()
        .map_err(|_| format!("invalid numeric value for {flag}: {value_text}"))?;
    if !value.is_finite() {
        return Err(format!("{flag} must be finite, got {value_text}"));
    }
    Ok(value)
}

fn set_cross_option<T>(
    slot: &mut Option<T>,
    value: T,
    flag: &str,
) -> std::result::Result<(), String> {
    if slot.replace(value).is_some() {
        Err(format!("duplicate dis-cross-section option: {flag}"))
    } else {
        Ok(())
    }
}

fn required_cross_option<T>(value: Option<T>, option: &str) -> std::result::Result<T, String> {
    value.ok_or_else(|| format!("missing required dis-cross-section option: {option}"))
}

fn run_dis_kinematics(arguments: DisCliArgs) -> Result<()> {
    let beams = collider_beams(arguments.electron_energy, arguments.proton_energy)
        .map_err(|error| Error::Msg(error.to_string()))?;
    let outgoing = scattered_electron(arguments.scattered_electron_energy, arguments.theta_deg)
        .map_err(|error| Error::Msg(error.to_string()))?;
    let event = compute_dis_kinematics(beams.proton, beams.electron, outgoing)
        .map_err(|error| Error::Msg(error.to_string()))?;

    println!("Neutral-current inclusive e⁻p DIS kinematics");
    println!("s   = {:.12} GeV²", event.s);
    println!("Q²  = {:.12} GeV²", event.q2);
    println!("x   = {:.12}", event.x);
    println!("y   = {:.12}", event.y);
    println!("W²  = {:.12} GeV²", event.w2);
    Ok(())
}

fn run_dis_cross_section(arguments: CrossSectionCliArgs) -> Result<()> {
    let beams = collider_beams(arguments.electron_energy, arguments.proton_energy)
        .map_err(|error| Error::Msg(error.to_string()))?;
    let s = (beams.proton + beams.electron).mass_squared();

    // Reject an unphysical beam/point combination before loading or querying a
    // potentially expensive native PDF grid.
    exact_inelasticity(arguments.x, arguments.q2, s)
        .map_err(|error| Error::Msg(error.to_string()))?;

    let provider = LhapdfProvider::new(arguments.pdf_set, arguments.pdf_member)
        .map_err(|error| Error::Msg(error.to_string()))?;
    let structure_functions = evaluate_lo_structure_functions(&provider, arguments.x, arguments.q2)
        .map_err(|error| Error::Msg(error.to_string()))?;
    let result = lo_differential_cross_section(
        arguments.x,
        arguments.q2,
        s,
        structure_functions.f2,
        &FixedAlpha::default(),
    )
    .map_err(|error| Error::Msg(error.to_string()))?;
    let densities = structure_functions.densities;

    println!("Leading-order electromagnetic neutral-current e⁻p DIS");
    println!(
        "PDF set/member: {}/{}",
        provider.set_name(),
        provider.member()
    );
    println!("x      = {:.12e}", result.x);
    println!("Q²     = {:.12e} GeV²", result.q2);
    println!("s      = {:.12e} GeV²", result.s);
    println!("y      = {:.12e}", result.y);
    println!("Y₊     = {:.12e}", result.y_plus);
    println!("LHAPDF x f(x,Q²):");
    println!("  g    = {:.12e}", densities.gluon);
    println!("  u    = {:.12e}", densities.up);
    println!("  ū    = {:.12e}", densities.anti_up);
    println!("  d    = {:.12e}", densities.down);
    println!("  d̄    = {:.12e}", densities.anti_down);
    println!("  s    = {:.12e}", densities.strange);
    println!("  s̄    = {:.12e}", densities.anti_strange);
    println!("  c    = {:.12e}", densities.charm);
    println!("  c̄    = {:.12e}", densities.anti_charm);
    println!("  b    = {:.12e}", densities.bottom);
    println!("  b̄    = {:.12e}", densities.anti_bottom);
    println!("F₂     = {:.12e}", result.f2);
    println!("F_L    = {:.12e} (LO assumption)", result.fl);
    println!("xF₃    = {:.12e} (photon-exchange assumption)", result.xf3);
    println!("α      = {:.12e} (fixed α(0))", result.alpha);
    println!(
        "d²σ/(dx dQ²) = {:.12e} GeV⁻⁴",
        result.d2sigma_dx_dq2_gev_minus4
    );
    println!(
        "d²σ/(dx dQ²) = {:.12e} pb/GeV²",
        result.d2sigma_dx_dq2_pb_per_gev2
    );
    Ok(())
}

fn model_config_path(model_path: &Path) -> Result<PathBuf> {
    let stem = model_path
        .file_stem()
        .and_then(|value| value.to_str())
        .ok_or_else(|| Error::Msg(format!("invalid model path: {}", model_path.display())))?;
    Ok(model_path.with_file_name(format!("{stem}_config.json")))
}

fn active_device() -> Result<Device> {
    #[cfg(feature = "cuda")]
    {
        if candle_core::utils::cuda_is_available() {
            println!("CUDA feature enabled; using CUDA device 0.");
            return Device::new_cuda(0);
        }
        eprintln!("CUDA feature enabled, but no CUDA device is available; falling back to CPU.");
    }

    println!("Using CPU.");
    Ok(Device::Cpu)
}

fn create_output_dir(suffix: &str) -> Result<String> {
    let timestamp = Utc::now().format("%Y%m%d_%H%M%S").to_string();
    let output_dir = format!("outputs/{timestamp}_{suffix}");
    std::fs::create_dir_all(&output_dir).map_err(Error::wrap)?;
    println!("Output directory: {output_dir}");
    Ok(output_dir)
}

fn run_training() -> Result<()> {
    let output_dir = create_output_dir("GMT")?;
    let device = active_device()?;

    println!("Preparing {TRAINING_SAMPLES} training samples...");
    let (distances, target, target_mean, target_std) =
        generate_training_data(TRAINING_SAMPLES, &device)?;
    let (model, mut optimizer, varmap) = create_model_and_optimizer(&device, LEARNING_RATE)?;
    let loss_history = train_model(
        &model,
        &mut optimizer,
        &distances,
        &target,
        target_mean,
        target_std,
        TRAINING_EPOCHS,
        &device,
    )?;

    let model_path = format!("{output_dir}/trained_model.safetensors");
    let config_path = format!("{output_dir}/trained_model_config.json");
    save_model_with_config(&varmap, &model_path, &config_path, target_mean, target_std)?;

    let (test_distances, cornell_values, nn_values, theory_points, nn_points) =
        test_model(&model, target_mean, target_std, &device)?;
    let (loss_file, potential_file) = plot_results(
        &output_dir,
        &loss_history,
        &test_distances,
        &cornell_values,
        &nn_values,
        &model,
        target_mean,
        target_std,
        &device,
    )?;

    let scattering_params = ScatteringParams::default();
    let electrons =
        simulate_scattering(&model, &scattering_params, target_mean, target_std, &device)?;
    let scattering_file = format!("{output_dir}/scattering.svg");
    plot_scattering(&electrons, &scattering_file)?;

    let electron_data = electrons
        .iter()
        .map(|electron| crate::gui::legacy_cornell::ElectronData {
            trajectory: electron.trajectory.clone(),
            impact_parameter: electron.impact_parameter,
        })
        .collect();
    let app_data = AppData {
        loss_history,
        potential_theory: theory_points,
        potential_nn: nn_points,
        test_distances,
        cornell_values,
        nn_values,
        loss_file,
        potential_file,
        scattering_file: Some(scattering_file),
        electrons: Some(electron_data),
    };
    app_data.save_session(&output_dir).map_err(Error::wrap)?;

    let interactive_context = InteractiveContext {
        model: Arc::new(model),
        device,
        mean: target_mean,
        std: target_std,
        live_electrons: Vec::new(),
        targets: get_proton_quarks(),
    };
    launch_gui(app_data, "Cornell Laboratuvarı", Some(interactive_context))
}

fn run_with_pretrained_model(model_path: &Path, config_path: &Path) -> Result<()> {
    println!("Loading trained model...");
    let device = active_device()?;
    let (model, _varmap, target_mean, target_std) = load_model_with_config(
        &model_path.to_string_lossy(),
        &config_path.to_string_lossy(),
        &device,
    )?;
    let output_dir = create_output_dir("LOADED")?;

    let (test_distances, cornell_values, nn_values, theory_points, nn_points) =
        test_model(&model, target_mean, target_std, &device)?;
    let (loss_file, potential_file) = plot_results(
        &output_dir,
        &[],
        &test_distances,
        &cornell_values,
        &nn_values,
        &model,
        target_mean,
        target_std,
        &device,
    )?;

    let scattering_params = ScatteringParams::default();
    let electrons =
        simulate_scattering(&model, &scattering_params, target_mean, target_std, &device)?;
    let scattering_file = format!("{output_dir}/scattering.svg");
    plot_scattering(&electrons, &scattering_file)?;

    let electron_data = electrons
        .iter()
        .map(|electron| crate::gui::legacy_cornell::ElectronData {
            trajectory: electron.trajectory.clone(),
            impact_parameter: electron.impact_parameter,
        })
        .collect();
    let app_data = AppData {
        loss_history: Vec::new(),
        potential_theory: theory_points,
        potential_nn: nn_points,
        test_distances,
        cornell_values,
        nn_values,
        loss_file,
        potential_file,
        scattering_file: Some(scattering_file),
        electrons: Some(electron_data),
    };
    app_data.save_session(&output_dir).map_err(Error::wrap)?;

    let interactive_context = InteractiveContext {
        model: Arc::new(model),
        device,
        mean: target_mean,
        std: target_std,
        live_electrons: Vec::new(),
        targets: get_proton_quarks(),
    };
    launch_gui(
        app_data,
        "Cornell Laboratuvarı (Yüklenmiş Model)",
        Some(interactive_context),
    )
}

fn parse_generate_dis_events_command(
    args: &[String],
) -> std::result::Result<GenerateDisEventsCommand, String> {
    if matches!(args, [flag] if flag == "-h" || flag == "--help") {
        return Ok(GenerateDisEventsCommand::Help);
    }
    if args.is_empty() {
        return Err(format!(
            "generate-dis-events requires parameters\n\n{GENERATE_DIS_EVENTS_HELP}"
        ));
    }

    let mut electron_energy = None;
    let mut proton_energy = None;
    let mut q2_min = None;
    let mut q2_max = Some(10000.0);
    let mut x_min = Some(0.0001);
    let mut x_max = Some(0.8);
    let mut y_min = Some(0.01);
    let mut y_max = Some(0.95);
    let mut events = None;
    let mut seed = None;
    let mut pdf_set = None;
    let mut pdf_member = Some(0);
    let mut parton_shower = Some(true);
    let mut hadronization = Some(true);
    let mut output = None;

    let mut index = 0;
    while index < args.len() {
        let flag = args[index].as_str();
        if flag == "-h" || flag == "--help" {
            return Err("--help must be used by itself after generate-dis-events".to_string());
        }

        let value_text = args
            .get(index + 1)
            .filter(|value| !value.starts_with("--"))
            .ok_or_else(|| format!("{flag} requires a value"))?;

        match flag {
            "--electron-energy" => {
                electron_energy = Some(parse_finite_cross_number(flag, value_text)?)
            }
            "--proton-energy" => proton_energy = Some(parse_finite_cross_number(flag, value_text)?),
            "--q2-min" => q2_min = Some(parse_finite_cross_number(flag, value_text)?),
            "--q2-max" => q2_max = Some(parse_finite_cross_number(flag, value_text)?),
            "--x-min" => x_min = Some(parse_finite_cross_number(flag, value_text)?),
            "--x-max" => x_max = Some(parse_finite_cross_number(flag, value_text)?),
            "--y-min" => y_min = Some(parse_finite_cross_number(flag, value_text)?),
            "--y-max" => y_max = Some(parse_finite_cross_number(flag, value_text)?),
            "--events" => {
                let val = value_text
                    .parse::<usize>()
                    .map_err(|_| format!("invalid positive integer for {flag}: {value_text}"))?;
                events = Some(val);
            }
            "--seed" => {
                let val = value_text
                    .parse::<i32>()
                    .map_err(|_| format!("invalid integer for {flag}: {value_text}"))?;
                seed = Some(val);
            }
            "--pdf-set" => {
                let val = value_text.trim();
                if val.is_empty() {
                    return Err("--pdf-set must not be empty".to_string());
                }
                pdf_set = Some(val.to_owned());
            }
            "--pdf-member" => {
                let val = value_text.parse::<i32>().map_err(|_| {
                    format!("invalid non-negative integer for {flag}: {value_text}")
                })?;
                if val < 0 {
                    return Err(format!("{flag} must be non-negative, got {val}"));
                }
                pdf_member = Some(val);
            }
            "--parton-shower" => {
                let val = value_text
                    .parse::<bool>()
                    .map_err(|_| format!("invalid boolean for {flag}: {value_text}"))?;
                parton_shower = Some(val);
            }
            "--hadronization" => {
                let val = value_text
                    .parse::<bool>()
                    .map_err(|_| format!("invalid boolean for {flag}: {value_text}"))?;
                hadronization = Some(val);
            }
            "--output" => {
                let val = value_text.trim();
                if val.is_empty() {
                    return Err("--output must not be empty".to_string());
                }
                output = Some(PathBuf::from(val));
            }
            _ => return Err(format!("unknown generate-dis-events option: {flag}")),
        }
        index += 2;
    }

    let electron_energy =
        electron_energy.ok_or_else(|| "missing required option: --electron-energy".to_string())?;
    let proton_energy =
        proton_energy.ok_or_else(|| "missing required option: --proton-energy".to_string())?;
    let q2_min = q2_min.ok_or_else(|| "missing required option: --q2-min".to_string())?;
    let events = events.ok_or_else(|| "missing required option: --events".to_string())?;
    let pdf_set = pdf_set.ok_or_else(|| "missing required option: --pdf-set".to_string())?;
    let output = output.ok_or_else(|| "missing required option: --output".to_string())?;

    Ok(GenerateDisEventsCommand::Calculate(
        GenerateDisEventsCliArgs {
            schema_version: 1,
            process: "neutral_current_dis".to_string(),
            electron_energy_gev: electron_energy,
            proton_energy_gev: proton_energy,
            q2_min_gev2: q2_min,
            q2_max_gev2: q2_max.unwrap_or(10000.0),
            x_min: x_min.unwrap_or(0.0001),
            x_max: x_max.unwrap_or(0.8),
            y_min: y_min.unwrap_or(0.01),
            y_max: y_max.unwrap_or(0.95),
            number_of_events: events,
            random_seed: seed,
            pdf_set,
            pdf_member: pdf_member.unwrap_or(0),
            parton_shower: parton_shower.unwrap_or(true),
            hadronization: hadronization.unwrap_or(true),
            output,
        },
    ))
}

fn run_generate_dis_events(arguments: GenerateDisEventsCliArgs) -> Result<()> {
    if arguments.electron_energy_gev <= 0.0 || arguments.proton_energy_gev <= 0.0 {
        return Err(Error::Msg(
            "incoming beam energies must be positive".to_string(),
        ));
    }
    if arguments.q2_min_gev2 <= 0.0 || arguments.q2_max_gev2 <= arguments.q2_min_gev2 {
        return Err(Error::Msg(
            "invalid Q2 cuts: q2-min must be positive and less than q2-max".to_string(),
        ));
    }
    if arguments.x_min <= 0.0 || arguments.x_max <= arguments.x_min || arguments.x_max >= 1.0 {
        return Err(Error::Msg(
            "invalid x cuts: x-min must be positive and less than x-max".to_string(),
        ));
    }
    if arguments.y_min <= 0.0 || arguments.y_max <= arguments.y_min || arguments.y_max >= 1.0 {
        return Err(Error::Msg(
            "invalid y cuts: y-min must be positive and less than y-max".to_string(),
        ));
    }
    if arguments.number_of_events == 0 {
        return Err(Error::Msg("number of events must be positive".to_string()));
    }

    let timestamp = Utc::now().format("%Y%m%d_%H%M%S").to_string();
    let run_dir_name = format!("dis_run_{}", timestamp);
    let run_dir = arguments.output.join(&run_dir_name);
    std::fs::create_dir_all(&run_dir).map_err(Error::wrap)?;
    println!("Output directory: {}", run_dir.display());

    let config_path = run_dir.join("config.json");
    let config_json = serde_json::to_string_pretty(&arguments)
        .map_err(|source| Error::Msg(format!("failed to serialize request: {source}")))?;
    std::fs::write(&config_path, &config_json).map_err(Error::wrap)?;

    let backend_bin = std::env::var("PYTHIA_BACKEND_BIN")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("physics-engine/build/pythia_dis_cli"));

    if !backend_bin.is_file() {
        return Err(Error::Msg(format!(
            "PYTHIA 8 backend executable not found: {} (run setup scripts and build first)",
            backend_bin.display()
        )));
    }

    let log_path = run_dir.join("generator.log");
    let log_file = std::fs::File::create(&log_path).map_err(Error::wrap)?;

    println!("Launching PYTHIA 8 event generator backend...");
    let mut child = std::process::Command::new(&backend_bin)
        .arg(run_dir.to_string_lossy().as_ref())
        .stdin(std::process::Stdio::piped())
        .stdout(log_file.try_clone().map_err(Error::wrap)?)
        .stderr(log_file)
        .spawn()
        .map_err(|err| Error::Msg(format!("failed to spawn backend process: {err}")))?;

    if let Some(mut stdin) = child.stdin.take() {
        use std::io::Write;
        stdin
            .write_all(config_json.as_bytes())
            .map_err(Error::wrap)?;
    }

    let status = child
        .wait()
        .map_err(|err| Error::Msg(format!("failed to wait for backend: {err}")))?;

    if !status.success() {
        let code = status.code().unwrap_or(-1);
        return Err(Error::Msg(format!(
            "PYTHIA 8 backend failed with exit code: {code}"
        )));
    }

    let expected_files = [
        "config.json",
        "metadata.json",
        "generator.log",
        "events.hepmc3",
        "inclusive_observables.csv",
        "summary.json",
    ];
    for file_name in &expected_files {
        let file_path = run_dir.join(file_name);
        if !file_path.is_file() {
            return Err(Error::Msg(format!(
                "Missing expected output file: {file_name}"
            )));
        }
    }

    let summary_path = run_dir.join("summary.json");
    let summary_content = std::fs::read_to_string(&summary_path).map_err(Error::wrap)?;
    let summary: serde_json::Value = serde_json::from_str(&summary_content)
        .map_err(|source| Error::Msg(format!("failed to parse summary.json: {source}")))?;

    let success = summary
        .get("success")
        .and_then(|v| v.as_bool())
        .unwrap_or(false);
    if !success {
        return Err(Error::Msg(
            "summary.json indicates generation failed".to_string(),
        ));
    }

    println!("DIS events generation completed successfully.");
    if let Some(accepted) = summary.get("accepted_events") {
        println!("Accepted events: {}", accepted);
    }
    if let Some(failed) = summary.get("failed_events") {
        println!("Failed events: {}", failed);
    }
    if let Some(vetoed) = summary.get("vetoed_cuts_events") {
        println!("Vetoed by cuts: {}", vetoed);
    }

    Ok(())
}

fn parse_validate_hera_command(args: &[String]) -> std::result::Result<ValidateHeraCliArgs, String> {
    if matches!(args, [flag] if flag == "-h" || flag == "--help") {
        return Err("validate-hera --dataset <DATASET_ID> --backend apfel --order NLO --pdf-set <SET> --output outputs/validation/".to_owned());
    }
    
    let mut dataset = None;
    let mut backend = None;
    let mut order = None;
    let mut pdf_set = None;
    let mut pdf_member = Some(0);
    let mut output = None;
    let mut index = 0;
    
    while index < args.len() {
        let flag = args[index].as_str();
        if flag == "-h" || flag == "--help" {
            return Err("--help must be used by itself after validate-hera".to_string());
        }
        if !matches!(
            flag,
            "--dataset" | "--backend" | "--order" | "--pdf-set" | "--pdf-member" | "--output"
        ) {
            return Err(format!("unknown validate-hera option: {flag}"));
        }
        
        let value_text = args
            .get(index + 1)
            .filter(|value| !value.starts_with("--"))
            .ok_or_else(|| format!("{flag} requires a value"))?;
            
        match flag {
            "--dataset" => dataset = Some(value_text.clone()),
            "--backend" => backend = Some(value_text.clone()),
            "--order" => order = Some(value_text.clone()),
            "--pdf-set" => pdf_set = Some(value_text.clone()),
            "--pdf-member" => {
                let parsed = value_text
                    .parse::<i32>()
                    .map_err(|_| format!("invalid integer for --pdf-member: {value_text}"))?;
                pdf_member = Some(parsed);
            }
            "--output" => output = Some(PathBuf::from(value_text)),
            _ => unreachable!(),
        }
        index += 2;
    }
    
    Ok(ValidateHeraCliArgs {
        dataset: dataset.ok_or_else(|| "missing required option: --dataset".to_owned())?,
        backend: backend.ok_or_else(|| "missing required option: --backend".to_owned())?,
        order: order.ok_or_else(|| "missing required option: --order".to_owned())?,
        pdf_set: pdf_set.ok_or_else(|| "missing required option: --pdf-set".to_owned())?,
        pdf_member: pdf_member.unwrap_or(0),
        output: output.ok_or_else(|| "missing required option: --output".to_owned())?,
    })
}

fn run_validate_hera(arguments: ValidateHeraCliArgs) -> Result<()> {
    if arguments.backend != "apfel" {
        return Err(Error::Msg(format!("Unsupported backend: {}. Only 'apfel' is supported currently.", arguments.backend)));
    }
    if arguments.order != "LO" && arguments.order != "NLO" {
        return Err(Error::Msg(format!("Unsupported order: {}. Only 'LO' or 'NLO' is supported.", arguments.order)));
    }
    
    let compare_script = PathBuf::from("analysis/validation/compare.py");
    if !compare_script.is_file() {
        return Err(Error::Msg("compare.py script not found under analysis/validation/compare.py".to_string()));
    }
    
    println!("Launching HERA validation pipeline via Python...");
    
    let mut cmd = std::process::Command::new("python3");
    cmd.arg(compare_script.to_string_lossy().as_ref())
        .arg("--dataset").arg(&arguments.dataset)
        .arg("--backend").arg(&arguments.backend)
        .arg("--order").arg(&arguments.order)
        .arg("--pdf-set").arg(&arguments.pdf_set)
        .arg("--pdf-member").arg(arguments.pdf_member.to_string())
        .arg("--output").arg(&arguments.output);
        
    let status = cmd.status().map_err(|err| {
        Error::Msg(format!("Failed to execute python validation script: {err}"))
    })?;
    
    if !status.success() {
        let code = status.code().unwrap_or(-1);
        return Err(Error::Msg(format!("Validation pipeline failed with exit code: {code}")));
    }
    
    let summary_path = arguments.output.join(&arguments.dataset).join("summary.json");
    if summary_path.is_file() {
        let summary_text = std::fs::read_to_string(&summary_path).map_err(Error::wrap)?;
        let summary: serde_json::Value = serde_json::from_str(&summary_text)
            .map_err(|err| Error::Msg(format!("failed to parse summary.json: {err}")))?;
        
        println!("\n============================================================");
        println!("Validation Summary (summary.json)");
        println!("============================================================");
        println!("Number of Points:       {}", summary["number_of_points"]);
        println!("Uncorrelated Chi2:      {:.3}", summary["chi_square_uncorrelated"]);
        println!("Full Covariance Chi2:   {:.3}", summary["chi_square"]);
        println!("Degrees of Freedom:     {}", summary["degrees_of_freedom"]);
        println!("Chi2 / NDF:             {:.3}", summary["chi_square_per_ndf"]);
        println!("Mean Ratio (D/T):       {:.4}", summary["mean_ratio"]);
        println!("Max Absolute Pull:      {:.3}", summary["maximum_absolute_pull"]);
        println!("============================================================\n");
    } else {
        println!("Warning: summary.json not found under {}", summary_path.display());
    }
    
    Ok(())
}

fn parse_theory_uncertainties_command(args: &[String]) -> std::result::Result<TheoryUncertaintiesCliArgs, String> {
    if matches!(args, [flag] if flag == "-h" || flag == "--help") {
        return Err("theory-uncertainties --dataset <DATASET_ID> --backend apfel --order NLO --pdf-set <SET> [--pdf-uncertainty] [--scale-variations] --output outputs/uncertainties/".to_owned());
    }
    
    let mut dataset = None;
    let mut backend = None;
    let mut order = None;
    let mut pdf_set = None;
    let mut pdf_member = Some(0);
    let mut pdf_uncertainty = false;
    let mut scale_variations = false;
    let mut output = None;
    let mut index = 0;
    
    while index < args.len() {
        let flag = args[index].as_str();
        if flag == "-h" || flag == "--help" {
            return Err("--help must be used by itself after theory-uncertainties".to_string());
        }
        if flag == "--pdf-uncertainty" {
            pdf_uncertainty = true;
            index += 1;
            continue;
        }
        if flag == "--scale-variations" {
            scale_variations = true;
            index += 1;
            continue;
        }
        if !matches!(
            flag,
            "--dataset" | "--backend" | "--order" | "--pdf-set" | "--pdf-member" | "--output"
        ) {
            return Err(format!("unknown theory-uncertainties option: {flag}"));
        }
        
        let value_text = args
            .get(index + 1)
            .filter(|value| !value.starts_with("--"))
            .ok_or_else(|| format!("{flag} requires a value"))?;
            
        match flag {
            "--dataset" => dataset = Some(value_text.clone()),
            "--backend" => backend = Some(value_text.clone()),
            "--order" => order = Some(value_text.clone()),
            "--pdf-set" => pdf_set = Some(value_text.clone()),
            "--pdf-member" => {
                let parsed = value_text
                    .parse::<i32>()
                    .map_err(|_| format!("invalid integer for --pdf-member: {value_text}"))?;
                pdf_member = Some(parsed);
            }
            "--output" => output = Some(PathBuf::from(value_text)),
            _ => unreachable!(),
        }
        index += 2;
    }
    
    Ok(TheoryUncertaintiesCliArgs {
        dataset: dataset.ok_or_else(|| "missing required option: --dataset".to_owned())?,
        backend: backend.ok_or_else(|| "missing required option: --backend".to_owned())?,
        order: order.ok_or_else(|| "missing required option: --order".to_owned())?,
        pdf_set: pdf_set.ok_or_else(|| "missing required option: --pdf-set".to_owned())?,
        pdf_member: pdf_member.unwrap_or(0),
        pdf_uncertainty,
        scale_variations,
        output: output.ok_or_else(|| "missing required option: --output".to_owned())?,
    })
}

fn run_theory_uncertainties(arguments: TheoryUncertaintiesCliArgs) -> Result<()> {
    if arguments.backend != "apfel" {
        return Err(Error::Msg(format!("Unsupported backend: {}. Only 'apfel' is supported currently.", arguments.backend)));
    }
    if arguments.order != "LO" && arguments.order != "NLO" {
        return Err(Error::Msg(format!("Unsupported order: {}. Only 'LO' or 'NLO' is supported.", arguments.order)));
    }
    
    let compare_script = PathBuf::from("analysis/validation/compare_uncertainty.py");
    if !compare_script.is_file() {
        return Err(Error::Msg("compare_uncertainty.py script not found".to_string()));
    }
    
    println!("Launching theory uncertainties pipeline via Python...");
    
    let mut cmd = std::process::Command::new("python3");
    cmd.arg(compare_script.to_string_lossy().as_ref())
        .arg("--dataset").arg(&arguments.dataset)
        .arg("--backend").arg(&arguments.backend)
        .arg("--order").arg(&arguments.order)
        .arg("--pdf-set").arg(&arguments.pdf_set)
        .arg("--pdf-member").arg(arguments.pdf_member.to_string())
        .arg("--output").arg(&arguments.output);
        
    if arguments.pdf_uncertainty {
        cmd.arg("--pdf-uncertainty");
    }
    if arguments.scale_variations {
        cmd.arg("--scale-variations");
    }
        
    let status = cmd.status().map_err(|err| {
        Error::Msg(format!("Failed to execute python script: {err}"))
    })?;
    
    if !status.success() {
        let code = status.code().unwrap_or(-1);
        return Err(Error::Msg(format!("Theory uncertainties pipeline failed with exit code: {code}")));
    }
    
    let summary_path = arguments.output.join(&arguments.dataset).join("summary.json");
    if summary_path.is_file() {
        let summary_text = std::fs::read_to_string(&summary_path).map_err(Error::wrap)?;
        let summary: serde_json::Value = serde_json::from_str(&summary_text)
            .map_err(|err| Error::Msg(format!("failed to parse summary.json: {err}")))?;
        
        println!("\n============================================================");
        println!("Theory Uncertainties Summary (summary.json)");
        println!("============================================================");
        println!("Number of Points:       {}", summary["number_of_points"]);
        println!("Full Covariance Chi2:   {:.3}", summary["chi_square"]);
        println!("Degrees of Freedom:     {}", summary["degrees_of_freedom"]);
        println!("Chi2 / NDF:             {:.3}", summary["chi_square_per_ndf"]);
        println!("Mean Ratio (D/T):       {:.4}", summary["mean_ratio"]);
        println!("Max Absolute Pull:      {:.3}", summary["maximum_absolute_pull"]);
        println!("============================================================\n");
    } else {
        println!("Warning: summary.json not found under {}", summary_path.display());
    }
    
    Ok(())
}
fn parse_structure_functions_command(args: &[String]) -> std::result::Result<StructureFunctionsCliArgs, String> {
    let mut backend = None;
    let mut x = None;
    let mut q2 = None;
    let mut order = None;
    let mut pdf_set = None;
    let mut pdf_member = None;
    let mut mu_f_over_q = 1.0;
    let mut mu_r_over_q = 1.0;
    let mut index = 0;

    while index < args.len() {
        let flag = args[index].as_str();
        let value_text = args
            .get(index + 1)
            .ok_or_else(|| format!("{flag} requires a value"))?;

        match flag {
            "--backend" => backend = Some(value_text.clone()),
            "--x" => x = Some(parse_finite_cross_number("--x", value_text)?),
            "--q2" => q2 = Some(parse_finite_cross_number("--q2", value_text)?),
            "--order" => order = Some(value_text.clone()),
            "--pdf-set" => pdf_set = Some(value_text.clone()),
            "--pdf-member" => {
                pdf_member = Some(value_text.parse::<i32>().map_err(|_| format!("invalid integer for --pdf-member: {value_text}"))?);
            }
            "--mu-f-over-q" => mu_f_over_q = parse_finite_cross_number("--mu-f-over-q", value_text)?,
            "--mu-r-over-q" => mu_r_over_q = parse_finite_cross_number("--mu-r-over-q", value_text)?,
            _ => return Err(format!("unknown option: {flag}")),
        }
        index += 2;
    }

    Ok(StructureFunctionsCliArgs {
        backend: backend.ok_or_else(|| "missing required option: --backend".to_owned())?,
        x: x.ok_or_else(|| "missing required option: --x".to_owned())?,
        q2: q2.ok_or_else(|| "missing required option: --q2".to_owned())?,
        order: order.ok_or_else(|| "missing required option: --order".to_owned())?,
        pdf_set: pdf_set.ok_or_else(|| "missing required option: --pdf-set".to_owned())?,
        pdf_member: pdf_member.unwrap_or(0),
        mu_f_over_q,
        mu_r_over_q,
    })
}

fn run_structure_functions(args: StructureFunctionsCliArgs) -> Result<()> {
    use quark_sim::physics::structure_function_provider::{
        StructureFunctionBackend, StructureFunctionProvider, StructureFunctionRequest,
        PerturbativeOrder, StructureFunctionProcess, DisProjectile, DisTarget,
    };
    use quark_sim::physics::apfel::ApfelStructureFunctionProvider;
    use quark_sim::physics::surrogate::SurrogateProvider;
    use quark_sim::physics::LoPdfStructureFunctionProvider;
    use quark_sim::physics::LhapdfProvider;
    use std::str::FromStr;

    let order = PerturbativeOrder::from_str(&args.order).map_err(|_| {
        Error::Msg(format!("Invalid perturbative order: {}", args.order))
    })?;

    let mut request = StructureFunctionRequest::electromagnetic_nc(
        args.x,
        args.q2,
        order,
        args.pdf_set.clone(),
        args.pdf_member,
    );
    request.mu_f_over_q = args.mu_f_over_q;
    request.mu_r_over_q = args.mu_r_over_q;

    let result = match args.backend.as_str() {
        "apfel" => {
            let provider = ApfelStructureFunctionProvider::new("physics-engine/build/apfel_cli");
            provider.evaluate(&request)
        }
        "surrogate" => {
            let dir = std::env::current_dir().unwrap().join("models/surrogate_v1");
            let provider = SurrogateProvider::load(&dir)
                .map_err(|e| Error::Msg(e.to_string()))?;
            provider.evaluate(&request)
        }
        "lo" => {
            let pdf = LhapdfProvider::new(&args.pdf_set, args.pdf_member)
                .map_err(|e| Error::Msg(e.to_string()))?;
            let provider = LoPdfStructureFunctionProvider::new(pdf, &args.pdf_set, args.pdf_member, 0, 0)
                .map_err(|e| Error::Msg(e.to_string()))?;
            provider.evaluate(&request)
        }
        other => return Err(Error::Msg(format!("Unsupported backend: {other}"))),
    }.map_err(|e| Error::Msg(e.to_string()))?;

    // Enrich with reproducibility metadata
    let mut enriched_result = result;
    enriched_result.metadata.os_arch = option_env!("OS_ARCH").map(String::from);
    enriched_result.metadata.rust_version = option_env!("RUSTC_VERSION").map(String::from);
    enriched_result.metadata.git_commit = option_env!("GIT_HASH").map(String::from);
    if let Some(dirty_str) = option_env!("GIT_DIRTY") {
        enriched_result.metadata.git_dirty = Some(dirty_str == "true");
    }

    println!("{}", serde_json::to_string(&enriched_result).unwrap());
    Ok(())
}

fn parse_train_surrogate_command(args: &[String]) -> std::result::Result<TrainSurrogateCliArgs, String> {
    let mut pdf_set = None;
    let mut pdf_member = None;
    let mut order = None;
    let mut output = None;
    let mut index = 0;

    while index < args.len() {
        let flag = args[index].as_str();
        let value_text = args
            .get(index + 1)
            .ok_or_else(|| format!("{flag} requires a value"))?;

        match flag {
            "--pdf-set" => pdf_set = Some(value_text.clone()),
            "--pdf-member" => {
                let parsed = value_text
                    .parse::<i32>()
                    .map_err(|_| format!("invalid integer for --pdf-member: {value_text}"))?;
                pdf_member = Some(parsed);
            }
            "--order" => order = Some(value_text.clone()),
            "--output" => output = Some(PathBuf::from(value_text)),
            _ => return Err(format!("unknown option: {flag}")),
        }
        index += 2;
    }

    Ok(TrainSurrogateCliArgs {
        pdf_set: pdf_set.ok_or_else(|| "missing required option: --pdf-set".to_owned())?,
        pdf_member: pdf_member.unwrap_or(0),
        order: order.unwrap_or_else(|| "NLO".to_string()),
        output: output.ok_or_else(|| "missing required option: --output".to_owned())?,
    })
}

fn run_train_surrogate(arguments: TrainSurrogateCliArgs) -> Result<()> {
    use quark_sim::physics::apfel::ApfelStructureFunctionProvider;
    use quark_sim::physics::structure_function_provider::PerturbativeOrder;
    use quark_sim::physics::surrogate_training::{generate_dataset, train_and_save_surrogate};
    use std::str::FromStr;

    println!("Starting surrogate dataset generation and training...");
    
    let order = PerturbativeOrder::from_str(&arguments.order).map_err(|_| {
        Error::Msg(format!("Invalid perturbative order: {}", arguments.order))
    })?;

    let provider = ApfelStructureFunctionProvider::new("physics-engine/build/apfel_cli");
    
    let dataset = generate_dataset(&provider, &arguments.pdf_set, arguments.pdf_member, order)
        .map_err(|e| Error::Msg(e.to_string()))?;

    train_and_save_surrogate(
        dataset,
        &arguments.output,
        arguments.pdf_set,
        arguments.pdf_member,
        order,
    ).map_err(|e| Error::Msg(e.to_string()))?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn parse(args: &[&str]) -> std::result::Result<Command, String> {
        parse_command(args.iter().map(|value| (*value).to_string()))
    }

    #[test]
    fn help_is_explicit_and_does_not_select_training() {
        assert_eq!(parse(&["--help"]), Ok(Command::Help));
        assert_eq!(parse(&["-h"]), Ok(Command::Help));
    }

    #[test]
    fn malformed_commands_are_rejected() {
        assert!(parse(&["--load"]).is_err());
        assert!(parse(&["--load-model"]).is_err());
        assert!(parse(&["--unknown"]).is_err());
        assert!(parse(&["--help", "extra"]).is_err());
        assert!(parse(&["dis-kinematics"]).is_err());
    }

    #[test]
    fn dis_help_is_explicit_and_side_effect_free() {
        assert_eq!(
            parse(&["dis-kinematics", "--help"]),
            Ok(Command::DisKinematics(DisCommand::Help))
        );
    }

    #[test]
    fn dis_options_are_parsed_in_any_order() {
        let command = parse(&[
            "dis-kinematics",
            "--theta-deg",
            "20",
            "--proton-energy",
            "920",
            "--electron-energy",
            "27.5",
            "--scattered-electron-energy",
            "15",
        ]);

        assert_eq!(
            command,
            Ok(Command::DisKinematics(DisCommand::Calculate(DisCliArgs {
                electron_energy: 27.5,
                proton_energy: 920.0,
                scattered_electron_energy: 15.0,
                theta_deg: 20.0,
            })))
        );
    }

    #[test]
    fn malformed_dis_options_are_rejected() {
        assert!(parse(&[
            "dis-kinematics",
            "--electron-energy",
            "27.5",
            "--electron-energy",
            "30",
        ])
        .is_err());
        assert!(parse(&["dis-kinematics", "--electron-energy", "not-a-number",]).is_err());
        assert!(parse(&["dis-kinematics", "--unknown", "1"]).is_err());
        assert!(parse(&[
            "dis-kinematics",
            "--electron-energy",
            "--proton-energy",
            "920"
        ])
        .is_err());
    }

    #[test]
    fn cross_section_help_is_explicit_and_side_effect_free() {
        assert_eq!(
            parse(&["dis-cross-section", "--help"]),
            Ok(Command::DisCrossSection(CrossSectionCommand::Help))
        );
    }

    #[test]
    fn cross_section_options_are_parsed_in_any_order() {
        let command = parse(&[
            "dis-cross-section",
            "--pdf-member",
            "0",
            "--q2",
            "100",
            "--proton-energy",
            "920",
            "--pdf-set",
            "CT18LO",
            "--x",
            "0.01",
            "--electron-energy",
            "27.5",
        ]);

        assert_eq!(
            command,
            Ok(Command::DisCrossSection(CrossSectionCommand::Calculate(
                CrossSectionCliArgs {
                    x: 0.01,
                    q2: 100.0,
                    electron_energy: 27.5,
                    proton_energy: 920.0,
                    pdf_set: "CT18LO".to_string(),
                    pdf_member: 0,
                }
            )))
        );
    }

    #[test]
    fn malformed_cross_section_options_are_rejected() {
        assert!(parse(&["dis-cross-section"]).is_err());
        assert!(parse(&["dis-cross-section", "--unknown", "1"]).is_err());
        assert!(parse(&["dis-cross-section", "--x", "NaN"]).is_err());
        assert!(parse(&["dis-cross-section", "--pdf-member", "-1"]).is_err());
        assert!(parse(&["dis-cross-section", "--x", "0.01", "--x", "0.02"]).is_err());
        assert!(parse(&["dis-cross-section", "--q2", "--electron-energy", "27.5"]).is_err());
    }

    #[test]
    fn model_config_is_a_sibling_with_config_suffix() -> Result<()> {
        let model = Path::new("outputs/run/trained_model.safetensors");
        assert_eq!(
            model_config_path(model)?,
            PathBuf::from("outputs/run/trained_model_config.json")
        );
        Ok(())
    }
}
