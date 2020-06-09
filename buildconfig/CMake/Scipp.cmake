configure_file(
  ${CMAKE_SOURCE_DIR}/buildconfig/CMake/Scipp.in
  ${CMAKE_BINARY_DIR}/scipp-download/CMakeLists.txt
)

execute_process(
  COMMAND ${CMAKE_COMMAND} -G "${CMAKE_GENERATOR}" .
  WORKING_DIRECTORY ${CMAKE_BINARY_DIR}/scipp-download
  RESULTS_VARIABLE result
)
if(result)
  message(FATAL_ERROR "CMake step for scipp failed: ${result}")
endif()

execute_process(
  COMMAND ${CMAKE_COMMAND} --build .
  RESULT_VARIABLE result
  WORKING_DIRECTORY ${CMAKE_BINARY_DIR}/scipp-download
)
if(result)
  message(FATAL_ERROR "Build step for scipp failed: ${result}")
endif()

# Note will build is in Release mode
# Note will install to mantid build directory
execute_process(
	COMMAND ${CMAKE_COMMAND} -G${CMAKE_GENERATOR} -DCMAKE_INSTALL_PREFIX=${CMAKE_BINARY_DIR}/bin -DCMAKE_BUILD_TYPE=Release -DPYTHON_EXECUTABLE=${PYTHON_EXECUTABLE} "${CMAKE_BINARY_DIR}/scipp-src" 
  RESULT_VARIABLE result
  WORKING_DIRECTORY ${CMAKE_BINARY_DIR}/scipp-build
)
if(result)
  message(FATAL_ERROR "Build step for scipp failed: ${result}")
endif()

execute_process(
  COMMAND ${CMAKE_COMMAND} --build . --target install
  RESULT_VARIABLE result
  WORKING_DIRECTORY ${CMAKE_BINARY_DIR}/scipp-build
)
if(result)
  message(FATAL_ERROR "Install step for scipp failed: ${result}")
endif()
