#include <LHAPDF/LHAPDF.h>
#include <apfel/apfelxx.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <exception>
#include <map>
#include <memory>
#include <mutex>
#include <limits>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

namespace {

constexpr int kFlavors[] = {-5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 21};
constexpr std::size_t kFlavorCount = sizeof(kFlavors) / sizeof(kFlavors[0]);
constexpr std::size_t kIndependentMomentStride = 29;

constexpr int kPersistentOk = 0;
constexpr int kPersistentInvalidArgument = 1;
constexpr int kPersistentInvalidHandle = 2;
constexpr int kPersistentUnsupportedFlavor = 3;
constexpr int kPersistentInactiveFlavor = 4;
constexpr int kPersistentOutsideSupport = 5;
constexpr int kPersistentNonFinite = 6;
constexpr int kPersistentCacheFailure = 7;

struct PersistentBridgeError final : public std::runtime_error {
  PersistentBridgeError(int code_in, const std::string& message)
      : std::runtime_error(message), code(code_in) {}
  int code;
};

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

struct PersistentApfelContext {
  std::string evaluator_policy_identity;
  std::string theta_transport_identity;
  std::string projected_boundary_identity;
  std::string raw_set;
  int raw_member = 0;
  double delta_v = 0;
  double sea_scale = 1;
  double a_u = 1;
  double a_d = 1;
  double a_g = 1;
  double x_min = 0;
  double x_max = 1;
  double q_min = 0;
  double q_max = 0;
  double charm_threshold = 0;
  double bottom_threshold = 0;

  // Declaration order is a lifetime contract. Destruction is reversed:
  // cached distributions, then Dglap, then AlphaQCD, then its Grid, then the
  // authoritative raw boundary member used for exact-Q0 queries.
  std::unique_ptr<LHAPDF::PDF> raw;
  std::unique_ptr<apfel::Grid> grid;
  std::unique_ptr<apfel::AlphaQCD> alpha;
  std::unique_ptr<apfel::Dglap<apfel::Distribution>> evolved;
  std::map<int, apfel::Distribution> exact_q_cache;
  bool cache_valid = false;
  std::uint64_t cached_q_bits = 0;

