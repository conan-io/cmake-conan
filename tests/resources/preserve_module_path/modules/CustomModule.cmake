
message(STATUS "Loaded custom module")

macro(hello_world)
    message(WARNING "We should be seeing this warning, if we do the test works")
endmacro()