#include <LHAPDF/LHAPDF.h>
#include <apfel/apfelxx.h>

#include <algorithm>
#include <array>
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
constexpr std::size_t kIndependentMomentStride = 29;

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

std::map<int, double> boundary_values_v2(
    LHAPDF::PDF& raw, double q0, double exported_xmin, double x,
    double delta_v, double sea_scale, double a_u, double a_d, double a_g) {
  if (x < exported_xmin) {
    std::map<int, double> zero;
    for (int id = -6; id <= 6; ++id) {
      zero[id] = 0;
    }
    zero[0] = 0;
    return zero;
  }
  return boundary_values(raw, q0, x, delta_v, sea_scale, a_u, a_d, a_g);
}

apfel::Grid computational_grid(double xmin, int node_multiplier) {
  if (node_multiplier != 1 && node_multiplier != 2) {
    throw std::invalid_argument("APFEL node multiplier must be one or two");
  }
  return apfel::Grid{
      {apfel::SubGrid{400 * node_multiplier, xmin, 3},
       apfel::SubGrid{250 * node_multiplier, 1e-1, 3},
       apfel::SubGrid{180 * node_multiplier, 6e-1, 3},
       apfel::SubGrid{160 * node_multiplier, 8.5e-1, 5}}};
}

std::pair<std::array<double, 64>, std::array<double, 64>>
gauss_legendre_64() {
  std::array<double, 64> nodes{};
  std::array<double, 64> weights{};
  constexpr double tolerance = 1e-15;
  constexpr double pi = 3.141592653589793238462643383279502884;
  for (int i = 0; i < 32; ++i) {
    double root = std::cos(pi * (i + 0.75) / 64.5);
    double derivative = 0;
    for (int iteration = 0; iteration < 128; ++iteration) {
      double p0 = 1;
      double p1 = root;
      for (int degree = 2; degree <= 64; ++degree) {
        const double p =
            ((2 * degree - 1) * root * p1 - (degree - 1) * p0) / degree;
        p0 = p1;
        p1 = p;
      }
      derivative = 64 * (root * p1 - p0) / (root * root - 1);
      const double next = root - p1 / derivative;
      if (std::abs(next - root) <= tolerance) {
        root = next;
        break;
      }
      root = next;
      if (iteration == 127) {
        throw std::runtime_error("GL64 node construction did not converge");
      }
    }
    const double weight = 2 / ((1 - root * root) * derivative * derivative);
    nodes[i] = -root;
    nodes[63 - i] = root;
    weights[i] = weight;
    weights[63 - i] = weight;
  }
  return {nodes, weights};
}

