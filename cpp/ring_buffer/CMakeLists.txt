cmake_minimum_required(VERSION 4.3.0)
project(RingBuffer)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# No main() yet, so build as an object library; switch to add_executable once one exists
add_library(RingBuffer OBJECT thread_unsafe_ring_buffer.cpp)
target_compile_options(RingBuffer PRIVATE -Wall -Wextra)