  std::uint64_t scalar_calls = 0;
  std::uint64_t batch_calls = 0;
  std::uint64_t batch_queries = 0;
  std::uint64_t alpha_s_calls = 0;
  std::uint64_t cache_hits = 0;
  std::uint64_t cache_misses = 0;
  std::uint64_t rejected_calls = 0;
};

// APFEL++/LHAPDF reentrancy is not established. This one boundary protects
// construction, lookup, evaluation, cache mutation, diagnostics, and
// destruction for every prototype context in the process.
// This recursive process boundary is also acquired by Rust before any D1C
// LHAPDF-backed boundary construction or fresh-reference APFEL call. Native
// persistent calls reacquire it on the same thread. The single acquisition
// order is: process boundary, then any Rust evaluator-instance mutex, then a
// nested native C ABI call.
std::recursive_mutex persistent_apfel_mutex;
std::unordered_map<std::uintptr_t, std::unique_ptr<PersistentApfelContext>>
    persistent_apfel_contexts;
std::uintptr_t next_persistent_handle = 1;

std::uintptr_t handle_key(void* handle) {
  return reinterpret_cast<std::uintptr_t>(handle);
}

PersistentApfelContext& lookup_persistent_context(void* handle) {
  const auto key = handle_key(handle);
  if (key == 0) {
    throw PersistentBridgeError(kPersistentInvalidHandle,
                                "persistent APFEL handle is null");
  }
  const auto found = persistent_apfel_contexts.find(key);
  if (found == persistent_apfel_contexts.end() || found->second == nullptr) {
    throw PersistentBridgeError(kPersistentInvalidHandle,
                                "persistent APFEL handle is invalid or destroyed");
  }
  return *found->second;
}

void validate_persistent_flavor(int flavor) {
  if (flavor == 6 || flavor == -6) {
    throw PersistentBridgeError(kPersistentInactiveFlavor,
                                "top is inactive in the five-flavor context");
  }
  if (flavor == 0 || (std::abs(flavor) > 5 && flavor != 21)) {
    throw PersistentBridgeError(kPersistentUnsupportedFlavor,
                                "unsupported persistent APFEL flavor");
  }
}

void validate_persistent_query(PersistentApfelContext& context, int flavor,
                               double x, double q) {
  validate_persistent_flavor(flavor);
  if (!std::isfinite(x) || !std::isfinite(q)) {
    throw PersistentBridgeError(kPersistentNonFinite,
                                "persistent APFEL query must be finite");
  }
  if (x < context.x_min || x > context.x_max || q < context.q_min ||
      q > context.q_max) {
    throw PersistentBridgeError(kPersistentOutsideSupport,
                                "persistent APFEL query is outside strict support");
  }
}

std::uint64_t binary64_bits(double value) {
  std::uint64_t bits = 0;
  static_assert(sizeof(bits) == sizeof(value), "binary64 size mismatch");
  std::memcpy(&bits, &value, sizeof(bits));
  return bits;
}

const std::map<int, apfel::Distribution>& evaluate_persistent_q(
    PersistentApfelContext& context, double q) {
  const auto bits = binary64_bits(q);
  if (context.cache_valid && context.cached_q_bits == bits) {
    ++context.cache_hits;
    return context.exact_q_cache;
  }
  ++context.cache_misses;
  try {
    context.exact_q_cache =
        apfel::QCDEvToPhys(context.evolved->Evaluate(q).GetObjects());
  } catch (const std::exception& error) {
    context.cache_valid = false;
    context.exact_q_cache.clear();
    throw PersistentBridgeError(
        kPersistentCacheFailure,
        std::string("persistent APFEL cache fill failed: ") + error.what());
  }
  context.cached_q_bits = bits;
  context.cache_valid = true;
  return context.exact_q_cache;
}

double persistent_xf(PersistentApfelContext& context, int flavor, double x,
                     double q) {
  validate_persistent_query(context, flavor, x, q);
  if (binary64_bits(q) == binary64_bits(context.q_min)) {
    const int boundary_id = flavor == 21 ? 0 : flavor;
    const auto boundary = boundary_values_v2(
        *context.raw, context.q_min, context.x_min, x, context.delta_v,
        context.sea_scale, context.a_u, context.a_d, context.a_g);
    const auto found = boundary.find(boundary_id);
    if (found == boundary.end()) {
      throw PersistentBridgeError(kPersistentUnsupportedFlavor,
                                  "D0R boundary flavor is unavailable");
    }
    if (!std::isfinite(found->second)) {
      throw PersistentBridgeError(
          kPersistentNonFinite,
          "persistent D0R boundary returned a non-finite value");
    }
    return found->second;
  }
  const auto& physical = evaluate_persistent_q(context, q);
  const int apfel_id = flavor == 21 ? 0 : flavor;
  const auto found = physical.find(apfel_id);
  if (found == physical.end()) {
    throw PersistentBridgeError(kPersistentUnsupportedFlavor,
                                "APFEL physical flavor is unavailable");
  }
  const double value = found->second.Evaluate(x);
  if (!std::isfinite(value)) {
    throw PersistentBridgeError(kPersistentNonFinite,
                                "persistent APFEL returned a non-finite value");
  }
  return value;
}

int threshold_side(const PersistentApfelContext& context, double q) {
  if (binary64_bits(q) == binary64_bits(context.charm_threshold)) {
    return -1;
  }
  if (binary64_bits(q) == binary64_bits(context.bottom_threshold)) {
    return 1;
  }
  if (q < context.charm_threshold) {
    return -2;
  }
  if (q < context.bottom_threshold) {
    return 0;
  }
  return 2;
}

void copy_persistent_string(const std::string& value, char* output,
                            std::size_t output_size) {
  if (output == nullptr || output_size == 0 || value.size() + 1 > output_size) {
    throw PersistentBridgeError(kPersistentInvalidArgument,
                                "persistent APFEL string buffer is too small");
  }
  std::snprintf(output, output_size, "%s", value.c_str());
}

int report_persistent_exception(char* error_buffer,
                                std::size_t error_buffer_size) {
  try {
    throw;
  } catch (const PersistentBridgeError& error) {
    report_error(error, error_buffer, error_buffer_size);
    return error.code;
  } catch (const std::exception& error) {
    report_error(error, error_buffer, error_buffer_size);
    return kPersistentInvalidArgument;
  }
}

}  // namespace

