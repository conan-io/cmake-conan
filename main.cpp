#include "hello.h"

int main(){
    hello();
}

/*#include "Poco/Timer.h"
#include "Poco/Thread.h"
#include "Poco/Stopwatch.h"
#include <iostream>

using Poco::Timer;
using Poco::TimerCallback;
using Poco::Thread;
using Poco::Stopwatch;

class TimerExample{
public:
        TimerExample(){ _sw.start();}

        void onTimer(Timer& timer){
                std::cout << "Callback called after " << _sw.elapsed()/1000 << " milliseconds." << std::endl;
        }
private:
        Stopwatch _sw;
};

int main(int argc, char** argv){
        TimerExample example;
        Timer timer(250, 500);
        timer.start(TimerCallback<TimerExample>(example, &TimerExample::onTimer));

        Thread::sleep(1000);
        timer.stop();
        return 0;
}*/