#include "apfel_backend.hpp"

#include <LHAPDF/LHAPDF.h>
#include <LHAPDF/Version.h>
#include <apfel/apfelxx.h>
#include <apfel/version.h>
#include <nlohmann/json.hpp>

#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <map>
#include <memory>
#include <sstream>
#include <utility>
#include <vector>

namespace neuronswquarks::apfel_backend
{
  namespace
  {
    constexpr int RequestErrorExitCode = 2;
    constexpr int BackendErrorExitCode = 3;

    class StdoutToStderr final
    {
    public:
      StdoutToStderr():
        _original(std::cout.rdbuf(_captured.rdbuf()))
      {
      }

      StdoutToStderr(StdoutToStderr const&) = delete;
      StdoutToStderr& operator=(StdoutToStderr const&) = delete;

      ~StdoutToStderr()
      {
        std::cout.rdbuf(_original);
        const std::string diagnostics = _captured.str();
        if (!diagnostics.empty())
          std::cerr << diagnostics;
      }

    private:
      std::ostringstream _captured;
      std::streambuf*     _original;
    };

    [[noreturn]] void invalid_request(std::string const& code,
                                      std::string const& message,
                                      std::string const& hint)
    {
      throw BackendError{code, message, hint, RequestErrorExitCode};
    }

    nlohmann::json const& required_field(nlohmann::json const& input,
                                         std::string const&    name)
    {
      if (!input.contains(name))
        invalid_request("missing_field",
                        "Required request field '" + name + "' is missing.",
                        "Send every schema-version 1 field explicitly.");
      return input.at(name);
    }

    std::string required_string(nlohmann::json const& input,
                                std::string const&    name)
    {
      nlohmann::json const& value = required_field(input, name);
      if (!value.is_string())
        invalid_request("invalid_field_type",
                        "Request field '" + name + "' must be a string.",
                        "Correct the JSON request and retry.");
      return value.get<std::string>();
    }

    int required_integer(nlohmann::json const& input,
                         std::string const&    name)
    {
      nlohmann::json const& value = required_field(input, name);
      if (!value.is_number_integer() && !value.is_number_unsigned())
        invalid_request("invalid_field_type",
                        "Request field '" + name + "' must be an integer.",
                        "Correct the JSON request and retry.");

      try
        {
          const auto integer = value.get<long long>();
          if (integer < std::numeric_limits<int>::min()
              || integer > std::numeric_limits<int>::max())
            invalid_request("invalid_field_value",
                            "Request field '" + name + "' is outside the supported integer range.",
                            "Use a 32-bit signed integer value.");
          return static_cast<int>(integer);
        }
      catch (nlohmann::json::exception const&)
        {
          invalid_request("invalid_field_value",
                          "Request field '" + name + "' is outside the supported integer range.",
                          "Use a 32-bit signed integer value.");
        }
    }

    double required_number(nlohmann::json const& input,
                           std::string const&    name)
    {
      nlohmann::json const& value = required_field(input, name);
      if (!value.is_number())
        invalid_request("invalid_field_type",
                        "Request field '" + name + "' must be numeric.",
                        "Correct the JSON request and retry.");

      double number = 0;
      try
        {
          number = value.get<double>();
        }
      catch (nlohmann::json::exception const&)
        {
          invalid_request("invalid_field_value",
                          "Request field '" + name + "' is outside the supported numeric range.",
                          "Use a finite IEEE-754 JSON number.");
        }
      if (!std::isfinite(number))
        invalid_request("invalid_field_value",
                        "Request field '" + name + "' must be finite.",
                        "Use a finite JSON number.");
      return number;
    }

