#include <LHAPDF/LHAPDF.h>
#include <apfel/apfelxx.h>

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdio>
#include <exception>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr int kFlavors[] = {-5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 21};
constexpr std::size_t kFlavorCount = sizeof(kFlavors) / sizeof(kFlavors[0]);

void report_error(const std::exception& error, char* buffer, std::size_t size) {
  if (buffer != nullptr && size > 0) {
    std::snprintf(buffer, size, "%s", error.what());
  }
}

void validate_grid(const double* xs, std::size_t nx, const double* qs,
                   std::size_t nq, double* values, double* alphas) {
  if (xs == nullptr || qs == nullptr || values == nullptr || alphas == nullptr ||
      nx < 2 || nq < 2) {
    throw std::invalid_argument("invalid APFEL evolution grid buffers");
  }
  for (std::size_t i = 0; i < nx; ++i) {
    if (!std::isfinite(xs[i]) || xs[i] <= 0 || xs[i] > 1 ||
        (i > 0 && xs[i - 1] >= xs[i])) {
      throw std::invalid_argument("x grid must be finite, ordered, and inside (0,1]");
    }
  }
  for (std::size_t i = 0; i < nq; ++i) {
    if (!std::isfinite(qs[i]) || qs[i] <= 0 ||
        (i > 0 && qs[i - 1] >= qs[i])) {
      throw std::invalid_argument("Q grid must be finite, positive, and ordered");
    }
  }
}

std::map<int, double> boundary_values(LHAPDF::PDF& raw, double q0, double x,
                                      double delta_v, double sea_scale,
                                      double a_u, double a_d, double a_g) {
  const double q2 = q0 * q0;
  const auto xf = [&](int id) { return raw.xfxQ2(id, x, q2); };
  const double tilt = std::pow(x / 0.1, delta_v);
  const double ubar = sea_scale * xf(-2);
  const double dbar = sea_scale * xf(-1);
  const double strange = sea_scale * xf(3);
  const double antistrange = sea_scale * xf(-3);
  std::map<int, double> physical;
  physical[-6] = 0;
  physical[-5] = 0;
  physical[-4] = 0;
  physical[-3] = antistrange;
  physical[-2] = ubar;
  physical[-1] = dbar;
  physical[0] = a_g * xf(21);
  physical[1] = a_d * (xf(1) - xf(-1)) * tilt + dbar;
  physical[2] = a_u * (xf(2) - xf(-2)) * tilt + ubar;
  physical[3] = strange;
  physical[4] = 0;
  physical[5] = 0;
  physical[6] = 0;
  return physical;
}

}  // namespace

