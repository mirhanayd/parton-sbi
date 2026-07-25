#include "pythia_dis_generator.hpp"
#include "Pythia8/Pythia.h"
#include "Pythia8Plugins/HepMC3.h"
#include "HepMC3/WriterAscii.h"
#include "HepMC3/GenEvent.h"
#include "LHAPDF/Version.h"

#include <iostream>
#include <fstream>
#include <sstream>
#include <cmath>
#include <iomanip>
#include <chrono>
#include <algorithm>
#include <stdexcept>

#ifndef PYTHIA8_VERSION_STR
#define PYTHIA8_VERSION_STR "unknown"
#endif

#ifndef HEPMC3_VERSION_STR
#define HEPMC3_VERSION_STR "unknown"
#endif

#ifndef LHAPDF_VERSION_STR
#define LHAPDF_VERSION_STR "unknown"
#endif

#ifndef GIT_COMMIT_STR
#define GIT_COMMIT_STR "unknown"
#endif

#ifndef BUILD_TIMESTAMP_STR
#define BUILD_TIMESTAMP_STR "unknown"
#endif

namespace neuronswquarks::pythia_dis_generator
{
  DisEventRequest request_from_json(nlohmann::json const& input)
  {
    DisEventRequest req;
    if (input.contains("schema_version"))
      {
        req.schema_version = input.at("schema_version").get<int>();
      }
    if (req.schema_version != SchemaVersion)
      {
        throw GeneratorError("invalid_schema_version",
                             "Unsupported schema version: " + std::to_string(req.schema_version),
                             "Use schema version 1.", 2);
      }
    if (input.contains("process"))
      {
        req.process = input.at("process").get<std::string>();
      }
    if (req.process != "neutral_current_dis")
      {
        throw GeneratorError("invalid_process",
                             "Unsupported process: " + req.process,
                             "Only neutral_current_dis is supported.", 2);
      }
    if (input.contains("electron_energy_gev"))
      {
        req.electron_energy_gev = input.at("electron_energy_gev").get<double>();
      }
    if (input.contains("proton_energy_gev"))
      {
        req.proton_energy_gev = input.at("proton_energy_gev").get<double>();
      }
    if (input.contains("q2_min_gev2"))
      {
        req.q2_min_gev2 = input.at("q2_min_gev2").get<double>();
      }
    if (input.contains("q2_max_gev2"))
      {
        req.q2_max_gev2 = input.at("q2_max_gev2").get<double>();
      }
    if (input.contains("x_min"))
      {
        req.x_min = input.at("x_min").get<double>();
      }
    if (input.contains("x_max"))
      {
        req.x_max = input.at("x_max").get<double>();
      }
    if (input.contains("y_min"))
      {
        req.y_min = input.at("y_min").get<double>();
      }
    if (input.contains("y_max"))
      {
        req.y_max = input.at("y_max").get<double>();
      }
    if (input.contains("number_of_events"))
      {
        req.number_of_events = input.at("number_of_events").get<int>();
      }
    if (input.contains("random_seed"))
      {
        req.random_seed = input.at("random_seed").get<int>();
      }
    if (input.contains("pdf_set"))
      {
        req.pdf_set = input.at("pdf_set").get<std::string>();
      }
    if (input.contains("pdf_member"))
      {
        req.pdf_member = input.at("pdf_member").get<int>();
      }
    if (input.contains("parton_shower"))
      {
        req.parton_shower = input.at("parton_shower").get<bool>();
      }
    if (input.contains("hadronization"))
      {
        req.hadronization = input.at("hadronization").get<bool>();
      }

    // High level kinematic validation
    if (req.electron_energy_gev <= 0.0 || req.proton_energy_gev <= 0.0)
      {
        throw GeneratorError("invalid_beam_energies",
                             "Beam energies must be positive.",
                             "Provide positive energies for electron and proton.", 2);
      }
    if (req.q2_min_gev2 <= 0.0 || req.q2_max_gev2 <= req.q2_min_gev2)
      {
        throw GeneratorError("invalid_cuts",
                             "Invalid Q2 cuts: Q2_min must be positive and less than Q2_max.",
                             "Ensure 0 < q2_min < q2_max.", 2);
      }
    if (req.x_min <= 0.0 || req.x_max <= req.x_min || req.x_max >= 1.0)
      {
        throw GeneratorError("invalid_cuts",
                             "Invalid x cuts: x_min must be positive and less than x_max (which must be < 1.0).",
                             "Ensure 0 < x_min < x_max < 1.", 2);
      }
    if (req.y_min <= 0.0 || req.y_max <= req.y_min || req.y_max >= 1.0)
      {
        throw GeneratorError("invalid_cuts",
                             "Invalid y cuts: y_min must be positive and less than y_max (which must be < 1.0).",
                             "Ensure 0 < y_min < y_max < 1.", 2);
      }
    if (req.number_of_events <= 0)
      {
        throw GeneratorError("invalid_event_count",
                             "Number of events must be positive.",
                             "Set number_of_events >= 1.", 2);
      }

    return req;
  }

