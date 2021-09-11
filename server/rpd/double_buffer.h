#pragma once

class DoubleBuffer
{
  typedef void (*CallbackFunction) (unsigned short *pbuf);
  
  private:
    int count;
    int emg_buffer_sel_idx;
    unsigned short *pcur;
    unsigned short *emg_buffer[2];
    unsigned short *pemg_buffer;

    void switch_emg_buffer();

    CallbackFunction on_filling_complete = NULL;

  public:
    DoubleBuffer(int cnt);
    ~DoubleBuffer();

    void add(unsigned short v);

    void onFillingComplete(CallbackFunction f);
};