    void validate_request(StructureFunctionRequest const& request)
    {
      if (request.schema_version != SchemaVersion)
        invalid_request("unsupported_schema_version",
                        "Only schema_version 1 is supported.",
                        "Set schema_version to 1.");
      if (request.process != "nc_dis")
        invalid_request("unsupported_process",
                        "Only process 'nc_dis' is supported.",
                        "Set process to 'nc_dis'.");
      if (request.projectile != "electron")
        invalid_request("unsupported_projectile",
                        "Only projectile 'electron' is supported.",
                        "Set projectile to 'electron'.");
      if (request.target != "proton")
        invalid_request("unsupported_target",
                        "Only target 'proton' is supported.",
                        "Set target to 'proton'.");
      if (request.order != PerturbativeOrder::LO
          && request.order != PerturbativeOrder::NLO)
        invalid_request("unsupported_order",
                        "Only LO and NLO perturbative orders are supported.",
                        "Set order to 'LO' or 'NLO'.");
      if (!(request.x > 0 && request.x < 1))
        invalid_request("invalid_x",
                        "Bjorken x must satisfy 0 < x < 1.",
                        "Choose a physical DIS x value.");
      if (!(request.q2 > 0) || !std::isfinite(request.q2))
        invalid_request("invalid_q2",
                        "Q2 must be finite and strictly positive.",
                        "Provide Q2 in GeV^2.");
      if (request.pdf_set.empty())
        invalid_request("invalid_pdf_set",
                        "pdf_set must not be empty.",
                        "Provide the name of an installed proton PDF set.");
      if (request.pdf_member < 0)
        invalid_request("invalid_pdf_member",
                        "pdf_member must be non-negative.",
                        "Use an installed member index, normally 0 for the central member.");
      if (!(request.mu_f_over_q > 0) || !std::isfinite(request.mu_f_over_q))
        invalid_request("invalid_factorization_scale",
                        "mu_f_over_q must be finite and strictly positive.",
                        "Use a positive factorization-scale ratio such as 0.5, 1, or 2.");
      if (!(request.mu_r_over_q > 0) || !std::isfinite(request.mu_r_over_q))
        invalid_request("invalid_renormalization_scale",
                        "mu_r_over_q must be finite and strictly positive.",
                        "Use a positive renormalization-scale ratio such as 0.5, 1, or 2.");
    }

    std::unique_ptr<LHAPDF::PDF> load_pdf(StructureFunctionRequest const& request)
    {
      try
        {
          return std::unique_ptr<LHAPDF::PDF>{LHAPDF::mkPDF(request.pdf_set,
                                                            request.pdf_member)};
        }
      catch (std::exception const& error)
        {
          throw BackendError{
            "pdf_unavailable",
            "LHAPDF could not load set '" + request.pdf_set + "', member "
              + std::to_string(request.pdf_member) + ": " + error.what(),
            "Install the requested set, check LHAPDF_DATA_PATH, and verify the member index.",
            BackendErrorExitCode};
        }
    }