extern "C" int partonsbi_apfel_process_lock(char* error_buffer,
                                             std::size_t error_buffer_size) {
  try {
    persistent_apfel_mutex.lock();
    return kPersistentOk;
  } catch (const std::exception& error) {
    report_error(error, error_buffer, error_buffer_size);
    return kPersistentInvalidHandle;
  }
}

extern "C" int partonsbi_apfel_process_unlock(char* error_buffer,
                                               std::size_t error_buffer_size) {
  try {
    persistent_apfel_mutex.unlock();
    return kPersistentOk;
  } catch (const std::exception& error) {
    report_error(error, error_buffer, error_buffer_size);
    return kPersistentInvalidHandle;
  }
}

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

extern "C" int partonsbi_persistent_apfel_create(
    const char* raw_set, int raw_member, double q0, double alpha_s_mz,
    double mz, double qmax, double charm_mass, double charm_threshold,
    double bottom_mass, double bottom_threshold, double top_mass,
    double top_threshold, int order, double delta_v, double sea_scale,
    double a_u, double a_d, double a_g, double computational_xmin,
    double exported_xmin, double exported_xmax,
    const char* evaluator_policy_identity,
    const char* theta_transport_identity,
    const char* projected_boundary_identity, void** output_handle,
    char* error_buffer, std::size_t error_buffer_size) {
  try {
    std::lock_guard<std::recursive_mutex> lock(persistent_apfel_mutex);
    if (output_handle == nullptr) {
      throw PersistentBridgeError(kPersistentInvalidArgument,
                                  "persistent APFEL output handle is required");
    }
    *output_handle = nullptr;
    if (raw_set == nullptr || evaluator_policy_identity == nullptr ||
        theta_transport_identity == nullptr ||
        projected_boundary_identity == nullptr || raw_member < 0 ||
        order != 1) {
      throw PersistentBridgeError(kPersistentInvalidArgument,
                                  "persistent APFEL identity/configuration is invalid");
    }
    if (std::string(evaluator_policy_identity).empty() ||
        std::string(theta_transport_identity).empty() ||
        std::string(projected_boundary_identity).empty()) {
      throw PersistentBridgeError(kPersistentInvalidArgument,
                                  "persistent APFEL identities must be non-empty");
    }
    for (double value : {q0, alpha_s_mz, mz, qmax, charm_mass,
                         charm_threshold, bottom_mass, bottom_threshold,
                         top_mass, top_threshold, sea_scale, a_u, a_d, a_g,
                         computational_xmin, exported_xmin, exported_xmax}) {
      if (!std::isfinite(value) || value <= 0) {
        throw PersistentBridgeError(
            kPersistentInvalidArgument,
            "persistent APFEL metadata and normalizations must be positive");
      }
    }
    if (!std::isfinite(delta_v) || q0 > charm_threshold || q0 > qmax ||
        !(computational_xmin == 1e-11 && exported_xmin == 1e-9 &&
          exported_xmax == 1.0)) {
      throw PersistentBridgeError(
          kPersistentInvalidArgument,
          "persistent APFEL requires the accepted D0R/D1 support contract");
    }

    apfel::SetVerbosityLevel(0);
    LHAPDF::setVerbosity(0);
    auto context = std::make_unique<PersistentApfelContext>();
    context->evaluator_policy_identity = evaluator_policy_identity;
    context->theta_transport_identity = theta_transport_identity;
    context->projected_boundary_identity = projected_boundary_identity;
    context->raw_set = raw_set;
    context->raw_member = raw_member;
    context->delta_v = delta_v;
    context->sea_scale = sea_scale;
    context->a_u = a_u;
    context->a_d = a_d;
    context->a_g = a_g;
    context->x_min = exported_xmin;
    context->x_max = exported_xmax;
    context->q_min = q0;
    context->q_max = qmax;
    context->charm_threshold = charm_threshold;
    context->bottom_threshold = bottom_threshold;
    context->raw =
        std::unique_ptr<LHAPDF::PDF>{LHAPDF::mkPDF(raw_set, raw_member)};

    const std::vector<double> masses =
        {0, 0, 0, charm_mass, bottom_mass, top_mass};
    const double inactive_top_threshold =
        std::nextafter(std::max(qmax, top_threshold), INFINITY);
    const std::vector<double> thresholds =
        {0, 0, 0, charm_threshold, bottom_threshold,
         inactive_top_threshold};
    context->grid =
        std::make_unique<apfel::Grid>(computational_grid(computational_xmin, 1));
    context->alpha = std::make_unique<apfel::AlphaQCD>(
        alpha_s_mz, mz, masses, thresholds, order);
    apfel::AlphaQCD* alpha = context->alpha.get();
    const auto alpha_function = [alpha](double q) { return alpha->Evaluate(q); };
    // APFEL 4.8.0 BuildDglap materializes InDistFunc into DistributionMap
    // during this call; it does not store this input callback. Capture only
    // owned/pod values anyway, never the local `context` variable by reference.
    LHAPDF::PDF* raw_boundary = context->raw.get();
    const auto input = [raw_boundary, q0, exported_xmin, delta_v, sea_scale,
                        a_u, a_d, a_g](double x, double) {
      return apfel::PhysToQCDEv(boundary_values_v2(
          *raw_boundary, q0, exported_xmin, x, delta_v, sea_scale, a_u, a_d,
          a_g));
    };
    context->evolved = apfel::BuildDglap(
        apfel::InitializeDglapObjectsQCD(*context->grid, thresholds), input,
        q0, order, alpha_function);
    if (context->evolved == nullptr) {
      throw PersistentBridgeError(kPersistentInvalidArgument,
                                  "APFEL returned a null evolution context");
    }

    if (next_persistent_handle == 0) {
      throw PersistentBridgeError(kPersistentInvalidArgument,
                                  "persistent APFEL handle space exhausted");
    }
    const std::uintptr_t key = next_persistent_handle++;
    persistent_apfel_contexts.emplace(key, std::move(context));
    *output_handle = reinterpret_cast<void*>(key);
    return kPersistentOk;
  } catch (...) {
    return report_persistent_exception(error_buffer, error_buffer_size);
  }
}

