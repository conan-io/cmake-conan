#include "fmt/color.h"

int main() {
    fmt::print(fg(fmt::terminal_color::cyan), "Hello fmt {}!\n", FMT_VERSION );
    return 0;
}
