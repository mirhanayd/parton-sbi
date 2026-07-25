#include "pythia_dis_generator.hpp"
#include <nlohmann/json.hpp>
#include <iostream>
#include <iterator>
#include <string>
#include <fstream>
#include <sys/stat.h>

#ifdef _WIN32
#include <direct.h>
#define mkdir(dir, mode) _mkdir(dir)
#endif

int main(int argc, char* argv[])
{
  using namespace neuronswquarks::pythia_dis_generator;

  if (argc < 2)
    {
      std::cerr << "Usage: pythia_dis_cli <output_directory>\n";
      return 1;
    }
  std::string output_dir = argv[1];

  const std::string input{std::istreambuf_iterator<char>{std::cin},
                          std::istreambuf_iterator<char>{}};

  try
    {
      if (input.empty())
        throw GeneratorError{"invalid_json",
                             "No JSON request was provided on stdin.",
                             "Pipe one schema-version 1 JSON object to pythia_dis_cli.",
                             2};

      const nlohmann::json document = nlohmann::json::parse(input);
      const DisEventRequest request = request_from_json(document);

      // Create output directory if it doesn't exist
      #ifdef _WIN32
      _mkdir(output_dir.c_str());
      #else
      mkdir(output_dir.c_str(), 0777);
      #endif

      run_generator(request, output_dir);
      return 0;
    }
  catch (GeneratorError const& error)
    {
      nlohmann::json err_resp = error_response(error.code(), error.what(), error.hint());
      std::cerr << err_resp.dump() << '\n';

      // Write error json to summary.json if directory is valid and writable
      std::ofstream summary_file(output_dir + "/summary.json");
      if (summary_file.is_open())
        {
          summary_file << err_resp.dump(2) << '\n';
        }
      return error.exit_code();
    }
  catch (nlohmann::json::parse_error const& error)
    {
      nlohmann::json err_resp = error_response("invalid_json",
                                               "The stdin payload is not valid JSON: "
                                                 + std::string{error.what()},
                                               "Send exactly one valid JSON object.");
      std::cerr << err_resp.dump() << '\n';
      return 2;
    }
  catch (std::exception const& error)
    {
      nlohmann::json err_resp = error_response("internal_error",
                                               "Unexpected backend failure: "
                                                 + std::string{error.what()},
                                               "Inspect stdout/stderr logs and check native setup.");
      std::cerr << err_resp.dump() << '\n';
      return 4;
    }
}