extern "C" int partonsbi_persistent_apfel_destroy(
    void* handle, char* error_buffer, std::size_t error_buffer_size) {
  try {
    std::lock_guard<std::recursive_mutex> lock(persistent_apfel_mutex);
    const auto key = handle_key(handle);
    if (key == 0) {
      throw PersistentBridgeError(kPersistentInvalidHandle,
                                  "persistent APFEL handle is null");
    }
    auto found = persistent_apfel_contexts.find(key);
    if (found == persistent_apfel_contexts.end() || found->second == nullptr) {
      throw PersistentBridgeError(kPersistentInvalidHandle,
                                  "persistent APFEL handle is invalid or destroyed");
    }
    auto context = std::move(found->second);
    persistent_apfel_contexts.erase(found);
    context->cache_valid = false;
    context->exact_q_cache.clear();
    context->evolved.reset();
    context->alpha.reset();
    context->grid.reset();
    context->raw.reset();
    return kPersistentOk;
  } catch (...) {
    return report_persistent_exception(error_buffer, error_buffer_size);
  }
}

extern "C" int partonsbi_persistent_apfel_evaluate_scalar(
    void* handle, int flavor, double x, double q, double* output_value,
    int* output_threshold_side, char* error_buffer,
    std::size_t error_buffer_size) {
  try {
    std::lock_guard<std::recursive_mutex> lock(persistent_apfel_mutex);
    auto& context = lookup_persistent_context(handle);
    if (output_value == nullptr || output_threshold_side == nullptr) {
      throw PersistentBridgeError(kPersistentInvalidArgument,
                                  "persistent scalar outputs are required");
    }
    try {
      *output_value = persistent_xf(context, flavor, x, q);
    } catch (const PersistentBridgeError&) {
      ++context.rejected_calls;
      throw;
    }
    *output_threshold_side = threshold_side(context, q);
    ++context.scalar_calls;
    return kPersistentOk;
  } catch (...) {
    return report_persistent_exception(error_buffer, error_buffer_size);
  }
}

