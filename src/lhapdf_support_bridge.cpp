#include <LHAPDF/GridPDF.h>
#include <LHAPDF/LHAPDF.h>
#include <LHAPDF/Version.h>

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdio>
#include <exception>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

void copy_string(const std::string& value, char* buffer, std::size_t size) {
  if (buffer == nullptr || size == 0) {
    throw std::invalid_argument("invalid string buffer passed to LHAPDF bridge");
  }
  std::snprintf(buffer, size, "%s", value.c_str());
}

void report_error(const std::exception& error, char* buffer, std::size_t size) {
  if (buffer != nullptr && size > 0) {
    std::snprintf(buffer, size, "%s", error.what());
  }
}

}  // namespace

extern "C" int partonsbi_lhapdf_member_support(
    const char* set_name,
    int member,
    double* x_minimum,
    double* x_maximum,
    double* q_minimum_gev,
    double* q_maximum_gev,
    char* error_buffer,
    std::size_t error_buffer_size) {
  try {
    if (set_name == nullptr || x_minimum == nullptr || x_maximum == nullptr ||
        q_minimum_gev == nullptr || q_maximum_gev == nullptr) {
      throw std::invalid_argument("null pointer passed to LHAPDF support bridge");
    }
    LHAPDF::setVerbosity(0);
    std::unique_ptr<LHAPDF::PDF> pdf{LHAPDF::mkPDF(set_name, member)};
    *x_minimum = pdf->xMin();
    *x_maximum = pdf->xMax();
    *q_minimum_gev = pdf->qMin();
    *q_maximum_gev = pdf->qMax();
    return 0;
  } catch (const std::exception& error) {
    report_error(error, error_buffer, error_buffer_size);
    return 1;
  }
}

extern "C" int partonsbi_lhapdf_member_metadata(
    const char* set_name,
    int member,
    int* data_version,
    int* order_qcd,
    double* alpha_s_mz,
    double* charm_mass_gev,
    double* charm_threshold_gev,
    double* bottom_mass_gev,
    double* bottom_threshold_gev,
    double* top_mass_gev,
    double* top_threshold_gev,
    double* mz_gev,
    char* flavor_scheme,
    std::size_t flavor_scheme_size,
    char* lhapdf_version,
    std::size_t lhapdf_version_size,
    char* interpolation_policy,
    std::size_t interpolation_policy_size,
    char* extrapolator_policy,
    std::size_t extrapolator_policy_size,
    int* flavors,
    std::size_t flavor_capacity,
    std::size_t* flavor_count,
    double* x_knots,
    std::size_t x_knot_capacity,
    std::size_t* x_knot_count,
    double* q_knots,
    std::size_t q_knot_capacity,
    std::size_t* q_knot_count,
    char* error_buffer,
    std::size_t error_buffer_size) {
  try {
    if (set_name == nullptr || data_version == nullptr || order_qcd == nullptr ||
        alpha_s_mz == nullptr || charm_mass_gev == nullptr ||
        charm_threshold_gev == nullptr || bottom_mass_gev == nullptr ||
        bottom_threshold_gev == nullptr || top_mass_gev == nullptr ||
        top_threshold_gev == nullptr || mz_gev == nullptr || flavors == nullptr ||
        flavor_count == nullptr || x_knots == nullptr || x_knot_count == nullptr) {
      throw std::invalid_argument("null pointer passed to LHAPDF metadata bridge");
    }

    LHAPDF::setVerbosity(0);
    std::unique_ptr<LHAPDF::PDF> pdf{LHAPDF::mkPDF(set_name, member)};
    const auto* grid = dynamic_cast<const LHAPDF::GridPDF*>(pdf.get());
    if (grid == nullptr) {
      throw std::runtime_error("selected LHAPDF member is not a GridPDF");
    }

    const std::vector<int> member_flavors = pdf->flavors();
    const std::vector<double>& member_x_knots = grid->xKnots();
    const std::vector<double>& member_q2_knots = grid->q2Knots();
    if (member_flavors.size() > flavor_capacity) {
      throw std::runtime_error("flavor output buffer is too small");
    }
    if (member_x_knots.size() > x_knot_capacity) {
      throw std::runtime_error("x-knot output buffer is too small");
    }
    if (q_knots == nullptr || q_knot_count == nullptr) {
      throw std::invalid_argument("null Q-knot buffer passed to LHAPDF metadata bridge");
    }
    if (member_q2_knots.size() > q_knot_capacity) {
      throw std::runtime_error("Q-knot output buffer is too small");
    }

    *data_version = pdf->info().get_entry_as<int>("DataVersion");
    *order_qcd = pdf->orderQCD();
    *alpha_s_mz = pdf->info().get_entry_as<double>("AlphaS_MZ");
    *charm_mass_gev = pdf->quarkMass(4);
    *charm_threshold_gev = pdf->quarkThreshold(4);
    *bottom_mass_gev = pdf->quarkMass(5);
    *bottom_threshold_gev = pdf->quarkThreshold(5);
    *top_mass_gev = pdf->quarkMass(6);
    *top_threshold_gev = pdf->quarkThreshold(6);
    *mz_gev = pdf->info().get_entry_as<double>("MZ");
    copy_string(pdf->info().get_entry("FlavorScheme"), flavor_scheme,
                flavor_scheme_size);
    copy_string(LHAPDF::version(), lhapdf_version, lhapdf_version_size);
    copy_string(grid->interpolator().type(), interpolation_policy,
                interpolation_policy_size);
    copy_string(pdf->info().get_entry("Extrapolator"), extrapolator_policy,
                extrapolator_policy_size);

    std::copy(member_flavors.begin(), member_flavors.end(), flavors);
    std::copy(member_x_knots.begin(), member_x_knots.end(), x_knots);
    std::transform(member_q2_knots.begin(), member_q2_knots.end(), q_knots,
                   [](double q2) { return std::sqrt(q2); });
    *flavor_count = member_flavors.size();
    *x_knot_count = member_x_knots.size();
    *q_knot_count = member_q2_knots.size();
    return 0;
  } catch (const std::exception& error) {
    report_error(error, error_buffer, error_buffer_size);
    return 1;
  }
}
