#include <iostream>
#include "hello.h"
#include "bye.h"
#include "archconfig.h"
#include "archconfig_arch.h"

int main(){
    hello();
    bye();
    archconfig();
    std::cout << "archconfig: " << ARCHCONFIG_ARCH << std::endl;
}
