#pragma once

#include <nlohmann/json.hpp>
#include <string>
#include <vector>

namespace neuronswquarks::pythia_dis_generator
{
  inline constexpr int SchemaVersion = 1;

  struct DisEventRequest
  {
    int         schema_version = SchemaVersion;
    std::string process = "neutral_current_dis";
    double      electron_energy_gev = 27.5;
    double      proton_energy_gev = 920.0;
    double      q2_min_gev2 = 10.0;
    double      q2_max_gev2 = 10000.0;
    double      x_min = 0.0001;
    double      x_max = 0.8;
    double      y_min = 0.01;
    double      y_max = 0.95;
    int         number_of_events = 10000;
    int         random_seed = -1;
    std::string pdf_set = "";
    int         pdf_member = 0;
    bool        parton_shower = true;
    bool        hadronization = true;
  };

  struct EventObservables
  {
    int    event_number = 0;
    double event_weight = 1.0;
    double q2_true = 0.0;
    double x_true = 0.0;
    double y_true = 0.0;
    double w2_true = 0.0;
    double q2_reco = 0.0;
    double x_reco = 0.0;
    double y_reco = 0.0;
    double w2_reco = 0.0;
    double scattered_electron_e = 0.0;
    double scattered_electron_px = 0.0;
    double scattered_electron_py = 0.0;
    double scattered_electron_pz = 0.0;
    int    num_final_state_particles = 0;
    int    num_charged_final_state_particles = 0;
  };

  struct RunSummary
  {
    int    requested_events = 0;
    int    attempted_events = 0;
    int    accepted_events = 0;
    int    failed_events = 0;
    int    vetoed_cuts_events = 0;
    int    vetoed_conservation_events = 0;
    double max_momentum_mismatch_gev = 0.0;
    double max_energy_mismatch_gev = 0.0;
    double momentum_conservation_tolerance_gev = 1.0e-3;
  };

  class GeneratorError : public std::runtime_error
  {
  public:
    GeneratorError(std::string code, std::string message, std::string hint, int exit_code)
      : std::runtime_error(message), _code(std::move(code)), _hint(std::move(hint)), _exit_code(exit_code) {}

    [[nodiscard]] std::string const& code() const noexcept { return _code; }
    [[nodiscard]] std::string const& hint() const noexcept { return _hint; }
    [[nodiscard]] int                exit_code() const noexcept { return _exit_code; }

  private:
    std::string _code;
    std::string _hint;
    int         _exit_code;
  };

  [[nodiscard]] DisEventRequest request_from_json(nlohmann::json const& input);

  void run_generator(DisEventRequest const& request, std::string const& output_dir);

  [[nodiscard]] nlohmann::json error_response(std::string const& code,
                                              std::string const& message,
                                              std::string const& hint);
}
