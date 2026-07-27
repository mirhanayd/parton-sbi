#include <LHAPDF/LHAPDF.h>

#include <cstddef>
#include <cstdio>
#include <exception>
#include <memory>
#include <stdexcept>
#include <string>

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
    if (error_buffer != nullptr && error_buffer_size > 0) {
      std::snprintf(error_buffer, error_buffer_size, "%s", error.what());
    }
    return 1;
  }
}
