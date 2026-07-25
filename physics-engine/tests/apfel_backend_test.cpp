#include "apfel_backend.hpp"

#include <LHAPDF/LHAPDF.h>
#include <nlohmann/json.hpp>

#include <algorithm>
#include <cmath>
#include <iostream>
#include <map>
#include <memory>
#include <string>

namespace
{
  using neuronswquarks::apfel_backend::BackendError;
  using neuronswquarks::apfel_backend::PerturbativeOrder;
  using neuronswquarks::apfel_backend::StructureFunctionRequest;
  using neuronswquarks::apfel_backend::StructureFunctionResult;

  int failures = 0;

  void check(bool const condition, std::string const& message)
  {
    if (!condition)
      {
        std::cerr << "FAIL: " << message << '\n';
        ++failures;
      }
  }

  bool approximately_equal(double const lhs,
                           double const rhs,
                           double const relative_tolerance,
                           double const absolute_tolerance = 0)
  {
    const double scale = std::max(std::abs(lhs), std::abs(rhs));
    return std::abs(lhs - rhs)
           <= std::max(absolute_tolerance, relative_tolerance * scale);
  }

  StructureFunctionRequest request(PerturbativeOrder const order)
  {
    return {1,
            "nc_dis",
            "electron",
            "proton",
            0.01,
            100,
            order,
            "CT18NLO",
            0,
            1,
            1};
  }

  double direct_lo_f2(LHAPDF::PDF const& pdf, double const x, double const q)
  {
    const std::map<int, double> xfx = pdf.xfxQ(x, q);
    const auto density = [&xfx](int const pid) {
      const auto found = xfx.find(pid);
      return found == xfx.end() ? 0.0 : found->second;
    };

    double f2 = 0;
    for (int flavor = 1; flavor <= 5; ++flavor)
      {
        const double charge_squared = flavor == 2 || flavor == 4 ? 4.0 / 9.0
                                                                  : 1.0 / 9.0;
        f2 += charge_squared * (density(flavor) + density(-flavor));
      }
    return f2;
  }

  void test_invalid_protocol_requests()
  {
    nlohmann::json invalid_order{{"schema_version", 1},
                                 {"process", "nc_dis"},
                                 {"projectile", "electron"},
                                 {"target", "proton"},
                                 {"x", 0.01},
                                 {"q2", 100},
                                 {"order", "NNLO"},
                                 {"pdf_set", "CT18NLO"},
                                 {"pdf_member", 0},
                                 {"mu_f_over_q", 1},
                                 {"mu_r_over_q", 1}};
    try
      {
        static_cast<void>(neuronswquarks::apfel_backend::request_from_json(invalid_order));
        check(false, "NNLO request should be rejected");
      }
    catch (BackendError const& error)
      {
        check(error.code() == "unsupported_order", "invalid order error code");
      }

    invalid_order["order"] = "LO";
    invalid_order["mu_f_over_q"] = 0;
    try
      {
        static_cast<void>(neuronswquarks::apfel_backend::request_from_json(invalid_order));
        check(false, "zero factorization scale should be rejected");
      }
    catch (BackendError const& error)
      {
        check(error.code() == "invalid_factorization_scale",
              "invalid factorization scale error code");
      }

    const nlohmann::json failure =
      neuronswquarks::apfel_backend::error_response("invalid_request",
                                                    "bad request",
                                                    "fix it");
    check(failure.at("schema_version") == 1 && !failure.at("success").get<bool>(),
          "failure response carries schema version and success=false");
    check(failure.at("error").at("code") == "invalid_request"
            && failure.at("error").at("hint") == "fix it",
          "failure response carries the structured error object");
  }
}