extern "C" int partonsbi_persistent_apfel_evaluate_batch(
    void* handle, const int* flavors, const double* xs, const double* qs,
    std::size_t count, double* output_values, int* output_threshold_sides,
    std::size_t* rejected_index, char* error_buffer,
    std::size_t error_buffer_size) {
  try {
    std::lock_guard<std::recursive_mutex> lock(persistent_apfel_mutex);
    auto& context = lookup_persistent_context(handle);
    if (rejected_index == nullptr ||
        (count > 0 &&
         (flavors == nullptr || xs == nullptr || qs == nullptr ||
          output_values == nullptr || output_threshold_sides == nullptr))) {
      throw PersistentBridgeError(kPersistentInvalidArgument,
                                  "persistent batch buffers are required");
    }
    *rejected_index = std::numeric_limits<std::size_t>::max();
    // Validate the whole batch before mutating cache or counters.
    for (std::size_t i = 0; i < count; ++i) {
      try {
        validate_persistent_query(context, flavors[i], xs[i], qs[i]);
      } catch (const PersistentBridgeError&) {
        *rejected_index = i;
        ++context.rejected_calls;
        throw;
      }
    }
    for (std::size_t i = 0; i < count; ++i) {
      try {
        output_values[i] = persistent_xf(context, flavors[i], xs[i], qs[i]);
      } catch (const PersistentBridgeError&) {
        *rejected_index = i;
        ++context.rejected_calls;
        throw;
      }
      output_threshold_sides[i] = threshold_side(context, qs[i]);
    }
    ++context.batch_calls;
    context.batch_queries += count;
    return kPersistentOk;
  } catch (...) {
    return report_persistent_exception(error_buffer, error_buffer_size);
  }
}

extern "C" int partonsbi_persistent_apfel_alpha_s(
    void* handle, double q, double* output_value, char* error_buffer,
    std::size_t error_buffer_size) {
  try {
    std::lock_guard<std::recursive_mutex> lock(persistent_apfel_mutex);
    auto& context = lookup_persistent_context(handle);
    if (output_value == nullptr || !std::isfinite(q)) {
      throw PersistentBridgeError(kPersistentInvalidArgument,
                                  "persistent alpha_s output/Q is invalid");
    }
    if (q < context.q_min || q > context.q_max) {
      throw PersistentBridgeError(kPersistentOutsideSupport,
                                  "persistent alpha_s Q is outside strict support");
    }
    const double value = context.alpha->Evaluate(q);
    if (!std::isfinite(value)) {
      throw PersistentBridgeError(kPersistentNonFinite,
                                  "persistent APFEL returned non-finite alpha_s");
    }
    *output_value = value;
    ++context.alpha_s_calls;
    return kPersistentOk;
  } catch (...) {
    return report_persistent_exception(error_buffer, error_buffer_size);
  }
}