std::array<double, 14> independent_moments(
    const std::map<int, apfel::Distribution>& physical, double xmin,
    double xmax) {
  if (!(xmin > 0 && xmin < xmax && xmax <= 1)) {
    throw std::invalid_argument("invalid independent-moment support");
  }
  static const auto rule = gauss_legendre_64();
  std::array<double, 14> result{};
  constexpr int panels = 64;
  const double zmin = std::log(xmin);
  const double zmax = std::log(xmax);
  for (int panel = 0; panel < panels; ++panel) {
    const double left = zmin + (zmax - zmin) * panel / panels;
    const double right = zmin + (zmax - zmin) * (panel + 1) / panels;
    const double midpoint = (left + right) / 2;
    const double half_width = (right - left) / 2;
    for (std::size_t inode = 0; inode < rule.first.size(); ++inode) {
      const double z = midpoint + half_width * rule.first[inode];
      const double x = std::exp(z);
      const double jacobian_weight =
          half_width * rule.second[inode] * x;
      const double up = physical.at(2).Evaluate(x);
      const double antiup = physical.at(-2).Evaluate(x);
      const double down = physical.at(1).Evaluate(x);
      const double antidown = physical.at(-1).Evaluate(x);
      result[0] += jacobian_weight * (up - antiup) / x;
      result[1] += jacobian_weight * (down - antidown) / x;
      double total = 0;
      for (std::size_t flavor = 0; flavor < kFlavorCount; ++flavor) {
        const int id = kFlavors[flavor] == 21 ? 0 : kFlavors[flavor];
        const double contribution = physical.at(id).Evaluate(x);
        result[3 + flavor] += jacobian_weight * contribution;
        total += contribution;
      }
      result[2] += jacobian_weight * total;
    }
  }
  return result;
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

extern "C" int partonsbi_apfel_evolve_grid_v2(
    const char* raw_set, int raw_member, double q0, double alpha_s_mz,
    double mz, double qmax, double charm_mass, double charm_threshold,
    double bottom_mass, double bottom_threshold, double top_mass,
    double top_threshold, int order, double delta_v, double sea_scale,
    double a_u, double a_d, double a_g, double computational_xmin,
    double exported_xmin, int node_multiplier, int compute_moments, const double* xs,
    std::size_t nx, const double* qs, std::size_t nq, double* values,
    double* alphas, double* native_sum_rules, double* independent,
    char* error_buffer, std::size_t error_buffer_size) {
  try {
    validate_grid(xs, nx, qs, nq, values, alphas);
    if (compute_moments != 0 && compute_moments != 1) {
      throw std::invalid_argument("compute_moments must be zero or one");
    }
    if (compute_moments == 1 &&
        (native_sum_rules == nullptr || independent == nullptr)) {
      throw std::invalid_argument("v2 moment output buffers are required");
    }
    if (raw_set == nullptr || raw_member < 0 || order != 1) {
      throw std::invalid_argument("revised D1 requires a named NLO member");
    }
    if (!(computational_xmin == 1e-11 && exported_xmin == 1e-9) ||
        xs[0] < exported_xmin || xs[nx - 1] != 1 || qs[0] != q0) {
      throw std::invalid_argument(
          "revised D1 requires computational xmin=1e-11 and exported support [1e-9,1]");
    }

    apfel::SetVerbosityLevel(0);
    LHAPDF::setVerbosity(0);
    std::unique_ptr<LHAPDF::PDF> raw{LHAPDF::mkPDF(raw_set, raw_member)};
    const std::vector<double> masses =
        {0, 0, 0, charm_mass, bottom_mass, top_mass};
    const double inactive_top_threshold =
        std::nextafter(std::max(qmax, top_threshold), INFINITY);
    const std::vector<double> thresholds =
        {0, 0, 0, charm_threshold, bottom_threshold, inactive_top_threshold};
    apfel::AlphaQCD alpha{alpha_s_mz, mz, masses, thresholds, order};
    const auto alpha_function = [&alpha](double q) { return alpha.Evaluate(q); };
    const apfel::Grid grid =
        computational_grid(computational_xmin, node_multiplier);
    const auto input = [&](double x, double) {
      return apfel::PhysToQCDEv(boundary_values_v2(
          *raw, q0, exported_xmin, x, delta_v, sea_scale, a_u, a_d, a_g));
    };
    auto evolved = apfel::BuildDglap(
        apfel::InitializeDglapObjectsQCD(grid, thresholds), input, q0, order,
        alpha_function);

    for (std::size_t iq = 0; iq < nq; ++iq) {
      alphas[iq] = alpha.Evaluate(qs[iq]);
      const bool at_boundary = qs[iq] == q0;
      const std::map<int, apfel::Distribution> physical =
          apfel::QCDEvToPhys(evolved->Evaluate(qs[iq]).GetObjects());
      if (compute_moments == 1) {
        const auto inverse_x = [](double x) { return 1 / x; };
        native_sum_rules[3 * iq] =
            (inverse_x * (physical.at(2) - physical.at(-2)))
                .Integrate(computational_xmin, 1);
        native_sum_rules[3 * iq + 1] =
            (inverse_x * (physical.at(1) - physical.at(-1)))
                .Integrate(computational_xmin, 1);
        apfel::Distribution momentum = physical.at(0);
        for (int flavor = 1; flavor <= 5; ++flavor) {
          momentum = momentum + physical.at(flavor) + physical.at(-flavor);
        }
        native_sum_rules[3 * iq + 2] =
            momentum.Integrate(computational_xmin, 1);

        const auto full =
            independent_moments(physical, computational_xmin, 1);
        const auto retained = independent_moments(physical, exported_xmin, 1);
        double* target = independent + iq * kIndependentMomentStride;
        target[0] = full[0];
        target[1] = full[1];
        target[2] = full[2];
        target[3] = retained[0];
        target[4] = retained[1];
        target[5] = retained[2];
        target[6] = full[2] - retained[2];
        for (std::size_t flavor = 0; flavor < kFlavorCount; ++flavor) {
          target[7 + flavor] = full[3 + flavor];
          target[18 + flavor] = retained[3 + flavor];
        }
      }

      for (std::size_t ix = 0; ix < nx; ++ix) {
        const std::map<int, double> boundary =
            at_boundary
                ? boundary_values_v2(*raw, q0, exported_xmin, xs[ix],
                                     delta_v, sea_scale, a_u, a_d, a_g)
                : std::map<int, double>{};
        for (std::size_t flavor = 0; flavor < kFlavorCount; ++flavor) {
          const int id = kFlavors[flavor] == 21 ? 0 : kFlavors[flavor];
          const double value =
              at_boundary ? boundary.at(id) : physical.at(id).Evaluate(xs[ix]);
          if (!std::isfinite(value)) {
            throw std::runtime_error(
                "APFEL returned a non-finite revised-D1 density");
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

extern "C" int partonsbi_apfel_artifact_observables_v2(
    const char* raw_set, int raw_member, double q0, double alpha_s_mz,
    double mz, double qmax, double charm_mass, double charm_threshold,
    double bottom_mass, double bottom_threshold, double top_mass,
    double top_threshold, int order, double delta_v, double sea_scale,
    double a_u, double a_d, double a_g, double computational_xmin,
    double exported_xmin, int node_multiplier, const char* search_parent,
    const char* set_name, const double* xs, std::size_t nx, const double* qs,
    std::size_t nq, double* direct_values, double* artifact_values,
    char* error_buffer, std::size_t error_buffer_size) {
  try {
    if (raw_set == nullptr || search_parent == nullptr || set_name == nullptr ||
        xs == nullptr || qs == nullptr || direct_values == nullptr ||
        artifact_values == nullptr || nx == 0 || nq == 0 || order != 1) {
      throw std::invalid_argument("invalid revised-D1 observable buffers");
    }
    apfel::SetVerbosityLevel(0);
    LHAPDF::setVerbosity(0);
    LHAPDF::pathsPrepend(search_parent);
    std::unique_ptr<LHAPDF::PDF> raw{LHAPDF::mkPDF(raw_set, raw_member)};
    std::unique_ptr<LHAPDF::PDF> artifact{LHAPDF::mkPDF(set_name, 0)};
    const std::vector<double> masses =
        {0, 0, 0, charm_mass, bottom_mass, top_mass};
    const double inactive_top_threshold =
        std::nextafter(std::max(qmax, top_threshold), INFINITY);
    const std::vector<double> thresholds =
        {0, 0, 0, charm_threshold, bottom_threshold, inactive_top_threshold};
    apfel::AlphaQCD alpha{alpha_s_mz, mz, masses, thresholds, order};
    const auto direct_alpha = [&alpha](double q) { return alpha.Evaluate(q); };
    const auto artifact_alpha =
        [&artifact](double q) { return artifact->alphasQ(q); };
    const apfel::Grid evolution_grid =
        computational_grid(computational_xmin, node_multiplier);
    const double observable_xmin = std::min(1e-5, xs[0] / 10);
    if (!(observable_xmin > 0 && observable_xmin < 0.1)) {
      throw std::invalid_argument(
          "revised-D1 observable x values do not define a valid convolution "
          "grid");
    }
    const apfel::Grid observable_grid{
        {apfel::SubGrid{100, observable_xmin, 3},
         apfel::SubGrid{60, 1e-1, 3}, apfel::SubGrid{50, 6e-1, 3},
         apfel::SubGrid{50, 8e-1, 3}}};
    const auto input = [&](double x, double) {
      return apfel::PhysToQCDEv(boundary_values_v2(
          *raw, q0, exported_xmin, x, delta_v, sea_scale, a_u, a_d, a_g));
    };
    auto evolved = apfel::BuildDglap(
        apfel::InitializeDglapObjectsQCD(evolution_grid, thresholds), input,
        q0, order, direct_alpha);
    double direct_cache_q = -1;
    std::map<int, apfel::Distribution> direct_cache;
    auto direct_pdfs = [&evolved, &direct_cache_q,
                        &direct_cache](double x, double q) {
      if (q != direct_cache_q) {
        direct_cache = evolved->Evaluate(q).GetObjects();
        direct_cache_q = q;
      }
      std::map<int, double> result;
      for (const auto& item : direct_cache) {
        result[item.first] = item.second.Evaluate(x);
      }
      return result;
    };
    const auto artifact_pdfs = [&artifact](double x, double q) {
      std::map<int, double> physical;
      for (int id = -6; id <= 6; ++id) {
        physical[id] = artifact->xfxQ(id, x, q);
      }
      physical[0] = artifact->xfxQ(21, x, q);
      return apfel::PhysToQCDEv(physical);
    };
    const auto charges = [](double) {
      return std::vector<double>{1.0 / 9, 4.0 / 9, 1.0 / 9,
                                 4.0 / 9, 1.0 / 9, 4.0 / 9};
    };
    const auto f2_objects =
        apfel::InitializeF2NCObjectsZM(observable_grid, thresholds);
    const auto fl_objects =
        apfel::InitializeFLNCObjectsZM(observable_grid, thresholds);
    const auto direct_f2 = apfel::BuildStructureFunctions(
        f2_objects, direct_pdfs, order, direct_alpha, charges);
    const auto direct_fl = apfel::BuildStructureFunctions(
        fl_objects, direct_pdfs, order, direct_alpha, charges);
    const auto artifact_f2 = apfel::BuildStructureFunctions(
        f2_objects, artifact_pdfs, order, artifact_alpha, charges);
    const auto artifact_fl = apfel::BuildStructureFunctions(
        fl_objects, artifact_pdfs, order, artifact_alpha, charges);
    for (std::size_t iq = 0; iq < nq; ++iq) {
      const auto direct_f2_q = direct_f2.at(0).Evaluate(qs[iq]);
      const auto direct_fl_q = direct_fl.at(0).Evaluate(qs[iq]);
      const auto artifact_f2_q = artifact_f2.at(0).Evaluate(qs[iq]);
      const auto artifact_fl_q = artifact_fl.at(0).Evaluate(qs[iq]);
      for (std::size_t ix = 0; ix < nx; ++ix) {
        const std::size_t index = 2 * (iq * nx + ix);
        direct_values[index] = direct_f2_q.Evaluate(xs[ix]);
        direct_values[index + 1] = direct_fl_q.Evaluate(xs[ix]);
        artifact_values[index] = artifact_f2_q.Evaluate(xs[ix]);
        artifact_values[index + 1] = artifact_fl_q.Evaluate(xs[ix]);
        for (double value :
             {direct_values[index], direct_values[index + 1],
              artifact_values[index], artifact_values[index + 1]}) {
          if (!std::isfinite(value)) {
            throw std::runtime_error(
                "non-finite revised-D1 photon structure function");
          }
        }
      }
    }
    return 0;
  } catch (const std::exception& error) {
    report_error(error, error_buffer, error_buffer_size);
    return 1;
  }
}
