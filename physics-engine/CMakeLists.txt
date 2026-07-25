cmake_minimum_required(VERSION 3.20)

project(neuronswquarks_apfel_backend VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(APFELXX_ROOT "" CACHE PATH "APFEL++ installation prefix")
if(NOT APFELXX_ROOT AND DEFINED ENV{APFELXX_ROOT})
  set(APFELXX_ROOT "$ENV{APFELXX_ROOT}")
endif()

set(NLOHMANN_JSON_INCLUDE_DIR "" CACHE PATH
    "Directory containing nlohmann/json.hpp")
if(NOT NLOHMANN_JSON_INCLUDE_DIR AND DEFINED ENV{NLOHMANN_JSON_INCLUDE_DIR})
  set(NLOHMANN_JSON_INCLUDE_DIR "$ENV{NLOHMANN_JSON_INCLUDE_DIR}")
endif()

find_program(APFELXX_CONFIG_EXECUTABLE
  NAMES apfelxx-config
  HINTS "${APFELXX_ROOT}/bin"
  REQUIRED)

execute_process(
  COMMAND "${APFELXX_CONFIG_EXECUTABLE}" --version
  RESULT_VARIABLE APFELXX_VERSION_RESULT
  OUTPUT_VARIABLE APFELXX_VERSION
  OUTPUT_STRIP_TRAILING_WHITESPACE)
if(NOT APFELXX_VERSION_RESULT EQUAL 0)
  message(FATAL_ERROR "apfelxx-config --version failed")
endif()
if(NOT APFELXX_VERSION STREQUAL "4.8.0")
  message(FATAL_ERROR
    "This backend is pinned to APFEL++ 4.8.0, found ${APFELXX_VERSION}")
endif()

execute_process(
  COMMAND "${APFELXX_CONFIG_EXECUTABLE}" --incdir
  RESULT_VARIABLE APFELXX_INCDIR_RESULT
  OUTPUT_VARIABLE APFELXX_INCDIR
  OUTPUT_STRIP_TRAILING_WHITESPACE)
execute_process(
  COMMAND "${APFELXX_CONFIG_EXECUTABLE}" --libdir
  RESULT_VARIABLE APFELXX_LIBDIR_RESULT
  OUTPUT_VARIABLE APFELXX_LIBDIR
  OUTPUT_STRIP_TRAILING_WHITESPACE)
if(NOT APFELXX_INCDIR_RESULT EQUAL 0 OR NOT APFELXX_LIBDIR_RESULT EQUAL 0)
  message(FATAL_ERROR "apfelxx-config could not report include/library directories")
endif()

find_path(APFELXX_INCLUDE_DIR
  NAMES apfel/apfelxx.h
  HINTS "${APFELXX_INCDIR}"
  REQUIRED)
find_library(APFELXX_LIBRARY
  NAMES apfelxx
  HINTS "${APFELXX_LIBDIR}"
  REQUIRED)

find_package(PkgConfig REQUIRED)
pkg_check_modules(LHAPDF REQUIRED IMPORTED_TARGET lhapdf>=6.5.6)

find_path(NLOHMANN_JSON_INCLUDE_DIR_RESOLVED
  NAMES nlohmann/json.hpp
  HINTS "${NLOHMANN_JSON_INCLUDE_DIR}"
  REQUIRED)

add_library(apfel_backend STATIC src/apfel_backend.cpp)
add_library(neuronswquarks::apfel_backend ALIAS apfel_backend)
target_include_directories(apfel_backend
  PUBLIC
    "${CMAKE_CURRENT_SOURCE_DIR}/include"
    "${NLOHMANN_JSON_INCLUDE_DIR_RESOLVED}"
  PRIVATE
    "${APFELXX_INCLUDE_DIR}")
target_link_libraries(apfel_backend
  PRIVATE
    "${APFELXX_LIBRARY}"
    PkgConfig::LHAPDF)

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(apfel_backend PRIVATE -Wall -Wextra -Wpedantic)
endif()

add_executable(apfel_cli src/apfel_cli.cpp)
target_link_libraries(apfel_cli PRIVATE apfel_backend)

set(APFEL_ENGINE_RPATH "${APFELXX_LIBDIR}")
list(APPEND APFEL_ENGINE_RPATH ${LHAPDF_LIBRARY_DIRS})
list(REMOVE_DUPLICATES APFEL_ENGINE_RPATH)
set_target_properties(apfel_cli PROPERTIES
  BUILD_RPATH "${APFEL_ENGINE_RPATH}"
  INSTALL_RPATH "${APFEL_ENGINE_RPATH}")

include(CTest)
if(BUILD_TESTING)
  add_executable(apfel_backend_test tests/apfel_backend_test.cpp)
  target_link_libraries(apfel_backend_test
    PRIVATE
      apfel_backend
      PkgConfig::LHAPDF)
  set_target_properties(apfel_backend_test PROPERTIES
    BUILD_RPATH "${APFEL_ENGINE_RPATH}")
  add_test(NAME apfel_backend_test COMMAND apfel_backend_test)
  set_tests_properties(apfel_backend_test PROPERTIES SKIP_RETURN_CODE 77)
endif()

# Find HepMC3 and PYTHIA 8
set(HEPMC3_ROOT "" CACHE PATH "HepMC3 installation prefix")
if(NOT HEPMC3_ROOT AND DEFINED ENV{HEPMC3_ROOT})
  set(HEPMC3_ROOT "$ENV{HEPMC3_ROOT}")
endif()

find_package(HepMC3 REQUIRED HINTS "${HEPMC3_ROOT}")

set(PYTHIA8_ROOT "" CACHE PATH "PYTHIA 8 installation prefix")
if(NOT PYTHIA8_ROOT AND DEFINED ENV{PYTHIA8_ROOT})
  set(PYTHIA8_ROOT "$ENV{PYTHIA8_ROOT}")
endif()

find_program(PYTHIA8_CONFIG_EXECUTABLE
  NAMES pythia8-config
  HINTS "${PYTHIA8_ROOT}/bin"
  REQUIRED)

execute_process(
  COMMAND "${PYTHIA8_CONFIG_EXECUTABLE}" --includedir
  RESULT_VARIABLE PYTHIA8_INCDIR_RESULT
  OUTPUT_VARIABLE PYTHIA8_INCDIR
  OUTPUT_STRIP_TRAILING_WHITESPACE)

execute_process(
  COMMAND "${PYTHIA8_CONFIG_EXECUTABLE}" --libdir
  RESULT_VARIABLE PYTHIA8_LIBDIR_RESULT
  OUTPUT_VARIABLE PYTHIA8_LIBDIR
  OUTPUT_STRIP_TRAILING_WHITESPACE)

find_path(PYTHIA8_INCLUDE_DIR
  NAMES Pythia8/Pythia.h
  HINTS "${PYTHIA8_INCDIR}"
  REQUIRED)

find_library(PYTHIA8_LIBRARY
  NAMES pythia8
  HINTS "${PYTHIA8_LIBDIR}"
  REQUIRED)

execute_process(
  COMMAND "${PYTHIA8_CONFIG_EXECUTABLE}" --version
  OUTPUT_VARIABLE PYTHIA8_VERSION
  OUTPUT_STRIP_TRAILING_WHITESPACE)

find_program(HEPMC3_CONFIG_EXECUTABLE
  NAMES hepmc3-config HepMC3-config
  HINTS "${HEPMC3_ROOT}/bin"
  REQUIRED)

execute_process(
  COMMAND "${HEPMC3_CONFIG_EXECUTABLE}" --version
  OUTPUT_VARIABLE HEPMC3_VERSION
  OUTPUT_STRIP_TRAILING_WHITESPACE)

find_package(Git QUIET)
if(GIT_FOUND)
  execute_process(
    COMMAND "${GIT_EXECUTABLE}" rev-parse HEAD
    WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
    OUTPUT_VARIABLE GIT_COMMIT
    OUTPUT_STRIP_TRAILING_WHITESPACE)
else()
  set(GIT_COMMIT "unknown")
endif()

string(TIMESTAMP BUILD_TIMESTAMP "%Y-%m-%dT%H:%M:%SZ" UTC)

add_library(pythia_dis_backend STATIC src/pythia_dis_generator.cpp)
target_include_directories(pythia_dis_backend
  PUBLIC
    "${CMAKE_CURRENT_SOURCE_DIR}/include"
    "${NLOHMANN_JSON_INCLUDE_DIR_RESOLVED}"
    "${HEPMC3_ROOT}/include"
  PRIVATE
    "${PYTHIA8_INCLUDE_DIR}")
target_link_libraries(pythia_dis_backend
  PRIVATE
    "${PYTHIA8_LIBRARY}"
    HepMC3::HepMC3
    PkgConfig::LHAPDF)

target_compile_definitions(pythia_dis_backend PRIVATE
  PYTHIA8_VERSION_STR="${PYTHIA8_VERSION}"
  HEPMC3_VERSION_STR="${HEPMC3_VERSION}"
  LHAPDF_VERSION_STR="${LHAPDF_VERSION}"
  GIT_COMMIT_STR="${GIT_COMMIT}"
  BUILD_TIMESTAMP_STR="${BUILD_TIMESTAMP}"
)

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(pythia_dis_backend PRIVATE -Wall -Wextra -Wpedantic)
endif()

add_executable(pythia_dis_cli src/pythia_dis_cli.cpp)
target_link_libraries(pythia_dis_cli PRIVATE pythia_dis_backend)

set(PYTHIA_ENGINE_RPATH "${PYTHIA8_LIBDIR}")
list(APPEND PYTHIA_ENGINE_RPATH "${HEPMC3_ROOT}/lib")
list(APPEND PYTHIA_ENGINE_RPATH "${HEPMC3_ROOT}/lib64")
list(APPEND PYTHIA_ENGINE_RPATH "${APFELXX_LIBDIR}")
list(APPEND PYTHIA_ENGINE_RPATH ${LHAPDF_LIBRARY_DIRS})
list(REMOVE_DUPLICATES PYTHIA_ENGINE_RPATH)
set_target_properties(pythia_dis_cli PROPERTIES
  BUILD_RPATH "${PYTHIA_ENGINE_RPATH}"
  INSTALL_RPATH "${PYTHIA_ENGINE_RPATH}")

install(TARGETS apfel_cli pythia_dis_cli RUNTIME DESTINATION bin)
install(FILES include/apfel_backend.hpp include/pythia_dis_generator.hpp DESTINATION include)

message(STATUS "APFEL++ version: ${APFELXX_VERSION}")
message(STATUS "APFEL++ library: ${APFELXX_LIBRARY}")
message(STATUS "LHAPDF version: ${LHAPDF_VERSION}")
message(STATUS "PYTHIA 8 version: ${PYTHIA8_VERSION}")
message(STATUS "HepMC3 version: ${HEPMC3_VERSION}")