extern "C" int partonsbi_persistent_apfel_identity(
    void* handle, int identity_kind, char* output, std::size_t output_size,
    char* error_buffer, std::size_t error_buffer_size) {
  try {
    std::lock_guard<std::recursive_mutex> lock(persistent_apfel_mutex);
    const auto& context = lookup_persistent_context(handle);
    if (identity_kind == 0) {
      copy_persistent_string(context.evaluator_policy_identity, output,
                             output_size);
    } else if (identity_kind == 1) {
      copy_persistent_string(context.theta_transport_identity, output,
                             output_size);
    } else if (identity_kind == 2) {
      copy_persistent_string(context.projected_boundary_identity, output,
                             output_size);
    } else {
      throw PersistentBridgeError(kPersistentInvalidArgument,
                                  "unknown persistent identity kind");
    }
    return kPersistentOk;
  } catch (...) {
    return report_persistent_exception(error_buffer, error_buffer_size);
  }
}

extern "C" int partonsbi_persistent_apfel_support(
    void* handle, double* x_min, double* x_max, double* q_min, double* q_max,
    double* charm_threshold, double* bottom_threshold, char* error_buffer,
    std::size_t error_buffer_size) {
  try {
    std::lock_guard<std::recursive_mutex> lock(persistent_apfel_mutex);
    const auto& context = lookup_persistent_context(handle);
    if (x_min == nullptr || x_max == nullptr || q_min == nullptr ||
        q_max == nullptr || charm_threshold == nullptr ||
        bottom_threshold == nullptr) {
      throw PersistentBridgeError(kPersistentInvalidArgument,
                                  "persistent support outputs are required");
    }
    *x_min = context.x_min;
    *x_max = context.x_max;
    *q_min = context.q_min;
    *q_max = context.q_max;
    *charm_threshold = context.charm_threshold;
    *bottom_threshold = context.bottom_threshold;
    return kPersistentOk;
  } catch (...) {
    return report_persistent_exception(error_buffer, error_buffer_size);
  }
}

extern "C" int partonsbi_persistent_apfel_diagnostics(
    void* handle, std::uint64_t* scalar_calls, std::uint64_t* batch_calls,
    std::uint64_t* batch_queries, std::uint64_t* alpha_s_calls,
    std::uint64_t* cache_hits, std::uint64_t* cache_misses,
    std::uint64_t* rejected_calls, char* error_buffer,
    std::size_t error_buffer_size) {
  try {
    std::lock_guard<std::recursive_mutex> lock(persistent_apfel_mutex);
    const auto& context = lookup_persistent_context(handle);
    if (scalar_calls == nullptr || batch_calls == nullptr ||
        batch_queries == nullptr || alpha_s_calls == nullptr ||
        cache_hits == nullptr || cache_misses == nullptr ||
        rejected_calls == nullptr) {
      throw PersistentBridgeError(kPersistentInvalidArgument,
                                  "persistent diagnostic outputs are required");
    }
    *scalar_calls = context.scalar_calls;
    *batch_calls = context.batch_calls;
    *batch_queries = context.batch_queries;
    *alpha_s_calls = context.alpha_s_calls;
    *cache_hits = context.cache_hits;
    *cache_misses = context.cache_misses;
    *rejected_calls = context.rejected_calls;
    return kPersistentOk;
  } catch (...) {
    return report_persistent_exception(error_buffer, error_buffer_size);
  }
}

extern "C" std::size_t partonsbi_persistent_apfel_live_contexts() {
  std::lock_guard<std::recursive_mutex> lock(persistent_apfel_mutex);
  return persistent_apfel_contexts.size();
}