extern "C" int partonsbi_apfel_evolve_grid(
    const char* raw_set, int raw_member, double q0, double alpha_s_mz,
    double mz, double qmax, double charm_mass, double charm_threshold, double bottom_mass,
    double bottom_threshold, double top_mass, double top_threshold, int order,
    double delta_v, double sea_scale, double a_u, double a_d, double a_g,
    const double* xs, std::size_t nx, const double* qs, std::size_t nq,
    double* values, double* alphas, double* sum_rules, char* error_buffer,
    std::size_t error_buffer_size) {
  try {
    validate_grid(xs, nx, qs, nq, values, alphas);
    if (sum_rules == nullptr) {
      throw std::invalid_argument("sum-rule output buffer is required");
    }
    if (raw_set == nullptr || raw_member < 0 || order != 1) {
      throw std::invalid_argument("D1 requires a named member and NLO order 1");
    }
    for (double value : {q0, alpha_s_mz, mz, qmax, charm_mass, charm_threshold,
                         bottom_mass, bottom_threshold, top_mass, top_threshold,
                         sea_scale, a_u, a_d, a_g}) {
      if (!std::isfinite(value) || value <= 0) {
        throw std::invalid_argument("APFEL metadata and normalizations must be positive");
      }
    }
    if (!std::isfinite(delta_v)) {
      throw std::invalid_argument("delta_v must be finite");
    }
    if (xs[0] < 1e-12 || xs[nx - 1] != 1.0 || qs[0] != q0) {
      throw std::invalid_argument("D1 grids must start at Q0 and end at x=1");
    }

    apfel::SetVerbosityLevel(0);
    LHAPDF::setVerbosity(0);
    std::unique_ptr<LHAPDF::PDF> raw{LHAPDF::mkPDF(raw_set, raw_member)};
    const std::vector<double> masses = {0, 0, 0, charm_mass, bottom_mass, top_mass};
    // CT18NLO declares NumFlavors=5. Keep the authoritative top metadata for
    // provenance, but place its evolution threshold strictly above artifact
    // support so no unrepresented top momentum is created.
    const double inactive_top_threshold =
        std::nextafter(std::max(qmax, top_threshold), INFINITY);
    const std::vector<double> thresholds =
        {0, 0, 0, charm_threshold, bottom_threshold, inactive_top_threshold};
    apfel::AlphaQCD alpha{alpha_s_mz, mz, masses, thresholds, order};
    const auto alpha_function = [&alpha](double q) { return alpha.Evaluate(q); };

    const double xmin = xs[0];
    const apfel::Grid grid{{apfel::SubGrid{400, xmin, 3},
                            apfel::SubGrid{250, 1e-1, 3},
                            apfel::SubGrid{180, 6e-1, 3},
                            apfel::SubGrid{160, 8.5e-1, 5}}};
    const auto input = [&](double x, double) {
      return apfel::PhysToQCDEv(boundary_values(*raw, q0, x, delta_v,
                                                sea_scale, a_u, a_d, a_g));
    };
    auto evolved = apfel::BuildDglap(
        apfel::InitializeDglapObjectsQCD(grid, thresholds), input, q0, order,
        alpha_function);

    for (std::size_t iq = 0; iq < nq; ++iq) {
      alphas[iq] = alpha.Evaluate(qs[iq]);
      const bool at_boundary = qs[iq] == q0;
      std::map<int, apfel::Distribution> physical;
      physical = apfel::QCDEvToPhys(evolved->Evaluate(qs[iq]).GetObjects());
      const auto inverse_x = [](double x) { return 1 / x; };
      sum_rules[3 * iq] =
          (inverse_x * (physical.at(2) - physical.at(-2))).Integrate(xs[0], 1);
      sum_rules[3 * iq + 1] =
          (inverse_x * (physical.at(1) - physical.at(-1))).Integrate(xs[0], 1);
      apfel::Distribution momentum = physical.at(0);
      for (int flavor = 1; flavor <= 5; ++flavor) {
        momentum = momentum + physical.at(flavor) + physical.at(-flavor);
      }
      sum_rules[3 * iq + 2] = momentum.Integrate(xs[0], 1);
      for (std::size_t ix = 0; ix < nx; ++ix) {
        const std::map<int, double> boundary =
            at_boundary
                ? boundary_values(*raw, q0, xs[ix], delta_v, sea_scale, a_u,
                                  a_d, a_g)
                : std::map<int, double>{};
        for (std::size_t flavor = 0; flavor < kFlavorCount; ++flavor) {
          const int id = kFlavors[flavor] == 21 ? 0 : kFlavors[flavor];
          const double value =
              at_boundary ? boundary.at(id) : physical.at(id).Evaluate(xs[ix]);
          if (!std::isfinite(value)) {
            throw std::runtime_error("APFEL returned a non-finite evolved density");
          }
          values[(iq * nx + ix) * kFlavorCount + flavor] = value;
        }
      }
    }
    return 0;
  } catch (const std::exception& error) {
    report_error(error, error_buffer, error_buffer_size);
    return 1;
  }
}

extern "C" int partonsbi_lhapdf_artifact_evaluate(
    const char* search_parent, const char* set_name, const double* xs,
    std::size_t nx, const double* qs, std::size_t nq, double* values,
    double* alphas, char* error_buffer, std::size_t error_buffer_size) {
  try {
    validate_grid(xs, nx, qs, nq, values, alphas);
    if (search_parent == nullptr || set_name == nullptr) {
      throw std::invalid_argument("artifact path and set name are required");
    }
    LHAPDF::setVerbosity(0);
    LHAPDF::pathsPrepend(search_parent);
    std::unique_ptr<LHAPDF::PDF> pdf{LHAPDF::mkPDF(set_name, 0)};
    for (std::size_t iq = 0; iq < nq; ++iq) {
      if (!pdf->inRangeQ(qs[iq])) {
        throw std::out_of_range("artifact Q request is outside strict support");
      }
      alphas[iq] = pdf->alphasQ(qs[iq]);
      for (std::size_t ix = 0; ix < nx; ++ix) {
        if (!pdf->inRangeX(xs[ix])) {
          throw std::out_of_range("artifact x request is outside strict support");
        }
        for (std::size_t flavor = 0; flavor < kFlavorCount; ++flavor) {
          values[(iq * nx + ix) * kFlavorCount + flavor] =
              pdf->xfxQ(kFlavors[flavor], xs[ix], qs[iq]);
        }
      }
    }
    return 0;
  } catch (const std::exception& error) {
    report_error(error, error_buffer, error_buffer_size);
    return 1;
  }
}