    StructureFunctionResult evaluate_impl(StructureFunctionRequest const& request)
    {
      std::unique_ptr<LHAPDF::PDF> pdf = load_pdf(request);

      int pdf_order_qcd = 0;
      int data_version = 0;
      std::vector<double> thresholds;
      try
        {
          pdf_order_qcd = pdf->orderQCD();
          data_version = pdf->dataversion();
          thresholds = {0,
                        0,
                        0,
                        pdf->quarkThreshold(4),
                        pdf->quarkThreshold(5),
                        pdf->quarkThreshold(6)};
        }
      catch (std::exception const& error)
        {
          throw BackendError{
            "pdf_metadata_error",
            "Required LHAPDF metadata could not be read: " + std::string{error.what()},
            "Use a standard proton PDF set with OrderQCD and heavy-quark threshold metadata.",
            BackendErrorExitCode};
        }

      const int requested_order = static_cast<int>(request.order);
      if (pdf_order_qcd < requested_order)
        throw BackendError{
          "pdf_order_mismatch",
          "The requested " + order_name(request.order) + " coefficient order requires a PDF set "
            "with OrderQCD >= " + std::to_string(requested_order) + ", but '"
            + request.pdf_set + "' reports OrderQCD=" + std::to_string(pdf_order_qcd) + ".",
          "Select a matching NLO proton PDF set for an NLO calculation.",
          BackendErrorExitCode};

      const double q = std::sqrt(request.q2);
      const double mu_f = q * request.mu_f_over_q;
      const double mu_r = q * request.mu_r_over_q;
      if (!std::isfinite(q) || !std::isfinite(mu_f) || !std::isfinite(mu_r))
        throw BackendError{
          "scale_overflow",
          "The requested Q or derived scale is not finite.",
          "Reduce Q2 or the scale ratios.",
          BackendErrorExitCode};

      if (!pdf->inRangeX(request.x))
        throw BackendError{
          "x_outside_pdf_grid",
          "The requested x is outside the selected LHAPDF grid.",
          "Choose x inside [" + std::to_string(pdf->xMin()) + ", "
            + std::to_string(pdf->xMax()) + "].",
          BackendErrorExitCode};
      if (!pdf->inRangeQ(mu_f))
        throw BackendError{
          "factorization_scale_outside_pdf_grid",
          "mu_f = (mu_f_over_q * Q) is outside the selected LHAPDF grid.",
          "Choose a ratio giving mu_f inside [" + std::to_string(pdf->qMin()) + ", "
            + std::to_string(pdf->qMax()) + "] GeV.",
          BackendErrorExitCode};
      if (!pdf->inRangeQ(mu_r))
        throw BackendError{
          "renormalization_scale_outside_pdf_grid",
          "mu_r = (mu_r_over_q * Q) is outside the selected LHAPDF alpha_s grid.",
          "Choose a ratio giving mu_r inside [" + std::to_string(pdf->qMin()) + ", "
            + std::to_string(pdf->qMax()) + "] GeV.",
          BackendErrorExitCode};

      const double grid_x_min = std::max(pdf->xMin(),
                                         std::min(1e-5, request.x / 10));
      if (!(grid_x_min > 0 && grid_x_min < 0.1) || pdf->xMax() < 1)
        throw BackendError{
          "unsupported_pdf_grid",
          "The selected PDF grid cannot cover the APFEL++ convolution grid.",
          "Use a proton PDF set covering x from at most 0.1 through 1.",
          BackendErrorExitCode};

      const apfel::Grid grid{{apfel::SubGrid{100, grid_x_min, 3},
                              apfel::SubGrid{60, 1e-1, 3},
                              apfel::SubGrid{50, 6e-1, 3},
                              apfel::SubGrid{50, 8e-1, 3}}};

      const auto distributions = [&pdf](double const& x, double const& mu) {
        return apfel::PhysToQCDEv(pdf->xfxQ(x, mu));
      };
      const auto alpha_s = [&pdf](double const& mu) {
        return pdf->alphasQ(mu);
      };
      const auto electromagnetic_charges = [](double const&) {
        return apfel::QCh2;
      };
      const auto zero_parity_violating_charges = [](double const&) {
        return std::vector<double>(6, 0);
      };

      try
        {
          const auto f2 = apfel::BuildStructureFunctions(
            apfel::InitializeF2NCObjectsZM(grid, thresholds),
            distributions,
            requested_order,
            alpha_s,
            electromagnetic_charges,
            request.mu_r_over_q,
            request.mu_f_over_q);
          const auto fl = apfel::BuildStructureFunctions(
            apfel::InitializeFLNCObjectsZM(grid, thresholds),
            distributions,
            requested_order,
            alpha_s,
            electromagnetic_charges,
            request.mu_r_over_q,
            request.mu_f_over_q);
          const auto xf3 = apfel::BuildStructureFunctions(
            apfel::InitializeF3NCObjectsZM(grid, thresholds),
            distributions,
            requested_order,
            alpha_s,
            zero_parity_violating_charges,
            request.mu_r_over_q,
            request.mu_f_over_q);

          std::string pdf_error_type = "unknown";
          int pdf_size = 0;
          try {
              LHAPDF::PDFSet set(request.pdf_set);
              pdf_error_type = set.errorType();
              pdf_size = set.size();
          } catch (...) {}

          StructureFunctionResult result;
          result.f2 = f2.at(0).Evaluate(q).Evaluate(request.x);
          result.fl = fl.at(0).Evaluate(q).Evaluate(request.x);
          result.xf3 = xf3.at(0).Evaluate(q).Evaluate(request.x);
          result.metadata = {VERSION,
                             LHAPDF::version(),
                             request.pdf_set,
                             pdf->memberID(),
                             pdf_order_qcd,
                             data_version,
                             order_name(request.order),
                             request.process,
                             request.projectile,
                             request.target,
                             request.mu_f_over_q,
                             request.mu_r_over_q,
                             "ZM-VFNS",
                             "photon_exchange",
                             pdf_error_type,
                             pdf_size};

          // Evaluate multiple PDF members
          for (int m : request.pdf_members) {
              std::unique_ptr<LHAPDF::PDF> member_pdf{LHAPDF::mkPDF(request.pdf_set, m)};
              const auto member_dist = [&member_pdf](double const& x, double const& mu) {
                  return apfel::PhysToQCDEv(member_pdf->xfxQ(x, mu));
              };
              const auto member_f2 = apfel::BuildStructureFunctions(
                  apfel::InitializeF2NCObjectsZM(grid, thresholds),
                  member_dist,
                  requested_order,
                  alpha_s,
                  electromagnetic_charges,
                  request.mu_r_over_q,
                  request.mu_f_over_q);
              const auto member_fl = apfel::BuildStructureFunctions(
                  apfel::InitializeFLNCObjectsZM(grid, thresholds),
                  member_dist,
                  requested_order,
                  alpha_s,
                  electromagnetic_charges,
                  request.mu_r_over_q,
                  request.mu_f_over_q);
              result.f2_pdf_members.push_back(member_f2.at(0).Evaluate(q).Evaluate(request.x));
              result.fl_pdf_members.push_back(member_fl.at(0).Evaluate(q).Evaluate(request.x));
          }

          // Evaluate scale variations
          for (const auto& scales : request.scale_members) {
              double mu_r_ratio = scales[0];
              double mu_f_ratio = scales[1];
              const auto scale_f2 = apfel::BuildStructureFunctions(
                  apfel::InitializeF2NCObjectsZM(grid, thresholds),
                  distributions,
                  requested_order,
                  alpha_s,
                  electromagnetic_charges,
                  mu_r_ratio,
                  mu_f_ratio);
              const auto scale_fl = apfel::BuildStructureFunctions(
                  apfel::InitializeFLNCObjectsZM(grid, thresholds),
                  distributions,
                  requested_order,
                  alpha_s,
                  electromagnetic_charges,
                  mu_r_ratio,
                  mu_f_ratio);
              result.f2_scale_members.push_back(scale_f2.at(0).Evaluate(q).Evaluate(request.x));
              result.fl_scale_members.push_back(scale_fl.at(0).Evaluate(q).Evaluate(request.x));
          }

          if (!std::isfinite(result.f2)
              || !std::isfinite(result.fl)
              || !std::isfinite(result.xf3))
            throw BackendError{
              "non_finite_result",
              "APFEL++ returned a non-finite structure function.",
              "Check the requested point, scales, and PDF-set validity.",
              BackendErrorExitCode};

          return result;
        }
      catch (BackendError const&)
        {
          throw;
        }
      catch (std::exception const& error)
        {
          throw BackendError{
            "apfel_evaluation_failed",
            "APFEL++ could not evaluate the requested structure functions: "
              + std::string{error.what()},
            "Verify the APFEL++ installation, PDF grid, and requested scales.",
            BackendErrorExitCode};
        }
    }
  }

