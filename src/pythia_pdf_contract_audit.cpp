#include "Pythia8/PartonDistributions.h"
#include "Pythia8/Pythia.h"

#include <algorithm>
#include <cstddef>
#include <cstring>
#include <memory>
#include <stdexcept>
#include <string>

namespace {

void write_error(char* buffer, std::size_t size, const std::string& message) {
  if (buffer == nullptr || size == 0) return;
  const std::size_t copied = std::min(size - 1, message.size());
  std::memcpy(buffer, message.data(), copied);
  buffer[copied] = '\0';
}

class SignedPdfContractProbe final : public Pythia8::PDF {
public:
  SignedPdfContractProbe() : Pythia8::PDF(2212) {}

  double raw_inclusive(int id, double x, double q2) {
    xfUpdate(id, x, q2);
    return xfRaw(id);
  }

  double raw_valence(int id, double x, double q2) {
    xfUpdate(id, x, q2);
    return xfRaw(id) - xfRaw(-id);
  }

  double raw_sea(int id, double x, double q2) {
    xfUpdate(id, x, q2);
    return xfRaw(-id);
  }

private:
  void xfUpdate(int, double, double) override {
    xg = -1.0;
    xu = -2.0;
    xubar = -0.5;
    xd = xdbar = xs = xsbar = xc = xcbar = xb = xbbar = 0.0;
  }
};

} // namespace

extern "C" int partonsbi_pythia_pdf_signed_boundary_audit(
    double* raw_inclusive, double* base_inclusive, double* raw_valence,
    double* base_valence, double* raw_sea, double* base_sea,
    int* pythia_version_integer, char* error_buffer,
    std::size_t error_buffer_size) {
  try {
    if (raw_inclusive == nullptr || base_inclusive == nullptr ||
        raw_valence == nullptr || base_valence == nullptr ||
        raw_sea == nullptr || base_sea == nullptr ||
        pythia_version_integer == nullptr) {
      write_error(error_buffer, error_buffer_size,
                  "signed-boundary audit received a null output pointer");
      return 1;
    }

    auto concrete = std::make_shared<SignedPdfContractProbe>();
    Pythia8::PDFPtr base = concrete;
    constexpr double x = 0.999;
    constexpr double q2 = 1.295 * 1.295;

    *raw_inclusive = concrete->raw_inclusive(21, x, q2);
    *base_inclusive = base->xf(21, x, q2);
    *raw_valence = concrete->raw_valence(2, x, q2);
    *base_valence = base->xfVal(2, x, q2);
    *raw_sea = concrete->raw_sea(2, x, q2);
    *base_sea = base->xfSea(2, x, q2);
    *pythia_version_integer = PYTHIA_VERSION_INTEGER;
    return 0;
  } catch (const std::exception& error) {
    write_error(error_buffer, error_buffer_size, error.what());
    return 2;
  } catch (...) {
    write_error(error_buffer, error_buffer_size,
                "unknown PYTHIA signed-boundary audit failure");
    return 3;
  }
}