  // Tracer to identify final-state scattered electron descended from incoming electron
  static int find_scattered_electron(const Pythia8::Event& event, int electron_beam_idx)
  {
    for (int i = 0; i < event.size(); ++i)
      {
        if (event[i].id() == 11 && event[i].isFinal())
          {
            int current = i;
            while (current > 0)
              {
                if (current == electron_beam_idx)
                  {
                    return i;
                  }
                current = event[current].mother1();
              }
          }
      }
    // Fallback: search for any final-state electron
    for (int i = 0; i < event.size(); ++i)
      {
        if (event[i].id() == 11 && event[i].isFinal())
          {
            return i;
          }
      }
    return -1;
  }

  void run_generator(DisEventRequest const& request, std::string const& output_dir)
  {
    Pythia8::Pythia pythia;

    // Beam settings
    pythia.readString("Beams:idA = 11");      // electron
    pythia.readString("Beams:idB = 2212");    // proton
    pythia.readString("Beams:frameType = 2"); // unequal beam energies
    pythia.readString("Beams:eA = " + std::to_string(request.electron_energy_gev));
    pythia.readString("Beams:eB = " + std::to_string(request.proton_energy_gev));

    // Process selection: t-channel electroweak boson exchange (neutral current DIS)
    pythia.readString("WeakBosonExchange:ff2ff(t:gmZ) = on");

    // Phase space cuts
    pythia.readString("PhaseSpace:Q2Min = " + std::to_string(request.q2_min_gev2));

    // Recommended for t-channel exchange (DIS) processes
    pythia.readString("SpaceShower:dipoleRecoil = on");

    // Random seed configuration
    if (request.random_seed >= 0)
      {
        pythia.readString("Random:setSeed = on");
        pythia.readString("Random:seed = " + std::to_string(request.random_seed));
      }
    else
      {
        // Enforce explicit seed or random one if not provided, avoiding same implicit seed
        pythia.readString("Random:setSeed = on");
        unsigned int generated_seed = std::chrono::system_clock::now().time_since_epoch().count() % 900000000;
        pythia.readString("Random:seed = " + std::to_string(generated_seed));
      }

    // PDF Configuration
    if (!request.pdf_set.empty())
      {
        // PDF set and member configuration
        pythia.readString("PDF:pSet = LHAPDF6:" + request.pdf_set + "/" + std::to_string(request.pdf_member));
      }

    // Parton Shower switches
    if (!request.parton_shower)
      {
        pythia.readString("PartonLevel:ISR = off");
        pythia.readString("PartonLevel:FSR = off");
        pythia.readString("PartonLevel:MPI = off");
      }
    else
      {
        pythia.readString("PartonLevel:ISR = on");
        pythia.readString("PartonLevel:FSR = on");
        pythia.readString("PartonLevel:MPI = off"); // MPI is typically disabled for DIS
      }

    // Hadronization switches
    if (!request.hadronization)
      {
        pythia.readString("HadronLevel:all = off");
      }
    else
      {
        pythia.readString("HadronLevel:all = on");
      }

    // Mute detailed process listings to keep logs readable unless there's an error
    pythia.readString("Init:showChangedSettings = on");
    pythia.readString("Init:showAllSettings = off");
    pythia.readString("Init:showMultipartonInteractions = off");
    pythia.readString("Init:showProcesses = off");

    // Initialize Pythia
    if (!pythia.init())
      {
        throw GeneratorError("pythia_init_failed",
                             "PYTHIA initialization failed.",
                             "Check configured parameters, LHAPDF environment path, or beam constraints.", 3);
      }

    // Setup HepMC3 output
    std::string hepmc3_filename = output_dir + "/events.hepmc3";
    HepMC3::Pythia8ToHepMC3 toHepMC;
    HepMC3::WriterAscii ascii_io(hepmc3_filename);

    // Setup CSV output
    std::string csv_filename = output_dir + "/inclusive_observables.csv";
    std::ofstream csv_file(csv_filename);
    if (!csv_file.is_open())
      {
        throw GeneratorError("io_error",
                             "Failed to open output CSV file.",
                             "Ensure output directory path is correct and writable.", 4);
      }
    csv_file << "event_number,event_weight,Q2,x,y,W2,"
             << "scattered_electron_E,scattered_electron_px,scattered_electron_py,scattered_electron_pz,"
             << "number_of_final_state_particles,number_of_charged_final_state_particles,"
             << "Q2_reco,x_reco,y_reco,W2_reco,Q2_mismatch,x_mismatch,y_mismatch,W2_mismatch\n";

    // Setup stats tracking
    RunSummary stats;
    stats.requested_events = request.number_of_events;
    std::vector<std::string> failure_reasons;

    // Kinematic constraints
    double tolerance = stats.momentum_conservation_tolerance_gev;

    // Main Event Loop
    int accepted_count = 0;
    int attempted_count = 0;

    while (accepted_count < request.number_of_events)
      {
        attempted_count++;
        stats.attempted_events = attempted_count;

        // Try to generate next event
        if (!pythia.next())
          {
            stats.failed_events++;
            failure_reasons.push_back("pythia_next_failed");
            continue;
          }

        // 1. Find the beams (indices 1 & 2)
        int electron_beam_idx = (pythia.event[1].id() == 11) ? 1 : ((pythia.event[2].id() == 11) ? 2 : -1);
        int proton_beam_idx = (pythia.event[1].id() == 2212) ? 1 : ((pythia.event[2].id() == 2212) ? 2 : -1);

        if (electron_beam_idx == -1 || proton_beam_idx == -1)
          {
            stats.failed_events++;
            failure_reasons.push_back("invalid_beam_particles");
            continue;
          }

        const auto& e_beam = pythia.event[electron_beam_idx];
        const auto& p_beam = pythia.event[proton_beam_idx];

        // 2. Identify the scattered electron in the final state
        int scattered_idx = find_scattered_electron(pythia.event, electron_beam_idx);
        if (scattered_idx == -1)
          {
            stats.failed_events++;
            failure_reasons.push_back("scattered_electron_not_found");
            continue;
          }
        const auto& e_scattered = pythia.event[scattered_idx];

        // 3. Extract the hard scattering values directly from Pythia Info
        double q2_true = -pythia.info.tHat();
        double x_true = pythia.info.x2(); // parton x of beam B (proton)
        // Reconstruct y from Q2 and x
        double y_true = q2_true / (pythia.info.s() * x_true);
        double w2_true = p_beam.m2() + q2_true * (1.0 / x_true - 1.0);

        // 4. Reconstruct variables using Four-Vectors
        // q = k_beam - k_scattered
        double q_e  = e_beam.e()  - e_scattered.e();
        double q_px = e_beam.px() - e_scattered.px();
        double q_py = e_beam.py() - e_scattered.py();
        double q_pz = e_beam.pz() - e_scattered.pz();

        // Q2_reco = -q^2 = q_x^2 + q_y^2 + q_z^2 - q_e^2
        double q2_reco = q_px*q_px + q_py*q_py + q_pz*q_pz - q_e*q_e;

        // P . q
        double P_dot_q = p_beam.e()*q_e - p_beam.px()*q_px - p_beam.py()*q_py - p_beam.pz()*q_pz;
        // P . k
        double P_dot_k = p_beam.e()*e_beam.e() - p_beam.px()*e_beam.px() - p_beam.py()*e_beam.py() - p_beam.pz()*e_beam.pz();

        double x_reco = q2_reco / (2.0 * P_dot_q);
        double y_reco = P_dot_q / P_dot_k;

        double W_e = p_beam.e() + q_e;
        double W_px = p_beam.px() + q_px;
        double W_py = p_beam.py() + q_py;
        double W_pz = p_beam.pz() + q_pz;
        double w2_reco = W_e*W_e - W_px*W_px - W_py*W_py - W_pz*W_pz;

        // 5. Validation Check: Finite vectors (No NaN / Inf)
        bool finite_vectors = std::isfinite(e_scattered.e()) && std::isfinite(e_scattered.px()) &&
                              std::isfinite(e_scattered.py()) && std::isfinite(e_scattered.pz()) &&
                              std::isfinite(q2_reco) && std::isfinite(x_reco) &&
                              std::isfinite(y_reco) && std::isfinite(w2_reco);

        if (!finite_vectors)
          {
            stats.failed_events++;
            failure_reasons.push_back("nan_or_inf_detected");
            continue;
          }

        // 6. Validation Check: Kinematic cuts (applied to reconstructed values to be safe)
        bool cuts_satisfied = (q2_reco >= request.q2_min_gev2 && q2_reco <= request.q2_max_gev2) &&
                              (x_reco >= request.x_min && x_reco <= request.x_max) &&
                              (y_reco >= request.y_min && y_reco <= request.y_max);

        if (!cuts_satisfied)
          {
            stats.vetoed_cuts_events++;
            // Do not write failed events to output, but don't fail the generator run.
            continue;
          }

        // 7. Validation Check: Momentum Conservation
        double final_px = 0.0;
        double final_py = 0.0;
        double final_pz = 0.0;
        double final_e = 0.0;
        int num_final = 0;
        int num_charged = 0;

        for (int i = 0; i < pythia.event.size(); ++i)
          {
            if (pythia.event[i].isFinal())
              {
                final_px += pythia.event[i].px();
                final_py += pythia.event[i].py();
                final_pz += pythia.event[i].pz();
                final_e += pythia.event[i].e();
                num_final++;
                if (pythia.event[i].chargeType() != 0)
                  {
                    num_charged++;
                  }
              }
          }

        double init_px = e_beam.px() + p_beam.px();
        double init_py = e_beam.py() + p_beam.py();
        double init_pz = e_beam.pz() + p_beam.pz();
        double init_e  = e_beam.e()  + p_beam.e();

        double diff_px = std::abs(final_px - init_px);
        double diff_py = std::abs(final_py - init_py);
        double diff_pz = std::abs(final_pz - init_pz);
        double diff_e  = std::abs(final_e  - init_e);

        double mismatch_p = std::max({diff_px, diff_py, diff_pz});
        double mismatch_e = diff_e;

        stats.max_momentum_mismatch_gev = std::max(stats.max_momentum_mismatch_gev, mismatch_p);
        stats.max_energy_mismatch_gev = std::max(stats.max_energy_mismatch_gev, mismatch_e);

        if (mismatch_p > tolerance || mismatch_e > tolerance)
          {
            stats.vetoed_conservation_events++;
            continue;
          }

        // 8. Event Accepted! Write to HepMC3 file
        HepMC3::GenEvent ge(HepMC3::Units::GEV, HepMC3::Units::MM);
        toHepMC.fill_next_event(pythia, &ge);
        ascii_io.write_event(ge);

        // 9. Write event observables to CSV
        double q2_mismatch = std::abs(q2_reco - q2_true);
        double x_mismatch = std::abs(x_reco - x_true);
        double y_mismatch = std::abs(y_reco - y_true);
        double w2_mismatch = std::abs(w2_reco - w2_true);

        csv_file << accepted_count << ","
                 << pythia.info.weight() << ","
                 << q2_true << ","
                 << x_true << ","
                 << y_true << ","
                 << w2_true << ","
                 << e_scattered.e() << ","
                 << e_scattered.px() << ","
                 << e_scattered.py() << ","
                 << e_scattered.pz() << ","
                 << num_final << ","
                 << num_charged << ","
                 << q2_reco << ","
                 << x_reco << ","
                 << y_reco << ","
                 << w2_reco << ","
                 << q2_mismatch << ","
                 << x_mismatch << ","
                 << y_mismatch << ","
                 << w2_mismatch << "\n";

        accepted_count++;
      }

    csv_file.close();
    pythia.stat();

    stats.accepted_events = accepted_count;

    // Write metadata.json
    std::string metadata_filename = output_dir + "/metadata.json";
    std::ofstream metadata_file(metadata_filename);
    if (metadata_file.is_open())
      {
        nlohmann::json meta;
        meta["pythia_version"] = PYTHIA8_VERSION_STR;
        meta["hepmc3_version"] = HEPMC3_VERSION_STR;
        meta["lhapdf_version"] = LHAPDF_VERSION_STR;
        meta["pdf_set"] = request.pdf_set.empty() ? "default" : request.pdf_set;
        meta["pdf_member"] = request.pdf_member;
        meta["electron_energy_gev"] = request.electron_energy_gev;
        meta["proton_energy_gev"] = request.proton_energy_gev;
        meta["cuts"] = {
          {"q2_min_gev2", request.q2_min_gev2},
          {"q2_max_gev2", request.q2_max_gev2},
          {"x_min", request.x_min},
          {"x_max", request.x_max},
          {"y_min", request.y_min},
          {"y_max", request.y_max}
        };
        meta["requested_event_count"] = request.number_of_events;
        meta["accepted_event_count"] = accepted_count;
        meta["failed_event_count"] = stats.failed_events + stats.vetoed_cuts_events + stats.vetoed_conservation_events;
        meta["random_seed"] = pythia.settings.mode("Random:seed"); // get actual seed used
        meta["git_commit"] = GIT_COMMIT_STR;
        meta["build_timestamp"] = BUILD_TIMESTAMP_STR;
        meta["parton_shower_state"] = request.parton_shower;
        meta["hadronization_state"] = request.hadronization;
        metadata_file << meta.dump(2) << "\n";
        metadata_file.close();
      }

    // Write summary.json
    std::string summary_filename = output_dir + "/summary.json";
    std::ofstream summary_file(summary_filename);
    if (summary_file.is_open())
      {
        nlohmann::json summary;
        summary["success"] = true;
        summary["requested_events"] = stats.requested_events;
        summary["attempted_events"] = stats.attempted_events;
        summary["accepted_events"] = stats.accepted_events;
        summary["failed_events"] = stats.failed_events;
        summary["vetoed_cuts_events"] = stats.vetoed_cuts_events;
        summary["vetoed_conservation_events"] = stats.vetoed_conservation_events;
        summary["max_momentum_mismatch_gev"] = stats.max_momentum_mismatch_gev;
        summary["max_energy_mismatch_gev"] = stats.max_energy_mismatch_gev;
        summary["momentum_conservation_tolerance_gev"] = stats.momentum_conservation_tolerance_gev;
        summary["failure_reasons"] = failure_reasons;
        summary_file << summary.dump(2) << "\n";
        summary_file.close();
      }
  }

  nlohmann::json error_response(std::string const& code,
                                std::string const& message,
                                std::string const& hint)
  {
    nlohmann::json response;
    response["success"] = false;
    response["error"] = {
      {"code", code},
      {"message", message},
      {"hint", hint}
    };
    return response;
  }
}
