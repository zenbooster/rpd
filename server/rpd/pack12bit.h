#pragma once

class Pack12bit
{
    typedef void (*CallbackFunction) (unsigned short);
    
    private:
        unsigned short ov; // old value
        unsigned short t;

        CallbackFunction on_produce = NULL;
    
    public:
        Pack12bit() {reset();};
    
        void push(unsigned short v);
        //void finalize();
        void reset();
        
        void onProduce(CallbackFunction f);
};
