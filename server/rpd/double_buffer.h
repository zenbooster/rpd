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
    unsigned short *pemg_buffer_old;

    void switch_emg_buffer();

    CallbackFunction on_filling_complete = NULL;

  public:
    DoubleBuffer(int cnt);
    ~DoubleBuffer();

    void add(unsigned short v);
    unsigned short *get_pemg_buffer_old() const;

    void onFillingComplete(CallbackFunction f);
};