  BackendError::BackendError(std::string code,
                             std::string message,
                             std::string hint,
                             int         exit_code):
    std::runtime_error{std::move(message)},
    _code{std::move(code)},
    _hint{std::move(hint)},
    _exit_code{exit_code}
  {
  }

  std::string const& BackendError::code() const noexcept
  {
    return _code;
  }

  std::string const& BackendError::hint() const noexcept
  {
    return _hint;
  }

  int BackendError::exit_code() const noexcept
  {
    return _exit_code;
  }

  std::string order_name(PerturbativeOrder const order)
  {
    switch (order)
      {
      case PerturbativeOrder::LO:
        return "LO";
      case PerturbativeOrder::NLO:
        return "NLO";
      }
    throw BackendError{"unsupported_order",
                       "Only LO and NLO perturbative orders are supported.",
                       "Set order to 'LO' or 'NLO'.",
                       RequestErrorExitCode};
  }

  StructureFunctionRequest request_from_json(nlohmann::json const& input)
  {
    if (!input.is_object())
      invalid_request("invalid_request",
                      "The protocol request must be a JSON object.",
                      "Send one schema-version 1 JSON object on stdin.");

    StructureFunctionRequest request;
    request.schema_version = required_integer(input, "schema_version");
    request.process = required_string(input, "process");
    request.projectile = required_string(input, "projectile");
    request.target = required_string(input, "target");
    request.x = required_number(input, "x");
    request.q2 = required_number(input, "q2");

    const std::string order = required_string(input, "order");
    if (order == "LO")
      request.order = PerturbativeOrder::LO;
    else if (order == "NLO")
      request.order = PerturbativeOrder::NLO;
    else
      invalid_request("unsupported_order",
                      "Only order 'LO' or 'NLO' is supported.",
                      "Use an uppercase schema order value: 'LO' or 'NLO'.");

    request.pdf_set = required_string(input, "pdf_set");
    request.pdf_member = required_integer(input, "pdf_member");
    request.mu_f_over_q = required_number(input, "mu_f_over_q");
    request.mu_r_over_q = required_number(input, "mu_r_over_q");
    
    if (input.contains("pdf_members")) {
        for (const auto& item : input["pdf_members"]) {
            request.pdf_members.push_back(item.get<int>());
        }
    }
    if (input.contains("scale_members")) {
        for (const auto& item : input["scale_members"]) {
            request.scale_members.push_back(item.get<std::vector<double>>());
        }
    }

    validate_request(request);
    return request;
  }

