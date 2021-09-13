void DoubleBuffer::switch_emg_buffer()
{
  emg_buffer_sel_idx = (emg_buffer_sel_idx + 1) & 1;
  pemg_buffer_old = pemg_buffer;
  pemg_buffer = emg_buffer[emg_buffer_sel_idx];
  pcur = pemg_buffer;

  on_filling_complete(pemg_buffer_old);
}

DoubleBuffer::DoubleBuffer(int cnt):
  count(cnt),
  emg_buffer_sel_idx(0)
{
  for(int i = 0; i < 2; i++)
  {
    emg_buffer[i] = new unsigned short[count];
  }
  pemg_buffer_old = emg_buffer[(emg_buffer_sel_idx + 1) & 1];
  pemg_buffer = emg_buffer[emg_buffer_sel_idx];
  pcur = pemg_buffer;
}

DoubleBuffer::~DoubleBuffer()
{
  for(int i = 0; i < 2; i++)
  {
    delete [] emg_buffer[i];
  }
}

void DoubleBuffer::add(unsigned short v)
{
  *pcur++ = v;

  if(pcur - pemg_buffer == count)
  {
    switch_emg_buffer();
  }
}

unsigned short *DoubleBuffer::get_pemg_buffer_old() const
{
  return pemg_buffer_old;
}

void DoubleBuffer::onFillingComplete(CallbackFunction f)
{
    on_filling_complete = f;
}
