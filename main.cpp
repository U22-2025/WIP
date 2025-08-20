#include <iostream>
#include <thread>

int main() {
    std::thread t([](){ std::cout << "Hello from thread!" << std::endl; });
    t.join();
    std::cout << "Hello from main!" << std::endl;
    return 0;
}