int main()
{
  using neuronswquarks::apfel_backend::evaluate;

  test_invalid_protocol_requests();
  if (failures != 0)
    return 1;

  LHAPDF::setVerbosity(0);
  std::unique_ptr<LHAPDF::PDF> pdf;
  try
    {
      pdf.reset(LHAPDF::mkPDF("CT18NLO", 0));
    }
  catch (std::exception const& error)
    {
      std::cerr << "SKIP: CT18NLO member 0 is unavailable: " << error.what() << '\n';
      return 77;
    }

  try
    {
      const StructureFunctionResult lo = evaluate(request(PerturbativeOrder::LO));
      check(std::isfinite(lo.f2) && std::isfinite(lo.fl) && std::isfinite(lo.xf3),
            "LO structure functions are finite");
      check(lo.f2 > 0, "LO F2 is positive");
      check(std::abs(lo.fl) <= 1e-12, "LO FL vanishes in the massless coefficient scheme");
      check(std::abs(lo.xf3) <= 1e-12, "pure-photon LO xF3 vanishes");

      const double direct = direct_lo_f2(*pdf, 0.01, 10);
      check(approximately_equal(lo.f2, direct, 1e-4),
            "APFEL++ LO F2 agrees with direct charge-weighted LHAPDF x*f");

      check(lo.metadata.apfelxx_version == "4.8.0", "APFEL++ version metadata");
      check(!lo.metadata.lhapdf_version.empty(), "LHAPDF version metadata");
      check(lo.metadata.pdf_set == "CT18NLO" && lo.metadata.pdf_member == 0,
            "PDF metadata");
      check(lo.metadata.pdf_order_qcd >= 1, "CT18NLO reports NLO OrderQCD");
      check(lo.metadata.data_version > 0, "PDF data-version metadata");
      check(lo.metadata.scheme == "ZM-VFNS", "scheme metadata");
      check(lo.metadata.electromagnetic_mode == "photon_exchange",
            "electromagnetic-mode metadata");

      const nlohmann::json serialized =
        neuronswquarks::apfel_backend::success_response(lo);
      check(serialized.at("metadata").at("backend") == "apfel",
            "wire metadata identifies the APFEL backend");
      check(serialized.at("metadata").at("pdf_data_version")
              == lo.metadata.data_version,
            "wire metadata exposes pdf_data_version");

      const StructureFunctionResult nlo = evaluate(request(PerturbativeOrder::NLO));
      check(std::isfinite(nlo.f2) && std::isfinite(nlo.fl) && std::isfinite(nlo.xf3),
            "NLO structure functions are finite");
      check(nlo.f2 > 0, "NLO F2 is positive");
      check(std::abs(nlo.fl) > 1e-10, "NLO FL contains a nonzero coefficient contribution");
      check(std::abs(nlo.xf3) <= 1e-12, "pure-photon NLO xF3 vanishes");
      check(std::abs(nlo.f2 - lo.f2) > 1e-10, "NLO and LO F2 differ");

      StructureFunctionRequest varied = request(PerturbativeOrder::NLO);
      varied.mu_f_over_q = 2;
      varied.mu_r_over_q = 0.5;
      const StructureFunctionResult scaled = evaluate(varied);
      check(std::isfinite(scaled.f2) && std::isfinite(scaled.fl),
            "scale-varied NLO result is finite");
      check(std::abs(scaled.f2 - nlo.f2) > 1e-10
              || std::abs(scaled.fl - nlo.fl) > 1e-10,
            "scale variation changes an NLO structure function");
      check(scaled.metadata.mu_f_over_q == 2
              && scaled.metadata.mu_r_over_q == 0.5,
            "scale metadata captures requested ratios");
    }
  catch (BackendError const& error)
    {
      std::cerr << "FAIL: backend error [" << error.code() << "]: "
                << error.what() << '\n';
      ++failures;
    }
  catch (std::exception const& error)
    {
      std::cerr << "FAIL: unexpected exception: " << error.what() << '\n';
      ++failures;
    }

  if (failures == 0)
    std::cerr << "All APFEL++ backend tests passed.\n";
  return failures == 0 ? 0 : 1;
}
