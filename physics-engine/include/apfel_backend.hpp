#pragma once

#include <nlohmann/json.hpp>

#include <stdexcept>
#include <string>

namespace neuronswquarks::apfel_backend
{
  inline constexpr int SchemaVersion = 1;

  enum class PerturbativeOrder: int
  {
    LO  = 0,
    NLO = 1,
  };

  struct StructureFunctionRequest
  {
    int                               schema_version = SchemaVersion;
    std::string                       process;
    std::string                       projectile;
    std::string                       target;
    double                            x = 0;
    double                            q2 = 0;
    PerturbativeOrder                 order = PerturbativeOrder::LO;
    std::string                       pdf_set;
    int                               pdf_member = 0;
    double                            mu_f_over_q = 1;
    double                            mu_r_over_q = 1;
    std::vector<int>                  pdf_members;
    std::vector<std::vector<double>>  scale_members;
  };

  struct StructureFunctionMetadata
  {
    std::string apfelxx_version;
    std::string lhapdf_version;
    std::string pdf_set;
    int         pdf_member = 0;
    int         pdf_order_qcd = 0;
    int         data_version = 0;
    std::string order;
    std::string process;
    std::string projectile;
    std::string target;
    double      mu_f_over_q = 1;
    double      mu_r_over_q = 1;
    std::string scheme;
    std::string electromagnetic_mode;
    std::string pdf_error_type;
    int         pdf_size = 0;
  };

  struct StructureFunctionResult
  {
    double                    f2 = 0;
    double                    fl = 0;
    double                    xf3 = 0;
    StructureFunctionMetadata metadata;
    std::vector<double>       f2_pdf_members;
    std::vector<double>       fl_pdf_members;
    std::vector<double>       f2_scale_members;
    std::vector<double>       fl_scale_members;
  };

  class BackendError: public std::runtime_error
  {
  public:
    BackendError(std::string code,
                 std::string message,
                 std::string hint,
                 int         exit_code);

    [[nodiscard]] std::string const& code() const noexcept;
    [[nodiscard]] std::string const& hint() const noexcept;
    [[nodiscard]] int                exit_code() const noexcept;

  private:
    std::string _code;
    std::string _hint;
    int         _exit_code;
  };

  [[nodiscard]] std::string order_name(PerturbativeOrder order);

  [[nodiscard]] StructureFunctionRequest request_from_json(nlohmann::json const& input);

  [[nodiscard]] StructureFunctionResult evaluate(StructureFunctionRequest const& request);

  [[nodiscard]] nlohmann::json success_response(StructureFunctionResult const& result);

  [[nodiscard]] nlohmann::json error_response(std::string const& code,
                                              std::string const& message,
                                              std::string const& hint);
}
