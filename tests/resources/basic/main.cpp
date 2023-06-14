#include "hello.h"
#include "bye.h"
#include <vector>
#include <string>
int main(){
    std::vector<std::string> vec;
    vec.push_back("consumer");
    
    hello();
    hello_print_vector(vec);
    bye();
    bye_print_vector(vec);
}
