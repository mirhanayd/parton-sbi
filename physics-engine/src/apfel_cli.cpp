#include "apfel_backend.hpp"

#include <nlohmann/json.hpp>

#include <iostream>
#include <iterator>
#include <string>

int main()
{
  using namespace neuronswquarks::apfel_backend;

  const std::string input{std::istreambuf_iterator<char>{std::cin},
                          std::istreambuf_iterator<char>{}};

  try
    {
      if (input.empty())
        throw BackendError{"invalid_json",
                           "No JSON request was provided on stdin.",
                           "Pipe one schema-version 1 JSON object to apfel_cli.",
                           2};

      const nlohmann::json document = nlohmann::json::parse(input);
      const StructureFunctionRequest request = request_from_json(document);
      const StructureFunctionResult result = evaluate(request);
      std::cout << success_response(result).dump() << '\n';
      return 0;
    }
  catch (BackendError const& error)
    {
      std::cout << error_response(error.code(), error.what(), error.hint()).dump() << '\n';
      return error.exit_code();
    }
  catch (nlohmann::json::parse_error const& error)
    {
      std::cout << error_response("invalid_json",
                                  "The stdin payload is not valid JSON: "
                                    + std::string{error.what()},
                                  "Send exactly one valid JSON object.")
                     .dump()
                << '\n';
      return 2;
    }
  catch (std::exception const& error)
    {
      std::cout << error_response("internal_error",
                                  "Unexpected backend failure: "
                                    + std::string{error.what()},
                                  "Inspect stderr and verify the native backend installation.")
                     .dump()
                << '\n';
      return 4;
    }
}