  StructureFunctionResult evaluate(StructureFunctionRequest const& request)
  {
    validate_request(request);

    StdoutToStderr redirect;
    apfel::SetVerbosityLevel(0);
    LHAPDF::setVerbosity(0);
    return evaluate_impl(request);
  }

  nlohmann::json success_response(StructureFunctionResult const& result)
  {
    return {{"schema_version", SchemaVersion},
            {"success", true},
            {"f2", result.f2},
            {"fl", result.fl},
            {"xf3", result.xf3},
            {"f2_pdf_members", result.f2_pdf_members},
            {"fl_pdf_members", result.fl_pdf_members},
            {"f2_scale_members", result.f2_scale_members},
            {"fl_scale_members", result.fl_scale_members},
            {"metadata",
             {{"backend", "apfel"},
              {"apfelxx_version", result.metadata.apfelxx_version},
              {"lhapdf_version", result.metadata.lhapdf_version},
              {"pdf_set", result.metadata.pdf_set},
              {"pdf_member", result.metadata.pdf_member},
              {"pdf_order_qcd", result.metadata.pdf_order_qcd},
              {"pdf_data_version", result.metadata.data_version},
              {"data_version", result.metadata.data_version},
              {"order", result.metadata.order},
              {"process", result.metadata.process},
              {"projectile", result.metadata.projectile},
              {"target", result.metadata.target},
              {"mu_f_over_q", result.metadata.mu_f_over_q},
              {"mu_r_over_q", result.metadata.mu_r_over_q},
              {"scheme", result.metadata.scheme},
              {"electromagnetic_mode", result.metadata.electromagnetic_mode},
              {"pdf_error_type", result.metadata.pdf_error_type},
              {"pdf_size", result.metadata.pdf_size}}}};
  }

  nlohmann::json error_response(std::string const& code,
                                std::string const& message,
                                std::string const& hint)
  {
    return {{"schema_version", SchemaVersion},
            {"success", false},
            {"error", {{"code", code}, {"message", message}, {"hint", hint}}}};
  }
}
